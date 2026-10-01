"""Small, independently specified tests for source loading and profiling."""

import hashlib

import pandas as pd
import pytest

from retail_analysis.data import (
    REQUIRED_COLUMNS,
    file_sha256,
    load_workbook,
    profile_raw,
)


def example_frame():
    """One sale, one cancellation, and one other negative adjustment."""
    return pd.DataFrame(
        [
            ["100", "A1", "Product A", 5,
             "2011-01-05 10:00:00", 10, None, "United Kingdom"],
            [" c101 ", "A1", "Product A", -2,
             "2011-01-06 10:00:00", 10, "12345", "United Kingdom"],
            ["102", "A1", "Product A", -1,
             "2011-01-07 10:00:00", 10, "12345", "United Kingdom"],
        ],
        columns=REQUIRED_COLUMNS,
    )


def test_profile_signs_missing_values_and_dates():
    result = profile_raw(example_frame())

    assert result["rows"] == 3
    assert result["columns"] == 8
    assert result["missing_by_column"]["CustomerID"] == 1
    assert result["c_prefixed_invoice_rows"] == 1
    assert result["negative_quantity_rows"] == 2
    assert result["negative_quantity_without_c_prefix"] == 1
    assert result["c_prefixed_nonnegative_quantity_rows"] == 0
    assert result["minimum_quantity"] == -2
    assert result["maximum_quantity"] == 5
    assert result["first_timestamp"] == "2011-01-05 10:00:00"
    assert result["last_timestamp"] == "2011-01-07 10:00:00"


def test_duplicates_use_all_eight_raw_fields_without_mutation():
    original = example_frame()

    # An exact duplicate, including its missing customer ID.
    duplicate = original.iloc[[0]].copy()

    # A description difference means this is not an exact duplicate.
    changed = original.iloc[[0]].copy()
    changed["Description"] = "Different description"

    frame = pd.concat(
        [original, duplicate, changed], ignore_index=True
    )
    frame["source_row"] = range(2, len(frame) + 2)
    before = frame.copy(deep=True)

    result = profile_raw(frame)

    assert result["exact_duplicates_beyond_first"] == 1
    pd.testing.assert_frame_equal(frame, before)


def test_profile_reports_invalid_values_and_inconsistent_signs():
    frame = pd.DataFrame(
        [
            ["C1", "A", "Item", 2, "2011-01-01", 1, None, "UK"],
            ["2", "A", "Item", 0, "bad date", 0, None, "UK"],
            ["3", "A", "Item", 1.5, "2011-01-01", -1, None, "UK"],
            ["4", "A", "Item", "bad", "2011-01-01", "bad", None, "UK"],
            ["5", "A", "Item", float("inf"), "2011-01-01",
             float("inf"), None, "UK"],
        ],
        columns=REQUIRED_COLUMNS,
    )

    result = profile_raw(frame)

    assert result["c_prefixed_nonnegative_quantity_rows"] == 1
    assert result["zero_quantity_rows"] == 1
    assert result["zero_price_rows"] == 1
    assert result["negative_price_rows"] == 1
    assert result["nonintegral_quantity_rows"] == 1
    assert result["invalid_or_nonfinite_quantity_rows"] == 2
    assert result["invalid_or_nonfinite_price_rows"] == 2
    assert result["invalid_or_missing_date_rows"] == 1


def test_load_workbook_preserves_identifiers_and_source_bytes(tmp_path):
    frame = example_frame()
    frame.loc[0, "InvoiceNo"] = "00100"
    frame.loc[0, "StockCode"] = "NA"
    frame.loc[0, "CustomerID"] = "00123"

    path = tmp_path / "input with spaces.xlsx"
    frame.to_excel(path, index=False, engine="openpyxl")
    original_bytes = path.read_bytes()

    loaded = load_workbook(path)

    assert loaded.columns.tolist() == REQUIRED_COLUMNS
    assert len(loaded) == 3
    assert loaded.loc[0, "InvoiceNo"] == "00100"
    assert loaded.loc[0, "StockCode"] == "NA"
    assert loaded.loc[0, "CustomerID"] == "00123"
    assert file_sha256(path) == hashlib.sha256(original_bytes).hexdigest()
    assert path.read_bytes() == original_bytes


def test_missing_workbook_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Input workbook not found"):
        load_workbook(tmp_path / "missing.xlsx")


def test_missing_required_column_has_clear_error(tmp_path):
    frame = example_frame().drop(columns=["Country"])
    path = tmp_path / "missing column.xlsx"
    frame.to_excel(path, index=False, engine="openpyxl")

    with pytest.raises(ValueError, match="Missing required columns: Country"):
        load_workbook(path)