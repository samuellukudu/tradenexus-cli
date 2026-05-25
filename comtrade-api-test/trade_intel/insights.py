"""Plain-language insight generator for trade intelligence.

Rule-based summaries that translate raw data into actionable language for
investors, businesses, and entrepreneurs. No LLM required.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_usd(value: float) -> str:
    """Format USD value with B/M/K suffix."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K"
    else:
        return f"${value:.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:+.{decimals}f}%"


def fmt_number(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


# ── Destination market insights ───────────────────────────────────────────────

def summarize_destinations(
    df: pd.DataFrame,
    country_name: str,
    *,
    period: str = "",
    cmd: str = "TOTAL",
) -> list[str]:
    """
    Produce 2–4 plain-language bullet points about export destinations.

    Returns a list of insight strings.
    """
    insights: list[str] = []

    if df is None or df.empty:
        return ["No export destination data found for the selected country and period."]

    value_col = "primaryValue"
    partner_col = "partnerDesc"

    if value_col not in df.columns or partner_col not in df.columns:
        return ["Destination data loaded — select columns to analyze."]

    total = float(df[value_col].sum())
    if total <= 0:
        return ["Export values are zero or unavailable for this period."]

    top3 = df.head(3)
    top3_total = float(top3[value_col].sum())
    top3_pct = 100 * top3_total / total
    top3_names = ", ".join(top3[partner_col].astype(str).tolist())
    top1 = df.iloc[0]
    top1_name = str(top1[partner_col])
    top1_val = float(top1[value_col])
    top1_pct = 100 * top1_val / total

    period_label = f" in {period}" if period else ""

    # Top market
    insights.append(
        f"**Top destination{period_label}:** {top1_name} absorbs {fmt_usd(top1_val)} "
        f"({top1_pct:.0f}% of exports)."
    )

    # Concentration risk
    if top3_pct >= 80:
        risk = "⚠️ **High concentration risk** — your top 3 markets ({}) account for {:.0f}% of exports. Consider diversifying.".format(
            top3_names, top3_pct
        )
    elif top3_pct >= 60:
        risk = "🔶 **Moderate concentration** — top 3 markets ({}) represent {:.0f}% of exports.".format(
            top3_names, top3_pct
        )
    else:
        risk = "✅ **Well-diversified** — top 3 markets ({}) account for {:.0f}% of exports.".format(
            top3_names, top3_pct
        )
    insights.append(risk)

    # Market count
    n = len(df)
    if n >= 20:
        insights.append(f"**Broad reach:** Active trade relationships with {n}+ destination markets.")
    elif n >= 10:
        insights.append(f"**Moderate reach:** Exports flowing to {n} destination markets.")
    else:
        insights.append(f"**Narrow reach:** Only {n} active destination markets found — growth opportunity exists.")

    # HS product context
    if cmd and cmd.upper() != "TOTAL":
        insights.append(f"HS code filter: `{cmd}` — data reflects product-specific flows only.")

    return insights


# ── Opportunity ranker insights ───────────────────────────────────────────────

def summarize_opportunities(
    df: pd.DataFrame,
    country_name: str,
) -> list[str]:
    """Produce 2–3 bullets about the ranked opportunity list."""
    insights: list[str] = []

    if df is None or df.empty:
        return ["No scored opportunities found. Try a different period or HS code."]

    scored = df[df["opportunity"].notna()].copy() if "opportunity" in df.columns else df.copy()

    if scored.empty:
        return ["Opportunity scoring requires WITS bilateral data. No pairs scored yet."]

    top = scored.iloc[0]
    partner = str(top.get("partner", "N/A"))
    opp = float(top.get("opportunity", 0))
    cg = top.get("cagr")
    latest_kusd = top.get("wits_latest_kusd")

    opp_label = "High" if opp >= 0.65 else ("Medium" if opp >= 0.40 else "Low")

    # Top opportunity summary
    detail = f"**Top opportunity: {partner}** — score {opp:.2f} ({opp_label})."
    if cg is not None and not (isinstance(cg, float) and math.isnan(cg)):
        detail += f" Trade corridor CAGR: {cg * 100:+.1f}%."
    if latest_kusd is not None:
        detail += f" Latest bilateral flow: {fmt_usd(float(latest_kusd) * 1000)}."
    insights.append(detail)

    # Distribution of scores
    high = (scored["opportunity"] >= 0.65).sum() if "opportunity" in scored.columns else 0
    mid = ((scored["opportunity"] >= 0.40) & (scored["opportunity"] < 0.65)).sum() if "opportunity" in scored.columns else 0
    low = (scored["opportunity"] < 0.40).sum() if "opportunity" in scored.columns else 0

    insights.append(
        f"**Score distribution:** 🟢 High {high} · 🟡 Medium {mid} · 🔴 Low {low} markets."
    )

    # How many scored vs not
    total_rows = len(df)
    scored_count = len(scored)
    if scored_count < total_rows:
        unscored = total_rows - scored_count
        insights.append(
            f"ℹ️ {unscored} market(s) could not be scored (missing WITS data) and are excluded from rankings."
        )

    return insights


# ── Bilateral corridor insights ───────────────────────────────────────────────

def summarize_corridor(
    series: list[tuple[str, float]],
    exporter: str,
    importer: str,
    *,
    kusd: bool = True,
) -> list[str]:
    """Produce insight bullets for a bilateral export trend."""
    insights: list[str] = []

    if not series or len(series) < 2:
        return [f"Insufficient data for {exporter} → {importer} corridor."]

    unit = "US$ thousand" if kusd else "USD"
    multiplier = 1000.0 if kusd else 1.0

    y0, v0 = series[0]
    y_last, v_last = series[-1]
    span = int(y_last) - int(y0)

    cagr_val: float | None = None
    if span > 0 and v0 > 0 and v_last > 0:
        cagr_val = (v_last / v0) ** (1.0 / span) - 1.0

    # Trend direction
    trend_arrow = "📈" if v_last > v0 else "📉"
    pct_change = 100 * (v_last - v0) / v0 if v0 > 0 else 0
    insights.append(
        f"{trend_arrow} **{exporter} → {importer}:** "
        f"{fmt_usd(v0 * multiplier)} ({y0}) → {fmt_usd(v_last * multiplier)} ({y_last}), "
        f"change: {pct_change:+.0f}%."
    )

    # CAGR
    if cagr_val is not None:
        if cagr_val >= 0.10:
            cagr_label = "🟢 Strong growth"
        elif cagr_val >= 0.03:
            cagr_label = "🟡 Moderate growth"
        elif cagr_val >= -0.03:
            cagr_label = "⚪ Flat"
        else:
            cagr_label = "🔴 Declining"
        insights.append(f"**CAGR ({y0}–{y_last}):** {cagr_val * 100:+.1f}% — {cagr_label}.")

    # Peak
    peak_year, peak_val = max(series, key=lambda x: x[1])
    if peak_year != y_last:
        insights.append(
            f"⚡ **Peak year:** {peak_year} at {fmt_usd(peak_val * multiplier)} — corridor has not recovered to its peak."
        )

    return insights


# ── World Bank / Country profile insights ────────────────────────────────────

def summarize_country_profile(
    profile: dict[str, Any],
    country_name: str,
) -> list[str]:
    """Produce 3–5 investor-focused bullets from a World Bank country profile."""
    insights: list[str] = []

    gdp_pc = profile.get("gdp_per_capita_latest")
    gdp_year = profile.get("gdp_per_capita_latest_year", "")
    gdp_growth = profile.get("gdp_growth_latest")
    fdi = profile.get("fdi_inflows_latest")
    trade_pct = profile.get("trade_pct_gdp_latest")
    inflation = profile.get("inflation_latest")
    pop = profile.get("population_latest")

    # GDP per capita context
    if gdp_pc is not None:
        tier = (
            "high-income" if gdp_pc >= 12_000
            else "upper-middle-income" if gdp_pc >= 4_000
            else "lower-middle-income" if gdp_pc >= 1_000
            else "low-income"
        )
        insights.append(
            f"**GDP per capita ({gdp_year}):** {fmt_usd(gdp_pc)} — {tier} economy."
        )

    # Growth signal
    if gdp_growth is not None:
        if gdp_growth >= 5:
            growth_label = "🟢 Fast-growing economy"
        elif gdp_growth >= 2:
            growth_label = "🟡 Steady growth"
        elif gdp_growth >= 0:
            growth_label = "⚪ Slow growth"
        else:
            growth_label = "🔴 Contracting economy"
        insights.append(f"**GDP growth:** {gdp_growth:+.1f}% — {growth_label}.")

    # FDI signal
    if fdi is not None:
        fdi_label = "attracting foreign capital" if fdi > 0 else "net capital outflow"
        insights.append(f"**FDI inflows:** {fmt_usd(abs(float(fdi)))} — {fdi_label}.")

    # Trade openness
    if trade_pct is not None:
        if trade_pct >= 80:
            open_label = "🟢 Highly open — trade-friendly market"
        elif trade_pct >= 40:
            open_label = "🟡 Moderately open"
        else:
            open_label = "🔴 Relatively closed — potential trade barriers"
        insights.append(f"**Trade openness:** {trade_pct:.0f}% of GDP — {open_label}.")

    # Inflation risk
    if inflation is not None:
        if inflation > 15:
            infl_label = "🔴 High inflation — currency/pricing risk for exporters"
        elif inflation > 7:
            infl_label = "🟡 Elevated inflation — monitor closely"
        else:
            infl_label = "🟢 Stable inflation environment"
        insights.append(f"**Inflation:** {inflation:.1f}% — {infl_label}.")

    # Population / market size
    if pop is not None:
        insights.append(f"**Market size:** Population of {fmt_number(float(pop))} people.")

    return insights


# ── Opportunity score badge ───────────────────────────────────────────────────

def score_badge(score: float | None) -> str:
    """Return a colored badge label for an opportunity score 0–1."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "⚫ N/A"
    if score >= 0.65:
        return f"🟢 {score:.2f}"
    elif score >= 0.40:
        return f"🟡 {score:.2f}"
    else:
        return f"🔴 {score:.2f}"
