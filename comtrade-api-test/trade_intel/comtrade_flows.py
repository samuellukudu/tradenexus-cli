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
