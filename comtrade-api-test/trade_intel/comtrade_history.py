"""Comtrade annual history helpers for display-oriented UIs."""

from __future__ import annotations

import json
from datetime import date

import comtradeapicall
import pandas as pd

from comtrade_countries import Country, resolve_country
from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle


def latest_completed_annual_year() -> int:
    return date.today().year - 1


def recent_annual_years(*, count: int = 10, last_year: int | None = None) -> list[str]:
    end_year = last_year or latest_completed_annual_year()
    start_year = end_year - count + 1
    return [str(year) for year in range(end_year, start_year - 1, -1)]


def fetch_export_history(
    supplier: str | Country,
    *,
    year_from: int,
    year_to: int,
    cmd_code: str = "TOTAL",
) -> tuple[pd.DataFrame, Country]:
    """
    Annual export totals for one reporter to the world over a year range.

    The preview helper is used so the request can span multiple annual periods.
    """
    c = supplier if isinstance(supplier, Country) else resolve_country(supplier)
    key = make_key(
        "comtrade_export_history",
        reporter=str(c.code),
        y0=year_from,
        y1=year_to,
        cmd=cmd_code,
    )
    cached = cache_get(key)
    if cached is not None:
        return pd.DataFrame(cached), c

    periods = ",".join(str(year) for year in range(year_from, year_to + 1))
    throttle()
    df = comtradeapicall._previewFinalData(
        typeCode="C",
        freqCode="A",
        clCode="HS",
        period=periods,
        reporterCode=str(c.code),
        cmdCode=cmd_code,
        flowCode="X",
        partnerCode="0",
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=500,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    if df is None or df.empty or "period" not in df.columns or "primaryValue" not in df.columns:
        out = pd.DataFrame(columns=["period", "export_usd"])
        return out, c

    out = df.copy()
    out["period"] = out["period"].astype(str)
    out["primaryValue"] = pd.to_numeric(out["primaryValue"], errors="coerce")
    out = out.dropna(subset=["primaryValue"])
    out = (
        out.groupby("period", as_index=False)["primaryValue"]
        .sum()
        .rename(columns={"primaryValue": "export_usd"})
        .sort_values("period")
        .reset_index(drop=True)
    )
    records = json.loads(out.to_json(orient="records"))
    cache_set(key, records)
    return out, c
