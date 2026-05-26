"""Reusable Streamlit UI components for the TradeNexus dashboard."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
import re

import streamlit as st

from trade_intel.config import RunConfig, set_config


def configure_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-kicker">Macro Trade Terminal</div>
            <div class="sidebar-title">TradeNexus</div>
            <div class="sidebar-copy">
                A premium global trade dashboard combining UN Comtrade, WITS,
                World Bank, and IMF data in one analyst workspace.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    with st.sidebar.expander("Control Center", expanded=False):
        no_cache = st.checkbox("Disable disk cache", value=False)
        ttl_h = st.number_input("Cache TTL (hours)", min_value=1, max_value=168, value=24)
        interval = st.slider("Min seconds between API calls", 0.0, 2.0, 0.35, 0.05)
        cache_dir = Path(st.text_input("Cache directory", ".trade_intel_cache"))
        set_config(
            RunConfig(
                cache_enabled=not no_cache,
                cache_dir=cache_dir,
                cache_ttl_seconds=int(ttl_h * 3600),
                min_request_interval=float(interval),
            )
        )

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div class="sidebar-section-title">Data Sources</div>
        <div class="source-node">
            <strong>UN Comtrade</strong>
            <span>Trade flows, partner ranking, product snapshots, destination concentration.</span>
        </div>
        <div class="source-node">
            <strong>World Bank WITS</strong>
            <span>Bilateral corridor time series and trend validation for exporter-importer pairs.</span>
        </div>
        <div class="source-node">
            <strong>World Bank Indicators</strong>
            <span>GDP, FDI, inflation, population, trade openness, and macro market context.</span>
        </div>
        <div class="source-node">
            <strong>IMF SDMX</strong>
            <span>CPI, exchange rates, balance of payments, and flexible macro series queries.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div class="sidebar-copy" style="text-align:center; padding: 0.2rem 0 0.6rem 0;">
            Cached locally for 24h.<br>
            Public APIs power most workflows without authentication.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    today = date.today().isoformat()
    st.markdown(
        f"""
        <div class="terminal-shell terminal-shell-compact">
            <div class="macro-topline">
                <div class="macro-topline-left">
                    <span class="brand-led"></span>
                    <span class="macro-app-name">TradeNexus B2B</span>
                    <span class="macro-app-tag">Macro Insights Terminal</span>
                </div>
                <div class="macro-topline-right">
                    <span class="status-badge">4 data rails</span>
                    <span class="status-badge">dense layout</span>
                    <span class="status-badge pink">session {today}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insights(insights: list[str], box_class: str = "") -> None:
    if not insights:
        return
    lines = "".join(f"<p>• {_format_rich_text(line)}</p>" for line in insights)
    st.markdown(f'<div class="insight-box {box_class}">{lines}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", negative: bool = False) -> str:
    sub_class = "kpi-sub negative" if negative else "kpi-sub"
    sub_html = f'<div class="{sub_class}">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


def section_intro(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-intro">
            <div class="section-kicker">{kicker}</div>
            <div class="section-title">{title}</div>
            <div class="section-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_header(title: str, subtitle: str = "", tag: str = "") -> None:
    subtitle_html = f'<div class="panel-subtitle">{subtitle}</div>' if subtitle else ""
    tag_html = f'<div class="panel-tag">{tag}</div>' if tag else ""
    st.markdown(
        f"""
        <div class="panel-shell">
            <div class="panel-title-row">
                <div>
                    <div class="panel-title">{title}</div>
                    {subtitle_html}
                </div>
                {tag_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_feed(items: list[str], *, empty_message: str) -> None:
    rows = items[:5] if items else [empty_message]
    html_rows = []
    for idx, item in enumerate(rows):
        html_rows.append(
            (
                '<div class="news-row">'
                f'<div class="news-time">{14 + idx:02d}:{(18 + idx * 7) % 60:02d}</div>'
                f'<div class="news-copy">{_format_rich_text(item)}</div>'
                "</div>"
            )
        )
    st.markdown(f'<div class="news-feed">{"".join(html_rows)}</div>', unsafe_allow_html=True)


def _format_rich_text(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r'<span class="inline-code">\1</span>', escaped)
    return escaped


def render_data_source_tree() -> None:
    st.markdown(
        """
        <div class="source-tree">
            <div class="tree-group">
                <div class="tree-group-title">World Bank</div>
                <div class="tree-item">Macro indicators</div>
                <div class="tree-item">GDP, inflation, FDI, debt</div>
                <div class="tree-item">Country profile lens</div>
            </div>
            <div class="tree-group">
                <div class="tree-group-title">UN Comtrade</div>
                <div class="tree-item">Trade flows</div>
                <div class="tree-item">HS code drill-down</div>
                <div class="tree-item">Partner ranking</div>
            </div>
            <div class="tree-group">
                <div class="tree-group-title">World Bank WITS</div>
                <div class="tree-item">Bilateral corridor trends</div>
                <div class="tree-item">Mirror trade context</div>
            </div>
            <div class="tree-group">
                <div class="tree-group-title">IMF SDMX</div>
                <div class="tree-item">Dataset catalog</div>
                <div class="tree-item">Query builder</div>
                <div class="tree-item">Time-series extraction</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_matrix(cards: list[dict[str, str]]) -> None:
    tiles = []
    for card in cards:
        tone = escape(card.get("tone", "cyan"))
        kicker = escape(card.get("kicker", ""))
        title = escape(card.get("title", ""))
        value = escape(card.get("value", ""))
        copy = escape(card.get("copy", ""))
        tiles.append(
            (
                f'<div class="matrix-card {tone}">'
                f'<div class="matrix-card-kicker">{kicker}</div>'
                f'<div class="matrix-card-title">{title}</div>'
                f'<div class="matrix-card-value">{value}</div>'
                f'<div class="matrix-card-copy">{copy}</div>'
                "</div>"
            )
        )
    st.markdown(f'<div class="matrix-grid">{"".join(tiles)}</div>', unsafe_allow_html=True)
