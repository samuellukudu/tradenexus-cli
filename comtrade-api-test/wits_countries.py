"""Load and resolve WITS country codes (Trade Stats + TRAINS)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from xml.etree.ElementTree import Element

from wits_client import BASE_URL, WITS_NS, get_xml


@dataclass(frozen=True)
class WitsCountry:
    code: str
    iso3: str
    name: str
    is_reporter: bool
    is_partner: bool
    is_group: bool


def _parse_country(node: Element) -> WitsCountry:
    def flag(attr: str) -> bool:
        return (node.get(attr) or "").strip().lower() in {"1", "yes", "true"}

    return WitsCountry(
        code=(node.get("countrycode") or "").strip(),
        iso3=node.findtext(f"{{{WITS_NS}}}iso3Code", default="").strip(),
        name=node.findtext(f"{{{WITS_NS}}}name", default="").strip(),
        is_reporter=flag("isreporter"),
        is_partner=flag("ispartner"),
        is_group=flag("isgroup"),
    )


@lru_cache(maxsize=2)
def load_countries(datasource: str = "tradestats-trade") -> list[WitsCountry]:
    """datasource: tradestats-trade | trn (UNCTAD TRAINS metadata)."""
    url = f"{BASE_URL}/wits/datasource/{datasource}/country/ALL"
    root = get_xml(url)
    countries = [_parse_country(node) for node in root.findall(f".//{{{WITS_NS}}}country")]
    return sorted(countries, key=lambda c: c.name.lower())


def list_countries(*, reporters_only: bool = False, partners_only: bool = False) -> list[WitsCountry]:
    out = [c for c in load_countries() if not c.is_group]
    if reporters_only:
        out = [c for c in out if c.is_reporter]
    if partners_only:
        out = [c for c in out if c.is_partner]
    return out


def search_countries(query: str, *, limit: int = 20) -> list[WitsCountry]:
    q = query.strip().lower()
    if not q:
        return list_countries()[:limit]
    hits: list[tuple[int, WitsCountry]] = []
    for country in list_countries():
        hay = f"{country.name} {country.iso3} {country.code}".lower()
        if q in hay:
            rank = 0 if country.iso3.lower() == q or country.name.lower() == q else 1
            hits.append((rank, country))
    hits.sort(key=lambda x: (x[0], x[1].name))
    return [c for _, c in hits[:limit]]


def resolve_country(query: str) -> WitsCountry:
    raw = query.strip()
    if not raw:
        raise ValueError("Country cannot be empty.")

    upper = raw.upper()
    if len(upper) == 3 and upper.isalpha():
        hits = [c for c in list_countries() if c.iso3.upper() == upper]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(f"Ambiguous ISO3 {upper}: {[c.name for c in hits]}")

    if re.fullmatch(r"\d+", raw):
        hits = [c for c in list_countries() if c.code == raw]
        if len(hits) == 1:
            return hits[0]
        if hits:
            raise ValueError(f"Code {raw} matched a group or duplicate; use ISO3 or name.")

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


def pick_country(prompt: str) -> WitsCountry:
    while True:
        query = input(f"{prompt} (search name / ISO3 / code, or 'list'): ").strip()
        if not query:
            continue
        if query.lower() == "list":
            for i, country in enumerate(list_countries()[:40], start=1):
                print(f"  {i:3}. {country.name:<28} {country.iso3:3}  code={country.code}")
            print("  ... use search to narrow down")
            continue
        matches = search_countries(query, limit=15)
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
        choice = input("  Pick number (or Enter to search again): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            country = matches[int(choice) - 1]
            print(f"  → {country.name} ({country.iso3}, code {country.code})")
            return country
