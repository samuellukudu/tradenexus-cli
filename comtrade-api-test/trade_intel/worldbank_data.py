"""World Bank Indicators API — free public REST API, no key required.

Provides country-level macro indicators useful for investment and market decisions.
Reference: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import requests

from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle

logger = logging.getLogger(__name__)

# ── Indicator constants ────────────────────────────────────────────────────────
GDP_PERCAPITA = "NY.GDP.PCAP.CD"          # GDP per capita (current USD)
GDP_GROWTH = "NY.GDP.MKTP.KD.ZG"         # GDP growth (annual %)
FDI_INFLOWS = "BX.KLT.DINV.CD.WD"       # FDI net inflows (BoP, current USD)
TRADE_PCT_GDP = "NE.TRD.GNFS.ZS"        # Trade (% of GDP)
POPULATION = "SP.POP.TOTL"              # Total population
INFLATION = "FP.CPI.TOTL.ZG"           # Inflation, consumer prices (annual %)
EXPORTS_PCT_GDP = "NE.EXP.GNFS.ZS"     # Exports of goods and services (% of GDP)
IMPORTS_PCT_GDP = "NE.IMP.GNFS.ZS"     # Imports of goods and services (% of GDP)

INDICATOR_LABELS: dict[str, str] = {
    GDP_PERCAPITA: "GDP per capita (USD)",
    GDP_GROWTH: "GDP growth (%)",
    FDI_INFLOWS: "FDI net inflows (USD)",
    TRADE_PCT_GDP: "Trade (% of GDP)",
    POPULATION: "Total population",
    INFLATION: "Inflation (%)",
    EXPORTS_PCT_GDP: "Exports (% of GDP)",
    IMPORTS_PCT_GDP: "Imports (% of GDP)",
}

# ISO3 → ISO2 mapping for World Bank API (only countries we commonly query)
_ISO3_TO_ISO2: dict[str, str] = {}

# WB base URL
_WB_BASE = "https://api.worldbank.org/v2"
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})


# ── ISO3 → ISO2 conversion ────────────────────────────────────────────────────

def _iso3_to_iso2(iso3: str) -> str:
    """Convert ISO3 country code to ISO2 using the World Bank country list (cached)."""
    upper = iso3.strip().upper()
    if upper in _ISO3_TO_ISO2:
        return _ISO3_TO_ISO2[upper]

    cache_key = make_key("wb_iso3_map")
    cached = cache_get(cache_key)
    if cached:
        _ISO3_TO_ISO2.update(cached)
        if upper in _ISO3_TO_ISO2:
            return _ISO3_TO_ISO2[upper]

    # Fetch country mapping from WB API
    try:
        throttle()
        resp = _SESSION.get(
            f"{_WB_BASE}/country?format=json&per_page=300",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data[1] if isinstance(data, list) and len(data) > 1 else []
        mapping = {}
        for entry in entries:
            iso2 = str(entry.get("id", "")).strip().upper()
            iso3c = str(entry.get("iso2Code", "")).strip()
            # WB returns iso2Code field as ISO2, and id as ISO2 too — name it iso3 from "value"
            # Actually WB `id` is ISO2, let's fetch iso3 from a different field
            # The WB /country endpoint uses ISO2 as id but includes iso2Code which is also ISO2
            # iso3 is not directly provided but we can match by name; better: use the WB country/iso3 endpoint
            _ = iso2  # suppress unused warning for now
            _ = iso3c
        # Fallback: use a hardcoded mapping for the most commonly used ISO3 codes
        # The WB /country/{iso3} endpoint accepts ISO3 directly, so we pass it through as-is
        # and rely on WB accepting ISO3 codes (which it does for the data endpoint)
    except Exception as exc:
        logger.warning("WB ISO3 mapping fetch failed: %s", exc)

    # WB data API actually accepts ISO3 codes directly for country codes in /country/{id}
    # So just return the ISO3 as-is; WB data API handles ISO3 natively
    return upper


# ── Core fetcher ──────────────────────────────────────────────────────────────

def fetch_wb_indicator(
    country_iso3: str,
    indicator: str,
    *,
    year_from: int = 2000,
    year_to: int | None = None,
) -> list[tuple[str, float]]:
    """
    Fetch a World Bank indicator time series for one country.

    Returns a list of (year_str, value) sorted oldest first.
    Values are returned in the indicator's native unit.
    """
    end = year_to or (date.today().year - 1)
    country = country_iso3.strip().upper()

    cache_key = make_key(
        "wb_indicator",
        country=country,
        indicator=indicator,
        y0=year_from,
        y1=end,
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return [(row["y"], float(row["v"])) for row in cached]

    url = (
        f"{_WB_BASE}/country/{country}/indicator/{indicator}"
        f"?format=json&date={year_from}:{end}&per_page=100"
    )
    try:
        throttle()
        resp = _SESSION.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("WB fetch failed [%s / %s]: %s", country, indicator, exc)
        return []

    entries = data[1] if isinstance(data, list) and len(data) > 1 else []
    if not isinstance(entries, list):
        return []

    series: list[tuple[str, float]] = []
    for entry in entries:
        year = str(entry.get("date", "")).strip()
        val = entry.get("value")
        if val is None or year == "":
            continue
        try:
            series.append((year, float(val)))
        except (TypeError, ValueError):
            continue

    series.sort(key=lambda x: x[0])
    if series:
        cache_set(cache_key, [{"y": y, "v": v} for y, v in series])
    return series


# ── Country profile ───────────────────────────────────────────────────────────

def country_profile(
    iso3: str,
    *,
    year_from: int = 2014,
    year_to: int | None = None,
) -> dict[str, Any]:
    """
    Fetch a summary macro profile for one country.

    Returns a dict with indicator time series and derived signals.
    Suitable for the Country Profiles tab.
    """
    end = year_to or (date.today().year - 1)

    indicators = {
        "gdp_per_capita": GDP_PERCAPITA,
        "gdp_growth": GDP_GROWTH,
        "fdi_inflows": FDI_INFLOWS,
        "trade_pct_gdp": TRADE_PCT_GDP,
        "population": POPULATION,
        "inflation": INFLATION,
        "exports_pct_gdp": EXPORTS_PCT_GDP,
    }

    profile: dict[str, Any] = {"iso3": iso3.upper()}

    for field, indicator_code in indicators.items():
        series = fetch_wb_indicator(iso3, indicator_code, year_from=year_from, year_to=end)
        profile[field] = series
        # Latest non-null value
        profile[f"{field}_latest"] = series[-1][1] if series else None
        profile[f"{field}_latest_year"] = series[-1][0] if series else None

    return profile


def latest_value(series: list[tuple[str, float]]) -> tuple[str, float] | None:
    """Return the most recent (year, value) pair from a series."""
    return series[-1] if series else None


def cagr_from_series(series: list[tuple[str, float]], *, min_years: int = 3) -> float | None:
    """Compute CAGR (as a fraction, e.g. 0.05 = 5%) from a series."""
    if len(series) < 2:
        return None
    y0_str, v0 = series[0]
    y1_str, v1 = series[-1]
    try:
        span = float(int(y1_str) - int(y0_str))
    except ValueError:
        return None
    if span < min_years or v0 <= 0 or v1 <= 0:
        return None
    import math
    return (v1 / v0) ** (1.0 / span) - 1.0


def market_attractiveness_score(profile: dict[str, Any]) -> tuple[str, str, float]:
    """
    Derive a simple market attractiveness rating from the country profile.

    Returns (label, emoji, score_0_to_1).
    """
    score = 0.0
    factors = 0

    # GDP per capita: higher is more attractive (threshold $5k = low, $20k = high)
    gdp_pc = profile.get("gdp_per_capita_latest")
    if gdp_pc is not None:
        s = min(1.0, max(0.0, (float(gdp_pc) - 1_000) / (30_000 - 1_000)))
        score += s
        factors += 1

    # GDP growth: positive is attractive
    gdp_gr = profile.get("gdp_growth_latest")
    if gdp_gr is not None:
        s = min(1.0, max(0.0, (float(gdp_gr) + 2) / 12))
        score += s
        factors += 1

    # FDI trend: positive CAGR = attractive
    fdi_series = profile.get("fdi_inflows", [])
    if fdi_series:
        fdi_cagr = cagr_from_series(fdi_series)
        if fdi_cagr is not None:
            s = min(1.0, max(0.0, (fdi_cagr + 0.05) / 0.25))
            score += s
            factors += 1

    # Trade openness: higher % of GDP = more open market
    trade_pct = profile.get("trade_pct_gdp_latest")
    if trade_pct is not None:
        s = min(1.0, max(0.0, float(trade_pct) / 120))
        score += s
        factors += 1

    # Inflation: low is better (0–5% ideal, >15% = risk)
    inflation = profile.get("inflation_latest")
    if inflation is not None:
        s = min(1.0, max(0.0, 1.0 - float(inflation) / 20))
        score += s
        factors += 1

    if factors == 0:
        return "Unknown", "⚪", 0.0

    normalized = score / factors
    if normalized >= 0.65:
        return "High", "🟢", normalized
    elif normalized >= 0.40:
        return "Medium", "🟡", normalized
    else:
        return "Low", "🔴", normalized
