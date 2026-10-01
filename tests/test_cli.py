"""Exercise the application through real command-line subprocesses."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from retail_analysis.data import REQUIRED_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CSV_FILES = {
    "overall_summary.csv",
    "product_summary.csv",
    "country_summary.csv",
    "monthly_summary.csv",
    "customer_summary.csv",
    "duplicate_comparison.csv",
    "excluded_entries.csv",
    "cleaning_summary.csv",
    "large_value_lines.csv",
}

PNG_FILES = {
    "top_products.png",
    "country_sales.png",
    "monthly_sales.png",
    "sales_to_net.png",
}

EXPECTED_FILES = CSV_FILES | PNG_FILES | {"run_metadata.json"}


def run_cli(*arguments, cwd=None):
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(PROJECT_ROOT) + (os.pathsep + existing if existing else "")
    )

    return subprocess.run(
        [sys.executable, "-m", "retail_analysis", *map(str, arguments)],
        cwd=cwd or PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )


def write_workbook(path, quantity=5, invoice="100"):
    frame = pd.DataFrame(
        [
            [
                invoice, "TEST_A", "Test product", quantity,
                "2011-12-09 12:50:00", 10, "00123", "United Kingdom",
            ],
        ],
        columns=REQUIRED_COLUMNS,
    )
    frame.to_excel(path, index=False, engine="openpyxl")
    return frame


def test_help_and_required_input():
    help_result = run_cli("--help")
    assert help_result.returncode == 0
    assert "--input" in help_result.stdout
    assert "--output" in help_result.stdout

    missing_argument = run_cli()
    assert missing_argument.returncode != 0
    assert "--input" in missing_argument.stderr


def test_cli_outputs_metadata_and_repeatability_with_spaced_paths(tmp_path):
    source = tmp_path / "source workbook.xlsx"
    output = tmp_path / "analysis output"
    write_workbook(source)
    original_bytes = source.read_bytes()

    output.mkdir()
    unrelated = output / "keep this.txt"
    unrelated.write_text("Do not remove me.", encoding="utf-8")

    first = run_cli("--input", source, "--output", output)
    assert first.returncode == 0, first.stdout + first.stderr

    assert {path.name for path in output.iterdir()} == (
        EXPECTED_FILES | {"keep this.txt"}
    )
    assert source.read_bytes() == original_bytes
    assert unrelated.read_text(encoding="utf-8") == "Do not remove me."

    for filename in PNG_FILES:
        content = (output / filename).read_bytes()
        assert content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(content) > 1000

    overall = pd.read_csv(output / "overall_summary.csv")
    assert overall.loc[0, "positive_sales_gbp"] == 50
    assert overall.loc[0, "net_value_gbp"] == 50

    products = pd.read_csv(output / "product_summary.csv")
    assert products.loc[0, "positive_sales_rank"] == 1
    assert products.loc[0, "net_value_rank"] == 1

    months = pd.read_csv(output / "monthly_summary.csv")
    assert bool(months.loc[0, "is_partial_month"])

    metadata = json.loads(
        (output / "run_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["input_filename"] == source.name
    assert metadata["input_sha256"] == hashlib.sha256(
        original_bytes
    ).hexdigest()
    assert metadata["python_version"]
    assert metadata["run_timestamp_utc"]
    assert {"pandas", "openpyxl", "matplotlib", "pytest"}.issubset(
        metadata["dependency_versions"]
    )
    assert set(metadata["output_paths"]) == EXPECTED_FILES

    first_contents = {
        filename: (output / filename).read_bytes()
        for filename in CSV_FILES | PNG_FILES
    }

    second = run_cli("--input", source, "--output", output)
    assert second.returncode == 0, second.stdout + second.stderr

    for filename, original in first_contents.items():
        assert (output / filename).read_bytes() == original

    assert unrelated.read_text(encoding="utf-8") == "Do not remove me."
    assert source.read_bytes() == original_bytes


def test_cancellation_only_cli_has_blank_rates_and_valid_charts(tmp_path):
    source = tmp_path / "cancellations.xlsx"
    output = tmp_path / "result"
    write_workbook(source, quantity=-2, invoice="C100")

    result = run_cli("--input", source, "--output", output)
    assert result.returncode == 0, result.stdout + result.stderr

    overall = pd.read_csv(
        output / "overall_summary.csv", keep_default_na=False
    )
    assert overall.loc[0, "positive_sales_gbp"] == 0
    assert overall.loc[0, "net_value_gbp"] == -20
    assert overall.loc[0, "cancellation_value_rate_pct"] == ""
    assert overall.loc[0, "top_10_customer_concentration_pct"] == ""

    for filename in PNG_FILES:
        assert (output / filename).stat().st_size > 1000


def test_default_output_directory(tmp_path):
    source = tmp_path / "input.xlsx"
    write_workbook(source)

    result = run_cli("--input", source, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "outputs" / "overall_summary.csv").is_file()


@pytest.mark.parametrize(
    "scenario",
    ["missing", "unreadable", "missing_columns", "no_eligible"],
)
def test_input_failures_are_clear_and_do_not_publish_results(tmp_path, scenario):
    source = tmp_path / "input.xlsx"
    output = tmp_path / "result"

    if scenario == "unreadable":
        source.write_text("This is not an Excel workbook.", encoding="utf-8")
    elif scenario == "missing_columns":
        frame = write_workbook(source).drop(columns=["Country"])
        frame.to_excel(source, index=False, engine="openpyxl")
    elif scenario == "no_eligible":
        frame = write_workbook(source)
        frame["UnitPrice"] = 0
        frame.to_excel(source, index=False, engine="openpyxl")

    result = run_cli("--input", source, "--output", output)

    assert result.returncode != 0
    assert "Error:" in result.stderr
    assert "Created 9 CSVs" not in result.stdout
    assert not (output / "run_metadata.json").exists()

    if scenario == "missing":
        assert "Input workbook not found" in result.stderr
    elif scenario == "missing_columns":
        assert "Missing required columns: Country" in result.stderr
    elif scenario == "no_eligible":
        assert "No eligible merchandise" in result.stderr


def test_output_path_that_is_a_file_fails_without_overwriting_it(tmp_path):
    source = tmp_path / "input.xlsx"
    write_workbook(source)

    output = tmp_path / "blocked output"
    output.write_text("Keep this file.", encoding="utf-8")

    result = run_cli("--input", source, "--output", output)

    assert result.returncode != 0
    assert "Error:" in result.stderr
    assert output.read_text(encoding="utf-8") == "Keep this file."


def test_unwritable_output_directory(tmp_path):
    source = tmp_path / "input.xlsx"
    write_workbook(source)
    output = tmp_path / "read only output"
    output.mkdir()
    output.chmod(0o555)

    try:
        if os.access(output, os.W_OK):
            pytest.skip(
                "This account can bypass directory write permissions."
            )

        result = run_cli("--input", source, "--output", output)
        assert result.returncode != 0
        assert "Error:" in result.stderr
        assert not (output / "run_metadata.json").exists()
    finally:
        output.chmod(0o755)