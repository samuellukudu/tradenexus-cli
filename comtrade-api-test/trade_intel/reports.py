"""High-level reports combining WITS trends and Comtrade snapshots."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trade_intel.analytics import describe_trend
from trade_intel.wits_timeseries import fetch_bilateral_export_series, fetch_bilateral_import_series

from comtrade_countries import resolve_country as resolve_ct
from trade_query import fetch_bilateral, summarize


@dataclass
class BilateralReport:
    export_iso3: str
    import_iso3: str
    wits_series: list[tuple[str, float]]
    comtrade_note: str = ""
    mirror_series: list[tuple[str, float]] | None = None


def build_bilateral_report(
    export_query: str,
    import_query: str,
    *,
    year_from: int,
    year_to: int,
    comtrade_period: str | None = None,
    comtrade_freq: str = "A",
    product: str = "total",
    include_mirror: bool = False,
) -> BilateralReport:
    exp = resolve_ct(export_query)
    imp = resolve_ct(import_query)
    series = fetch_bilateral_export_series(exp.iso3, imp.iso3, year_from, year_to, product=product)
    mirror = None
    if include_mirror:
        mirror = fetch_bilateral_import_series(exp.iso3, imp.iso3, year_from, year_to, product=product)
    note = ""
    if comtrade_period:
        try:
            df, _ = fetch_bilateral(
                exp,
                imp,
                period=comtrade_period,
                freq_code=comtrade_freq,
                cmd_code="TOTAL",
                max_records=50,
            )
            s = summarize(df)
            if s is not None and not s.empty and "primaryValue" in s.columns:
                total = pd.to_numeric(s["primaryValue"], errors="coerce").sum()
                note = (
                    f"Comtrade HS snapshot ({comtrade_period}, freq={comtrade_freq}): "
                    f"aggregate line value sum ≈ {total:,.0f} USD across detail rows (see API breakdown)."
                )
            else:
                note = "Comtrade preview returned no rows for this pair and period."
        except Exception as exc:
            note = f"Comtrade snapshot skipped: {exc}"
    return BilateralReport(
        export_iso3=exp.iso3,
        import_iso3=imp.iso3,
        wits_series=series,
        comtrade_note=note,
        mirror_series=mirror,
    )


def format_bilateral_report(report: BilateralReport) -> str:
    lines: list[str] = []
    lines.append(
        f"Bilateral trade: {report.export_iso3} → {report.import_iso3} "
        "(WITS export value, US$ thousand, annual)"
    )
    if not report.wits_series:
        lines.append("No WITS time series returned.")
    else:
        for y, v in report.wits_series:
            lines.append(f"  {y}: {v:,.1f}")
        ys = [t[0] for t in report.wits_series]
        vs = [t[1] for t in report.wits_series]
        lines.append(describe_trend(ys, vs))
    if report.mirror_series:
        lines.append("")
        lines.append(
            f"Mirror: {report.import_iso3} imports from {report.export_iso3} "
            "(WITS MPRT-TRD-VL, US$ thousand, annual — should align with export view)"
        )
        for y, v in report.mirror_series:
            lines.append(f"  {y}: {v:,.1f}")
    if report.comtrade_note:
        lines.append("")
        lines.append(report.comtrade_note)
    return "\n".join(lines)


def format_markets_table(df: pd.DataFrame, title: str) -> str:
    if df is None or df.empty:
        return f"{title}\n(no rows — try another period or check preview 500-row cap)\n"
    return f"{title}\n" + df.to_string(index=False) + "\n"
