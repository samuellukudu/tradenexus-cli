"""Map Comtrade partner numeric codes to ISO3 (for WITS alignment)."""

from __future__ import annotations

from functools import lru_cache

import comtradeapicall
import pandas as pd

from comtrade_countries import list_countries


@lru_cache(maxsize=1)
def _partner_table() -> pd.DataFrame:
    df = comtradeapicall.getReference("partner")
    if df is None or df.empty:
        return pd.DataFrame()
    return df


@lru_cache(maxsize=1)
def _valid_country_iso3() -> set[str]:
    return {country.iso3.upper() for country in list_countries() if country.iso3}


def partner_code_to_iso3(partner_code: int | str) -> str | None:
    code = str(int(partner_code)) if str(partner_code).strip().isdigit() else str(partner_code).strip()
    df = _partner_table()
    if df.empty or "PartnerCode" not in df.columns:
        return None
    row = df[df["PartnerCode"].astype(str) == code]
    if row.empty:
        return None
    iso3 = str(row.iloc[0].get("PartnerCodeIsoAlpha3", "") or "").strip()
    if not iso3 or len(iso3) != 3 or not iso3.isalpha():
        return None
    if row.iloc[0].get("isGroup", False):
        return None
    iso3 = iso3.upper()
    if iso3 not in _valid_country_iso3():
        return None
    return iso3


def partner_code_to_name(partner_code: int | str) -> str | None:
    code = str(int(partner_code)) if str(partner_code).strip().isdigit() else str(partner_code).strip()
    df = _partner_table()
    if df.empty:
        return None
    row = df[df["PartnerCode"].astype(str) == code]
    if row.empty:
        return None
    return str(row.iloc[0].get("PartnerDesc") or row.iloc[0].get("text") or "").strip() or None
