"""Bilateral trade queries: export country → import country."""

from __future__ import annotations

from dataclasses import dataclass

import comtradeapicall
import pandas as pd

from comtrade_countries import Country, resolve_country


@dataclass(frozen=True)
class BilateralQuery:
    export_country: Country
    import_country: Country
    period: str
    cmd_code: str
    max_records: int

    @property
    def reporter_code(self) -> str:
        return str(self.import_country.code)

    @property
    def partner_code(self) -> str:
        return str(self.export_country.code)


def fetch_bilateral(
  export: str | Country,
  import_: str | Country,
  *,
  period: str = "202205",
  freq_code: str = "M",
  cmd_code: str = "TOTAL",
  max_records: int = 500,
) -> tuple[pd.DataFrame, BilateralQuery]:
    """
    Trade from export country to import country.

    Comtrade reports from the importer's perspective: imports (M) into the
  reporter (import country) from the partner (export country).
    """
    export_c = export if isinstance(export, Country) else resolve_country(export)
    import_c = import_ if isinstance(import_, Country) else resolve_country(import_)
    if export_c.code == import_c.code:
        raise ValueError("Export and import country must be different.")

    spec = BilateralQuery(
        export_country=export_c,
        import_country=import_c,
        period=period,
        cmd_code=cmd_code,
        max_records=max_records,
    )

    df = comtradeapicall.previewFinalData(
        typeCode="C",
        freqCode=freq_code,
        clCode="HS",
        period=spec.period,
        reporterCode=spec.reporter_code,
        cmdCode=spec.cmd_code,
        flowCode="M",
        partnerCode=spec.partner_code,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=spec.max_records,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    return df, spec


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols = [
        c
        for c in (
            "period",
            "reporterDesc",
            "partnerDesc",
            "flowDesc",
            "cmdDesc",
            "primaryValue",
            "qty",
            "qtyUnitAbbr",
        )
        if c in df.columns
    ]
    return df[cols] if cols else df
