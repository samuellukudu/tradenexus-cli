"""
Streamlit UI for exporter-focused trade intelligence (Comtrade + WITS).

Run from project root:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from comtrade_countries import Country, list_countries
from trade_intel.comtrade_flows import top_export_destinations
from trade_intel.config import RunConfig, set_config
from trade_intel.opportunities import rank_exporter_opportunities
from trade_intel.reports import build_bilateral_report, format_bilateral_report
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
            period = st.text_input("Period", "2020", help="Annual e.g. 2020, or monthly YYYYMM")
        with c3:
            freq = st.selectbox("Frequency", ("A", "M"))
        with c4:
            cmd = st.text_input("HS code", "TOTAL")
        top_n = st.slider("Rows to show", 5, 50, 15)
        if st.button("Load destinations", type="primary"):
            with st.spinner("Fetching Comtrade preview…"):
                df, resolved = top_export_destinations(
                    country,
                    period=period,
                    freq_code=freq,
                    cmd_code=cmd,
                    top_n=top_n,
                )
            st.success(f"Reporter: **{resolved.name}** ({resolved.iso3})")
            if df.empty:
                st.warning("No rows returned.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                if "primaryValue" in df.columns:
                    chart = df.rename(columns={"partnerDesc": "Partner", "primaryValue": "USD"})[
                        ["Partner", "USD"]
                    ].head(min(20, len(df)))
                    st.bar_chart(chart.set_index("Partner"))

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
                st.line_chart(tdf.set_index("Year"))
                st.dataframe(tdf, use_container_width=True, hide_index=True)
            if mirror:
                from trade_intel.wits_timeseries import fetch_bilateral_import_series

                with st.spinner("Mirror series…"):
                    mseries = fetch_bilateral_import_series(
                        exp, imp, y0, y1, product=product.lower()
                    )
                if mseries:
                    mdf = pd.DataFrame(mseries, columns=["Year", "Import mirror (US$ thousand)"])
                    st.subheader("Importer-reported mirror (MPRT-TRD-VL)")
                    st.line_chart(mdf.set_index("Year"))

    with tab3:
        st.subheader("Rank markets by size + growth")
        st.markdown(
            "Uses your **latest Comtrade export destinations**, then scores each with **WITS bilateral export CAGR**."
        )
        o1, o2 = st.columns(2)
        with o1:
            sc = _country_selectbox("Supplier country", default_iso3="KEN", key="oc")
            p = st.text_input("Comtrade period", "2020", key="op")
            fq = st.selectbox("Comtrade freq", ("A", "M"), key="of")
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
                st.dataframe(disp, use_container_width=True, hide_index=True)
                if "opportunity" in disp.columns and "partner" in disp.columns:
                    iso = disp["partner_iso3"] if "partner_iso3" in disp.columns else pd.Series(["?"] * len(disp))
                    lbl = disp["partner"].astype(str) + " (" + iso.fillna("?").astype(str) + ")"
                    st.bar_chart(disp.assign(_lbl=lbl).set_index("_lbl")[["opportunity"]].head(15))

    st.divider()
    st.subheader("Full text report (optional)")
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        exp2 = _country_selectbox("Report — exporter country", default_iso3="KEN", key="r1")
    with rcol2:
        imp2 = _country_selectbox("Report — importer country", default_iso3="USA", key="r2")
    ry0, ry1 = st.slider("Report WITS years", 2000, 2023, (2018, 2022), key="r3")
    ctp = st.text_input("Comtrade snapshot period (blank to skip)", "", key="r4")
    rep_mirror = st.checkbox("Mirror in report", value=True, key="r5")
    if st.button("Build report"):
        report = build_bilateral_report(
            exp2,
            imp2,
            year_from=ry0,
            year_to=ry1,
            comtrade_period=ctp or None,
            comtrade_freq="A",
            product="total",
            include_mirror=rep_mirror,
        )
        st.text(format_bilateral_report(report))


if __name__ == "__main__":
    main()
