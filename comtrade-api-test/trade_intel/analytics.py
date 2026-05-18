"""Simple analytics on trade value series (US$ thousand from WITS, US$ from Comtrade)."""

from __future__ import annotations

import math
from typing import Sequence


def cagr(start: float, end: float, years: float) -> float | None:
    """Compound annual growth rate; years is span in years (e.g. 2022 - 2015 = 7)."""
    if years <= 0 or start <= 0 or end <= 0:
        return None
    return (end / start) ** (1.0 / years) - 1.0


def pct_change(start: float, end: float) -> float | None:
    if start == 0:
        return None
    return (end - start) / start


def describe_trend(years: Sequence[str], values: Sequence[float]) -> str:
    """One-line narrative for a monotonic-ish series."""
    if len(values) < 2:
        return "Not enough points for a trend."
    y0, y1 = float(values[0]), float(values[-1])
    span = float(int(years[-1]) - int(years[0]))
    g = cagr(y0, y1, span) if span > 0 else None
    direction = "flat"
    if y1 > y0 * 1.05:
        direction = "growing"
    elif y1 < y0 * 0.95:
        direction = "declining"
    parts = [f"From {years[0]} to {years[-1]}, values are broadly {direction}."]
    if g is not None and not math.isnan(g):
        parts.append(f"Approx. CAGR: {g * 100:.1f}% per year.")
    return " ".join(parts)
