#!/usr/bin/env python3
"""Smoke tests for World Bank WITS public API (no API key)."""

from wits_countries import list_countries, resolve_country
from wits_query import fetch_data_availability, fetch_trade_value, format_trade_result


def main() -> None:
    countries = list_countries()
    print(f"=== 1. Countries loaded: {len(countries)} ===")
    ken = resolve_country("KEN")
    usa = resolve_country("USA")
    print(f"  {ken.name} code={ken.code}  {usa.name} code={usa.code}\n")

    print("=== 2. Trade Stats: Kenya → USA export value, 2020 ===")
    payload, spec = fetch_trade_value(ken, usa, year="2020", product="total")
    print(format_trade_result(payload, spec))
    print()

    print("=== 3. TRAINS data availability: USA, year 2000 ===")
    rows = fetch_data_availability(usa, year="2000")
    row = rows[0]
    print(f"  {row['name']} year={row['year']} partners={len(row['partner_list'].split(';'))}")
    print("\nDone. Use: python wits_cli.py -e KEN -i USA -y 2020")


if __name__ == "__main__":
    main()
