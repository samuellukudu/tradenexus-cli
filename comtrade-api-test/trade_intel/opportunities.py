"""Exporter-focused opportunity scores: market size + growth (WITS), anchored on Comtrade partners."""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from trade_intel.analytics import cagr
from trade_intel.comtrade_flows import latest_available_period, top_export_destinations
from trade_intel.partner_codes import partner_code_to_iso3, partner_code_to_name
from trade_intel.wits_timeseries import fetch_bilateral_export_series

from comtrade_countries import Country, resolve_country

WITS_FULL_HISTORY_START_YEAR = 1988


def _growth_component(cagr_value: float | None) -> float:
    if cagr_value is None or math.isnan(cagr_value):
        return 0.5
    return max(0.0, min(1.0, (cagr_value + 0.08) / 0.28))


def _size_component(value: float, vmax: float) -> float:
    if vmax <= 0 or value <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log1p(value) / math.log1p(vmax)))


def _normalize_wits_window(year_from: int | None, year_to: int | None) -> tuple[int, int]:
    start_year = int(year_from) if year_from is not None else WITS_FULL_HISTORY_START_YEAR
    end_year = int(year_to) if year_to is not None else date.today().year
    if start_year > end_year:
        start_year, end_year = end_year, start_year
    return start_year, end_year


def _clean_series(series: list[tuple[str, float]]) -> list[tuple[int, float]]:
    cleaned: list[tuple[int, float]] = []
    for year, value in series:
        try:
            y = int(year)
            v = float(value)
        except (TypeError, ValueError):
            continue
        if math.isnan(v):
            continue
        cleaned.append((y, v))
    return sorted(cleaned, key=lambda item: item[0])


def rank_exporter_opportunities(
    supplier: str | Country,
    *,
    comtrade_period: str | None = None,
    comtrade_freq: str = "A",
    cmd_code: str = "TOTAL",
    pool_size: int = 25,
    score_count: int = 15,
    wits_year_from: int | None = None,
    wits_year_to: int | None = None,
    product: str = "total",
) -> tuple[pd.DataFrame, Country]:
    """
    For suppliers: take top Comtrade export destinations, enrich with WITS bilateral export CAGR.

    Opportunity score blends relative market size (latest WITS flow, US$ thousand) and growth.
    Pairs without WITS data are dropped from the scored table but are rare for major partners.
    """
    c = supplier if isinstance(supplier, Country) else resolve_country(supplier)
    resolved_period = comtrade_period
    if not resolved_period:
        resolved_period, _ = latest_available_period(c, freq_code=comtrade_freq, cmd_code=cmd_code, flow_code="X")
        if not resolved_period:
            empty = pd.DataFrame()
            empty.attrs.update(
                {
                    "comtrade_period": None,
                    "comtrade_freq": comtrade_freq,
                    "wits_year_from": None,
                    "wits_year_to": None,
                    "wits_window_mode": "full_available_history" if wits_year_from is None and wits_year_to is None else "custom_window",
                }
            )
            return empty, c

    requested_wits_year_from, requested_wits_year_to = _normalize_wits_window(wits_year_from, wits_year_to)
    window_mode = "full_available_history" if wits_year_from is None and wits_year_to is None else "custom_window"
    metadata = {
        "comtrade_period": resolved_period,
        "comtrade_freq": comtrade_freq,
        "wits_year_from": requested_wits_year_from,
        "wits_year_to": requested_wits_year_to,
        "wits_window_mode": window_mode,
    }

    ranked, _ = top_export_destinations(
        c,
        period=resolved_period,
        freq_code=comtrade_freq,
        cmd_code=cmd_code,
        top_n=pool_size,
    )
    if ranked.empty:
        ranked.attrs.update(metadata)
        return ranked, c

    rows: list[dict[str, object]] = []
    for _, r in ranked.iterrows():
        pcode = r.get("partnerCode")
        if pcode is not None and hasattr(pcode, "item"):
            try:
                pcode = pcode.item()
            except (ValueError, AttributeError):
                pass
        pname = str(r.get("partnerDesc", "") or "")
        iso3 = partner_code_to_iso3(pcode) if pcode is not None else None
        if not iso3:
            iso3 = None
        if iso3 == c.iso3:
            continue
        comtrade_usd = float(r["primaryValue"])
        if not iso3:
            rows.append(
                {
                    "partner": pname,
                    "partner_iso3": None,
                    "partner_code": pcode,
                    "comtrade_export_usd": comtrade_usd,
                    "wits_latest_year": None,
                    "wits_latest_kusd": None,
                    "cagr": None,
                    "opportunity": None,
                    "note": "no ISO3 mapping for partner code",
                }
            )
            continue
        try:
            raw_series = fetch_bilateral_export_series(
                c.iso3,
                iso3,
                requested_wits_year_from,
                requested_wits_year_to,
                product=product.lower(),
            )
        except RuntimeError as exc:
            rows.append(
                {
                    "partner": pname or partner_code_to_name(pcode) or iso3,
                    "partner_iso3": iso3,
                    "partner_code": pcode,
                    "comtrade_export_usd": comtrade_usd,
                    "wits_latest_year": None,
                    "wits_latest_kusd": None,
                    "cagr": None,
                    "opportunity": None,
                    "note": f"WITS lookup failed: {exc}",
                }
            )
            continue
        series = _clean_series(raw_series)
        if not series:
            rows.append(
                {
                    "partner": pname or partner_code_to_name(pcode) or iso3,
                    "partner_iso3": iso3,
                    "partner_code": pcode,
                    "comtrade_export_usd": comtrade_usd,
                    "wits_latest_year": None,
                    "wits_latest_kusd": None,
                    "cagr": None,
                    "opportunity": None,
                    "note": "insufficient WITS history",
                }
            )
            continue
        y0, v0 = series[0]
        y1, v1 = series[-1]
        span = float(int(y1) - int(y0))
        cg = cagr(v0, v1, span) if span > 0 and v0 > 0 and v1 > 0 else None
        rows.append(
            {
                "partner": pname or partner_code_to_name(pcode) or iso3,
                "partner_iso3": iso3,
                "partner_code": pcode,
                "comtrade_export_usd": comtrade_usd,
                "wits_start_year": y0,
                "wits_latest_year": y1,
                "wits_latest_kusd": v1,
                "wits_history_points": len(series),
                "cagr": cg,
                "opportunity": 0.0,
                "note": "",
            }
        )

    df = pd.DataFrame(rows)
    scored = df[df["wits_latest_kusd"].notna()].copy()
    if scored.empty:
        result = df.sort_values("comtrade_export_usd", ascending=False).head(score_count).reset_index(drop=True)
        result.attrs.update(metadata)
        return result, c

    vmax = float(scored["wits_latest_kusd"].max())
    scored["opportunity"] = [
        0.62 * _size_component(float(row["wits_latest_kusd"]), vmax)
        + 0.38 * _growth_component(row["cagr"] if row["cagr"] is not None else None)
        for _, row in scored.iterrows()
    ]
    result = scored.sort_values("opportunity", ascending=False).head(score_count).reset_index(drop=True)
    result.attrs.update(metadata)
    return result, c
