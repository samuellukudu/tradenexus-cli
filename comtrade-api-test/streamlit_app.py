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

import pandas as pd
import streamlit as st

from comtrade_countries import resolve_country
from trade_intel.comtrade_flows import annual_export_destination_trends, top_export_destinations
from trade_intel.comtrade_history import fetch_export_history, recent_annual_years
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
from trade_intel.ui_charts import (
    bar_chart,
    choropleth_map,
    imf_time_series_chart,
    line_chart,
    multi_line_chart,
    wb_profile_multi_chart,
)
from trade_intel.ui_components import (
    configure_sidebar,
    kpi_card,
    panel_header,
    render_hero,
    render_insights,
    render_terminal_feed,
    render_workspace_matrix,
    section_intro,
)
from trade_intel.ui_controls import (
    country_selectbox,
    imf_default_values,
    imf_option_label_map,
    imf_period_options,
    parse_kv_lines,
    period_options,
    period_selectbox,
)
from trade_intel.ui_theme import APP_CSS
from trade_intel.wits_timeseries import fetch_bilateral_export_series
from trade_intel.worldbank_data import (
    country_profile,
    market_attractiveness_score,
)


# ── Landing ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=21600, show_spinner=False)
def _command_center_profile() -> dict[str, object]:
    return country_profile("USA", year_from=2018, year_to=date.today().year - 1)


def _series_delta(series: list[tuple[str, float]]) -> str:
    if len(series) < 2:
        return "—"
    prev = series[-2][1]
    curr = series[-1][1]
    if prev in (None, 0) or curr is None:
        return "—"
    change = curr - prev
    if abs(prev) >= 1:
        return f"{change:+.1f}"
    return f"{change:+.2f}"


