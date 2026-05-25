#!/usr/bin/env python3
"""Smoke test for the IMF SDMX public API."""

from trade_intel.imf_data import fetch_dataset, IMFDataQuery, list_dataflows


def main() -> None:
    flows = list_dataflows(search="CPI")
    print(f"=== 1. Matching dataflows: {len(flows)} ===")
    print(flows.head(5).to_string(index=False))
    print()

    print("=== 2. CPI sample: USA + CAN from 2018 ===")
    query = IMFDataQuery(
        dataset="CPI",
        key="USA+CAN.CPI.CP01.IX.M",
        start_period="2018",
    )
    df = fetch_dataset(query)
    print(df.head(10).to_string(index=False))
    print(f"\nRows returned: {len(df)}")


if __name__ == "__main__":
    main()
