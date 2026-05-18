#!/usr/bin/env python3
"""Query World Bank WITS API with selectable export / import countries."""

from __future__ import annotations

import argparse
import sys

from wits_countries import list_countries, pick_country, resolve_country, search_countries
from wits_query import (
    fetch_data_availability,
    fetch_tariff,
    fetch_trade_value,
    format_trade_result,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="World Bank WITS API — bilateral trade and metadata.")
    p.add_argument("--export", "-e", help="Export country (name, ISO3, or WITS code)")
    p.add_argument("--import", "-i", dest="import_country", help="Import country")
    p.add_argument("--year", "-y", default="2020", help="Year (or 'all' for availability)")
    p.add_argument("--product", default="total", help="Product group (trade) or 6-digit HS (tariff)")
    p.add_argument(
        "--mode",
        choices=("trade", "availability", "tariff"),
        default="trade",
        help="trade=Trade Stats value; availability=TRAINS data availability; tariff=TRAINS tariff",
    )
    p.add_argument("--search", "-s", metavar="QUERY", help="Search countries")
    p.add_argument("--list-countries", action="store_true", help="List WITS countries")
    p.add_argument("--interactive", action="store_true", help="Pick countries interactively")
    return p


def cmd_list() -> None:
    for c in list_countries():
        print(f"{c.iso3:3}  {c.code:>4}  {c.name}")


def cmd_search(query: str) -> None:
    for c in search_countries(query, limit=30):
        print(f"{c.iso3:3}  {c.code:>4}  {c.name}")


def run_trade(export: str, import_country: str, year: str, product: str) -> int:
    payload, spec = fetch_trade_value(export, import_country, year=year, product=product)
    print(format_trade_result(payload, spec))
    return 0


def run_availability(import_country: str, year: str) -> int:
    rows = fetch_data_availability(import_country, year=year)
    if not rows:
        print("No availability records.")
        return 1
    for row in rows:
        print(f"{row['name']} ({row['iso3']}) — year {row['year']}")
        if row["nomenclature"]:
            print(f"  Nomenclature: {row['nomenclature']}")
        if row["partner_list"]:
            partners = row["partner_list"].split(";")
            print(f"  Partners ({len(partners)}): {';'.join(partners[:12])}{'...' if len(partners) > 12 else ''}")
        if row["last_updated"]:
            print(f"  Last updated: {row['last_updated']}")
    return 0


def run_tariff(export: str, import_country: str, year: str, product: str) -> int:
    export_c = resolve_country(export)
    import_c = resolve_country(import_country)
    print(f"Tariff on imports into {import_c.name} from {export_c.name}, HS {product}, {year}")
    try:
        payload = fetch_tariff(export_c, import_c, year=year, product=product)
    except RuntimeError as exc:
        print(exc)
        print("Tip: run --mode availability to see valid years/partners for the import country.")
        return 1
    print(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_countries:
        cmd_list()
        return 0
    if args.search:
        cmd_search(args.search)
        return 0

    export = args.export
    import_country = args.import_country
    year = args.year
    product = args.product

    if args.mode == "availability":
        if args.interactive or not import_country:
            print("Data availability is reported for the import (tariff-setting) country.\n")
            import_c = pick_country("Import / reporter country")
            import_country = import_c.iso3
            year = input("Year [all]: ").strip() or "all"
        elif not import_country:
            print("Provide --import for availability mode.", file=sys.stderr)
            return 2
        return run_availability(import_country, year)

    if args.interactive or not (export and import_country):
        print("Bilateral flow: export country → import country.\n")
        export_c = pick_country("Export country")
        import_c = pick_country("Import country")
        export = export_c.iso3
        import_country = import_c.iso3
        year = input(f"Year [{args.year}]: ").strip() or args.year
        product = input(f"Product [{args.product}]: ").strip() or args.product

    if not export or not import_country:
        print("Provide --export and --import, or use --interactive.", file=sys.stderr)
        return 2

    if args.mode == "tariff":
        return run_tariff(export, import_country, year, product)
    return run_trade(export, import_country, year, product)


if __name__ == "__main__":
    sys.exit(main())
