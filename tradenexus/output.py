"""
tradenexus/output.py

Rich-formatted terminal display helpers.
"""

from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule

from .models import Lead, MarketReport, RegionSuggestion

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color(score: int) -> str:
    if score >= 80:
        return "bright_green"
    if score >= 60:
        return "yellow"
    return "red"


def _demand_color(level: str) -> str:
    return {"High": "bright_green", "Medium": "yellow", "Low": "red"}.get(level, "white")


# ---------------------------------------------------------------------------
# Region Suggestions
# ---------------------------------------------------------------------------

def print_region_suggestions(suggestions: list[RegionSuggestion]) -> None:
    table = Table(
        title="[bold cyan]Top Export Markets[/]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Region", style="bold")
    table.add_column("Demand", justify="center", width=10)
    table.add_column("Reason")

    for i, s in enumerate(suggestions, 1):
        demand_str = f"[{_demand_color(s.demand_level)}]{s.demand_level}[/]"
        table.add_row(str(i), s.region, demand_str, s.reason)

    console.print(table)


# ---------------------------------------------------------------------------
# Market Report
# ---------------------------------------------------------------------------

def print_market_report(report: MarketReport) -> None:
    console.print(Rule(f"[bold cyan] Market Report — {report.region} [/]", style="cyan"))

    console.print(Panel(
        report.overview,
        title="[bold]Market Overview[/]",
        border_style="blue",
        padding=(1, 2),
    ))

    metrics = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    metrics.add_column("Field", style="bold cyan", width=22)
    metrics.add_column("Value")
    rows = [
        ("Market Size", report.market_size),
        ("HS Code", report.hs_code),
        ("Import Duty", report.import_duty),
        ("Shipping Time", report.shipping_time),
        ("Price Structure", report.price_structure),
        ("Entry Strategy", report.entry_strategy),
        ("Regulations", report.regulations),
        ("Localization", report.localization),
        ("Buying Habits", report.buying_habits),
    ]
    for k, v in rows:
        metrics.add_row(k, v or "N/A")
    console.print(metrics)

    if report.competitors:
        console.print(f"\n[bold]Key Competitors:[/] {', '.join(report.competitors)}")

    if report.trade_shows:
        console.print(f"[bold]Trade Shows:[/] {', '.join(report.trade_shows)}")

    if report.sources:
        console.print("\n[bold dim]Sources:[/]")
        for s in report.sources[:5]:
            console.print(f"  [dim]• {s.title} — {s.url}[/]")

    if report.stats:
        _print_stats(report.stats)

    console.print()


def _print_stats(stats) -> None:
    console.print("\n[bold]Statistical Data[/]")

    def mini_table(title: str, points) -> None:
        t = Table(title=title, box=box.MINIMAL, show_header=True)
        t.add_column("Label", style="bold")
        t.add_column("Value", justify="right")
        for p in points:
            t.add_row(p.label, f"{p.value:.1f}")
        console.print(t)

    mini_table("Competitor Share (%)", stats.competitor_share)
    mini_table("Growth Trend", stats.growth_trend)
    mini_table("User Segments (%)", stats.user_segments)


# ---------------------------------------------------------------------------
# Lead Card
# ---------------------------------------------------------------------------

def print_lead_card(lead: Lead, index: int | None = None) -> None:
    title_prefix = f"[dim]#{index}[/] " if index is not None else ""
    score_color = _score_color(lead.confidence_score)
    score_bar = f"[{score_color}]{'█' * (lead.confidence_score // 10)}{'░' * (10 - lead.confidence_score // 10)}[/] {lead.confidence_score}%"

    lines: list[str] = [
        score_bar,
        f"[bold cyan]Region:[/] {lead.region}",
        f"[bold cyan]Status:[/] {lead.status.value}",
    ]
    if lead.website:
        lines.append(f"[bold cyan]Website:[/] {lead.website}")
    if lead.address:
        lines.append(f"[bold cyan]Address:[/] {lead.address}")
    if lead.contact_email:
        lines.append(f"[bold cyan]Email:[/] {lead.contact_email}")
    if lead.phone_number:
        lines.append(f"[bold cyan]Phone:[/] {lead.phone_number}")
    if lead.summary:
        lines.append(f"\n[italic]{lead.summary}[/]")
    if lead.google_maps_url:
        lines.append(f"[dim]📍 {lead.google_maps_url}[/]")
    if lead.verification_status:
        vs_color = {"VERIFIED": "green", "FAILED": "red", "UNVERIFIED": "yellow"}.get(lead.verification_status, "white")
        lines.append(f"[{vs_color}]✓ {lead.verification_status}[/]")
        if lead.verification_notes:
            lines.append(f"[dim]{lead.verification_notes}[/]")

    console.print(Panel(
        "\n".join(lines),
        title=f"{title_prefix}[bold white]{lead.company_name}[/]",
        border_style=score_color,
        padding=(0, 1),
    ))


def print_leads_table(leads: list[Lead]) -> None:
    table = Table(
        title=f"[bold cyan]Discovered Leads ({len(leads)})[/]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Company", style="bold")
    table.add_column("Region")
    table.add_column("Score", justify="center", width=8)
    table.add_column("Status", width=14)
    table.add_column("Email")
    table.add_column("Website")

    for i, lead in enumerate(leads, 1):
        score_color = _score_color(lead.confidence_score)
        table.add_row(
            str(i),
            lead.company_name,
            lead.region,
            f"[{score_color}]{lead.confidence_score}%[/]",
            lead.status.value,
            lead.contact_email or "—",
            lead.website or "—",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------

def print_verification_result(company_name: str, result: dict) -> None:
    status = result.get("verificationStatus", "UNVERIFIED")
    notes = result.get("verificationNotes", "")
    score = result.get("confidenceScore", 0)
    color = {"VERIFIED": "green", "FAILED": "red", "UNVERIFIED": "yellow"}.get(status, "white")

    console.print(Panel(
        f"[{color}]Status: {status}[/]\n"
        f"Confidence: {score}%\n"
        f"Notes: {notes}",
        title=f"[bold]Verification — {company_name}[/]",
        border_style=color,
    ))


# ---------------------------------------------------------------------------
# Strategic Context
# ---------------------------------------------------------------------------

def print_strategic_context(ctx) -> None:
    table = Table(
        title="[bold cyan]Strategic Context Extracted[/]",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=False,
    )
    table.add_column("Field", style="bold cyan", width=24)
    table.add_column("Value")

    table.add_row("Product Identity", ctx.product_identity)
    table.add_row("Ideal Buyer", ctx.ideal_buyer)
    table.add_row("Value Proposition", ctx.value_proposition)
    table.add_row("Exclusions", ctx.exclusions)
    table.add_row("Technical Specs", "\n".join(ctx.technical_specs) or "—")
    table.add_row("Certifications", ", ".join(ctx.certifications) or "—")
    console.print(table)