def _command_center_table(profile: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    specs = [
        ("gdp_per_capita", "US GDP per capita", lambda v: fmt_usd(float(v)) if v is not None else "N/A"),
        ("gdp_growth", "US GDP growth", lambda v: f"{float(v):+.1f}%" if v is not None else "N/A"),
        ("inflation", "US inflation", lambda v: f"{float(v):.1f}%" if v is not None else "N/A"),
        ("fdi_inflows", "US FDI inflows", lambda v: fmt_usd(float(v)) if v is not None else "N/A"),
        ("trade_pct_gdp", "Trade as % of GDP", lambda v: f"{float(v):.1f}%" if v is not None else "N/A"),
        ("exports_pct_gdp", "Exports as % of GDP", lambda v: f"{float(v):.1f}%" if v is not None else "N/A"),
    ]
    for field, label, formatter in specs:
        rows.append(
            {
                "Year": str(profile.get(f"{field}_latest_year", "—")),
                "Indicator": label,
                "Value": formatter(profile.get(f"{field}_latest")),
                "Change": _series_delta(profile.get(field, [])),
            }
        )
    return pd.DataFrame(rows)


def _tab_landing() -> None:
    section_intro(
        "Start Here",
        "Landing",
        "Use this page for orientation, then switch into the data workspaces for focused analysis with less explanatory chrome.",
    )

    profile = _command_center_profile()
    label, emoji, score = market_attractiveness_score(profile)
    gdp_growth_latest = profile.get("gdp_growth_latest")
    inflation_latest = profile.get("inflation_latest")
    trade_share_latest = profile.get("trade_pct_gdp_latest")
    fdi_latest = profile.get("fdi_inflows_latest")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        gdp_text = f"{float(gdp_growth_latest):+.1f}%" if gdp_growth_latest is not None else "N/A"
        st.markdown(kpi_card("GDP growth", gdp_text, "USA macro baseline", negative=float(gdp_growth_latest or 0) < 0), unsafe_allow_html=True)
    with m2:
        inflation_text = f"{float(inflation_latest):.1f}%" if inflation_latest is not None else "N/A"
        st.markdown(kpi_card("Inflation", inflation_text, "Latest World Bank reading", negative=float(inflation_latest or 0) > 5), unsafe_allow_html=True)
    with m3:
        trade_text = f"{float(trade_share_latest):.1f}%" if trade_share_latest is not None else "N/A"
        st.markdown(kpi_card("Trade / GDP", trade_text, "Openness signal"), unsafe_allow_html=True)
    with m4:
        fdi_text = fmt_usd(float(fdi_latest)) if fdi_latest is not None else "N/A"
        st.markdown(kpi_card("FDI inflows", fdi_text, f"{emoji} {label} desk score {score:.2f}"), unsafe_allow_html=True)

    center_col, right_col = st.columns([1.7, 1.0], gap="large")

    with center_col:
        panel_header("US GDP Growth vs. Inflation (YoY %)", "World Bank baseline view for the landing desk.", "Macro")
        gdp_df = pd.DataFrame(profile.get("gdp_growth", []), columns=["Year", "Value"])
        gdp_df["Indicator"] = "GDP Growth"
        inflation_df = pd.DataFrame(profile.get("inflation", []), columns=["Year", "Value"])
        inflation_df["Indicator"] = "Inflation"
        macro_chart_df = pd.concat([gdp_df, inflation_df], ignore_index=True)
        if macro_chart_df.empty:
            st.info("No baseline macro series were available for the landing desk.")
        else:
            multi_line_chart(macro_chart_df, x_col="Year", y_col="Value", series_col="Indicator", height=360)

    with right_col:
        panel_header("Global Trade News Feed", "Short analyst-style notes for a quick orientation pass.", "Intel")
        feed_items = summarize_country_profile(profile, "United States")
        feed_items.extend(
            [
                "Use Market Explorer for destination concentration, then switch to product drill-down for HS-level corridor detail.",
                "Use Corridor Trends to compare exporter-reported and mirror-import series before calling a route resilient.",
            ]
        )
        render_terminal_feed(feed_items[:5], empty_message="Load a workspace to populate the desk feed.")

    lower_left, lower_right = st.columns([1.15, 1.0], gap="large")
    with lower_left:
        panel_header("Workspace Matrix", "Capability cards styled to echo the lower trade matrix in the reference layout.", "Map")
        render_workspace_matrix(
            [
                {
                    "kicker": "UN Comtrade",
                    "title": "Market Explorer",
                    "value": "Destination mapping",
                    "copy": "Partner ranking, concentration risk, and product drill-down from the current reporter snapshot.",
                    "tone": "green",
                },
                {
                    "kicker": "World Bank WITS",
                    "title": "Corridor Trends",
                    "value": "Bilateral route watch",
                    "copy": "Track exporter and mirror-reported series over time to validate corridor momentum.",
                    "tone": "pink",
                },
                {
                    "kicker": "Scoring Engine",
                    "title": "Opportunity Ranker",
                    "value": "Prioritize markets",
                    "copy": "Blend size and growth signals to surface which partner markets deserve attention first.",
                    "tone": "cyan",
                },
                {
                    "kicker": "IMF + World Bank",
                    "title": "Macro Intelligence",
                    "value": "Macro signal stack",
                    "copy": "Profile inflation, openness, FDI, and IMF series before committing to a trade strategy.",
                    "tone": "amber",
                },
            ]
        )

    with lower_right:
        panel_header("Detailed Historical Data Table", "Latest macro snapshot for the landing desk baseline.", "Table")
        st.dataframe(_command_center_table(profile), hide_index=True, width="stretch")


# ── Tab 1: Market Explorer ────────────────────────────────────────────────────

def _tab_market_explorer() -> None:
    left_col, right_col = st.columns([1.0, 1.45], gap="large")
    with left_col:
        panel_header("Command Deck", "Configure the reporter, time lens, and HS product scope.", "Query")
        country = country_selectbox(
            "Reporting country",
            default_iso3="KEN",
            key="tab1_country",
            help="Exports originate here.",
        )
        view_mode = st.selectbox("View mode", ("Last 10 years", "Single period"), key="tab1_mode")
        cmd = st.text_input("HS code (or TOTAL)", "TOTAL", key="tab1_cmd")
        top_n = st.slider("Destinations to show", 5, 50, 15, key="tab1_topn")

    history_years = recent_annual_years(count=10)
    if view_mode == "Last 10 years":
        period = history_years[0]
        freq = "A"
    else:
        with left_col:
            s1, s2 = st.columns(2)
            with s1:
                freq = st.selectbox("Frequency", ("A", "M"), key="tab1_freq")
            with s2:
                period = period_selectbox(
                    "Period",
                    freq_code=freq,
                    default_period="2020" if freq == "A" else period_options("M")[0],
                    key="tab1_period",
                )
    with left_col:
        trigger_load = st.button("Load destinations", type="primary", key="tab1_load")

    dest_df = st.session_state.get("tab1_destinations_df")
    feed_items = (
        summarize_destinations(
            dest_df,
            st.session_state.get("tab1_destinations_reporter_name", "Current reporter"),
            period=str(st.session_state.get("tab1_destinations_period", "")),
            cmd=st.session_state.get("tab1_destinations_cmd", "TOTAL"),
        )
        if isinstance(dest_df, pd.DataFrame) and not dest_df.empty
        else []
    )

    with right_col:
        panel_header("Live Feed", "Headline-style insight stream for the current market scan.", "Intel")
        render_terminal_feed(
            feed_items,
            empty_message="Load a destination view to populate this feed with concentration risk, market size, and growth notes.",
        )

    if trigger_load:
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
        total_exports = float(dest_df["primaryValue"].sum()) if "primaryValue" in dest_df.columns and not dest_df.empty else 0
        n_partners = len(dest_df)
        top1_share = 100 * float(dest_df.iloc[0]["primaryValue"]) / total_exports if total_exports > 0 and not dest_df.empty else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(kpi_card("Reporter", dest_reporter_name, dest_reporter_iso3), unsafe_allow_html=True)
        with k2:
            st.markdown(kpi_card("Total exports", fmt_usd(total_exports), f"Period: {dest_period}"), unsafe_allow_html=True)
        with k3:
            st.markdown(kpi_card("Destination markets", str(n_partners), "in this result set"), unsafe_allow_html=True)
        with k4:
            st.markdown(kpi_card("Top market share", f"{top1_share:.0f}%", dest_df.iloc[0]["partnerDesc"] if not dest_df.empty and "partnerDesc" in dest_df.columns else ""), unsafe_allow_html=True)

        insights = summarize_destinations(dest_df, dest_reporter_name, period=str(dest_period), cmd=dest_cmd)
        box_class = "warning" if top1_share >= 80 else ("success" if top1_share < 50 else "")
        render_insights(insights, box_class=box_class)

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

        map_col, ranking_col = st.columns([1.45, 1.0], gap="large")
        with map_col:
            panel_header("Global Flow Map", "Destination footprint by partner country.", "Map")
            if not dest_df.empty and "partnerCode" in dest_df.columns and "primaryValue" in dest_df.columns:
                map_df = dest_df.copy()
                from trade_intel.partner_codes import partner_code_to_iso3

                map_df["iso3"] = map_df["partnerCode"].apply(
                    lambda c: partner_code_to_iso3(c) if c is not None else None
                )
                map_df = map_df.dropna(subset=["iso3"])
                map_df["primaryValue"] = pd.to_numeric(map_df["primaryValue"], errors="coerce")
                if not map_df.empty:
                    choropleth_map(
                        map_df,
                        locations_col="iso3",
                        color_col="primaryValue",
                        title=f"{dest_reporter_name} export destinations ({dest_period})",
                    )
                else:
                    st.info("No mapped ISO3 partner values were available for this snapshot.")
            else:
                st.info("Map data is unavailable for the current result set.")

        with ranking_col:
            panel_header("Destination Snapshot", "Ranked partner list with a quick share view.", "Table")
            if not dest_df.empty:
                display_df = dest_df.copy()
                if "primaryValue" in display_df.columns:
                    display_df["Export (USD)"] = display_df["primaryValue"].apply(
                        lambda v: fmt_usd(float(v)) if pd.notna(v) else "N/A"
                    )
                    total = display_df["primaryValue"].sum()
                    display_df["Share %"] = display_df["primaryValue"].apply(
                        lambda v: f"{100*float(v)/total:.1f}%" if total > 0 and pd.notna(v) else "—"
                    )
                    display_df = display_df.rename(
                        columns={"partnerDesc": "Partner", "period": "Period", "cmdDesc": "Product"}
                    )
                    disp_cols = ["Partner", "Export (USD)", "Share %"] + [
                        c for c in ["Period", "Product"] if c in display_df.columns
                    ]
                    st.dataframe(display_df[disp_cols], use_container_width=True, hide_index=True)
            if "primaryValue" in dest_df.columns and "partnerDesc" in dest_df.columns and not dest_df.empty:
                chart = dest_df.rename(columns={"partnerDesc": "Partner", "primaryValue": "Export (USD)"}).head(15)
                bar_chart(chart, x_col="Partner", y_col="Export (USD)", color="#62b0ff", height=290)

        if dest_mode == "Last 10 years" and isinstance(dest_history_df, pd.DataFrame):
            trend_col, partner_trend_col = st.columns([1.0, 1.2], gap="large")
            with trend_col:
                panel_header("10-Year History", f"Annual UN Comtrade exports for HS {dest_cmd}.", "Trend")
                if dest_history_df.empty:
                    st.warning("No annual history rows returned for this country and HS code.")
                else:
                    hist_chart = dest_history_df.rename(columns={"period": "Year", "export_usd": "Export (USD)"})
                    bar_chart(hist_chart, x_col="Year", y_col="Export (USD)", color="#2de2e6")

            with partner_trend_col:
                panel_header("Partner Market Trends", "How leading destination markets moved across the window.", "Compare")
                if isinstance(dest_trends_df, pd.DataFrame) and not dest_trends_df.empty:
                    trends_chart = dest_trends_df.rename(
                        columns={"period": "Year", "partnerDesc": "Partner", "export_usd": "Export (USD)"}
                    )
                    multi_line_chart(trends_chart, x_col="Year", y_col="Export (USD)", series_col="Partner")
                    with st.expander("Partner pivot table"):
                        trends_pivot = (
                            trends_chart.pivot_table(
                                index="Partner",
                                columns="Year",
                                values="Export (USD)",
                                aggfunc="sum",
                                fill_value=0.0,
                            )
                            .reindex(sorted(trends_chart["Year"].astype(str).unique().tolist()), axis=1)
                            .sort_index()
                        )
                        st.dataframe(trends_pivot, use_container_width=True)
                else:
                    st.info("No partner trend overlay was available for this request.")

        if not dest_df.empty:
            panel_header(
                "Product Drill-Down",
                f"Move from the {dest_period} market snapshot into HS products and WITS corridor context.",
                "Drill",
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
                        product_left, product_right = st.columns([1.0, 1.1], gap="large")
                        with product_left:
                            st.dataframe(drilldown.products, use_container_width=True, hide_index=True)
                        with product_right:
                            chart = drilldown.products.rename(columns={"product": "Product", "export_usd": "Export (USD)"})
                            bar_chart(
                                chart[["Product", "Export (USD)"]].head(15),
                                x_col="Product",
                                y_col="Export (USD)",
                                color="#ff4ecd",
                            )
                    if drilldown.export_series:
                        st.markdown("**WITS corridor context — export trend**")
                        trend_df = pd.DataFrame(drilldown.export_series, columns=["Year", "Export (US$ thousand)"])
                        line_chart(trend_df, x_col="Year", y_col="Export (US$ thousand)")
                    if drilldown.mirror_series:
                        st.markdown("**WITS mirror context — import-reported flow**")
                        mirror_df = pd.DataFrame(drilldown.mirror_series, columns=["Year", "Import mirror (US$ thousand)"])
                        line_chart(mirror_df, x_col="Year", y_col="Import mirror (US$ thousand)")


# ── Tab 2: Corridor Trends ────────────────────────────────────────────────────

def _tab_corridor_trends() -> None:
    control_col, intel_col = st.columns([1.0, 1.2], gap="large")
    with control_col:
        panel_header("Corridor Controls", "Set the corridor, time horizon, and product lens.", "WITS")
        e1, e2 = st.columns(2)
        with e1:
            exp = country_selectbox("Exporting country", default_iso3="KEN", key="texp")
        with e2:
            imp = country_selectbox("Importing country", default_iso3="USA", key="timp")
        y0, y1 = st.slider("Year range", 2000, 2023, (2018, 2022), key="tcorr_years")
        product = st.text_input(
            "WITS product group",
            "total",
            key="tprod",
            help="Use 'total' for all goods, or a product group code.",
        )
        mirror = st.checkbox("Include mirror import series", value=False, key="tcorr_mirror")
        load_corridor = st.button("Load corridor trend", type="primary", key="tcorr_load")

    series = st.session_state.get("tcorr_series")
    exp_name = st.session_state.get("tcorr_exp", exp)
    imp_name = st.session_state.get("tcorr_imp", imp)
    corridor_feed = summarize_corridor(series, exp_name, imp_name) if series else []

    with intel_col:
        panel_header("Live Corridor Feed", "Narrative-style notes for the selected bilateral route.", "Intel")
        render_terminal_feed(
            corridor_feed,
            empty_message="Load a corridor to generate growth, stagnation, and mirror-series notes.",
        )

    if load_corridor:
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
            insights = summarize_corridor(series, exp_name, imp_name)
            render_insights(insights)

            tdf = pd.DataFrame(series, columns=["Year", "Export (US$ thousand)"])
            if len(series) >= 2:
                y0_s, v0_s = series[0]
                y_last_s, v_last_s = series[-1]
                span_s = int(y_last_s) - int(y0_s)
                cagr_val = None
                if span_s > 0 and v0_s > 0 and v_last_s > 0:
                    cagr_val = ((v_last_s / v0_s) ** (1.0 / span_s) - 1.0) * 100

                mk1, mk2, mk3 = st.columns(3)
                with mk1:
                    st.markdown(kpi_card("Start value", fmt_usd(v0_s * 1000), str(y0_s)), unsafe_allow_html=True)
                with mk2:
                    st.markdown(kpi_card("Latest value", fmt_usd(v_last_s * 1000), str(y_last_s)), unsafe_allow_html=True)
                with mk3:
                    if cagr_val is not None:
                        neg = cagr_val < 0
                        st.markdown(kpi_card("CAGR", f"{cagr_val:+.1f}%", f"Over {span_s} years", negative=neg), unsafe_allow_html=True)

            chart_col, data_col = st.columns([1.45, 1.0], gap="large")
            with chart_col:
                panel_header("Exporter-Reported Trend", "Primary bilateral trade series from WITS.", "Chart")
                line_chart(tdf, x_col="Year", y_col="Export (US$ thousand)")
            with data_col:
                panel_header("Raw Corridor Data", "Exact points behind the trend line.", "Table")
                st.dataframe(tdf, use_container_width=True, hide_index=True)

        if mseries:
            panel_header("Mirror Series", "Importer-reported view of the same corridor.", "Mirror")
            insights_m = summarize_corridor(mseries, imp_name, exp_name)
            render_insights(insights_m)
            mdf = pd.DataFrame(mseries, columns=["Year", "Import mirror (US$ thousand)"])
            line_chart(mdf, x_col="Year", y_col="Import mirror (US$ thousand)")


# ── Tab 3: Opportunity Ranker ─────────────────────────────────────────────────

def _tab_opportunity_ranker() -> None:
    control_col, method_col = st.columns([1.0, 1.15], gap="large")
    with control_col:
        panel_header("Ranking Controls", "Choose the exporter plus whether to use the latest snapshot or full available history.", "Score")
        o1, o2 = st.columns(2)
        with o1:
            sc = country_selectbox("Supplier / exporter country", default_iso3="KEN", key="oc")
            fq = st.selectbox("Comtrade frequency", ("A", "M"), key="of")
            period_mode = st.radio(
                "Comtrade snapshot",
                ("Latest available", "Manual"),
                horizontal=True,
                key="op_mode",
                help="Latest available probes recent Comtrade periods and uses the newest one that returns partner data.",
            )
            p = None
            if period_mode == "Manual":
                p = period_selectbox(
                    "Comtrade period",
                    freq_code=fq,
                    default_period=period_options(fq)[0],
                    key="op",
                )
            else:
                st.caption("Uses the newest Comtrade period that actually returns destination rows.")
            hs = st.text_input("HS pool (or TOTAL)", "TOTAL", key="oh")
        with o2:
            pool = st.number_input("Destination pool size", 10, 50, 25, key="opool",
                                   help="How many top Comtrade destinations to score.")
            out_n = st.number_input("Top results to display", 5, 30, 15, key="ooutn")
            wits_window_mode = st.radio(
                "WITS history",
                ("Full available history", "Custom window"),
                horizontal=True,
                key="ow_mode",
                help="Full available history requests the complete WITS range and skips missing years automatically.",
            )
            wy0 = wy1 = None
            if wits_window_mode == "Custom window":
                wy0, wy1 = st.slider("WITS scoring window", 1988, date.today().year, (2018, min(2023, date.today().year)), key="ow")
            else:
                st.caption("Uses the actual earliest and latest WITS observations returned for each market pair.")
            wprod = st.text_input("WITS product", "total", key="owp")
        compute_opps = st.button("Compute opportunities", type="primary", key="ocompute")

    with method_col:
        panel_header("Scoring Logic", "How size and growth combine into a destination ranking.", "Method")
        st.markdown("""
        **Opportunity Score = 0.62 × Size + 0.38 × Growth**

        - **Size** (0–1): Log-scaled bilateral export value from the latest available WITS observation, normalized against the largest partner
        - **Growth** (0–1): CAGR across the actual available WITS history for each market pair, with missing years skipped
        - **Comtrade pool**: By default the destination pool comes from the latest Comtrade period that returns partner data

        | Score | Rating | Interpretation |
        |-------|--------|----------------|
        | ≥ 0.65 | 🟢 High | Large, fast-growing market — prioritize |
        | 0.40–0.65 | 🟡 Medium | Solid opportunity — worth exploring |
        | < 0.40 | 🔴 Low | Smaller or slower-growing market |
        """)

    if compute_opps:
        with st.spinner("Ranking markets — this may take a minute (rate-limited API calls)…"):
            df, resolved = rank_exporter_opportunities(
                sc, comtrade_period=p, comtrade_freq=fq, cmd_code=hs,
                pool_size=int(pool), score_count=int(out_n),
                wits_year_from=int(wy0) if wy0 is not None else None,
                wits_year_to=int(wy1) if wy1 is not None else None,
                product=wprod,
            )
        st.session_state["opp_df"] = df
        st.session_state["opp_reporter"] = resolved

    df_opp = st.session_state.get("opp_df")
    reporter_opp = st.session_state.get("opp_reporter")

    if df_opp is not None and reporter_opp is not None:
        resolved_period = df_opp.attrs.get("comtrade_period")
        resolved_freq = df_opp.attrs.get("comtrade_freq")
        wits_window_mode = df_opp.attrs.get("wits_window_mode", "custom_window")
        requested_wits_from = df_opp.attrs.get("wits_year_from")
        requested_wits_to = df_opp.attrs.get("wits_year_to")
        st.markdown(
            f'<span class="source-pill">Reporter</span> **{reporter_opp.name}** ({reporter_opp.iso3})',
            unsafe_allow_html=True,
        )
        meta_bits = []
        if resolved_period:
            meta_bits.append(f"Comtrade snapshot: {resolved_period} ({resolved_freq})")
        if wits_window_mode == "full_available_history":
            meta_bits.append("WITS history: full available range")
        elif requested_wits_from and requested_wits_to:
            meta_bits.append(f"WITS history: {requested_wits_from}-{requested_wits_to}")
        if meta_bits:
            st.caption(" | ".join(meta_bits))
        insights = summarize_opportunities(df_opp, reporter_opp.name)
        render_insights(insights)

        if df_opp.empty:
            st.warning("No scored rows returned.")
        else:
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
            if {"wits_start_year", "wits_latest_year"}.issubset(display_df.columns):
                display_df["WITS history"] = display_df.apply(
                    lambda row: (
                        f"{int(row['wits_start_year'])}-{int(row['wits_latest_year'])}"
                        if pd.notna(row["wits_start_year"]) and pd.notna(row["wits_latest_year"])
                        else "N/A"
                    ),
                    axis=1,
                )
            if "wits_history_points" in display_df.columns:
                display_df["WITS points"] = display_df["wits_history_points"].apply(
                    lambda v: str(int(v)) if v is not None and not pd.isna(v) else "N/A"
                )
            if "comtrade_export_usd" in display_df.columns:
                display_df["Comtrade export"] = display_df["comtrade_export_usd"].apply(
                    lambda v: fmt_usd(float(v)) if v is not None else "N/A"
                )

            show_cols = []
            for col_pair in [("partner", "Market"), ("Score", "Score"), ("CAGR", "CAGR"),
                              ("Latest flow", "Latest flow"), ("WITS history", "WITS history"),
                              ("WITS points", "WITS points"), ("Comtrade export", "Comtrade export"),
                              ("wits_latest_year", "Data year")]:
                src, dst = col_pair
                if src in display_df.columns:
                    display_df = display_df.rename(columns={src: dst}) if src != dst else display_df
                    show_cols.append(dst)

            result_col, chart_col = st.columns([1.15, 1.0], gap="large")
            with result_col:
                panel_header("Ranked Opportunities", "Scored destination list ready for export.", "Results")
                st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
            with chart_col:
                panel_header("Score Distribution", "Visual ranking of the strongest markets.", "Chart")
                if "opportunity" in df_opp.columns and "partner" in df_opp.columns:
                    chart_df = df_opp[["partner", "opportunity"]].dropna(subset=["opportunity"]).head(15)
                    chart_df = chart_df.rename(columns={"partner": "Market", "opportunity": "Score"})
                    bar_chart(chart_df, x_col="Market", y_col="Score", color="#ff4ecd", height=320)

            csv = df_opp.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Export to CSV",
                data=csv,
                file_name=f"opportunities_{reporter_opp.iso3}_{resolved_period or 'latest'}.csv",
                mime="text/csv",
                key="opp_csv",
            )


# ── Tab 4: Country Profiles ───────────────────────────────────────────────────

def _tab_country_profiles() -> None:
    control_col, notes_col = st.columns([1.0, 1.1], gap="large")
    with control_col:
        panel_header("Profile Controls", "Choose the country and historical range for the macro profile.", "Macro")
        p1, p2, p3 = st.columns(3)
        with p1:
            profile_country = country_selectbox("Country to profile", default_iso3="KEN", key="wb_country")
        with p2:
            yf = st.number_input("From year", min_value=1990, max_value=date.today().year - 1, value=2014, key="wb_yf")
        with p3:
            yt = st.number_input("To year", min_value=1990, max_value=date.today().year - 1, value=date.today().year - 1, key="wb_yt")
        load_profile = st.button("Load country profile", type="primary", key="wb_load")

    with notes_col:
        panel_header("Macro Briefing", "This workspace turns World Bank indicators into an investor-style profile.", "Brief")
        st.markdown(
            """
            <div class="terminal-note">
                Focus on the combination of GDP growth, FDI inflows, inflation, trade openness,
                and population scale when deciding whether a market deserves deeper corridor or
                product analysis.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if load_profile:
        with st.spinner(f"Fetching World Bank data for {profile_country}…"):
            prof = country_profile(profile_country, year_from=int(yf), year_to=int(yt))
        st.session_state["wb_profile"] = prof
        st.session_state["wb_country_iso3"] = profile_country

    prof = st.session_state.get("wb_profile")
    if prof is None:
        return

    label, emoji, score = market_attractiveness_score(prof)
    attr_class = {"High": "attr-high", "Medium": "attr-medium", "Low": "attr-low"}.get(label, "attr-medium")

    gdp_pc = prof.get("gdp_per_capita_latest")
    gdp_gr = prof.get("gdp_growth_latest")
    pop = prof.get("population_latest")
    fdi = prof.get("fdi_inflows_latest")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        val = fmt_usd(gdp_pc) if gdp_pc else "N/A"
        yr = prof.get("gdp_per_capita_latest_year", "")
        st.markdown(kpi_card("GDP per capita", val, str(yr)), unsafe_allow_html=True)
    with k2:
        val = f"{gdp_gr:+.1f}%" if gdp_gr is not None else "N/A"
        yr = prof.get("gdp_growth_latest_year", "")
        neg = gdp_gr is not None and gdp_gr < 0
        st.markdown(kpi_card("GDP growth", val, str(yr), negative=neg), unsafe_allow_html=True)
    with k3:
        val = fmt_usd(abs(float(fdi))) if fdi is not None else "N/A"
        yr = prof.get("fdi_inflows_latest_year", "")
        neg_fdi = fdi is not None and float(fdi) < 0
        st.markdown(kpi_card("FDI inflows", val, str(yr), negative=neg_fdi), unsafe_allow_html=True)
    with k4:
        val = fmt_number(float(pop)) if pop is not None else "N/A"
        yr = prof.get("population_latest_year", "")
        st.markdown(kpi_card("Population", val, str(yr)), unsafe_allow_html=True)

    st.markdown("")
    st.markdown(
        f'<div><b>Market Attractiveness: </b>'
        f'<span class="attr-badge {attr_class}">{emoji} {label} ({score:.2f})</span></div>',
        unsafe_allow_html=True,
    )

    country_name = profile_country  # ISO3; could be resolved to a full name
    insights = summarize_country_profile(prof, country_name)
    render_insights(insights)

    panel_header("Indicator Trends", "Compare core macro indicators in one integrated trend chart.", "Charts")

    indicators_to_plot = [
        ("gdp_per_capita", "GDP per capita (USD)"),
        ("gdp_growth", "GDP growth (annual %)"),
        ("fdi_inflows", "FDI net inflows (USD)"),
        ("trade_pct_gdp", "Trade (% of GDP)"),
        ("inflation", "Inflation (annual %)"),
        ("exports_pct_gdp", "Exports (% of GDP)"),
    ]
    indicator_map = {field: label for field, label in indicators_to_plot}
    trend_views = {
        "All": [field for field, _ in indicators_to_plot],
        "GDP": ["gdp_per_capita", "gdp_growth"],
        "Trade": ["trade_pct_gdp", "exports_pct_gdp"],
        "FDI": ["fdi_inflows"],
        "Consumer": ["inflation"],
    }
    selected_view = st.radio(
        "Integrated macro view",
        tuple(trend_views.keys()),
        horizontal=True,
        key="wb_trend_view",
        help="Switch between indicator groups while keeping the chart in one integrated workspace.",
    )
    selected_series = {
        indicator_map[field]: prof.get(field, [])
        for field in trend_views[selected_view]
        if prof.get(field, [])
    }
    if not selected_series and selected_view != "All":
        selected_series = {
            indicator_map[field]: prof.get(field, [])
            for field, _ in indicators_to_plot
            if prof.get(field, [])
        }
    st.caption("Lines are indexed to each series' own range so indicators with different units can share one chart. Hover for raw values.")
    wb_profile_multi_chart(selected_series, height=340)

    with st.expander("Raw World Bank data table"):
        rows = []
        for field, label in indicators_to_plot:
            series = prof.get(field, [])
            for year, val in series:
                rows.append({"Indicator": label, "Year": year, "Value": val})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Tab 5: Macro Intelligence (IMF) ──────────────────────────────────────────

def _tab_macro_intelligence() -> None:
    with st.expander("Quick picks — common IMF datasets", expanded=False):
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

    search_col, query_col = st.columns([1.0, 1.25], gap="large")
    with search_col:
        panel_header("Dataset Search", "Start from a known IMF family, then inspect its dimensions.", "Search")
        search_term = st.text_input(
            "Search IMF datasets",
            st.session_state.get("imf_search_term", "CPI"),
            key="imf_search_term",
            help="Filter by dataset code or name (e.g. CPI, IFS, BOP).",
        )
        if st.button("Search datasets", key="imf_search_button"):
            with st.spinner("Loading IMF datasets…"):
                st.session_state["imf_dataflows_df"] = list_dataflows(search=search_term)

    dataflows_df = st.session_state.get("imf_dataflows_df")
    with query_col:
        panel_header("Dataset Terminal", "Available IMF datasets matching the current search.", "Catalog")
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

    with st.expander("Dataset structure (raw)", expanded=False):
        if isinstance(dataflow_info, dict):
            st.json(dataflow_info)
        else:
            st.info("No structure loaded yet.")

    st.divider()
    panel_header("Build Query", "Select dimensions and produce an SDMX series key automatically.", "Query")
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
        label_map = imf_option_label_map(options)
        default_values = [v for v in imf_default_values(dim_id) if v in label_map]

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

    with st.expander("Advanced options"):
        imf_periods = imf_period_options(selected_freq)
        period_select_options = ["Any", "Custom..."] + imf_periods if imf_periods else ["Any", "Custom..."]
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

    if st.button("Load IMF data", key="imf_load_button", type="primary"):
        try:
            query = IMFDataQuery(
                dataset=dataset,
                key=series_key or None,
                start_period=start_period or None,
                end_period=end_period or None,
                extra_params=parse_kv_lines(extra_params),
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
                    st.markdown("### Adjust Time Period")
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

            chart_col, table_col = st.columns([1.35, 1.0], gap="large")
            with chart_col:
                panel_header("IMF Series Chart", "Rendered directly from the filtered SDMX response.", "Chart")
                imf_time_series_chart(filtered_df)
            with table_col:
                panel_header("Raw IMF Rows", "Underlying records for the visible chart.", "Table")
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Export to CSV", data=csv,
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

    st.markdown(APP_CSS, unsafe_allow_html=True)
    configure_sidebar()
    render_hero()

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏁 Landing",
        "🌍 Market Explorer",
        "📈 Corridor Trends",
        "🚀 Opportunity Ranker",
        "🌐 Country Profiles",
        "🏦 Macro Intelligence",
    ])

    with tab0:
        _tab_landing()
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
