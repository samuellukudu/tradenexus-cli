"""
tradenexus/agent/scoring/breakdown.py

Phase 4 — Score breakdown formatting and utility functions.
Port of server/agent/scoring/scoreBreakdown.ts (pure logic).
"""

from __future__ import annotations

from tradenexus.agent.types import LeadScoreBreakdown


DIMENSION_LABELS: dict[str, str] = {
    "overall": "Overall",
    "location_fit": "Location Fit",
    "product_fit": "Product Fit",
    "buyer_type_fit": "Buyer Type",
    "company_size_fit": "Company Size",
    "evidence_quality": "Evidence Quality",
    "social_activity": "Social Activity",
    "contactability": "Contactability",
    "competitive_opportunity": "Competitive Gap",
    "freshness": "Freshness",
}


def score_bar(value: int, width: int = 10) -> str:
    """Render a value as a unicode bar chart string."""
    filled = round((value / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def score_color(value: int) -> str:
    """Return a hex color for a score value."""
    if value >= 80:
        return "#34d399"
    if value >= 60:
        return "#fbbf24"
    if value >= 40:
        return "#f97316"
    return "#ef4444"


def get_score_label(value: int) -> str:
    """Return a human-readable label for a score value."""
    if value >= 80:
        return "Strong"
    if value >= 60:
        return "Good"
    if value >= 40:
        return "Fair"
    return "Weak"


def format_score_breakdown(score: LeadScoreBreakdown) -> str:
    """Format a LeadScoreBreakdown as a terminal-ready string with bar charts."""
    lines: list[str] = []
    dims = [
        "overall", "location_fit", "product_fit", "buyer_type_fit",
        "company_size_fit", "evidence_quality", "social_activity",
        "contactability", "competitive_opportunity", "freshness",
    ]

    for dim in dims:
        value = getattr(score, dim, 50)
        bar = score_bar(value)
        label = DIMENSION_LABELS.get(dim, dim)
        lines.append(f"{label:<22} {bar} {value}/100")

    if score.rationale:
        lines.append("")
        lines.append(f"Rationale: {score.rationale}")

    return "\n".join(lines)
