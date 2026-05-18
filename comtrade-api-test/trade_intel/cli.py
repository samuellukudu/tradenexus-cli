#!/usr/bin/env python3
"""Trade intelligence CLI: markets, trends, bilateral reports, exporter opportunities."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trade_intel.analytics import describe_trend
from trade_intel.comtrade_flows import top_export_destinations, top_import_sources
from trade_intel.config import RunConfig, set_config
from trade_intel.opportunities import rank_exporter_opportunities
from trade_intel.reports import build_bilateral_report, format_bilateral_report, format_markets_table
from trade_intel.wits_timeseries import fetch_bilateral_export_series, fetch_bilateral_import_series


def _apply_global_config(ns: argparse.Namespace) -> None:
    cache_dir = Path(ns.cache_dir) if ns.cache_dir else Path(".trade_intel_cache")
    set_config(
        RunConfig(
            cache_enabled=not ns.no_cache,
            cache_dir=cache_dir,
            cache_ttl_seconds=int(ns.cache_ttl),
            min_request_interval=float(ns.min_interval),
        )
    )


def _cmd_markets(ns: argparse.Namespace) -> int:
    if ns.role == "supplier":
        df, c = top_export_destinations(
            ns.country,
            period=ns.period,
            freq_code=ns.freq,
            cmd_code=ns.cmd,
            top_n=ns.top,
        )
        title = f"Top export destinations for {c.name} ({c.iso3}) — period {ns.period}, HS {ns.cmd}"
    else:
        df, c = top_import_sources(
            ns.country,
            period=ns.period,
            freq_code=ns.freq,
            cmd_code=ns.cmd,
            top_n=ns.top,
        )
        title = f"Top import sources for {c.name} ({c.iso3}) — period {ns.period}, HS {ns.cmd}"
    print(format_markets_table(df, title))
    print(
        "Note: Comtrade public preview returns at most 500 rows; "
        "rankings are within that cap. Use a specific HS chapter for narrower views."
    )
    return 0


def _cmd_trend(ns: argparse.Namespace) -> int:
    ex = ns.export.upper()
    im = ns.import_country.upper()
    series = fetch_bilateral_export_series(
        ex,
        im,
        ns.from_year,
        ns.to_year,
        product=ns.product.lower(),
    )
    if not series:
        print("No WITS data for this pair and range.")
        return 1
    print(f"Bilateral exports {ex} → {im} (US$ thousand, annual, product={ns.product})")
    for y, v in series:
        print(f"  {y}: {v:,.1f}")
    ys = [t[0] for t in series]
    vs = [t[1] for t in series]
    print()
    print(describe_trend(ys, vs))
    if ns.mirror:
        mir = fetch_bilateral_import_series(ex, im, ns.from_year, ns.to_year, product=ns.product.lower())
        if mir:
            print()
            print(f"Mirror — {im} imports from {ex} (MPRT-TRD-VL, US$ thousand)")
            for y, v in mir:
                print(f"  {y}: {v:,.1f}")
    return 0


def _cmd_report(ns: argparse.Namespace) -> int:
    report = build_bilateral_report(
        ns.export,
        ns.import_country,
        year_from=ns.from_year,
        year_to=ns.to_year,
        comtrade_period=ns.comtrade_period,
        comtrade_freq=ns.comtrade_freq,
        product=ns.product,
        include_mirror=ns.mirror,
    )
    print(format_bilateral_report(report))
    return 0


def _cmd_opportunities(ns: argparse.Namespace) -> int:
    df, c = rank_exporter_opportunities(
        ns.country,
        comtrade_period=ns.period,
        comtrade_freq=ns.freq,
        cmd_code=ns.cmd,
        pool_size=ns.pool,
        score_count=ns.top,
        wits_year_from=ns.from_year,
        wits_year_to=ns.to_year,
        product=ns.product,
    )
    title = (
        f"Exporter opportunity ranking — {c.name} ({c.iso3})\n"
        f"Comtrade anchor: {ns.period} (freq={ns.freq}, HS {ns.cmd}); "
        f"WITS growth window: {ns.from_year}–{ns.to_year}; product={ns.product}\n"
        "Score ≈ 62% relative size (latest bilateral exports, US$ thousand) + 38% growth (CAGR)."
    )
    if df.empty:
        print(title)
        print("\nNo scored markets (check period or partner mapping).")
        return 1
    show = df.drop(columns=["note"], errors="ignore") if "note" in df.columns and (df["note"].fillna("") == "").all() else df
    print(title)
    print()
    print(show.to_string(index=False))
    return 0


def _add_runtime_options(sp: argparse.ArgumentParser) -> None:
    g = sp.add_argument_group("cache & rate limits")
    g.add_argument(
        "--cache-dir",
        default=None,
        help="Disk cache directory (default: .trade_intel_cache)",
    )
    g.add_argument("--no-cache", action="store_true", help="Disable disk cache")
    g.add_argument(
        "--cache-ttl",
        type=int,
        default=86400,
        metavar="SEC",
        help="Cache entry TTL in seconds (default: 86400 = 24h)",
    )
    g.add_argument(
        "--min-interval",
        type=float,
        default=0.35,
        metavar="SEC",
        help="Minimum spacing between outbound API calls (default: 0.35)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Trade intelligence for B2B exporters: markets, trends, opportunities (Comtrade + WITS).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("markets", help="Rank partner countries for a supplier (exports) or buyer (imports).")
    _add_runtime_options(m)
    m.add_argument("--role", choices=("supplier", "buyer"), required=True)
    m.add_argument("--country", "-c", required=True, help="Home country (ISO3, name, or Comtrade code)")
    m.add_argument("--period", "-p", required=True, help="Period e.g. 2020 (annual) or 202205 (monthly)")
    m.add_argument("--freq", default="A", choices=("A", "M"), help="Comtrade frequency")
    m.add_argument("--cmd", default="TOTAL", help="HS commodity code, e.g. TOTAL or 87")
    m.add_argument("--top", type=int, default=15)
    m.set_defaults(func=_cmd_markets)

    t = sub.add_parser("trend", help="Annual bilateral export trend (WITS Trade Stats).")
    _add_runtime_options(t)
    t.add_argument("--export", "-e", required=True)
    t.add_argument("--import", "-i", dest="import_country", required=True)
    t.add_argument("--from-year", type=int, required=True)
    t.add_argument("--to-year", type=int, required=True)
    t.add_argument("--product", default="total", help="WITS product group e.g. total, fuels")
    t.add_argument(
        "--mirror",
        action="store_true",
        help="Also show importer-reported mirror series (MPRT-TRD-VL)",
    )
    t.set_defaults(func=_cmd_trend)

    r = sub.add_parser("report", help="Combined WITS trend + optional Comtrade HS snapshot.")
    _add_runtime_options(r)
    r.add_argument("--export", "-e", required=True)
    r.add_argument("--import", "-i", dest="import_country", required=True)
    r.add_argument("--from-year", type=int, required=True)
    r.add_argument("--to-year", type=int, required=True)
    r.add_argument("--product", default="total")
    r.add_argument(
        "--comtrade-period",
        default=None,
        help="Optional Comtrade period for bilateral snapshot (e.g. 2020 with --comtrade-freq A)",
    )
    r.add_argument("--comtrade-freq", default="A", choices=("A", "M"))
    r.add_argument(
        "--mirror",
        action="store_true",
        help="Append WITS import-side mirror series for the same corridor",
    )
    r.set_defaults(func=_cmd_report)

    o = sub.add_parser(
        "opportunities",
        help="Exporter view: rank destination markets by size + WITS growth (supplier workflow).",
    )
    _add_runtime_options(o)
    o.add_argument("--country", "-c", required=True, help="Supplier / home country")
    o.add_argument("--period", "-p", required=True, help="Comtrade period for destination pool (e.g. 2020)")
    o.add_argument("--freq", default="A", choices=("A", "M"))
    o.add_argument("--cmd", default="TOTAL", help="HS code for Comtrade partner pool")
    o.add_argument("--pool", type=int, default=25, help="How many top Comtrade destinations to evaluate")
    o.add_argument("--top", type=int, default=15, help="How many scored rows to print")
    o.add_argument("--from-year", type=int, default=2018, dest="from_year")
    o.add_argument("--to-year", type=int, default=2022, dest="to_year")
    o.add_argument("--product", default="total", help="WITS product group for growth series")
    o.set_defaults(func=_cmd_opportunities)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_global_config(args)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
