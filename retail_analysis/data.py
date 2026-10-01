"""Load, profile, and clean online retail data with reconciliation."""

import hashlib
import math
from dataclasses import dataclass
from numbers import Real
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

# Exact matches only, after stock-code normalization.
EXCLUSIONS = {
    "POST": ("delivery", "POSTAGE"),
    "DOT": ("delivery", "DOTCOM POSTAGE"),
    "C2": ("delivery", "CARRIAGE"),
    "23444": ("delivery", "Next Day Carriage"),
    "BANK CHARGES": ("fee", "Bank Charges"),
    "AMAZONFEE": ("fee", "AMAZON FEE"),
    "CRUK": ("fee", "CRUK Commission"),
    "D": ("discount", "Discount adjustment"),
    "B": ("accounting_adjustment", "Adjust bad debt"),
    "gift_0001_10": ("voucher", "£10 gift voucher"),
    "gift_0001_20": ("voucher", "£20 gift voucher"),
    "gift_0001_30": ("voucher", "£30 gift voucher"),
    "gift_0001_40": ("voucher", "£40 gift voucher"),
    "gift_0001_50": ("voucher", "£50 gift voucher"),
    "22016": ("voucher", "£100 gift voucher"),
    "M": ("manual", "Manual; underlying product/activity unclear"),
    "m": ("manual", "Manual; underlying product/activity unclear"),
    "S": ("samples", "Samples; code does not identify a specific product"),
}

AUDIT_FIELDS = [
    "signed_value_positive_price_gbp",
    "signed_value_nonpositive_price_gbp",
    "uncomputable_value_count",
]

EXCLUDED_COLUMNS = [
    "StockCode",
    "category",
    "reason",
    "basis",
    "row_count",
    "positive_price_row_count",
    "zero_price_row_count",
    "negative_price_row_count",
    "invalid_numeric_row_count",
    *AUDIT_FIELDS,
]

# Applied to unrounded GBP totals, not exported rounded values.
MONEY_ABS_TOLERANCE = 1e-6
MONEY_REL_TOLERANCE = 1e-12


@dataclass
class CleaningResult:
    eligible: pd.DataFrame
    excluded_entries: pd.DataFrame
    cleaning_summary: pd.DataFrame
    raw_profile: dict


def file_sha256(path):
    """Calculate a file fingerprint using small byte chunks."""
    digest = hashlib.sha256()

    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_columns(frame):
    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in frame.columns
    ]
    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )


