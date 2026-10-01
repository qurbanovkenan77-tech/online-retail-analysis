"""Command-line entry point: python -m retail_analysis."""

import argparse
import json
import os
import platform
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from retail_analysis.analysis import (
    NET_VALUE_DEFINITION,
    PARTIAL_MONTH_NOTE,
    build_analysis,
)
from retail_analysis.charts import CHART_FILENAMES, create_charts
from retail_analysis.data import (
    MONEY_ABS_TOLERANCE,
    MONEY_REL_TOLERANCE,
    clean_data,
    file_sha256,
    load_workbook,
)


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Analyze UCI Online Retail merchandise sales, cancellations, "
            "products, countries, months, and customer concentration."
        ),
        epilog=(
            "December 2011 is designated partial for this UCI source. "
            "Review this rule before using a different dataset."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the source Excel workbook.",
    )
    parser.add_argument(
        "--output",
        default=Path("outputs"),
        type=Path,
        help="Output directory (default: outputs).",
    )
    return parser.parse_args(argv)


def formatted_number(value):
    """Two decimals, blank for unavailable, and no displayed negative zero."""
    if pd.isna(value):
        return ""
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def export_table(table, destination):
    """Format an export copy without changing calculation precision."""
    exported = table.copy()

    for column in exported.columns:
        if (
            column.endswith("_gbp")
            or column.endswith("_pct")
            or column == "percentage_change"
        ):
            exported[column] = exported[column].map(formatted_number)

        elif (
            column.endswith("_rows")
            or column.endswith("_count")
            or column.endswith("_rank")
            or column in {"source_row", "display_order", "Quantity"}
        ):
            exported[column] = exported[column].astype("Int64")

    # UnitPrice retains source precision, including small positive prices.
    # Formatted GBP values contain no symbols or thousands separators,
    # so CSV readers can still interpret them as numeric values.
    exported.to_csv(
        destination,
        index=False,
        na_rep="",
        date_format="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        lineterminator="\n",
    )


def make_metadata(source, input_hash, output, filenames, cleaned):
    return {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_filename": source.name,
        "input_sha256": input_hash,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependency_versions": {
            name: version(name)
            for name in [
                "pandas", "openpyxl", "matplotlib", "pytest", "numpy"
            ]
        },
        "output_paths": {
            filename: str(output / filename)
            for filename in filenames
        },
        "currency": "GBP",
        "net_value_definition": NET_VALUE_DEFINITION,
        "partial_month_policy": PARTIAL_MONTH_NOTE,
        "monthly_timestamp_definition": (
            "First and last observed eligible transaction timestamps; "
            "these do not establish complete calendar coverage."
        ),
        "duplicate_policy": (
            "Remove exact duplicates using the eight original columns, "
            "retaining the first. Identical lines may be legitimate."
        ),
        "excluded_entries_basis": "post_deduplication",
        "monetary_reconciliation_tolerance": {
            "absolute_gbp": MONEY_ABS_TOLERANCE,
            "relative": MONEY_REL_TOLERANCE,
        },
        "export_policy": (
            "GBP amounts and percentages use two decimals. UnitPrice "
            "retains source precision. Blank means unavailable. "
            "Rounded group sums can differ from rounded overall totals."
        ),
        "raw_profile": cleaned.raw_profile,
    }


def run_analysis(source, output):
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()

    if not source.is_file():
        raise FileNotFoundError(f"Input workbook not found: {source}")

    print(f"Reading {source.name}...", flush=True)
    input_hash = file_sha256(source)
    raw = load_workbook(source)

    print("Cleaning and reconciling merchandise rows...", flush=True)
    cleaned = clean_data(raw)

    print("Calculating summaries and duplicate sensitivity...", flush=True)
    tables = build_analysis(raw, cleaned)

    if file_sha256(source) != input_hash:
        raise ValueError("Input workbook changed during the run.")

    filenames = [
        *tables,
        *CHART_FILENAMES,
        "run_metadata.json",
    ]

    output.mkdir(parents=True, exist_ok=True)

    for filename in filenames:
        target = output / filename
        if target.resolve() == source:
            raise ValueError("An output path would overwrite the input.")
        if target.is_symlink():
            raise ValueError(f"Refusing to replace symbolic link: {target}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Output target is not a file: {target}")

    # Prepare the complete output set before replacing existing reports.
    # Temporary files are created on the output filesystem.
    with tempfile.TemporaryDirectory(
        prefix=".retail-analysis-", dir=output
    ) as temporary:
        staging = Path(temporary)

        for filename, table in tables.items():
            export_table(table, staging / filename)

        create_charts(tables, staging)

        metadata = make_metadata(
            source, input_hash, output, filenames, cleaned
        )
        (staging / "run_metadata.json").write_text(
            json.dumps(metadata, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

        for filename in filenames:
            os.replace(staging / filename, output / filename)

    print(
        f"Created 9 CSVs, 4 PNGs, and run_metadata.json in {output}",
        flush=True,
    )
    print(f"Eligible merchandise rows: {len(cleaned.eligible):,}")
    return 0


def main(argv=None):
    args = parse_arguments(argv)

    try:
        return run_analysis(args.input, args.output)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())