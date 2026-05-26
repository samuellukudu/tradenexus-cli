"""Shared Streamlit controls and small UI-oriented parsing helpers."""

from __future__ import annotations

from datetime import date

import streamlit as st

from comtrade_countries import Country, list_countries


@st.cache_data(ttl=86400, show_spinner="Loading country list…")
def all_countries() -> list[Country]:
    return sorted(
        [country for country in list_countries() if country.iso3],
        key=lambda country: country.name.lower(),
    )


def country_selectbox(
    label: str,
    *,
    default_iso3: str,
    key: str | None = None,
    help: str | None = None,
) -> str:
    countries = all_countries()
    labels = [f"{country.name} ({country.iso3})" for country in countries]
    iso_list = [country.iso3 for country in countries]
    try:
        default_idx = iso_list.index(default_iso3.upper())
    except ValueError:
        default_idx = 0
    choice = st.selectbox(
        label,
        options=labels,
        index=default_idx,
        key=key,
        help=help or "Pick by country name; ISO3 is filled automatically.",
    )
    return iso_list[labels.index(choice)]


def period_options(freq_code: str, *, annual_start: int = 2000, monthly_count: int = 36) -> list[str]:
    today = date.today()
    if freq_code == "M":
        year = today.year
        month = today.month - 1
        if month == 0:
            year -= 1
            month = 12
        options: list[str] = []
        for _ in range(monthly_count):
            options.append(f"{year}{month:02d}")
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        return options
    latest_year = max(annual_start, today.year - 1)
    return [str(year) for year in range(latest_year, annual_start - 1, -1)]


def period_selectbox(
    label: str,
    *,
    freq_code: str,
    default_period: str,
    key: str,
    help: str | None = None,
) -> str:
    options = period_options(freq_code)
    try:
        default_idx = options.index(default_period)
    except ValueError:
        default_idx = 0
    return st.selectbox(label, options=options, index=default_idx, key=key, help=help)


def imf_period_options(freq_code: str, *, years_back: int = 25) -> list[str]:
    today = date.today()
    freq = (freq_code or "").upper()
    if freq == "M":
        year, month = today.year, today.month
        options: list[str] = []
        for _ in range(years_back * 12):
            options.append(f"{year}-M{month:02d}")
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return options
    if freq == "Q":
        quarter = ((today.month - 1) // 3) + 1
        year = today.year
        options = []
        for _ in range(years_back * 4):
            options.append(f"{year}-Q{quarter}")
            quarter -= 1
            if quarter == 0:
                quarter = 4
                year -= 1
        return options
    if freq == "A":
        return [str(year) for year in range(today.year, today.year - years_back, -1)]
    return []


def imf_default_values(dim_id: str) -> list[str]:
    defaults = {
        "COUNTRY": ["USA", "CAN"],
        "INDEX_TYPE": ["CPI"],
        "COICOP_1999": ["CP01"],
        "TYPE_OF_TRANSFORMATION": ["IX"],
        "FREQUENCY": ["M"],
    }
    return defaults.get(dim_id, [])


def imf_option_label_map(options: list[dict[str, str]]) -> dict[str, str]:
    return {row["value"]: f"{row['value']} - {row['label']}" for row in options}


def parse_kv_lines(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise ValueError(f"Expected KEY=VALUE format, got: {raw}")
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Parameter name cannot be blank: {raw}")
        params[name] = value.strip()
    return params
