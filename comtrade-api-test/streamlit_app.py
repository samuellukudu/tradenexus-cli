"""
TradeNexus — Premium Trade Intelligence Platform

Powered by UN Comtrade, World Bank, World Bank WITS, and IMF SDMX.
Built for investors, businesses, and entrepreneurs.

Run from project root:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from comtrade_countries import Country, list_countries, resolve_country
from trade_intel.comtrade_history import fetch_export_history, recent_annual_years
from trade_intel.comtrade_flows import annual_export_destination_trends, top_export_destinations
from trade_intel.config import RunConfig, set_config
from trade_intel.imf_data import IMFDataQuery, build_auth_headers, describe_dataflow, fetch_dataset, list_dataflows
from trade_intel.insights import (
    fmt_usd,
    fmt_number,
    score_badge,
    summarize_destinations,
    summarize_opportunities,
    summarize_corridor,
    summarize_country_profile,
)
from trade_intel.opportunities import rank_exporter_opportunities
from trade_intel.product_drilldown import ProductDrilldown, build_bilateral_product_drilldown
from trade_intel.wits_timeseries import fetch_bilateral_export_series
from trade_intel.worldbank_data import (
    country_profile,
    market_attractiveness_score,
    cagr_from_series,
    INDICATOR_LABELS,
    GDP_PERCAPITA,
    GDP_GROWTH,
    FDI_INFLOWS,
    TRADE_PCT_GDP,
    POPULATION,
    INFLATION,
    EXPORTS_PCT_GDP,
)


# ── Custom CSS / Theme ────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Dark sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1117 0%, #1a1f2e 100%);
    border-right: 1px solid rgba(99,179,237,0.15);
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #63b3ed !important;
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
}

/* ── Main background ── */
.stApp {
    background: linear-gradient(135deg, #0d1117 0%, #161b27 50%, #0d1117 100%);
    color: #e2e8f0;
}

/* ── Hero banner ── */
.hero-banner {
    background: linear-gradient(135deg, #1a2744 0%, #0f2460 40%, #1a3a6e 100%);
    border: 1px solid rgba(99,179,237,0.25);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(99,179,237,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.3rem 0;
    line-height: 1.2;
}
.hero-title span {
    background: linear-gradient(90deg, #63b3ed, #90cdf4, #4facfe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-subtitle {
    font-size: 1rem;
    color: #a0aec0;
    margin: 0;
    font-weight: 400;
}
.hero-badges {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}
.hero-badge {
    background: rgba(99,179,237,0.12);
    border: 1px solid rgba(99,179,237,0.3);
    color: #90cdf4;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ── KPI metric cards ── */
.kpi-card {
    background: linear-gradient(135deg, #1a2035 0%, #1e2640 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    transition: border-color 0.2s ease, transform 0.2s ease;
}
.kpi-card:hover {
    border-color: rgba(99,179,237,0.5);
    transform: translateY(-2px);
}
.kpi-label {
    font-size: 0.75rem;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-family: 'Outfit', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #63b3ed;
    line-height: 1;
}
.kpi-sub {
    font-size: 0.78rem;
    color: #68d391;
    margin-top: 0.3rem;
}
.kpi-sub.negative {
    color: #fc8181;
}

/* ── Insight box ── */
.insight-box {
    background: linear-gradient(135deg, rgba(26,45,80,0.6) 0%, rgba(26,37,65,0.8) 100%);
    border-left: 3px solid #63b3ed;
    border-radius: 0 10px 10px 0;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0 1.2rem 0;
}
.insight-box.warning {
    border-left-color: #f6ad55;
    background: linear-gradient(135deg, rgba(60,40,10,0.5) 0%, rgba(50,35,10,0.7) 100%);
}
.insight-box.success {
    border-left-color: #68d391;
    background: linear-gradient(135deg, rgba(10,50,30,0.5) 0%, rgba(10,45,25,0.7) 100%);
}
.insight-box p, .insight-box li {
    color: #e2e8f0;
    margin: 0.2rem 0;
    font-size: 0.9rem;
}

/* ── Section headers ── */
.section-header {
    font-family: 'Outfit', sans-serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: #e2e8f0;
    border-bottom: 2px solid rgba(99,179,237,0.3);
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
}

/* ── Data source pills ── */
.source-pill {
    display: inline-block;
    background: rgba(99,179,237,0.1);
    border: 1px solid rgba(99,179,237,0.25);
    color: #90cdf4;
    border-radius: 4px;
    padding: 0.1rem 0.5rem;
    font-size: 0.72rem;
    font-weight: 500;
    margin-right: 0.3rem;
}

/* ── Attractiveness rating ── */
.attr-badge {
    font-size: 1rem;
    font-weight: 600;
    padding: 0.3rem 0.8rem;
    border-radius: 8px;
    display: inline-block;
    margin-top: 0.5rem;
}
.attr-high { background: rgba(104,211,145,0.15); color: #68d391; border: 1px solid rgba(104,211,145,0.3); }
.attr-medium { background: rgba(246,173,85,0.15); color: #f6ad55; border: 1px solid rgba(246,173,85,0.3); }
.attr-low { background: rgba(252,129,129,0.15); color: #fc8181; border: 1px solid rgba(252,129,129,0.3); }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(26,31,46,0.8);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #a0aec0;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.6rem 1.2rem;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2b4c8c 0%, #1a3a6e 100%) !important;
    color: #90cdf4 !important;
    box-shadow: 0 2px 8px rgba(99,179,237,0.2);
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2b6cb0 0%, #1a4a8a 100%);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(43,108,176,0.3);
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%);
    box-shadow: 0 4px 16px rgba(43,108,176,0.5);
    transform: translateY(-1px);
}

/* ── Dataframe styling ── */
.stDataFrame {
    border: 1px solid rgba(99,179,237,0.15) !important;
    border-radius: 8px !important;
}

/* ── Score badges in tables ── */
.score-high { color: #68d391; font-weight: 600; }
.score-med { color: #f6ad55; font-weight: 600; }
.score-low { color: #fc8181; font-weight: 600; }

/* ── Dividers ── */
hr {
    border-color: rgba(99,179,237,0.15) !important;
}

/* ── Captions ── */
.stCaption, .caption {
    color: #718096 !important;
    font-size: 0.82rem !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(26,31,46,0.6) !important;
    border: 1px solid rgba(99,179,237,0.15) !important;
    border-radius: 8px !important;
    color: #a0aec0 !important;
}

/* ── Select boxes & inputs ── */
.stSelectbox > div > div,
.stTextInput > div > div,
.stNumberInput > div > div {
    background: rgba(26,31,46,0.9) !important;
    border-color: rgba(99,179,237,0.2) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
</style>
"""


# ── Shared utilities ──────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner="Loading country list…")
def _all_countries() -> list[Country]:
    return sorted(
        [c for c in list_countries() if c.iso3],
        key=lambda c: c.name.lower(),
    )


