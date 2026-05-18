"""Load and resolve UN Comtrade country / reporter codes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import comtradeapicall
import pandas as pd


@dataclass(frozen=True)
class Country:
    code: int
    name: str
    iso2: str
    iso3: str


def _active_reporters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "isGroup" in out.columns:
        out = out[~out["isGroup"].fillna(False)]
    if "entryExpiredDate" in out.columns:
        out = out[out["entryExpiredDate"].isna()]
    return out.sort_values("text", kind="stable").reset_index(drop=True)


@lru_cache(maxsize=1)
def load_countries() -> list[Country]:
    df = _active_reporters(comtradeapicall.getReference("reporter"))
    countries: list[Country] = []
    for row in df.itertuples(index=False):
        code = int(row.reporterCode)
        iso2 = str(getattr(row, "reporterCodeIsoAlpha2", "") or "").strip()
        iso3 = str(getattr(row, "reporterCodeIsoAlpha3", "") or "").strip()
        name = str(getattr(row, "text", "") or getattr(row, "reporterDesc", "")).strip()
        countries.append(Country(code=code, name=name, iso2=iso2, iso3=iso3))
    return countries


def list_countries() -> list[Country]:
    return load_countries()


def search_countries(query: str, *, limit: int = 20) -> list[Country]:
    q = query.strip().lower()
    if not q:
        return list_countries()[:limit]

    matches: list[tuple[int, Country]] = []
    for country in list_countries():
        hay = f"{country.name} {country.iso2} {country.iso3} {country.code}".lower()
        if q in hay:
            rank = 0 if hay.startswith(q) or country.iso3.lower() == q or str(country.code) == q else 1
            matches.append((rank, country))
    matches.sort(key=lambda item: (item[0], item[1].name))
    return [country for _, country in matches[:limit]]


def resolve_country(query: str) -> Country:
    """Resolve a country by ISO3, ISO2, numeric code, or name (unique match required)."""
    raw = query.strip()
    if not raw:
        raise ValueError("Country cannot be empty.")

    if re.fullmatch(r"\d+", raw):
        code = int(raw)
        for country in list_countries():
            if country.code == code:
                return country
        raise ValueError(f"No country with Comtrade code {code}.")

    upper = raw.upper()
    if len(upper) == 3 and upper.isalpha():
        hits = [c for c in list_countries() if c.iso3.upper() == upper]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(f"Ambiguous ISO3 {upper}: {[c.name for c in hits]}")

    if len(upper) == 2 and upper.isalpha():
        hits = [c for c in list_countries() if c.iso2.upper() == upper]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(f"Ambiguous ISO2 {upper}: {[c.name for c in hits]}")

    hits = search_countries(raw, limit=50)
    exact = [c for c in hits if c.name.lower() == raw.lower()]
    if len(exact) == 1:
        return exact[0]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"No country matched '{query}'.")
    names = ", ".join(f"{c.name} ({c.iso3})" for c in hits[:8])
    raise ValueError(f"'{query}' is ambiguous. Matches: {names}")


def pick_country(prompt: str) -> Country:
    """Interactive search-and-select for one country."""
    while True:
        query = input(f"{prompt} (search name / ISO / code, or 'list'): ").strip()
        if not query:
            continue
        if query.lower() == "list":
            for i, country in enumerate(list_countries()[:40], start=1):
                print(f"  {i:3}. {country.name:<28} {country.iso3:3}  code={country.code}")
            print("  ... use search to narrow down")
            continue
        try:
            matches = search_countries(query, limit=15)
        except Exception as exc:
            print(f"  ! {exc}")
            continue
        if not matches:
            print("  No matches. Try another term.")
            continue
        if len(matches) == 1:
            country = matches[0]
            print(f"  → {country.name} ({country.iso3}, code {country.code})")
            return country
        print()
        for i, country in enumerate(matches, start=1):
            print(f"  {i:2}. {country.name:<28} {country.iso3:3}  code={country.code}")
        choice = input("  Pick number (or press Enter to search again): ").strip()
        if not choice:
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            country = matches[int(choice) - 1]
            print(f"  → {country.name} ({country.iso3}, code {country.code})")
            return country
        print("  Invalid choice.")