def load_workbook(path):
    """Read the first worksheet once without changing the source file."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {path}")

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
    return pd.to_numeric(series, errors="coerce")


def finite_mask(series):
    return series.map(
        lambda value: (
            False if pd.isna(value) else math.isfinite(value)
        )
    ).astype(bool)


def cancellation_mask(series):
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.startswith("C", na=False)
    )


def profile_raw(frame):
    """Informational checks; overlapping checks are not removal totals."""
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
        "zero_price_rows": int((finite_price & price.eq(0)).sum()),
        "negative_price_rows": int((finite_price & price.lt(0)).sum()),
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


def identifier_text(value):
    """Keep identifiers as text; remove .0 only from integral numbers."""
    if pd.isna(value):
        return ""
    if isinstance(value, Real) and math.isfinite(value):
        if value == int(value):
            return str(int(value))
    return str(value).strip()


def require_close(actual, expected, label):
    """Raise a useful error if unrounded financial totals disagree."""
    if not math.isclose(
        actual,
        expected,
        rel_tol=MONEY_REL_TOLERANCE,
        abs_tol=MONEY_ABS_TOLERANCE,
    ):
        raise ValueError(
            f"Reconciliation failed for {label}: "
            f"{actual!r} versus {expected!r}"
        )


def prepare_working_rows(raw):
    """Add helpers while leaving all eight original columns intact."""
    frame = raw.loc[:, REQUIRED_COLUMNS].copy().reset_index(drop=True)
    frame["source_row"] = range(2, len(frame) + 2)

    frame["_stock_code"] = frame["StockCode"].map(identifier_text)
    frame["_invoice"] = frame["InvoiceNo"].map(identifier_text)
    frame["_quantity"] = numeric_values(frame["Quantity"]).astype(float)
    frame["_price"] = numeric_values(frame["UnitPrice"]).astype(float)
    frame["_date"] = pd.to_datetime(
        frame["InvoiceDate"], errors="coerce", format="mixed"
    )
    frame["_is_cancellation"] = cancellation_mask(frame["InvoiceNo"])

    frame["_computable"] = (
        finite_mask(frame["_quantity"]) & finite_mask(frame["_price"])
    )

    # Avoid multiplying invalid values such as infinity by zero.
    frame["_signed_value"] = (
        frame["_quantity"].where(frame["_computable"])
        * frame["_price"].where(frame["_computable"])
    )

    overflow = (
        frame["_computable"] & ~finite_mask(frame["_signed_value"])
    )
    if overflow.any():
        raise ValueError(
            "A quantity × price calculation exceeds numeric capacity."
        )

    return frame


def audit_values(frame):
    """Nonpositive-price values are diagnostic only, never sales."""
    computable = frame["_computable"]
    positive_price = computable & frame["_price"].gt(0)
    nonpositive_price = computable & frame["_price"].le(0)

    return {
        "signed_value_positive_price_gbp": math.fsum(
            frame.loc[positive_price, "_signed_value"]
        ),
        "signed_value_nonpositive_price_gbp": math.fsum(
            frame.loc[nonpositive_price, "_signed_value"]
        ),
        "uncomputable_value_count": int((~computable).sum()),
    }


def remove_stage(frame, mask, step, records):
    """Partition rows and verify counts and values before continuing."""
    mask = mask.fillna(False).astype(bool)
    removed = frame.loc[mask].copy()
    remaining = frame.loc[~mask].copy()

    if len(frame) != len(removed) + len(remaining):
        raise ValueError(f"Row reconciliation failed at {step}")

    partitions = {
        "input": audit_values(frame),
        "removed": audit_values(removed),
        "remaining": audit_values(remaining),
    }

    for field in AUDIT_FIELDS:
        before = partitions["input"][field]
        after = (
            partitions["removed"][field]
            + partitions["remaining"][field]
        )
        if field == "uncomputable_value_count":
            if before != after:
                raise ValueError(
                    f"Uncomputable-count reconciliation failed at {step}"
                )
        else:
            require_close(before, after, f"{step}: {field}")

    record = {
        "record_type": "removal_step",
        "step": step,
        "input_rows": len(frame),
        "removed_rows": len(removed),
        "remaining_rows": len(remaining),
    }
    for partition, values in partitions.items():
        for field, value in values.items():
            record[f"{partition}_{field}"] = value

    records.append(record)
    return remaining, removed


def summarize_exclusions(excluded, basis):
    records = []

    for code, group in excluded.groupby("_stock_code", sort=True):
        computable = group["_computable"]
        price = group["_price"]
        category, reason = EXCLUSIONS[code]

        record = {
            "StockCode": code,
            "category": category,
            "reason": reason,
            "basis": basis,
            "row_count": len(group),
            "positive_price_row_count": int(
                (computable & price.gt(0)).sum()
            ),
            "zero_price_row_count": int(
                (computable & price.eq(0)).sum()
            ),
            "negative_price_row_count": int(
                (computable & price.lt(0)).sum()
            ),
            "invalid_numeric_row_count": int((~computable).sum()),
            **audit_values(group),
        }

        status_total = sum(
            record[column]
            for column in [
                "positive_price_row_count",
                "zero_price_row_count",
                "negative_price_row_count",
                "invalid_numeric_row_count",
            ]
        )
        if status_total != len(group):
            raise ValueError(f"Excluded price counts disagree for {code}")

        records.append(record)

    result = pd.DataFrame(records, columns=EXCLUDED_COLUMNS)

    if int(result["row_count"].sum()) != len(excluded):
        raise ValueError("Excluded row counts do not reconcile")

    expected = audit_values(excluded)
    for field in AUDIT_FIELDS:
        total = math.fsum(result[field])
        if field == "uncomputable_value_count":
            if total != expected[field]:
                raise ValueError("Excluded uncomputable counts disagree")
        else:
            require_close(total, expected[field], f"exclusions: {field}")

    return result


def eligible_table(frame):
    """Return normalized eligible rows with explicit transaction types."""
    result = frame.loc[:, REQUIRED_COLUMNS].copy()
    result["source_row"] = frame["source_row"]
    result["InvoiceNo"] = frame["_invoice"]
    result["StockCode"] = frame["_stock_code"]
    result["Quantity"] = frame["_quantity"]
    result["UnitPrice"] = frame["_price"]
    result["InvoiceDate"] = frame["_date"]
    result["Description"] = (
        frame["Description"].astype("string").fillna("").str.strip()
    )
    result["CustomerID"] = (
        frame["CustomerID"].map(identifier_text).replace("", pd.NA)
    )
    result["Country"] = (
        frame["Country"].astype("string").fillna("").str.strip()
        .replace("", "Unknown")
    )
    result["signed_value_gbp"] = frame["_signed_value"]
    result["transaction_category"] = "other_negative"

    result.loc[
        frame["_quantity"].gt(0), "transaction_category"
    ] = "positive_sale"
    result.loc[
        frame["_is_cancellation"] & frame["_quantity"].lt(0),
        "transaction_category",
    ] = "cancellation"

    return result.reset_index(drop=True)


def information_records(profile):
    """Raw quality counts are informational and can overlap."""
    records = []

    for name, value in profile.items():
        if isinstance(value, int):
            records.append({
                "record_type": "informational_raw",
                "step": name,
                "observed_count": value,
            })

    for column, count in profile["missing_by_column"].items():
        records.append({
            "record_type": "informational_raw",
            "step": f"missing_{column}",
            "observed_count": count,
        })

    return records


def clean_data(raw, remove_duplicates=True):
    """Apply the reviewed ordered rules and return auditable tables.

    Set remove_duplicates=False only for the before-deduplication
    sensitivity analysis. Every other eligibility rule stays the same.
    """
    validate_columns(raw)
    profile = profile_raw(raw)
    frame = prepare_working_rows(raw)
    records = []

    duplicates = frame.duplicated(
        subset=REQUIRED_COLUMNS, keep="first"
    )
    if not remove_duplicates:
        duplicates = pd.Series(False, index=frame.index)

    frame, _ = remove_stage(
        frame, duplicates, "exact_duplicates", records
    )

    frame, excluded = remove_stage(
        frame,
        frame["_stock_code"].isin(EXCLUSIONS),
        "excluded_codes",
        records,
    )

    basis = "post_deduplication" if remove_duplicates else "raw"
    exclusion_summary = summarize_exclusions(excluded, basis)

    invalid = (
        frame["_invoice"].eq("")
        | frame["_stock_code"].eq("")
        | frame["_date"].isna()
        | ~frame["_computable"]
        | frame["_quantity"].where(frame["_computable"]).mod(1).ne(0)
    )
    frame, _ = remove_stage(
        frame, invalid, "invalid_required_fields", records
    )
    frame, _ = remove_stage(
        frame, frame["_price"].lt(0), "negative_prices", records
    )
    frame, _ = remove_stage(
        frame, frame["_price"].eq(0), "zero_prices", records
    )
    frame, _ = remove_stage(
        frame, frame["_quantity"].eq(0), "zero_quantities", records
    )
    frame, _ = remove_stage(
        frame,
        frame["_is_cancellation"] & frame["_quantity"].gt(0),
        "inconsistent_c_positive_quantity",
        records,
    )

    eligible = eligible_table(frame)

    removed_count = sum(record["removed_rows"] for record in records)
    if len(raw) != removed_count + len(eligible):
        raise ValueError("Overall row reconciliation failed")

    allowed_categories = {
        "positive_sale", "cancellation", "other_negative"
    }
    if not eligible["transaction_category"].isin(allowed_categories).all():
        raise ValueError("Unclassified eligible rows")

    records.append({
        "record_type": "eligible_total",
        "step": "eligible_merchandise",
        "remaining_rows": len(eligible),
        **{
            f"remaining_{field}": value
            for field, value in audit_values(frame).items()
        },
    })
    records.extend(information_records(profile))

    return CleaningResult(
        eligible=eligible,
        excluded_entries=exclusion_summary,
        cleaning_summary=pd.DataFrame(records),
        raw_profile=profile,
    )