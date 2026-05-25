"""Bilateral product drill-down for an exporter to importer corridor."""

from __future__ import annotations

import json
from dataclasses import dataclass

import comtradeapicall
import pandas as pd

from comtrade_countries import Country, resolve_country
from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle
from trade_intel.wits_timeseries import (
    fetch_bilateral_export_series,
    fetch_bilateral_import_series,
)

_HS_LEVELS = frozenset({"AG2", "AG4", "AG6"})


@dataclass(frozen=True)
class ProductDrilldown:
    exporter: Country
    importer: Country
    period: str
    freq_code: str
    hs_level: str
    products: pd.DataFrame
    export_series: list[tuple[str, float]]
    mirror_series: list[tuple[str, float]]
    notes: list[str]


def _normalize_hs_level(hs_level: str) -> str:
    level = hs_level.upper().strip()
    if level not in _HS_LEVELS:
        allowed = ", ".join(sorted(_HS_LEVELS))
        raise ValueError(f"HS detail level must be one of: {allowed}.")
    return level


def _fetch_bilateral_product_rows(
    exporter: Country,
    importer: Country,
    *,
    period: str,
    freq_code: str,
    hs_level: str,
    max_records: int = 500,
) -> pd.DataFrame:
    key = make_key(
        "comtrade_bilateral_products",
        exporter=str(exporter.code),
        importer=str(importer.code),
        period=period,
        freq=freq_code,
        hs=hs_level,
        max=max_records,
    )
    cached = cache_get(key)
    if cached is not None:
        return pd.DataFrame(cached)

    throttle()
    df = comtradeapicall.previewFinalData(
        typeCode="C",
        freqCode=freq_code,
        clCode="HS",
        period=period,
        reporterCode=str(exporter.code),
        cmdCode=hs_level,
        flowCode="X",
        partnerCode=str(importer.code),
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=max_records,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    if df is not None and not df.empty:
        records = json.loads(df.to_json(orient="records", date_format="iso"))
        cache_set(key, records)
    return df


def _prepare_product_table(df: pd.DataFrame | None, *, top_n: int) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if "cmdCode" not in out.columns or "primaryValue" not in out.columns:
        return pd.DataFrame()

    out["primaryValue"] = pd.to_numeric(out["primaryValue"], errors="coerce")
    out = out.dropna(subset=["primaryValue"])
    if out.empty:
        return pd.DataFrame()

    if "qty" in out.columns:
        out["qty"] = pd.to_numeric(out["qty"], errors="coerce")

    group_cols = [c for c in ("cmdCode", "cmdDesc", "period", "qtyUnitAbbr") if c in out.columns]
    agg_map: dict[str, str] = {"primaryValue": "sum"}
    if "qty" in out.columns:
        agg_map["qty"] = "sum"
    grouped = out.groupby(group_cols, dropna=False, as_index=False).agg(agg_map)

    total_value = float(grouped["primaryValue"].sum())
    grouped["share_pct"] = (
        grouped["primaryValue"] / total_value * 100.0 if total_value > 0 else 0.0
    )
    grouped = grouped.sort_values("primaryValue", ascending=False).head(top_n).reset_index(drop=True)

    renamed = grouped.rename(
        columns={
            "cmdCode": "product_code",
            "cmdDesc": "product",
            "primaryValue": "export_usd",
            "period": "period",
            "qty": "quantity",
            "qtyUnitAbbr": "quantity_unit",
        }
    )
    cols = [
        c
        for c in (
            "product_code",
            "product",
            "export_usd",
            "share_pct",
            "period",
            "quantity",
            "quantity_unit",
        )
        if c in renamed.columns
    ]
    return renamed[cols]


def build_bilateral_product_drilldown(
    exporter: str | Country,
    importer: str | Country,
    *,
    period: str,
    freq_code: str = "A",
    hs_level: str = "AG2",
    top_n: int = 15,
    wits_year_from: int = 2018,
    wits_year_to: int = 2022,
    wits_product: str = "total",
    include_mirror: bool = True,
) -> ProductDrilldown:
    exp = exporter if isinstance(exporter, Country) else resolve_country(exporter)
    imp = importer if isinstance(importer, Country) else resolve_country(importer)
    if exp.code == imp.code:
        raise ValueError("Exporter and importer must be different countries.")

    level = _normalize_hs_level(hs_level)
    raw = _fetch_bilateral_product_rows(
        exp,
        imp,
        period=period,
        freq_code=freq_code,
        hs_level=level,
    )
    products = _prepare_product_table(raw, top_n=top_n)

    notes: list[str] = []
    export_series: list[tuple[str, float]] = []
    mirror_series: list[tuple[str, float]] = []

    try:
        export_series = fetch_bilateral_export_series(
            exp.iso3,
            imp.iso3,
            wits_year_from,
            wits_year_to,
            product=wits_product.lower(),
        )
    except RuntimeError as exc:
        notes.append(f"WITS export context unavailable: {exc}")

    if include_mirror:
        try:
            mirror_series = fetch_bilateral_import_series(
                exp.iso3,
                imp.iso3,
                wits_year_from,
                wits_year_to,
                product=wits_product.lower(),
            )
        except RuntimeError as exc:
            notes.append(f"WITS mirror context unavailable: {exc}")

    if products.empty:
        notes.append("No Comtrade product rows returned for this corridor and period.")

    return ProductDrilldown(
        exporter=exp,
        importer=imp,
        period=period,
        freq_code=freq_code,
        hs_level=level,
        products=products,
        export_series=export_series,
        mirror_series=mirror_series,
        notes=notes,
    )