def _country_selectbox(
    label: str,
    *,
    default_iso3: str,
    key: str | None = None,
    help: str | None = None,
) -> str:
    countries = _all_countries()
    labels = [f"{c.name} ({c.iso3})" for c in countries]
    iso_list = [c.iso3 for c in countries]
    try:
        default_idx = iso_list.index(default_iso3.upper())
    except ValueError:
        default_idx = 0
    choice = st.selectbox(
        label,
        options=labels,
        index=default_idx,
        key=key,
        help=help or "Pick by country name; ISO3 is filled automatically.",
    )
    return iso_list[labels.index(choice)]


def _period_options(freq_code: str, *, annual_start: int = 2000, monthly_count: int = 36) -> list[str]:
    today = date.today()
    if freq_code == "M":
        year = today.year
        month = today.month - 1
        if month == 0:
            year -= 1
            month = 12
        options: list[str] = []
        for _ in range(monthly_count):
            options.append(f"{year}{month:02d}")
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        return options
    latest_year = max(annual_start, today.year - 1)
    return [str(year) for year in range(latest_year, annual_start - 1, -1)]


def _period_selectbox(
    label: str,
    *,
    freq_code: str,
    default_period: str,
    key: str,
    help: str | None = None,
) -> str:
    options = _period_options(freq_code)
    try:
        default_idx = options.index(default_period)
    except ValueError:
        default_idx = 0
    return st.selectbox(label, options=options, index=default_idx, key=key, help=help)


# ── Chart helpers ─────────────────────────────────────────────────────────────

_CHART_COLOR = "#63b3ed"
_ACCENT_GRADIENT = ["#63b3ed", "#4299e1", "#3182ce", "#2b6cb0", "#2c5282"]


