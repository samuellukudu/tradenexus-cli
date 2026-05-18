"""WITS queries: trade stats, TRAINS tariffs, and data availability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.etree.ElementTree import Element

from wits_client import BASE_URL, WITS_NS, get_json, get_xml, xml_text
from wits_countries import WitsCountry, load_countries, resolve_country

SDMX_BASE = f"{BASE_URL}/SDMX/V21/datasource"


@dataclass(frozen=True)
class BilateralTradeQuery:
    export_country: WitsCountry
    import_country: WitsCountry
    year: str
    product: str
    indicator: str


def _observation_value(payload: dict[str, Any]) -> tuple[str, float] | None:
    datasets = payload.get("dataSets") or []
    if not datasets:
        return None
    series = datasets[0].get("series") or {}
    if not series:
        return None
    first = next(iter(series.values()))
    observations = first.get("observations") or {}
    if not observations:
        return None
    obs = next(iter(observations.values()))
    value = float(obs[0])
    structure = payload.get("structure") or {}
    year = ""
    obs_dims = (structure.get("dimensions") or {}).get("observation") or []
    for dim in obs_dims:
        if dim.get("id") == "TIME_PERIOD":
            values = dim.get("values") or []
            if values:
                year = str(values[0].get("id", ""))
    return year, value


def fetch_trade_value(
    export: str | WitsCountry,
    import_: str | WitsCountry,
    *,
    year: str = "2020",
    product: str = "total",
    indicator: str = "XPRT-TRD-VL",
) -> tuple[dict[str, Any], BilateralTradeQuery]:
    """
    Bilateral export trade value (US$ thousand) from export → import country.

    Uses Trade Stats – Trade: reporter = exporter, partner = importer.
    """
    export_c = export if isinstance(export, WitsCountry) else resolve_country(export)
    import_c = import_ if isinstance(import_, WitsCountry) else resolve_country(import_)
    if export_c.iso3 == import_c.iso3:
        raise ValueError("Export and import country must be different.")

    spec = BilateralTradeQuery(
        export_country=export_c,
        import_country=import_c,
        year=year,
        product=product.lower(),
        indicator=indicator.upper(),
    )
    url = (
        f"{SDMX_BASE}/tradestats-trade/reporter/{export_c.iso3.lower()}/year/{year}"
        f"/partner/{import_c.iso3.lower()}/product/{spec.product}/indicator/{spec.indicator}"
        f"?format=JSON"
    )
    return get_json(url), spec


def fetch_data_availability(
    country: str | WitsCountry,
    *,
    year: str = "all",
    datasource: str = "trn",
) -> list[dict[str, str]]:
    """
    Data availability for a reporter country and year(s).

    Matches: .../datasource/trn/dataavailability/country/{code}/year/{year}
    """
    c = country if isinstance(country, WitsCountry) else resolve_country(country)
    url = f"{BASE_URL}/wits/datasource/{datasource}/dataavailability/country/{c.code}/year/{year}"
    root = get_xml(url)
    rows: list[dict[str, str]] = []
    for rep in root.findall(f".//{{{WITS_NS}}}reporter"):
        nom = rep.find(f"{{{WITS_NS}}}reporternernomenclature")
        nomen = ""
        if nom is not None:
            nomen = f"{nom.get('reporternernomenclaturecode', '')} {(nom.text or '').strip()}".strip()
        rows.append(
            {
                "country_code": rep.get("countrycode", ""),
                "iso3": rep.get("iso3Code", ""),
                "name": xml_text(rep, "name"),
                "year": xml_text(rep, "year"),
                "nomenclature": nomen,
                "partner_list": xml_text(rep, "partnerlist"),
                "last_updated": xml_text(rep, "lastupdateddate"),
            }
        )
    return rows


def fetch_tariff(
    export: str | WitsCountry,
    import_: str | WitsCountry,
    *,
    year: str = "2000",
    product: str = "020110",
    datatype: str = "reported",
) -> dict[str, Any]:
    """
  MFN/preferential tariff applied by the import country on goods from the export country.

  TRAINS: reporter = import country (numeric code), partner = export country.
    """
    export_c = export if isinstance(export, WitsCountry) else resolve_country(export)
    import_c = import_ if isinstance(import_, WitsCountry) else resolve_country(import_)
    # TRAINS metadata uses numeric codes on reporter/partner in tariff URLs
    trn_countries = {c.iso3: c for c in load_countries("trn") if not c.is_group}
    imp = trn_countries.get(import_c.iso3) or import_c
    exp = trn_countries.get(export_c.iso3) or export_c
    url = (
        f"{SDMX_BASE}/TRN/reporter/{imp.code}/partner/{exp.code}/product/{product}"
        f"/year/{year}/datatype/{datatype}?format=JSON"
    )
    return get_json(url)


def format_trade_result(payload: dict[str, Any], spec: BilateralTradeQuery) -> str:
    obs = _observation_value(payload)
    if obs is None:
        return "No trade value in response."
    yr, value = obs
    lines = [
        f"Export: {spec.export_country.name} ({spec.export_country.iso3})",
        f"Import: {spec.import_country.name} ({spec.import_country.iso3})",
        f"Year: {yr or spec.year}  Product: {spec.product}  Indicator: {spec.indicator}",
        f"Value (US$ thousand): {value:,.3f}",
    ]
    return "\n".join(lines)
