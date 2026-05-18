#!/usr/bin/env python3
"""Query UN Comtrade public API with selectable export / import countries."""

from __future__ import annotations

import argparse
import sys

from comtrade_countries import list_countries, pick_country, resolve_country, search_countries
from trade_query import fetch_bilateral, summarize


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch bilateral trade (export → import) via UN Comtrade public API.",
    )
    p.add_argument("--export", "-e", help="Export country (name, ISO3, ISO2, or Comtrade code)")
    p.add_argument("--import", "-i", dest="import_country", help="Import country (name, ISO3, ISO2, or code)")
    p.add_argument("--period", "-p", default="202205", help="Period YYYYMM (monthly) or YYYY (annual)")
    p.add_argument("--commodity", "-c", default="TOTAL", help="HS cmdCode (e.g. TOTAL, 91, 9*)")
    p.add_argument("--max-records", type=int, default=500, help="Max rows (public preview cap: 500)")
    p.add_argument("--search", "-s", metavar="QUERY", help="Search countries and exit")
    p.add_argument("--list-countries", action="store_true", help="Print all active countries")
    p.add_argument("--interactive", action="store_true", help="Pick export/import countries interactively")
    return p


def cmd_search(query: str) -> None:
    for country in search_countries(query, limit=30):
        print(f"{country.iso3:3}  {country.code:4}  {country.name}")


def cmd_list() -> None:
    for country in list_countries():
        print(f"{country.iso3:3}  {country.code:4}  {country.name}")


def run_query(export: str, import_country: str, period: str, commodity: str, max_records: int) -> int:
    export_c = resolve_country(export)
    import_c = resolve_country(import_country)
    print(f"Export: {export_c.name} ({export_c.iso3}) → Import: {import_c.name} ({import_c.iso3})")
    print(f"Period: {period}  Commodity: {commodity}\n")

    df, _spec = fetch_bilateral(
        export_c,
        import_c,
        period=period,
        cmd_code=commodity,
        max_records=max_records,
    )
    out = summarize(df)
    if out is None or out.empty:
        print("No data returned. Try another period or commodity code.")
        return 1
    print(out.to_string(index=False))
    print(f"\n{len(out)} row(s)")
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

    if args.interactive or not (export and import_country):
        print("Select countries for bilateral trade (goods flow: export → import).\n")
        export_c = pick_country("Export country")
        import_c = pick_country("Import country")
        export = export_c.iso3 or str(export_c.code)
        import_country = import_c.iso3 or str(import_c.code)
        if not args.period or args.period == "202205":
            period = input("Period [202205]: ").strip() or "202205"
        else:
            period = args.period
        commodity = args.commodity
    else:
        period = args.period
        commodity = args.commodity

    return run_query(export, import_country, period, commodity, args.max_records)


if __name__ == "__main__":
    sys.exit(main())
