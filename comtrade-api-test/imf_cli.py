#!/usr/bin/env python3
"""Query the IMF SDMX API with public access or optional interactive auth."""

from __future__ import annotations

import argparse
import json
import sys

from trade_intel.imf_data import build_auth_headers, describe_dataflow, fetch_dataset, IMFDataQuery, list_dataflows


def _parse_params(values: list[str] | None) -> dict[str, str]:
    params: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"Expected KEY=VALUE format, got: {raw}")
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Parameter name cannot be blank: {raw}")
        params[name] = value.strip()
    return params


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="IMF SDMX API via sdmx1. Public queries work without login; protected endpoints can use MSAL.",
    )
    parser.add_argument("--dataset", help="IMF dataset / dataflow, e.g. CPI or WEO")
    parser.add_argument("--key", help="SDMX key, e.g. USA+CAN.CPI.CP01.IX.M")
    parser.add_argument("--start-period", help="startPeriod query parameter")
    parser.add_argument("--end-period", help="endPeriod query parameter")
    parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        help="Additional SDMX query parameter; can be repeated.",
    )
    parser.add_argument("--head", type=int, default=20, help="Rows to print (default: 20)")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    parser.add_argument("--list-dataflows", action="store_true", help="List available IMF datasets")
    parser.add_argument("--search", help="Filter dataset list by code or label")
    parser.add_argument("--describe-dataflow", metavar="DATASET", help="Show dimensions for one dataset")
    parser.add_argument("--auth", action="store_true", help="Use interactive MSAL authentication")
    parser.add_argument("--access-token", help="Use an existing bearer token instead of interactive login")
    parser.add_argument("--client-id", help="Override the default IMF client ID")
    parser.add_argument("--authority", help="Override the default IMF authority URL")
    parser.add_argument("--scope", help="Override the default IMF scope")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        extra_params = _parse_params(args.param)
        headers = build_auth_headers(
            interactive=args.auth,
            access_token=args.access_token,
            client_id=args.client_id,
            authority=args.authority,
            scope=args.scope,
        )
        if args.list_dataflows:
            df = list_dataflows(headers=headers, search=args.search)
            if df.empty:
                print("No IMF dataflows matched.")
                return 1
            print(df.head(args.head).to_string(index=False))
            print(f"\n{len(df)} dataflow(s)")
            return 0

        if args.describe_dataflow:
            info = describe_dataflow(args.describe_dataflow, headers=headers)
            print(json.dumps(info, indent=2))
            return 0

        if not args.dataset:
            print("Provide --dataset, or use --list-dataflows / --describe-dataflow.", file=sys.stderr)
            return 2

        query = IMFDataQuery(
            dataset=args.dataset,
            key=args.key,
            start_period=args.start_period,
            end_period=args.end_period,
            extra_params=extra_params,
        )
        df = fetch_dataset(query, headers=headers)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if df.empty:
        print("No data returned.")
        return 1

    if args.json:
        print(df.head(args.head).to_json(orient="records", indent=2))
    else:
        print(df.head(args.head).to_string(index=False))
    print(f"\n{len(df)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
