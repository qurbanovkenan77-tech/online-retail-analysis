"""Read and inspect source data without modifying the workbook."""

import hashlib
import math
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def file_sha256(path):
    """Calculate a file fingerprint without loading all its bytes at once."""
    digest = hashlib.sha256()

    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_columns(frame):
    """Require the eight source columns; allow additional columns."""
    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )


def load_workbook(path):
    """Read the first worksheet once and preserve the original field values."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {path}")

    # Object dtype avoids treating identifier columns as measurements.
    # Preserve literal text such as "NA"; only empty cells become missing.
    frame = pd.read_excel(
        path,
        sheet_name=0,
        engine="openpyxl",
        dtype=object,
        keep_default_na=False,
        na_values=[""],
    )

    validate_columns(frame)
    return frame


def numeric_values(series):
    """Create a numeric working copy; unparseable values become missing."""
    return pd.to_numeric(series, errors="coerce")


def finite_mask(series):
    """Identify numeric values that are neither missing nor infinite."""
    return series.map(
        lambda value: (
            False if pd.isna(value) else math.isfinite(value)
        )
    )


def cancellation_mask(series):
    """Detect C-prefixed invoices, ignoring surrounding spaces and case."""
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.startswith("C", na=False)
    )


def profile_raw(frame):
    """Return informational checks; these are not cleaning removal counts."""
    validate_columns(frame)

    quantity = numeric_values(frame["Quantity"])
    price = numeric_values(frame["UnitPrice"])
    finite_quantity = finite_mask(quantity)
    finite_price = finite_mask(price)
    cancellations = cancellation_mask(frame["InvoiceNo"])

    dates = pd.to_datetime(
        frame["InvoiceDate"], errors="coerce", format="mixed"
    )
    valid_dates = dates.dropna()
    valid_quantities = quantity.loc[finite_quantity]

    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": frame.columns.tolist(),
        "missing_by_column": {
            column: int(frame[column].isna().sum())
            for column in REQUIRED_COLUMNS
        },
        "exact_duplicates_beyond_first": int(
            frame.duplicated(
                subset=REQUIRED_COLUMNS, keep="first"
            ).sum()
        ),
        "c_prefixed_invoice_rows": int(cancellations.sum()),
        "negative_quantity_rows": int(
            (finite_quantity & quantity.lt(0)).sum()
        ),
        "negative_quantity_without_c_prefix": int(
            (finite_quantity & quantity.lt(0) & ~cancellations).sum()
        ),
        "c_prefixed_nonnegative_quantity_rows": int(
            (cancellations & finite_quantity & quantity.ge(0)).sum()
        ),
        "zero_price_rows": int(
            (finite_price & price.eq(0)).sum()
        ),
        "negative_price_rows": int(
            (finite_price & price.lt(0)).sum()
        ),
        "zero_quantity_rows": int(
            (finite_quantity & quantity.eq(0)).sum()
        ),
        "invalid_or_nonfinite_quantity_rows": int(
            (~finite_quantity).sum()
        ),
        "invalid_or_nonfinite_price_rows": int(
            (~finite_price).sum()
        ),
        "nonintegral_quantity_rows": int(
            (
                finite_quantity
                & quantity.where(finite_quantity).mod(1).ne(0)
            ).sum()
        ),
        "invalid_or_missing_date_rows": int(dates.isna().sum()),
        "minimum_quantity": (
            float(valid_quantities.min())
            if not valid_quantities.empty else None
        ),
        "maximum_quantity": (
            float(valid_quantities.max())
            if not valid_quantities.empty else None
        ),
        "first_timestamp": (
            valid_dates.min().isoformat(sep=" ")
            if not valid_dates.empty else None
        ),
        "last_timestamp": (
            valid_dates.max().isoformat(sep=" ")
            if not valid_dates.empty else None
        ),
    }