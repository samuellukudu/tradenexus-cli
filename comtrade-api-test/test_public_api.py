#!/usr/bin/env python3
"""Smoke tests for UN Comtrade public API via comtradeapicall (no subscription key)."""

import comtradeapicall


def main() -> None:
    print("=== 1. Reference: reporters (first 5 rows) ===")
    reporters = comtradeapicall.getReference("reporter")
    print(reporters.head())
    print(f"Total reporters: {len(reporters)}\n")

    print("=== 2. Metadata (May 2022, Australia HS monthly) ===")
    meta = comtradeapicall._getMetadata(
        typeCode="C",
        freqCode="M",
        clCode="HS",
        period="202205",
        reporterCode="36",
        showHistory=False,
    )
    print(meta.head())
    print(f"Metadata rows: {len(meta)}\n")

    print("=== 3. Preview final trade data (max 10 rows) ===")
    # Australia imports, HS chapter 91, May 2022
    trades = comtradeapicall.previewFinalData(
        typeCode="C",
        freqCode="M",
        clCode="HS",
        period="202205",
        reporterCode="36",
        cmdCode="91",
        flowCode="M",
        partnerCode=None,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=10,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    if trades is None or trades.empty:
        print("No trade rows returned (API may be rate-limited or period unavailable).")
    else:
        cols = [c for c in ("period", "reporterDesc", "partnerDesc", "cmdDesc", "primaryValue") if c in trades.columns]
        print(trades[cols].head() if cols else trades.head())
        print(f"Rows returned: {len(trades)}")

    print("\n=== 4. ISO3 → Comtrade codes ===")
    codes = comtradeapicall.convertCountryIso3ToCode("USA,FRA")
    print(f"USA,FRA → {codes}")

    print("\nDone. Public preview/metadata/reference calls need no subscription key.")


if __name__ == "__main__":
    main()
