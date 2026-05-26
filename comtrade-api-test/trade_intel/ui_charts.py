"""Shared chart renderers for the TradeNexus Streamlit UI."""

from __future__ import annotations

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

CHART_COLOR = "#2de2e6"
ACCENT_GRADIENT = ["#2de2e6", "#62b0ff", "#8b5cf6", "#ff4ecd", "#ff85df"]


def bar_chart(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    color: str = CHART_COLOR,
    height: int = 360,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                f"{x_col}:N",
                sort=None,
                axis=alt.Axis(
                    labelAngle=-45,
                    title=None,
                    labelColor="#a0aec0",
                    domainColor="rgba(99,179,237,0.2)",
                    gridColor="transparent",
                ),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=None,
                scale=alt.Scale(zero=True),
                axis=alt.Axis(
                    labelColor="#a0aec0",
                    gridColor="rgba(99,179,237,0.1)",
                    domainColor="transparent",
                ),
            ),
            tooltip=[x_col, y_col],
            opacity=alt.value(0.9),
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def line_chart(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    color: str = CHART_COLOR,
    height: int = 320,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(
            color=color,
            point=alt.OverlayMarkDef(color=color, filled=True, size=60),
            strokeWidth=2.5,
        )
        .encode(
            x=alt.X(
                f"{x_col}:O",
                axis=alt.Axis(
                    labelAngle=-45,
                    title=None,
                    labelColor="#a0aec0",
                    domainColor="rgba(99,179,237,0.2)",
                    gridColor="transparent",
                ),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=None,
                scale=alt.Scale(zero=False),
                axis=alt.Axis(
                    labelColor="#a0aec0",
                    gridColor="rgba(99,179,237,0.1)",
                    domainColor="transparent",
                ),
            ),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def multi_line_chart(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    series_col: str,
    height: int = 360,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=50), strokeWidth=2)
        .encode(
            x=alt.X(
                f"{x_col}:O",
                axis=alt.Axis(
                    labelAngle=-45,
                    title=None,
                    labelColor="#a0aec0",
                    domainColor="rgba(99,179,237,0.2)",
                    gridColor="transparent",
                ),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=None,
                scale=alt.Scale(zero=False),
                axis=alt.Axis(
                    labelColor="#a0aec0",
                    gridColor="rgba(99,179,237,0.1)",
                    domainColor="transparent",
                ),
            ),
            color=alt.Color(
                f"{series_col}:N",
                title=None,
                scale=alt.Scale(range=ACCENT_GRADIENT),
            ),
            tooltip=[x_col, series_col, y_col],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def choropleth_map(
    df: pd.DataFrame,
    *,
    locations_col: str,
    color_col: str,
    title: str = "",
    height: int = 400,
) -> None:
    fig = px.choropleth(
        df,
        locations=locations_col,
        color=color_col,
        hover_name=locations_col,
        color_continuous_scale=[
            [0.0, "#10213e"],
            [0.25, "#1762cc"],
            [0.55, "#2de2e6"],
            [1.0, "#ff4ecd"],
        ],
        title=title,
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            bgcolor="rgba(4,11,23,0.94)",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="rgba(98,176,255,0.22)",
            showland=True,
            landcolor="#13233f",
            showocean=True,
            oceancolor="#07101d",
            showcountries=True,
            countrycolor="rgba(98,176,255,0.14)",
        ),
        coloraxis_colorbar=dict(
            bgcolor="rgba(8,17,34,0.86)",
            tickfont=dict(color="#c8d7ea"),
            title=dict(font=dict(color="#c8d7ea")),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=height,
        font=dict(color="#c8d7ea"),
    )
    st.plotly_chart(fig, use_container_width=True)


def wb_line_chart(series: list[tuple[str, float]], *, indicator_label: str, height: int = 240) -> None:
    if not series:
        st.caption("No data available.")
        return
    df = pd.DataFrame(series, columns=["Year", indicator_label])
    line_chart(df, x_col="Year", y_col=indicator_label, height=height)


def wb_profile_multi_chart(
    series_map: dict[str, list[tuple[str, float]]],
    *,
    height: int = 360,
) -> None:
    records: list[dict[str, object]] = []
    for indicator_label, series in series_map.items():
        if not series:
            continue
        clean_rows: list[tuple[str, float]] = []
        for year, value in series:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            clean_rows.append((str(year), numeric_value))
        if not clean_rows:
            continue

        values = [value for _, value in clean_rows]
        min_value = min(values)
        max_value = max(values)
        span = max_value - min_value

        for year, value in clean_rows:
            indexed_value = 50.0 if span == 0 else ((value - min_value) / span) * 100.0
            records.append(
                {
                    "Year": year,
                    "Indicator": indicator_label,
                    "Value": value,
                    "IndexedValue": indexed_value,
                    "ValueLabel": f"{value:,.2f}",
                }
            )

    if not records:
        st.info("No data available.")
        return

    chart_df = pd.DataFrame(records)
    chart = (
        alt.Chart(chart_df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=60), strokeWidth=2.5)
        .encode(
            x=alt.X(
                "Year:O",
                axis=alt.Axis(
                    labelAngle=-45,
                    title=None,
                    labelColor="#a0aec0",
                    domainColor="rgba(99,179,237,0.2)",
                    gridColor="transparent",
                ),
            ),
            y=alt.Y(
                "IndexedValue:Q",
                title="Indexed trend (0-100)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(
                    labelColor="#a0aec0",
                    titleColor="#a0aec0",
                    gridColor="rgba(99,179,237,0.1)",
                    domainColor="transparent",
                ),
            ),
            color=alt.Color(
                "Indicator:N",
                title=None,
                scale=alt.Scale(range=ACCENT_GRADIENT + ["#ffb703", "#ff6b6b"]),
                legend=alt.Legend(
                    orient="bottom",
                    labelColor="#c8d7ea",
                    symbolStrokeWidth=3,
                ),
            ),
            tooltip=[
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip("Indicator:N", title="Indicator"),
                alt.Tooltip("ValueLabel:N", title="Value"),
                alt.Tooltip("IndexedValue:Q", title="Indexed trend", format=".1f"),
            ],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)


def imf_time_series_chart(df: pd.DataFrame) -> None:
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
        (
            col
            for col in ("COUNTRY", "INDICATOR", "INDEX_TYPE", "COICOP_1999", "FREQUENCY")
            if col in chart_df.columns
        ),
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
                    y=alt.Y(
                        "value:Q",
                        title=None,
                        axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)"),
                    ),
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
                .mark_line(point=True, color=CHART_COLOR, strokeWidth=2.5)
                .encode(
                    x=alt.X("_time:T", title=None, axis=alt.Axis(labelColor="#a0aec0")),
                    y=alt.Y(
                        "value:Q",
                        title=None,
                        axis=alt.Axis(labelColor="#a0aec0", gridColor="rgba(99,179,237,0.1)"),
                    ),
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
                .encode(
                    x=enc_x,
                    y=enc_y,
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
                .mark_line(point=True, color=CHART_COLOR, strokeWidth=2.5)
                .encode(x=enc_x, y=enc_y, tooltip=tooltip_cols)
                .properties(height=360)
                .configure_view(strokeOpacity=0, fill="transparent")
                .configure(background="transparent")
            )
    st.altair_chart(chart, use_container_width=True)