def _bar_chart(df: pd.DataFrame, *, x_col: str, y_col: str, color: str = _CHART_COLOR, height: int = 360) -> None:
    chart = (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{x_col}:N", sort=None, axis=alt.Axis(labelAngle=-45, title=None, labelColor="#a0aec0", domainColor="rgba(99,179,237,0.2)", gridColor="transparent")),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=True), axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)", domainColor="transparent")),
            tooltip=[x_col, y_col],
            opacity=alt.value(0.9),
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def _line_chart(df: pd.DataFrame, *, x_col: str, y_col: str, color: str = _CHART_COLOR, height: int = 320) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(color=color, point=alt.OverlayMarkDef(color=color, filled=True, size=60), strokeWidth=2.5)
        .encode(
            x=alt.X(f"{x_col}:O", axis=alt.Axis(labelAngle=-45, title=None, labelColor="#a0aec0", domainColor="rgba(99,179,237,0.2)", gridColor="transparent")),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=False), axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)", domainColor="transparent")),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def _multi_line_chart(df: pd.DataFrame, *, x_col: str, y_col: str, series_col: str, height: int = 360) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=50), strokeWidth=2)
        .encode(
            x=alt.X(f"{x_col}:O", axis=alt.Axis(labelAngle=-45, title=None, labelColor="#a0aec0", domainColor="rgba(99,179,237,0.2)", gridColor="transparent")),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=False), axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)", domainColor="transparent")),
            color=alt.Color(f"{series_col}:N", title=None, scale=alt.Scale(scheme="blues")),
            tooltip=[x_col, series_col, y_col],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def _choropleth_map(df: pd.DataFrame, *, locations_col: str, color_col: str, title: str = "", height: int = 400) -> None:
    """Render a world choropleth map of export values."""
    fig = px.choropleth(
        df,
        locations=locations_col,
        color=color_col,
        hover_name=locations_col,
        color_continuous_scale="Blues",
        title=title,
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            bgcolor="rgba(13,17,23,0.9)",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="rgba(99,179,237,0.2)",
            showland=True,
            landcolor="#1a2035",
            showocean=True,
            oceancolor="#0d1117",
            showcountries=True,
            countrycolor="rgba(99,179,237,0.1)",
        ),
        coloraxis_colorbar=dict(
            bgcolor="rgba(26,31,46,0.8)",
            tickfont=dict(color="#a0aec0"),
            title=dict(font=dict(color="#a0aec0")),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=height,
        font=dict(color="#a0aec0"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _wb_line_chart(series: list[tuple[str, float]], *, indicator_label: str, height: int = 240) -> None:
    if not series:
        st.caption("No data available.")
        return
    df = pd.DataFrame(series, columns=["Year", indicator_label])
    _line_chart(df, x_col="Year", y_col=indicator_label, height=height)


# ── IMF-specific helpers ──────────────────────────────────────────────────────

def _imf_time_series_chart(df: pd.DataFrame) -> None:
    if "TIME_PERIOD" not in df.columns or "value" not in df.columns:
        return
    chart_df = df.copy()
    chart_df["value"] = pd.to_numeric(chart_df["value"], errors="coerce")
    chart_df = chart_df.dropna(subset=["value"])
    if chart_df.empty:
        return
    chart_df["_time"] = pd.to_datetime(
        chart_df["TIME_PERIOD"].astype(str).str.replace("-M", "-", regex=False),
        errors="coerce",
    )
    group_col = next(
        (col for col in ("COUNTRY", "INDICATOR", "INDEX_TYPE", "COICOP_1999", "FREQUENCY") if col in chart_df.columns),
        None,
    )
    tooltip_cols = [col for col in ("TIME_PERIOD", group_col, "value") if col]
    if chart_df["_time"].notna().any():
        chart_df = chart_df.dropna(subset=["_time"]).sort_values("_time").head(5000)
        if group_col:
            chart = (
                alt.Chart(chart_df)
                .mark_line(point=True, strokeWidth=2)
                .encode(
                    x=alt.X("_time:T", title=None, axis=alt.Axis(labelColor="#a0aec0")),
                    y=alt.Y("value:Q", title=None, axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)")),
                    color=alt.Color(f"{group_col}:N", title=None, scale=alt.Scale(scheme="blues")),
                    tooltip=tooltip_cols,
                )
                .properties(height=360)
                .configure_view(strokeOpacity=0, fill="transparent")
                .configure(background="transparent")
            )
        else:
            chart = (
                alt.Chart(chart_df)
                .mark_line(point=True, color=_CHART_COLOR, strokeWidth=2.5)
                .encode(
                    x=alt.X("_time:T", title=None, axis=alt.Axis(labelColor="#a0aec0")),
                    y=alt.Y("value:Q", title=None, axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)")),
                    tooltip=tooltip_cols,
                )
                .properties(height=360)
                .configure_view(strokeOpacity=0, fill="transparent")
                .configure(background="transparent")
            )
    else:
        chart_df = chart_df.head(200)
        enc_x = alt.X("TIME_PERIOD:O", title=None, axis=alt.Axis(labelAngle=-45, labelColor="#a0aec0"))
        enc_y = alt.Y("value:Q", title=None, axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)"))
        if group_col:
            chart = (
                alt.Chart(chart_df)
                .mark_line(point=True, strokeWidth=2)
                .encode(x=enc_x, y=enc_y, color=alt.Color(f"{group_col}:N", title=None, scale=alt.Scale(scheme="blues")), tooltip=tooltip_cols)
                .properties(height=360)
                .configure_view(strokeOpacity=0, fill="transparent")
                .configure(background="transparent")
            )
        else:
            chart = (
                alt.Chart(chart_df)
                .mark_line(point=True, color=_CHART_COLOR, strokeWidth=2.5)
                .encode(x=enc_x, y=enc_y, tooltip=tooltip_cols)
                .properties(height=360)
                .configure_view(strokeOpacity=0, fill="transparent")
                .configure(background="transparent")
            )
    st.altair_chart(chart, use_container_width=True)


def _imf_period_options(freq_code: str, *, years_back: int = 25) -> list[str]:
    today = date.today()
    freq = (freq_code or "").upper()
    if freq == "M":
        year, month = today.year, today.month
        options: list[str] = []
        for _ in range(years_back * 12):
            options.append(f"{year}-M{month:02d}")
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return options
    if freq == "Q":
        quarter = ((today.month - 1) // 3) + 1
        year = today.year
        options = []
        for _ in range(years_back * 4):
            options.append(f"{year}-Q{quarter}")
            quarter -= 1
            if quarter == 0:
                quarter = 4
                year -= 1
        return options
    if freq == "A":
        return [str(year) for year in range(today.year, today.year - years_back, -1)]
    return []


def _imf_default_values(dim_id: str) -> list[str]:
    defaults = {
        "COUNTRY": ["USA", "CAN"],
        "INDEX_TYPE": ["CPI"],
        "COICOP_1999": ["CP01"],
        "TYPE_OF_TRANSFORMATION": ["IX"],
        "FREQUENCY": ["M"],
    }
    return defaults.get(dim_id, [])


def _imf_option_label_map(options: list[dict[str, str]]) -> dict[str, str]:
    return {row["value"]: f"{row['value']} - {row['label']}" for row in options}


def _parse_kv_lines(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise ValueError(f"Expected KEY=VALUE format, got: {raw}")
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Parameter name cannot be blank: {raw}")
        params[name] = value.strip()
    return params


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _configure() -> None:
    st.sidebar.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem 0;'>
        <div style='font-family: Outfit, sans-serif; font-size: 1.4rem; font-weight: 700; color: #63b3ed;'>
            🌐 TradeNexus
        </div>
        <div style='font-size: 0.72rem; color: #718096; margin-top: 0.2rem;'>
            Trade Intelligence Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    with st.sidebar.expander("⚙️ Settings", expanded=False):
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
    st.sidebar.markdown("""
    <div style='padding: 0.5rem 0;'>
        <div style='font-family: Outfit, sans-serif; font-size: 0.85rem; font-weight: 600; color: #a0aec0; margin-bottom: 0.6rem;'>
            📡 Data Sources
        </div>
        <div style='font-size: 0.78rem; color: #718096; line-height: 1.8;'>
            🔵 <b style='color:#90cdf4'>UN Comtrade</b><br>
            &nbsp;&nbsp;&nbsp;Export/import flows, product codes<br>
            🟢 <b style='color:#90cdf4'>World Bank WITS</b><br>
            &nbsp;&nbsp;&nbsp;Bilateral trade time series<br>
            🟡 <b style='color:#90cdf4'>World Bank Indicators</b><br>
            &nbsp;&nbsp;&nbsp;GDP, FDI, population, inflation<br>
            🟠 <b style='color:#90cdf4'>IMF SDMX</b><br>
            &nbsp;&nbsp;&nbsp;Monetary & macro indicators
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()
    st.sidebar.markdown("""
    <div style='font-size: 0.72rem; color: #4a5568; text-align: center; padding: 0.5rem 0;'>
        Data is cached locally for 24h.<br>
        Public APIs — no authentication required for most features.
    </div>
    """, unsafe_allow_html=True)


# ── Hero banner ───────────────────────────────────────────────────────────────

def _render_hero() -> None:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">Trade<span>Nexus</span></div>
        <div class="hero-subtitle">
            Global trade intelligence for investors, businesses & entrepreneurs.
            Discover markets, benchmark corridors, and identify growth opportunities.
        </div>
        <div class="hero-badges">
            <span class="hero-badge">🌍 Export Markets</span>
            <span class="hero-badge">📈 Trade Trends</span>
            <span class="hero-badge">🚀 Opportunity Scoring</span>
            <span class="hero-badge">🌐 Country Profiles</span>
            <span class="hero-badge">🏦 Macro Intelligence</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Insight box renderer ──────────────────────────────────────────────────────

def _render_insights(insights: list[str], box_class: str = "") -> None:
    if not insights:
        return
    lines = "".join(f"<p>• {line}</p>" for line in insights)
    st.markdown(f'<div class="insight-box {box_class}">{lines}</div>', unsafe_allow_html=True)


def _kpi_card(label: str, value: str, sub: str = "", negative: bool = False) -> str:
    sub_class = "kpi-sub negative" if negative else "kpi-sub"
    sub_html = f'<div class="{sub_class}">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


# ── Tab 1: Market Explorer ────────────────────────────────────────────────────

def _tab_market_explorer() -> None:
    st.markdown('<div class="section-header">🌍 Market Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        "Discover **where your country's goods are flowing**. Identify top destination markets, "
        "analyze export concentration risk, and spot emerging corridors.",
        unsafe_allow_html=False,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        country = _country_selectbox("Reporting country", default_iso3="KEN", key="tab1_country",
                                     help="Exports originate here.")
    with c2:
        view_mode = st.selectbox("View mode", ("Last 10 years", "Single period"), key="tab1_mode")
    with c3:
        cmd = st.text_input("HS code (or TOTAL)", "TOTAL", key="tab1_cmd")
    with c4:
        top_n = st.slider("Destinations to show", 5, 50, 15, key="tab1_topn")

    history_years = recent_annual_years(count=10)
    if view_mode == "Last 10 years":
        period = history_years[0]
        freq = "A"
    else:
        s1, s2 = st.columns(2)
        with s1:
            freq = st.selectbox("Frequency", ("A", "M"), key="tab1_freq")
        with s2:
            period = _period_selectbox(
                "Period", freq_code=freq,
                default_period="2020" if freq == "A" else _period_options("M")[0],
                key="tab1_period",
            )

    if st.button("🔍 Load destinations", type="primary", key="tab1_load"):
        if view_mode == "Last 10 years":
            with st.spinner("Fetching Comtrade 10-year history…"):
                history_df, _ = fetch_export_history(
                    country, year_from=int(history_years[-1]), year_to=int(history_years[0]), cmd_code=cmd,
                )
            st.session_state["tab1_history_df"] = history_df
            available_history_years = (
                sorted(history_df["period"].astype(str).unique().tolist(), reverse=True)
                if not history_df.empty else []
            )
            st.session_state["tab1_history_year_options"] = available_history_years
            period = available_history_years[0] if available_history_years else period
            if available_history_years:
                with st.spinner("Fetching annual destination trends…"):
                    annual_trends_df, _ = annual_export_destination_trends(
                        country, years=available_history_years, cmd_code=cmd, top_n=min(max(5, top_n), 8),
                    )
                st.session_state["tab1_destination_trends_df"] = annual_trends_df
            else:
                st.session_state["tab1_destination_trends_df"] = pd.DataFrame()
        else:
            st.session_state["tab1_history_df"] = None
            st.session_state["tab1_history_year_options"] = []
            st.session_state["tab1_destination_trends_df"] = None

        with st.spinner("Fetching Comtrade preview…"):
            df, resolved = top_export_destinations(country, period=period, freq_code=freq, cmd_code=cmd, top_n=top_n)
        st.session_state.update({
            "tab1_destinations_df": df,
            "tab1_destinations_reporter_iso3": resolved.iso3,
            "tab1_destinations_reporter_name": resolved.name,
            "tab1_destinations_period": period,
            "tab1_destinations_freq": freq,
            "tab1_destinations_mode": view_mode,
            "tab1_destinations_cmd": cmd,
            "tab1_drilldown": None,
        })

    # ── Render results ──
    dest_df = st.session_state.get("tab1_destinations_df")
    dest_reporter_iso3 = st.session_state.get("tab1_destinations_reporter_iso3")
    dest_reporter_name = st.session_state.get("tab1_destinations_reporter_name")
    dest_period = st.session_state.get("tab1_destinations_period")
    dest_freq = st.session_state.get("tab1_destinations_freq", "A")
    dest_mode = st.session_state.get("tab1_destinations_mode")
    dest_cmd = st.session_state.get("tab1_destinations_cmd", "TOTAL")
    dest_history_df = st.session_state.get("tab1_history_df")
    dest_history_year_options = st.session_state.get("tab1_history_year_options", [])
    dest_trends_df = st.session_state.get("tab1_destination_trends_df")

    if dest_df is not None and dest_reporter_iso3 and dest_reporter_name and dest_period:
        # Reporter KPI strip
        total_exports = float(dest_df["primaryValue"].sum()) if "primaryValue" in dest_df.columns and not dest_df.empty else 0
        n_partners = len(dest_df)
        top1_share = 100 * float(dest_df.iloc[0]["primaryValue"]) / total_exports if total_exports > 0 and not dest_df.empty else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(_kpi_card("Reporter", dest_reporter_name, dest_reporter_iso3), unsafe_allow_html=True)
        with k2:
            st.markdown(_kpi_card("Total exports", fmt_usd(total_exports), f"Period: {dest_period}"), unsafe_allow_html=True)
        with k3:
            st.markdown(_kpi_card("Destination markets", str(n_partners), "in this result set"), unsafe_allow_html=True)
        with k4:
            st.markdown(_kpi_card("Top market share", f"{top1_share:.0f}%", dest_df.iloc[0]["partnerDesc"] if not dest_df.empty and "partnerDesc" in dest_df.columns else ""), unsafe_allow_html=True)

        st.markdown("")

        # Insight callout
        insights = summarize_destinations(dest_df, dest_reporter_name, period=str(dest_period), cmd=dest_cmd)
        box_class = "warning" if top1_share >= 80 else ("success" if top1_share < 50 else "")
        _render_insights(insights, box_class=box_class)

        if dest_mode == "Last 10 years" and dest_history_year_options:
            try:
                default_year_idx = dest_history_year_options.index(str(dest_period))
            except ValueError:
                default_year_idx = 0
            selected_table_year = st.selectbox(
                "Snapshot year", options=dest_history_year_options, index=default_year_idx,
                key="tab1_destination_year",
                help="Switch year for the snapshot without reloading the trend charts.",
            )
            if selected_table_year != str(dest_period):
                with st.spinner("Fetching Comtrade preview…"):
                    dest_df, resolved = top_export_destinations(
                        dest_reporter_iso3, period=selected_table_year,
                        freq_code=dest_freq, cmd_code=dest_cmd, top_n=top_n,
                    )
                dest_reporter_iso3 = resolved.iso3
                dest_reporter_name = resolved.name
                dest_period = selected_table_year
                st.session_state["tab1_destinations_df"] = dest_df
                st.session_state["tab1_destinations_period"] = dest_period
                st.session_state["tab1_drilldown"] = None

        # World map
        if not dest_df.empty and "partnerCode" in dest_df.columns and "primaryValue" in dest_df.columns:
            st.markdown('<div class="section-header">🗺️ World Export Map</div>', unsafe_allow_html=True)
            st.caption("Choropleth view of export flows by destination.")
            map_df = dest_df.copy()
            from trade_intel.partner_codes import partner_code_to_iso3

            map_df["iso3"] = map_df["partnerCode"].apply(
                lambda c: partner_code_to_iso3(c) if c is not None else None
            )
            map_df = map_df.dropna(subset=["iso3"])
            map_df["primaryValue"] = pd.to_numeric(map_df["primaryValue"], errors="coerce")
            if not map_df.empty:
                _choropleth_map(
                    map_df,
                    locations_col="iso3",
                    color_col="primaryValue",
                    title=f"{dest_reporter_name} export destinations ({dest_period})",
                )

        # 10-year history section
        if dest_mode == "Last 10 years" and isinstance(dest_history_df, pd.DataFrame):
            st.markdown('<div class="section-header">📊 10-Year Export History</div>', unsafe_allow_html=True)
            st.caption(f"Annual UN Comtrade exports for HS `{dest_cmd}` — total to world.")
            if dest_history_df.empty:
                st.warning("No annual history rows returned for this country and HS code.")
            else:
                hist_chart = dest_history_df.rename(columns={"period": "Year", "export_usd": "Export (USD)"})
                _bar_chart(hist_chart, x_col="Year", y_col="Export (USD)")

            if isinstance(dest_trends_df, pd.DataFrame) and not dest_trends_df.empty:
                st.markdown('<div class="section-header">🗺️ Top Partner Market Trends</div>', unsafe_allow_html=True)
                st.caption("Trade flows to your leading destination markets across the 10-year window.")
                trends_chart = dest_trends_df.rename(
                    columns={"period": "Year", "partnerDesc": "Partner", "export_usd": "Export (USD)"}
                )
                _multi_line_chart(trends_chart, x_col="Year", y_col="Export (USD)", series_col="Partner")
                with st.expander("📋 Data table — annual partner pivot"):
                    trends_pivot = (
                        trends_chart.pivot_table(
                            index="Partner", columns="Year", values="Export (USD)",
                            aggfunc="sum", fill_value=0.0,
                        )
                        .reindex(sorted(trends_chart["Year"].astype(str).unique().tolist()), axis=1)
                        .sort_index()
                    )
                    st.dataframe(trends_pivot, use_container_width=True)

        # Destination snapshot + choropleth
        if not dest_df.empty:
            st.markdown('<div class="section-header">📍 Destination Snapshot</div>', unsafe_allow_html=True)

            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.caption(f"Destination ranking for `{dest_period}`, HS `{dest_cmd}`.")
                # Format value column
                display_df = dest_df.copy()
                if "primaryValue" in display_df.columns:
                    display_df["Export (USD)"] = display_df["primaryValue"].apply(
                        lambda v: fmt_usd(float(v)) if pd.notna(v) else "N/A"
                    )
                    total = display_df["primaryValue"].sum()
                    display_df["Share %"] = display_df["primaryValue"].apply(
                        lambda v: f"{100*float(v)/total:.1f}%" if total > 0 and pd.notna(v) else "—"
                    )
                    disp_cols = [c for c in ["partnerDesc", "Export (USD)", "Share %", "period", "cmdDesc"] if c in display_df.columns]
                    display_df = display_df.rename(columns={"partnerDesc": "Partner", "period": "Period", "cmdDesc": "Product"})
                    disp_cols = ["Partner", "Export (USD)", "Share %"] + [c for c in ["Period", "Product"] if c in display_df.columns]
                    st.dataframe(display_df[disp_cols], use_container_width=True, hide_index=True)

            with col_right:
                if "primaryValue" in dest_df.columns and "partnerDesc" in dest_df.columns:
                    chart = dest_df.rename(columns={"partnerDesc": "Partner", "primaryValue": "Export (USD)"}).head(15)
                    _bar_chart(chart, x_col="Partner", y_col="Export (USD)")

            # Product drill-down
            st.divider()
            st.markdown('<div class="section-header">🔬 Product Drill-Down</div>', unsafe_allow_html=True)
            st.caption(
                f"Pick a destination from the {dest_period} snapshot to see which HS products are exported and WITS corridor context."
            )

            partner_lookup: dict[str, int] = {}
            for row in dest_df.itertuples(index=False):
                partner_desc = str(getattr(row, "partnerDesc", "") or "").strip()
                partner_code = getattr(row, "partnerCode", None)
                if not partner_desc or partner_code is None:
                    continue
                if hasattr(partner_code, "item"):
                    try:
                        partner_code = partner_code.item()
                    except (ValueError, AttributeError):
                        pass
                label = f"{partner_desc} ({partner_code})"
                try:
                    partner_lookup[label] = int(partner_code)
                except (TypeError, ValueError):
                    continue

            if not partner_lookup:
                st.info("No selectable destination country found in the current result set.")
            else:
                d1, d2, d3 = st.columns(3)
                with d1:
                    selected_partner = st.selectbox("Destination country", options=list(partner_lookup.keys()), key="tab1_partner_select")
                with d2:
                    hs_level = st.selectbox("HS detail level", ("AG2", "AG4", "AG6"), help="AG2=chapter, AG4=heading, AG6=product.", key="tab1_hs_level")
                with d3:
                    product_rows = st.slider("Products to show", 5, 50, 15, key="tab1_products_to_show")
                d4, d5, d6 = st.columns(3)
                with d4:
                    dy0, dy1 = st.slider("WITS context years", 2000, 2023, (2018, 2022), key="tab1_wits_window")
                with d5:
                    wits_product = st.text_input("WITS product", "total", key="tab1_wits_product")
                with d6:
                    include_mirror = st.checkbox("Include mirror context", value=True, key="tab1_wits_mirror")

                if st.button("🔬 Load product drill-down", key="tab1_drilldown_button", type="primary"):
                    partner_code = partner_lookup[selected_partner]
                    try:
                        partner_country = resolve_country(str(partner_code))
                    except ValueError:
                        st.session_state["tab1_drilldown"] = None
                        st.error("Selected destination could not be resolved to a country.")
                    else:
                        with st.spinner("Fetching product detail and corridor context…"):
                            st.session_state["tab1_drilldown"] = build_bilateral_product_drilldown(
                                dest_reporter_iso3, partner_country,
                                period=dest_period, freq_code=dest_freq, hs_level=hs_level,
                                top_n=int(product_rows), wits_year_from=int(dy0), wits_year_to=int(dy1),
                                wits_product=wits_product, include_mirror=include_mirror,
                            )

                drilldown = st.session_state.get("tab1_drilldown")
                if isinstance(drilldown, ProductDrilldown):
                    st.caption(
                        f"Corridor: **{drilldown.exporter.name}** ({drilldown.exporter.iso3}) → "
                        f"**{drilldown.importer.name}** ({drilldown.importer.iso3}), "
                        f"period `{drilldown.period}`, HS `{drilldown.hs_level}`"
                    )
                    for note in drilldown.notes:
                        st.caption(note)
                    if drilldown.products.empty:
                        st.warning("No product-level rows returned for the selected corridor.")
                    else:
                        st.dataframe(drilldown.products, use_container_width=True, hide_index=True)
                        chart = drilldown.products.rename(columns={"product": "Product", "export_usd": "Export (USD)"})
                        _bar_chart(chart[["Product", "Export (USD)"]].head(15), x_col="Product", y_col="Export (USD)")
                    if drilldown.export_series:
                        st.markdown("**WITS corridor context — export trend**")
                        trend_df = pd.DataFrame(drilldown.export_series, columns=["Year", "Export (US$ thousand)"])
                        _line_chart(trend_df, x_col="Year", y_col="Export (US$ thousand)")
                    if drilldown.mirror_series:
                        st.markdown("**WITS mirror context — import-reported flow**")
                        mirror_df = pd.DataFrame(drilldown.mirror_series, columns=["Year", "Import mirror (US$ thousand)"])
                        _line_chart(mirror_df, x_col="Year", y_col="Import mirror (US$ thousand)")


# ── Tab 2: Corridor Trends ────────────────────────────────────────────────────

def _tab_corridor_trends() -> None:
    st.markdown('<div class="section-header">📈 Corridor Trends</div>', unsafe_allow_html=True)
    st.markdown(
        "Analyze **bilateral trade trends** between any two countries over time. "
        "Track whether a corridor is growing, stagnating, or declining — and compute CAGR.",
    )

    e1, e2, e3 = st.columns(3)
    with e1:
        exp = _country_selectbox("Exporting country", default_iso3="KEN", key="texp")
    with e2:
        imp = _country_selectbox("Importing country", default_iso3="USA", key="timp")
    with e3:
        y0, y1 = st.slider("Year range", 2000, 2023, (2018, 2022), key="tcorr_years")

    p1, p2 = st.columns(2)
    with p1:
        product = st.text_input("WITS product group", "total", key="tprod",
                                help="Use 'total' for all goods, or a product group code.")
    with p2:
        mirror = st.checkbox("Include mirror import series", value=False, key="tcorr_mirror")

    if st.button("📈 Load corridor trend", type="primary", key="tcorr_load"):
        with st.spinner("Fetching WITS bilateral series…"):
            series = fetch_bilateral_export_series(exp, imp, y0, y1, product=product.lower())
        st.session_state["tcorr_series"] = series
        st.session_state["tcorr_exp"] = exp
        st.session_state["tcorr_imp"] = imp
        st.session_state["tcorr_mirror_series"] = None
        if mirror:
            from trade_intel.wits_timeseries import fetch_bilateral_import_series
            with st.spinner("Fetching mirror import series…"):
                mseries = fetch_bilateral_import_series(exp, imp, y0, y1, product=product.lower())
            st.session_state["tcorr_mirror_series"] = mseries

    series = st.session_state.get("tcorr_series")
    exp_name = st.session_state.get("tcorr_exp", exp)
    imp_name = st.session_state.get("tcorr_imp", imp)
    mseries = st.session_state.get("tcorr_mirror_series")

    if series is not None:
        if not series:
            st.error("No WITS data found for this corridor and period. Try adjusting the year range or product.")
        else:
            # Insight callout
            insights = summarize_corridor(series, exp_name, imp_name)
            _render_insights(insights)

            tdf = pd.DataFrame(series, columns=["Year", "Export (US$ thousand)"])
            _line_chart(tdf, x_col="Year", y_col="Export (US$ thousand)")

            # Summary metrics
            if len(series) >= 2:
                y0_s, v0_s = series[0]
                y_last_s, v_last_s = series[-1]
                span_s = int(y_last_s) - int(y0_s)
                cagr_val = None
                if span_s > 0 and v0_s > 0 and v_last_s > 0:
                    cagr_val = ((v_last_s / v0_s) ** (1.0 / span_s) - 1.0) * 100

                mk1, mk2, mk3 = st.columns(3)
                with mk1:
                    st.markdown(_kpi_card("Start value", fmt_usd(v0_s * 1000), str(y0_s)), unsafe_allow_html=True)
                with mk2:
                    st.markdown(_kpi_card("Latest value", fmt_usd(v_last_s * 1000), str(y_last_s)), unsafe_allow_html=True)
                with mk3:
                    if cagr_val is not None:
                        neg = cagr_val < 0
                        st.markdown(_kpi_card("CAGR", f"{cagr_val:+.1f}%", f"Over {span_s} years", negative=neg), unsafe_allow_html=True)

            with st.expander("📋 Raw data"):
                st.dataframe(tdf, use_container_width=True, hide_index=True)

        if mseries:
            st.markdown('<div class="section-header">🔄 Mirror: Importer-Reported Flows</div>', unsafe_allow_html=True)
            insights_m = summarize_corridor(mseries, imp_name, exp_name)
            _render_insights(insights_m)
            mdf = pd.DataFrame(mseries, columns=["Year", "Import mirror (US$ thousand)"])
            _line_chart(mdf, x_col="Year", y_col="Import mirror (US$ thousand)")


# ── Tab 3: Opportunity Ranker ─────────────────────────────────────────────────

def _tab_opportunity_ranker() -> None:
    st.markdown('<div class="section-header">🚀 Opportunity Ranker</div>', unsafe_allow_html=True)
    st.markdown(
        "Rank export destination markets by a blended **Opportunity Score** that combines "
        "current market size (Comtrade) and historical trade growth rate (WITS CAGR). "
        "Use this to prioritize where to focus business development efforts.",
    )

    with st.expander("ℹ️ How the score is calculated", expanded=False):
        st.markdown("""
        **Opportunity Score = 0.62 × Size + 0.38 × Growth**

        - **Size** (0–1): Log-scaled bilateral export value from WITS, normalized against the largest partner
        - **Growth** (0–1): CAGR of bilateral exports over the selected WITS window, scaled 0–20%+

        | Score | Rating | Interpretation |
        |-------|--------|----------------|
        | ≥ 0.65 | 🟢 High | Large, fast-growing market — prioritize |
        | 0.40–0.65 | 🟡 Medium | Solid opportunity — worth exploring |
        | < 0.40 | 🔴 Low | Smaller or slower-growing market |
        """)

    o1, o2 = st.columns(2)
    with o1:
        sc = _country_selectbox("Supplier / exporter country", default_iso3="KEN", key="oc")
        fq = st.selectbox("Comtrade frequency", ("A", "M"), key="of")
        p = _period_selectbox(
            "Comtrade period", freq_code=fq,
            default_period="2020" if fq == "A" else _period_options("M")[0],
            key="op",
        )
        hs = st.text_input("HS pool (or TOTAL)", "TOTAL", key="oh")
    with o2:
        pool = st.number_input("Destination pool size", 10, 50, 25, key="opool",
                               help="How many top Comtrade destinations to score.")
        out_n = st.number_input("Top results to display", 5, 30, 15, key="ooutn")
        wy0, wy1 = st.slider("WITS scoring window", 2000, 2023, (2018, 2022), key="ow")
        wprod = st.text_input("WITS product", "total", key="owp")

    if st.button("🚀 Compute opportunities", type="primary", key="ocompute"):
        with st.spinner("Ranking markets — this may take a minute (rate-limited API calls)…"):
            df, resolved = rank_exporter_opportunities(
                sc, comtrade_period=p, comtrade_freq=fq, cmd_code=hs,
                pool_size=int(pool), score_count=int(out_n),
                wits_year_from=int(wy0), wits_year_to=int(wy1), product=wprod,
            )
        st.session_state["opp_df"] = df
        st.session_state["opp_reporter"] = resolved

    df_opp = st.session_state.get("opp_df")
    reporter_opp = st.session_state.get("opp_reporter")

    if df_opp is not None and reporter_opp is not None:
        # Reporter KPI
        st.markdown(
            f'<span class="source-pill">Reporter</span> **{reporter_opp.name}** ({reporter_opp.iso3})',
            unsafe_allow_html=True,
        )
        st.markdown("")

        # Insight callout
        insights = summarize_opportunities(df_opp, reporter_opp.name)
        _render_insights(insights)

        if df_opp.empty:
            st.warning("No scored rows returned.")
        else:
            # Add score badge column
            display_df = df_opp.copy()
            if "opportunity" in display_df.columns:
                display_df["Score"] = display_df["opportunity"].apply(score_badge)
            if "cagr" in display_df.columns:
                display_df["CAGR"] = display_df["cagr"].apply(
                    lambda v: f"{v*100:+.1f}%" if v is not None and not (isinstance(v, float) and math.isnan(v)) else "N/A"
                )
            if "wits_latest_kusd" in display_df.columns:
                display_df["Latest flow"] = display_df["wits_latest_kusd"].apply(
                    lambda v: fmt_usd(float(v) * 1000) if v is not None else "N/A"
                )
            if "comtrade_export_usd" in display_df.columns:
                display_df["Comtrade export"] = display_df["comtrade_export_usd"].apply(
                    lambda v: fmt_usd(float(v)) if v is not None else "N/A"
                )

            # Column selection for display
            show_cols = []
            for col_pair in [("partner", "Market"), ("Score", "Score"), ("CAGR", "CAGR"),
                              ("Latest flow", "Latest flow"), ("Comtrade export", "Comtrade export"),
                              ("wits_latest_year", "Data year")]:
                src, dst = col_pair
                if src in display_df.columns:
                    display_df = display_df.rename(columns={src: dst}) if src != dst else display_df
                    show_cols.append(dst)

            st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)

            # Opportunity bar chart
            if "opportunity" in df_opp.columns and "partner" in df_opp.columns:
                chart_df = df_opp[["partner", "opportunity"]].dropna(subset=["opportunity"]).head(15)
                chart_df = chart_df.rename(columns={"partner": "Market", "opportunity": "Score"})
                _bar_chart(chart_df, x_col="Market", y_col="Score", color="#4299e1")

            # CSV export
            csv = df_opp.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Export to CSV",
                data=csv,
                file_name=f"opportunities_{reporter_opp.iso3}_{p}.csv",
                mime="text/csv",
                key="opp_csv",
            )


# ── Tab 4: Country Profiles ───────────────────────────────────────────────────

def _tab_country_profiles() -> None:
    st.markdown('<div class="section-header">🌐 Country Profiles</div>', unsafe_allow_html=True)
    st.markdown(
        "**World Bank macro intelligence** for any country. "
        "Assess GDP growth, FDI attractiveness, trade openness, inflation, and market size "
        "before entering a new market or making an investment decision.",
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        profile_country = _country_selectbox("Country to profile", default_iso3="KEN", key="wb_country")
    with p2:
        yf = st.number_input("From year", min_value=1990, max_value=date.today().year - 1, value=2014, key="wb_yf")
    with p3:
        yt = st.number_input("To year", min_value=1990, max_value=date.today().year - 1, value=date.today().year - 1, key="wb_yt")

    if st.button("🌐 Load country profile", type="primary", key="wb_load"):
        with st.spinner(f"Fetching World Bank data for {profile_country}…"):
            prof = country_profile(profile_country, year_from=int(yf), year_to=int(yt))
        st.session_state["wb_profile"] = prof
        st.session_state["wb_country_iso3"] = profile_country

    prof = st.session_state.get("wb_profile")
    if prof is None:
        return

    # Attractiveness score
    label, emoji, score = market_attractiveness_score(prof)
    attr_class = {"High": "attr-high", "Medium": "attr-medium", "Low": "attr-low"}.get(label, "attr-medium")

    # KPI strip
    gdp_pc = prof.get("gdp_per_capita_latest")
    gdp_gr = prof.get("gdp_growth_latest")
    pop = prof.get("population_latest")
    fdi = prof.get("fdi_inflows_latest")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        val = fmt_usd(gdp_pc) if gdp_pc else "N/A"
        yr = prof.get("gdp_per_capita_latest_year", "")
        st.markdown(_kpi_card("GDP per capita", val, str(yr)), unsafe_allow_html=True)
    with k2:
        val = f"{gdp_gr:+.1f}%" if gdp_gr is not None else "N/A"
        yr = prof.get("gdp_growth_latest_year", "")
        neg = gdp_gr is not None and gdp_gr < 0
        st.markdown(_kpi_card("GDP growth", val, str(yr), negative=neg), unsafe_allow_html=True)
    with k3:
        val = fmt_usd(abs(float(fdi))) if fdi is not None else "N/A"
        yr = prof.get("fdi_inflows_latest_year", "")
        neg_fdi = fdi is not None and float(fdi) < 0
        st.markdown(_kpi_card("FDI inflows", val, str(yr), negative=neg_fdi), unsafe_allow_html=True)
    with k4:
        val = fmt_number(float(pop)) if pop is not None else "N/A"
        yr = prof.get("population_latest_year", "")
        st.markdown(_kpi_card("Population", val, str(yr)), unsafe_allow_html=True)

    st.markdown("")
    st.markdown(
        f'<div><b>Market Attractiveness: </b>'
        f'<span class="attr-badge {attr_class}">{emoji} {label} ({score:.2f})</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Insights
    country_name = profile_country  # ISO3; could be resolved to a full name
    insights = summarize_country_profile(prof, country_name)
    _render_insights(insights)

    # Charts — two per row
    st.markdown('<div class="section-header">📊 Indicator Trends</div>', unsafe_allow_html=True)

    indicators_to_plot = [
        ("gdp_per_capita", "GDP per capita (USD)"),
        ("gdp_growth", "GDP growth (annual %)"),
        ("fdi_inflows", "FDI net inflows (USD)"),
        ("trade_pct_gdp", "Trade (% of GDP)"),
        ("inflation", "Inflation (annual %)"),
        ("exports_pct_gdp", "Exports (% of GDP)"),
    ]

    for i in range(0, len(indicators_to_plot), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(indicators_to_plot):
                break
            field, label = indicators_to_plot[i + j]
            series = prof.get(field, [])
            with col:
                st.caption(label)
                if series:
                    _wb_line_chart(series, indicator_label=label, height=200)
                else:
                    st.info("No data available.")

    with st.expander("📋 Raw World Bank data table"):
        rows = []
        for field, label in indicators_to_plot:
            series = prof.get(field, [])
            for year, val in series:
                rows.append({"Indicator": label, "Year": year, "Value": val})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Tab 5: Macro Intelligence (IMF) ──────────────────────────────────────────

def _tab_macro_intelligence() -> None:
    st.markdown('<div class="section-header">🏦 Macro Intelligence — IMF</div>', unsafe_allow_html=True)
    st.markdown(
        "Explore **IMF SDMX datasets** — CPI, interest rates, balance of payments, "
        "exchange rates, and more. Build queries using dropdowns and visualize results instantly.",
    )

    # Quick picks
    with st.expander("⚡ Quick picks — common IMF datasets", expanded=False):
        st.markdown("""
        | Dataset | Code | Description |
        |---------|------|-------------|
        | Consumer Price Index | `CPI` | Inflation by country & category |
        | International Financial Statistics | `IFS` | Broad macro indicators |
        | Balance of Payments | `BOP` | Current account, capital flows |
        | Direction of Trade Statistics | `DOT` | Bilateral trade values |
        | Government Finance Statistics | `GFS` | Fiscal data |

        *Enter the dataset code in the search box below, then click Search.*
        """)

    if "imf_dataflows_df" not in st.session_state:
        with st.spinner("Loading IMF datasets…"):
            st.session_state["imf_dataflows_df"] = list_dataflows(search="CPI")

    search_term = st.text_input(
        "Search IMF datasets",
        st.session_state.get("imf_search_term", "CPI"),
        key="imf_search_term",
        help="Filter by dataset code or name (e.g. CPI, IFS, BOP).",
    )
    if st.button("🔎 Search datasets", key="imf_search_button"):
        with st.spinner("Loading IMF datasets…"):
            st.session_state["imf_dataflows_df"] = list_dataflows(search=search_term)

    dataflows_df = st.session_state.get("imf_dataflows_df")
    if isinstance(dataflows_df, pd.DataFrame):
        if dataflows_df.empty:
            st.info("No IMF datasets matched the search term.")
        else:
            st.dataframe(dataflows_df, use_container_width=True, hide_index=True)

    dataset_options: list[str] = []
    dataset_lookup: dict[str, str] = {}
    if isinstance(dataflows_df, pd.DataFrame) and not dataflows_df.empty:
        for row in dataflows_df.itertuples(index=False):
            label = f"{row.dataset} - {row.name}" if getattr(row, "name", "") else str(row.dataset)
            dataset_lookup[label] = str(row.dataset)
            dataset_options.append(label)

    if not dataset_options:
        dataset_options = ["CPI"]
        dataset_lookup = {"CPI": "CPI"}

    selected_dataset_label = st.selectbox(
        "Dataset / dataflow", options=dataset_options, key="imf_dataset_select",
        help="Pick a dataset; dimensions are built from its published structure.",
    )
    dataset = dataset_lookup[selected_dataset_label]

    current_info = st.session_state.get("imf_dataflow_info")
    if not isinstance(current_info, dict) or current_info.get("dataset") != dataset:
        try:
            with st.spinner("Loading IMF dataset structure…"):
                st.session_state["imf_dataflow_info"] = describe_dataflow(dataset)
        except Exception as exc:
            st.session_state["imf_dataflow_info"] = None
            st.error(f"Could not load dataset structure: {exc}")

    dataflow_info = st.session_state.get("imf_dataflow_info")

    with st.expander("🔍 Dataset structure (raw)", expanded=False):
        if isinstance(dataflow_info, dict):
            st.json(dataflow_info)
        else:
            st.info("No structure loaded yet.")

    st.divider()
    st.markdown('<div class="section-header">🔧 Build Query</div>', unsafe_allow_html=True)
    dimension_details = dataflow_info.get("dimension_details", []) if isinstance(dataflow_info, dict) else []
    key_parts: list[str] = []
    selected_freq = ""

    if dimension_details:
        st.caption("Select dimensions below — the SDMX key is generated automatically.")

    for idx, dim in enumerate(dimension_details):
        if dim.get("is_time"):
            continue
        dim_id = str(dim.get("id", ""))
        options = dim.get("options", []) or []
        label_map = _imf_option_label_map(options)
        default_values = [v for v in _imf_default_values(dim_id) if v in label_map]

        if dim_id == "COUNTRY":
            if not default_values and options:
                default_values = [row["value"] for row in options[:1]]
            default_labels = [label_map[value] for value in default_values if value in label_map]
            selected_labels = st.multiselect(
                dim_id, options=list(label_map.values()), default=default_labels,
                key=f"imf_dim_{idx}_{dim_id}",
                help="Multiple selections are joined with '+'.",
            )
            reverse_map = {label: value for value, label in label_map.items()}
            selected_values = [reverse_map[label] for label in selected_labels]
            key_parts.append("+".join(selected_values) if selected_values else "")
        else:
            select_options = ["* - Any value"] + list(label_map.values())
            default_label = label_map[default_values[0]] if default_values else "* - Any value"
            selected_label = st.selectbox(
                dim_id, options=select_options,
                index=select_options.index(default_label) if default_label in select_options else 0,
                key=f"imf_dim_{idx}_{dim_id}",
            )
            reverse_map = {label: value for value, label in label_map.items()}
            selected_value = reverse_map.get(selected_label, "")
            key_parts.append(selected_value)
            if dim_id == "FREQUENCY":
                selected_freq = selected_value

    series_key = ".".join(key_parts) if key_parts else ""
    st.caption("Generated SDMX series key:")
    st.code(series_key or "*", language="text")

    with st.expander("⚙️ Advanced options"):
        period_options = _imf_period_options(selected_freq)
        period_select_options = ["Any", "Custom..."] + period_options if period_options else ["Any", "Custom..."]
        q1, q2 = st.columns(2)
        with q1:
            start_period_label = st.selectbox(
                "API Start period limit", options=period_select_options,
                index=0,  # Default to Any
                key="imf_start_period",
                help="Optionally limit data size requested from IMF server.",
            )
            start_period = st.text_input("Custom start period limit", key="imf_start_period_custom").strip() if start_period_label == "Custom..." else ("" if start_period_label == "Any" else start_period_label)
        with q2:
            end_period_label = st.selectbox(
                "API End period limit", options=period_select_options,
                index=0,  # Default to Any
                key="imf_end_period",
                help="Optionally limit data size requested from IMF server.",
            )
            end_period = st.text_input("Custom end period limit", key="imf_end_period_custom").strip() if end_period_label == "Custom..." else ("" if end_period_label == "Any" else end_period_label)

        extra_params = st.text_area("Extra query params", "", key="imf_extra_params",
                                    help="One KEY=VALUE per line, e.g. detail=full")
        access_token = st.text_input("Access token (optional)", "", key="imf_access_token", type="password")

    if st.button("📡 Load IMF data", key="imf_load_button", type="primary"):
        try:
            query = IMFDataQuery(
                dataset=dataset,
                key=series_key or None,
                start_period=start_period or None,
                end_period=end_period or None,
                extra_params=_parse_kv_lines(extra_params),
            )
            headers = build_auth_headers(access_token=access_token or None)
            with st.spinner("Fetching IMF data…"):
                imf_df = fetch_dataset(query, headers=headers)
            st.session_state["imf_result_df"] = imf_df
            st.session_state["imf_result_meta"] = {
                "dataset": dataset,
                "key": series_key or "*",
                "startPeriod": start_period or None,
                "endPeriod": end_period or None,
                "rows": len(imf_df),
            }
        except Exception as exc:
            st.session_state["imf_result_df"] = None
            st.session_state["imf_result_meta"] = None
            st.error(f"IMF query failed: {exc}")

    result_meta = st.session_state.get("imf_result_meta")
    result_df = st.session_state.get("imf_result_df")
    if isinstance(result_meta, dict):
        st.caption(
            f"Dataset `{result_meta['dataset']}` · Key `{result_meta['key']}` · {result_meta['rows']:,} rows"
        )
    if isinstance(result_df, pd.DataFrame):
        if result_df.empty:
            st.warning("No rows returned for the current IMF query.")
        else:
            filtered_df = result_df
            if "TIME_PERIOD" in result_df.columns:
                time_periods = sorted(result_df["TIME_PERIOD"].astype(str).unique().tolist())
                if len(time_periods) >= 2:
                    st.markdown("### 📅 Adjust Time Period")
                    start_sel, end_sel = st.select_slider(
                        "Drag the endpoints to adjust the time range of the data shown below:",
                        options=time_periods,
                        value=(time_periods[0], time_periods[-1]),
                        key="imf_time_range_slider",
                    )
                    filtered_df = result_df[
                        (result_df["TIME_PERIOD"].astype(str) >= start_sel) &
                        (result_df["TIME_PERIOD"].astype(str) <= end_sel)
                    ]
                    st.caption(f"Showing {len(filtered_df):,} of {len(result_df):,} rows from **{start_sel}** to **{end_sel}**")

            _imf_time_series_chart(filtered_df)
            with st.expander("📋 Raw data table"):
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Export to CSV", data=csv,
                file_name=f"imf_{result_meta['dataset']}_{result_meta['key']}.csv".replace("*", "all"),
                mime="text/csv", key="imf_csv",
            )


# ── Main entry point ──────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="TradeNexus — Global Trade Intelligence",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": "TradeNexus — Trade intelligence powered by UN Comtrade, World Bank, WITS & IMF.",
        },
    )

    st.markdown(_CSS, unsafe_allow_html=True)
    _configure()
    _render_hero()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌍 Market Explorer",
        "📈 Corridor Trends",
        "🚀 Opportunity Ranker",
        "🌐 Country Profiles",
        "🏦 Macro Intelligence",
    ])

    with tab1:
        _tab_market_explorer()
    with tab2:
        _tab_corridor_trends()
    with tab3:
        _tab_opportunity_ranker()
    with tab4:
        _tab_country_profiles()
    with tab5:
        _tab_macro_intelligence()


if __name__ == "__main__":
    main()
