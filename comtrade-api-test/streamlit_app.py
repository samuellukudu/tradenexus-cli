"""
Streamlit UI for exporter-focused trade intelligence (Comtrade + WITS).

Run from project root:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from comtrade_countries import Country, list_countries, resolve_country
from trade_intel.comtrade_history import fetch_export_history, recent_annual_years
from trade_intel.comtrade_flows import annual_export_destination_trends, top_export_destinations
from trade_intel.config import RunConfig, set_config
from trade_intel.opportunities import rank_exporter_opportunities
from trade_intel.product_drilldown import ProductDrilldown, build_bilateral_product_drilldown
from trade_intel.wits_timeseries import fetch_bilateral_export_series


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
    """Dropdown: full country name + ISO3; returns ISO3 for APIs."""
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
        help=help or "Pick by country name; ISO3 is filled in automatically.",
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
    return st.selectbox(
        label,
        options=options,
        index=default_idx,
        key=key,
        help=help,
    )


def _bar_chart_45(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    color: str = "#7fb6e8",
    height: int = 360,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_bar(color=color)
        .encode(
            x=alt.X(f"{x_col}:N", sort=None, axis=alt.Axis(labelAngle=-45, title=None)),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=True)),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, width="stretch")


def _line_chart_45(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    color: str = "#7fb6e8",
    height: int = 360,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(color=color, point=True)
        .encode(
            x=alt.X(f"{x_col}:O", axis=alt.Axis(labelAngle=-45, title=None)),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=True)),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, width="stretch")


def _multi_line_chart_45(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    series_col: str,
    height: int = 380,
) -> None:
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{x_col}:O", axis=alt.Axis(labelAngle=-45, title=None)),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=True)),
            color=alt.Color(f"{series_col}:N", title=None),
            tooltip=[x_col, series_col, y_col],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, width="stretch")


def _configure() -> None:
    st.sidebar.header("Cache & rate limits")
    no_cache = st.sidebar.checkbox("Disable disk cache", value=False)
    ttl_h = st.sidebar.number_input("Cache TTL (hours)", min_value=1, max_value=168, value=24)
    interval = st.sidebar.slider("Min seconds between API calls", 0.0, 2.0, 0.35, 0.05)
    cache_dir = Path(st.sidebar.text_input("Cache directory", ".trade_intel_cache"))
    set_config(
        RunConfig(
            cache_enabled=not no_cache,
            cache_dir=cache_dir,
            cache_ttl_seconds=int(ttl_h * 3600),
            min_request_interval=float(interval),
        )
    )


def main() -> None:
    st.set_page_config(page_title="Trade Intel — Exporters", layout="wide")
    st.title("Trade intelligence for exporters")
    st.caption("UN Comtrade (public preview) + World Bank WITS — market lists, trends, and opportunity scores.")
    _configure()

    tab1, tab2, tab3 = st.tabs(["Destination markets", "Bilateral trend", "Opportunity ranking"])

    with tab1:
        st.subheader("Where does your country export?")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            country = _country_selectbox(
                "Country",
                default_iso3="KEN",
                key="tab1_country",
                help="Your home / reporting country (exports originate here).",
            )
        with c2:
            view_mode = st.selectbox(
                "View mode",
                ("Last 10 years", "Single period"),
                key="tab1_mode",
                help="Default to a 10-year annual histogram, or switch to a single annual/monthly period.",
            )
        with c3:
            cmd = st.text_input("HS code", "TOTAL")
        with c4:
            top_n = st.slider("Rows to show", 5, 50, 15)

        history_df: pd.DataFrame | None = None
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
                    "Period",
                    freq_code=freq,
                    default_period="2020" if freq == "A" else _period_options("M")[0],
                    key="tab1_period",
                    help="Pick a year for annual data or a recent YYYYMM period for monthly data.",
                )
        if st.button("Load destinations", type="primary"):
            if view_mode == "Last 10 years":
                with st.spinner("Fetching Comtrade 10-year history…"):
                    history_df, _ = fetch_export_history(
                        country,
                        year_from=int(history_years[-1]),
                        year_to=int(history_years[0]),
                        cmd_code=cmd,
                    )
                st.session_state["tab1_history_df"] = history_df
                available_history_years = (
                    sorted(history_df["period"].astype(str).unique().tolist(), reverse=True)
                    if not history_df.empty
                    else []
                )
                st.session_state["tab1_history_year_options"] = available_history_years
                if available_history_years:
                    current_period = st.session_state.get("tab1_destinations_period")
                    if current_period in available_history_years:
                        period = current_period
                    else:
                        period = available_history_years[0]
                    if history_years[0] not in available_history_years:
                        st.session_state["tab1_history_note"] = (
                            f"No annual data was found for `{history_years[0]}` yet. "
                            f"Defaulting the destination table to latest available year `{period}`."
                        )
                    else:
                        st.session_state["tab1_history_note"] = None
                else:
                    st.session_state["tab1_history_note"] = (
                        "No annual Comtrade history was returned for the selected HS code."
                    )
                    st.session_state["tab1_history_year_options"] = []
                if available_history_years:
                    with st.spinner("Fetching annual destination trends…"):
                        annual_trends_df, _ = annual_export_destination_trends(
                            country,
                            years=available_history_years,
                            cmd_code=cmd,
                            top_n=min(max(5, top_n), 8),
                        )
                    st.session_state["tab1_destination_trends_df"] = annual_trends_df
                else:
                    st.session_state["tab1_destination_trends_df"] = pd.DataFrame()
            else:
                st.session_state["tab1_history_df"] = None
                st.session_state["tab1_history_note"] = None
                st.session_state["tab1_history_year_options"] = []
                st.session_state["tab1_destination_trends_df"] = None
            with st.spinner("Fetching Comtrade preview…"):
                df, resolved = top_export_destinations(
                    country,
                    period=period,
                    freq_code=freq,
                    cmd_code=cmd,
                    top_n=top_n,
                )
            st.session_state["tab1_destinations_df"] = df
            st.session_state["tab1_destinations_reporter_iso3"] = resolved.iso3
            st.session_state["tab1_destinations_reporter_name"] = resolved.name
            st.session_state["tab1_destinations_period"] = period
            st.session_state["tab1_destinations_freq"] = freq
            st.session_state["tab1_destinations_mode"] = view_mode
            st.session_state["tab1_destinations_cmd"] = cmd
            st.session_state["tab1_drilldown"] = None

        dest_df = st.session_state.get("tab1_destinations_df")
        dest_reporter_iso3 = st.session_state.get("tab1_destinations_reporter_iso3")
        dest_reporter_name = st.session_state.get("tab1_destinations_reporter_name")
        dest_period = st.session_state.get("tab1_destinations_period")
        dest_freq = st.session_state.get("tab1_destinations_freq", "A")
        dest_mode = st.session_state.get("tab1_destinations_mode")
        dest_cmd = st.session_state.get("tab1_destinations_cmd", "TOTAL")
        dest_history_df = st.session_state.get("tab1_history_df")
        dest_history_note = st.session_state.get("tab1_history_note")
        dest_history_year_options = st.session_state.get("tab1_history_year_options", [])
        dest_trends_df = st.session_state.get("tab1_destination_trends_df")

        if dest_df is not None and dest_reporter_iso3 and dest_reporter_name and dest_period:
            st.success(f"Reporter: **{dest_reporter_name}** ({dest_reporter_iso3})")
            if dest_mode == "Last 10 years" and isinstance(dest_history_df, pd.DataFrame):
                st.subheader("10-year export history")
                st.caption(
                    f"Annual Comtrade exports for HS `{dest_cmd}` over the last 10 completed years."
                )
                if dest_history_note:
                    st.info(dest_history_note)
                if dest_history_df.empty:
                    st.warning("No annual history rows were returned for this country and HS code.")
                else:
                    hist_chart = dest_history_df.rename(columns={"period": "Year", "export_usd": "USD"})
                    _bar_chart_45(hist_chart, x_col="Year", y_col="USD")
                if isinstance(dest_trends_df, pd.DataFrame) and not dest_trends_df.empty:
                    st.subheader("Annual destination trends")
                    st.caption(
                        "Top partner markets across the loaded annual window. This is the primary annual view; the snapshot below is just one selected year."
                    )
                    trends_chart = dest_trends_df.rename(
                        columns={"period": "Year", "partnerDesc": "Partner", "export_usd": "USD"}
                    )
                    _multi_line_chart_45(
                        trends_chart,
                        x_col="Year",
                        y_col="USD",
                        series_col="Partner",
                    )
                    trends_pivot = (
                        trends_chart.pivot_table(
                            index="Partner",
                            columns="Year",
                            values="USD",
                            aggfunc="sum",
                            fill_value=0.0,
                        )
                        .reindex(sorted(trends_chart["Year"].astype(str).unique().tolist()), axis=1)
                        .sort_index()
                    )
                    st.dataframe(trends_pivot, width="stretch")
            if dest_df.empty:
                st.warning("No rows returned.")
            else:
                st.subheader("Single-year destination snapshot")
                if dest_mode == "Last 10 years" and dest_history_year_options:
                    try:
                        default_year_idx = dest_history_year_options.index(str(dest_period))
                    except ValueError:
                        default_year_idx = 0
                    selected_table_year = st.selectbox(
                        "Snapshot year",
                        options=dest_history_year_options,
                        index=default_year_idx,
                        key="tab1_destination_year",
                        help="Switch the single-year destination snapshot without changing the annual trend views above.",
                    )
                    if selected_table_year != str(dest_period):
                        with st.spinner("Fetching Comtrade preview…"):
                            dest_df, resolved = top_export_destinations(
                                dest_reporter_iso3,
                                period=selected_table_year,
                                freq_code=dest_freq,
                                cmd_code=dest_cmd,
                                top_n=top_n,
                            )
                        dest_reporter_iso3 = resolved.iso3
                        dest_reporter_name = resolved.name
                        dest_period = selected_table_year
                        st.session_state["tab1_destinations_df"] = dest_df
                        st.session_state["tab1_destinations_reporter_iso3"] = dest_reporter_iso3
                        st.session_state["tab1_destinations_reporter_name"] = dest_reporter_name
                        st.session_state["tab1_destinations_period"] = dest_period
                        st.session_state["tab1_drilldown"] = None
                st.caption(
                    f"Showing the destination ranking for annual snapshot `{dest_period}` and HS `{dest_cmd}`."
                )
                st.dataframe(dest_df, width="stretch", hide_index=True)
                if "primaryValue" in dest_df.columns:
                    chart = dest_df.rename(columns={"partnerDesc": "Partner", "primaryValue": "USD"})[
                        ["Partner", "USD"]
                    ].head(min(20, len(dest_df)))
                    _bar_chart_45(chart, x_col="Partner", y_col="USD")

                st.divider()
                st.subheader("Product drill-down for one destination")
                st.caption(
                    f"Choose a destination from the snapshot year `{dest_period}` to see exported HS products and WITS corridor context."
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
                    st.info("No selectable destination country was found in the current result set.")
                else:
                    d1, d2, d3 = st.columns(3)
                    with d1:
                        selected_partner = st.selectbox(
                            "Destination country",
                            options=list(partner_lookup.keys()),
                            key="tab1_partner_select",
                        )
                    with d2:
                        hs_level = st.selectbox(
                            "HS detail level",
                            ("AG2", "AG4", "AG6"),
                            help="AG2 = chapter, AG4 = heading, AG6 = product detail.",
                            key="tab1_hs_level",
                        )
                    with d3:
                        product_rows = st.slider("Products to show", 5, 50, 15, key="tab1_products_to_show")
                    d4, d5, d6 = st.columns(3)
                    with d4:
                        dy0, dy1 = st.slider(
                            "WITS context years",
                            2000,
                            2023,
                            (2018, 2022),
                            key="tab1_wits_window",
                        )
                    with d5:
                        wits_product = st.text_input(
                            "WITS context product",
                            "total",
                            key="tab1_wits_product",
                        )
                    with d6:
                        include_mirror = st.checkbox(
                            "Include mirror context",
                            value=True,
                            key="tab1_wits_mirror",
                        )

                    if st.button("Load product drill-down", key="tab1_drilldown_button", type="primary"):
                        partner_code = partner_lookup[selected_partner]
                        try:
                            partner_country = resolve_country(str(partner_code))
                        except ValueError:
                            st.session_state["tab1_drilldown"] = None
                            st.error("Selected destination could not be resolved to a country.")
                        else:
                            with st.spinner("Fetching product detail and corridor context…"):
                                st.session_state["tab1_drilldown"] = build_bilateral_product_drilldown(
                                    dest_reporter_iso3,
                                    partner_country,
                                    period=dest_period,
                                    freq_code=dest_freq,
                                    hs_level=hs_level,
                                    top_n=int(product_rows),
                                    wits_year_from=int(dy0),
                                    wits_year_to=int(dy1),
                                    wits_product=wits_product,
                                    include_mirror=include_mirror,
                                )

                    drilldown = st.session_state.get("tab1_drilldown")
                    if isinstance(drilldown, ProductDrilldown):
                        st.caption(
                            f"Corridor: **{drilldown.exporter.name}** ({drilldown.exporter.iso3}) -> "
                            f"**{drilldown.importer.name}** ({drilldown.importer.iso3}), "
                            f"period `{drilldown.period}`, HS `{drilldown.hs_level}`"
                        )
                        for note in drilldown.notes:
                            st.caption(note)
                        if drilldown.products.empty:
                            st.warning("No product-level rows returned for the selected corridor.")
                        else:
                            st.dataframe(drilldown.products, width="stretch", hide_index=True)
                            chart = drilldown.products.rename(
                                columns={"product": "Product", "export_usd": "USD"}
                            )[["Product", "USD"]].head(min(15, len(drilldown.products)))
                            _bar_chart_45(chart, x_col="Product", y_col="USD")
                        if drilldown.export_series:
                            st.subheader("WITS corridor context")
                            trend_df = pd.DataFrame(
                                drilldown.export_series,
                                columns=["Year", "Export value (US$ thousand)"],
                            )
                            _line_chart_45(
                                trend_df,
                                x_col="Year",
                                y_col="Export value (US$ thousand)",
                            )
                        if drilldown.mirror_series:
                            mirror_df = pd.DataFrame(
                                drilldown.mirror_series,
                                columns=["Year", "Import mirror (US$ thousand)"],
                            )
                            st.subheader("WITS mirror context")
                            _line_chart_45(
                                mirror_df,
                                x_col="Year",
                                y_col="Import mirror (US$ thousand)",
                            )

    with tab2:
        st.subheader("How is bilateral trade evolving?")
        e1, e2, e3 = st.columns(3)
        with e1:
            exp = _country_selectbox("Exporter country", default_iso3="KEN", key="texp")
        with e2:
            imp = _country_selectbox("Importer country", default_iso3="USA", key="timp")
        with e3:
            y0, y1 = st.slider("Year range", 2000, 2023, (2018, 2022))
        product = st.text_input("WITS product group", "total", key="tprod")
        mirror = st.checkbox("Include mirror import series", value=False)
        if st.button("Load trend", type="primary"):
            with st.spinner("Fetching WITS…"):
                series = fetch_bilateral_export_series(exp, imp, y0, y1, product=product.lower())
            if not series:
                st.error("No WITS series for this pair.")
            else:
                tdf = pd.DataFrame(series, columns=["Year", "Export value (US$ thousand)"])
                _line_chart_45(
                    tdf,
                    x_col="Year",
                    y_col="Export value (US$ thousand)",
                )
            if mirror:
                from trade_intel.wits_timeseries import fetch_bilateral_import_series

                with st.spinner("Mirror series…"):
                    mseries = fetch_bilateral_import_series(
                        exp, imp, y0, y1, product=product.lower()
                    )
                if mseries:
                    mdf = pd.DataFrame(mseries, columns=["Year", "Import mirror (US$ thousand)"])
                    st.subheader("Importer-reported mirror (MPRT-TRD-VL)")
                    _line_chart_45(
                        mdf,
                        x_col="Year",
                        y_col="Import mirror (US$ thousand)",
                    )

    with tab3:
        st.subheader("Rank markets by size + growth")
        st.markdown(
            "Uses your **latest Comtrade export destinations**, then scores each with **WITS bilateral export CAGR**."
        )
        o1, o2 = st.columns(2)
        with o1:
            sc = _country_selectbox("Supplier country", default_iso3="KEN", key="oc")
            fq = st.selectbox("Comtrade freq", ("A", "M"), key="of")
            p = _period_selectbox(
                "Comtrade period",
                freq_code=fq,
                default_period="2020" if fq == "A" else _period_options("M")[0],
                key="op",
                help="Pick a year for annual data or a recent YYYYMM period for monthly data.",
            )
            hs = st.text_input("HS pool", "TOTAL", key="oh")
        with o2:
            pool = st.number_input("Destination pool size", 10, 50, 25)
            out_n = st.number_input("Top results", 5, 30, 15)
            wy0, wy1 = st.slider("WITS window", 2000, 2023, (2018, 2022), key="ow")
        wprod = st.text_input("WITS product", "total", key="owp")
        if st.button("Compute opportunities", type="primary"):
            with st.spinner("This may take a minute (several WITS calls, rate-limited)…"):
                df, resolved = rank_exporter_opportunities(
                    sc,
                    comtrade_period=p,
                    comtrade_freq=fq,
                    cmd_code=hs,
                    pool_size=int(pool),
                    score_count=int(out_n),
                    wits_year_from=int(wy0),
                    wits_year_to=int(wy1),
                    product=wprod,
                )
            st.caption(f"Home: **{resolved.name}** ({resolved.iso3})")
            if df.empty:
                st.warning("No scored rows.")
            else:
                disp = df.drop(columns=["note"], errors="ignore") if "note" in df.columns and (df["note"].fillna("") == "").all() else df
                st.dataframe(disp, width="stretch", hide_index=True)
                if "opportunity" in disp.columns and "partner" in disp.columns:
                    iso = disp["partner_iso3"] if "partner_iso3" in disp.columns else pd.Series(["?"] * len(disp))
                    lbl = disp["partner"].astype(str) + " (" + iso.fillna("?").astype(str) + ")"
                    opp_chart = disp.assign(_lbl=lbl)[["_lbl", "opportunity"]].head(15)
                    _bar_chart_45(opp_chart, x_col="_lbl", y_col="opportunity")

if __name__ == "__main__":
    main()
