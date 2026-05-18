"""WITS Trade Stats annual time series via SDMX REST (one request, multiple years)."""

from __future__ import annotations

from typing import Any

from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle

from wits_client import BASE_URL, get_json


def _parse_sdmx_trade_timeseries(payload: dict[str, Any]) -> list[tuple[str, float]]:
    datasets = payload.get("dataSets") or []
    if not datasets:
        return []
    series = datasets[0].get("series") or {}
    if not series:
        return []
    first = next(iter(series.values()))
    observations = first.get("observations") or {}
    structure = payload.get("structure") or {}
    obs_dims = (structure.get("dimensions") or {}).get("observation") or []
    time_values: list[str] = []
    for dim in obs_dims:
        if dim.get("id") == "TIME_PERIOD":
            for v in dim.get("values") or []:
                time_values.append(str(v.get("id", "")))
            break
    out: list[tuple[str, float]] = []
    for i in range(len(time_values)):
        key = str(i)
        if key not in observations:
            continue
        val = float(observations[key][0])
        out.append((time_values[i], val))
    return out


def fetch_bilateral_export_series(
    export_iso3: str,
    import_iso3: str,
    year_from: int,
    year_to: int,
    *,
    product: str = "total",
    indicator: str = "XPRT-TRD-VL",
) -> list[tuple[str, float]]:
    """
    Annual export value (US$ thousand) from export_iso3 to import_iso3.

    Uses SDMX: FREQ=A, reporter=exporter, partner=importer.
    """
    e, p = export_iso3.upper(), import_iso3.upper()
    prod = product.lower()
    ind = indicator.upper()
    series_key = f"A.{e}.{p}.{prod}.{ind}"
    url = (
        f"{BASE_URL}/SDMX/V21/rest/data/DF_WITS_TradeStats_Trade/{series_key}/"
        f"?startperiod={year_from}&endperiod={year_to}&format=json"
    )
    key = make_key("wits_sdmx_trade", series=series_key, y0=year_from, y1=year_to)
    cached = cache_get(key)
    if cached is not None:
        return [(str(x["y"]), float(x["v"])) for x in cached]
    throttle()
    payload = get_json(url)
    series = _parse_sdmx_trade_timeseries(payload)
    if series:
        cache_set(key, [{"y": y, "v": v} for y, v in series])
    return series


def fetch_bilateral_import_series(
    export_iso3: str,
    import_iso3: str,
    year_from: int,
    year_to: int,
    *,
    product: str = "total",
    indicator: str = "MPRT-TRD-VL",
) -> list[tuple[str, float]]:
    """Annual import value (US$ thousand) into import_iso3 from export_iso3."""
    imp, exp = import_iso3.upper(), export_iso3.upper()
    prod = product.lower()
    ind = indicator.upper()
    series_key = f"A.{imp}.{exp}.{prod}.{ind}"
    url = (
        f"{BASE_URL}/SDMX/V21/rest/data/DF_WITS_TradeStats_Trade/{series_key}/"
        f"?startperiod={year_from}&endperiod={year_to}&format=json"
    )
    key = make_key("wits_sdmx_trade", series=series_key, y0=year_from, y1=year_to)
    cached = cache_get(key)
    if cached is not None:
        return [(str(x["y"]), float(x["v"])) for x in cached]
    throttle()
    payload = get_json(url)
    series = _parse_sdmx_trade_timeseries(payload)
    if series:
        cache_set(key, [{"y": y, "v": v} for y, v in series])
    return series
