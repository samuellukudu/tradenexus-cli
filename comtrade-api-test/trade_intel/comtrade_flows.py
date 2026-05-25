"""Comtrade-based partner rankings for market discovery (public preview, capped at 500 rows)."""

from __future__ import annotations

import json

import comtradeapicall
import pandas as pd

from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle

from comtrade_countries import Country, resolve_country

_WORLD_LABELS = frozenset(
    {
        "world",
        "all",
        "europe",
        "asia",
        "americas",
        "africa",
        "oceania",
        "free zones",
        "unspecified",
    }
)


def _preview_by_flow(
    reporter: Country,
    *,
    flow_code: str,
    period: str,
    freq_code: str,
    cmd_code: str,
    max_records: int = 500,
) -> pd.DataFrame:
    key = make_key(
        "comtrade_preview",
        reporter=str(reporter.code),
        flow=flow_code,
        period=period,
        freq=freq_code,
        cmd=cmd_code,
        max=max_records,
    )
    cached = cache_get(key)
    if cached is not None:
        return pd.DataFrame(cached)
    throttle()
    df = comtradeapicall.previewFinalData(
        typeCode="C",
        freqCode=freq_code,
        clCode="HS",
        period=period,
        reporterCode=str(reporter.code),
        cmdCode=cmd_code,
        flowCode=flow_code,
        partnerCode=None,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=max_records,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    if df is not None and not df.empty:
        records = json.loads(df.to_json(orient="records", date_format="iso"))
        cache_set(key, records)
    return df


def _rank_partners(df: pd.DataFrame | None, *, top_n: int, exclude_world: bool) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if "partnerDesc" not in out.columns or "primaryValue" not in out.columns:
        return pd.DataFrame()
    out["primaryValue"] = pd.to_numeric(out["primaryValue"], errors="coerce")
    out = out.dropna(subset=["primaryValue"])
    if exclude_world and "partnerDesc" in out.columns:
        mask = out["partnerDesc"].str.strip().str.lower().isin(_WORLD_LABELS)
        if "partnerCode" in out.columns:
            mask = mask | (out["partnerCode"].astype(str) == "0")
        out = out[~mask]
    out = out.sort_values("primaryValue", ascending=False)
    cols = [c for c in ("partnerDesc", "partnerCode", "primaryValue", "period", "cmdDesc") if c in out.columns]
    return out[cols].head(top_n).reset_index(drop=True)


def top_export_destinations(
    supplier: str | Country,
    *,
    period: str,
    freq_code: str = "A",
    cmd_code: str = "TOTAL",
    top_n: int = 15,
    exclude_world: bool = True,
) -> tuple[pd.DataFrame, Country]:
    """
    Where does this country export to? (Comtrade: reporter = supplier, flow = exports.)

    Good for manufacturers / sales finding destination markets.
    """
    c = supplier if isinstance(supplier, Country) else resolve_country(supplier)
    df = _preview_by_flow(c, flow_code="X", period=period, freq_code=freq_code, cmd_code=cmd_code)
    ranked = _rank_partners(df, top_n=top_n, exclude_world=exclude_world)
    return ranked, c


def annual_export_destination_trends(
    supplier: str | Country,
    *,
    years: list[str],
    cmd_code: str = "TOTAL",
    top_n: int = 8,
    pool_n: int | None = None,
    exclude_world: bool = True,
) -> tuple[pd.DataFrame, Country]:
    """
    Annual destination history for the strongest partner markets across a window.

    This fetches annual top-destination snapshots year by year, then keeps the
    partners with the highest cumulative exports across the requested window.
    """
    c = supplier if isinstance(supplier, Country) else resolve_country(supplier)
    if not years:
        return pd.DataFrame(columns=["period", "partnerDesc", "partnerCode", "export_usd"]), c

    candidate_count = max(top_n, pool_n or top_n * 3)
    frames: list[pd.DataFrame] = []
    for year in sorted({str(year) for year in years}):
        yearly, _ = top_export_destinations(
            c,
            period=year,
            freq_code="A",
            cmd_code=cmd_code,
            top_n=candidate_count,
            exclude_world=exclude_world,
        )
        if yearly.empty:
            continue
        frame = yearly.copy()
        frame["period"] = frame["period"].astype(str) if "period" in frame.columns else year
        frame["primaryValue"] = pd.to_numeric(frame["primaryValue"], errors="coerce")
        frame = frame.dropna(subset=["primaryValue"])
        if frame.empty:
            continue
        frames.append(frame[["period", "partnerDesc", "partnerCode", "primaryValue"]])

    if not frames:
        return pd.DataFrame(columns=["period", "partnerDesc", "partnerCode", "export_usd"]), c

    out = pd.concat(frames, ignore_index=True)
    out = (
        out.groupby(["period", "partnerDesc", "partnerCode"], as_index=False)["primaryValue"]
        .sum()
        .sort_values(["period", "primaryValue"], ascending=[True, False])
    )
    totals = (
        out.groupby(["partnerDesc", "partnerCode"], as_index=False)["primaryValue"]
        .sum()
        .sort_values("primaryValue", ascending=False)
        .head(top_n)
    )
    out = out.merge(
        totals[["partnerDesc", "partnerCode"]],
        on=["partnerDesc", "partnerCode"],
        how="inner",
    )
    out = out.rename(columns={"primaryValue": "export_usd"}).reset_index(drop=True)
    return out, c


def top_import_sources(
    buyer: str | Country,
    *,
    period: str,
    freq_code: str = "A",
    cmd_code: str = "TOTAL",
    top_n: int = 15,
    exclude_world: bool = True,
) -> tuple[pd.DataFrame, Country]:
    """
    Where does this country import from? (Comtrade: reporter = buyer, flow = imports.)

    Good for procurement / sourcing.
    """
    c = buyer if isinstance(buyer, Country) else resolve_country(buyer)
    df = _preview_by_flow(c, flow_code="M", period=period, freq_code=freq_code, cmd_code=cmd_code)
    ranked = _rank_partners(df, top_n=top_n, exclude_world=exclude_world)
    return ranked, c
