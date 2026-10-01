"""Verify reviewed cleaning rules using small, known examples."""

import math

import pandas as pd
import pytest

from retail_analysis.data import (
    AUDIT_FIELDS,
    EXCLUSIONS,
    REQUIRED_COLUMNS,
    clean_data,
)


def make_row(**changes):
    row = {
        "InvoiceNo": "100",
        "StockCode": "A1",
        "Description": "Product A",
        "Quantity": 5,
        "InvoiceDate": "2011-01-01",
        "UnitPrice": 10,
        "CustomerID": "123",
        "Country": "United Kingdom",
    }
    row.update(changes)
    return row


def make_frame(rows):
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


APPROVED_CODES = [
    ("POST", "delivery"),
    ("DOT", "delivery"),
    ("C2", "delivery"),
    ("23444", "delivery"),
    ("BANK CHARGES", "fee"),
    ("AMAZONFEE", "fee"),
    ("CRUK", "fee"),
    ("D", "discount"),
    ("B", "accounting_adjustment"),
    ("gift_0001_10", "voucher"),
    ("gift_0001_20", "voucher"),
    ("gift_0001_30", "voucher"),
    ("gift_0001_40", "voucher"),
    ("gift_0001_50", "voucher"),
    ("22016", "voucher"),
    ("M", "manual"),
    ("m", "manual"),
    ("S", "samples"),
]


def test_exclusion_map_has_exactly_the_approved_codes():
    assert set(EXCLUSIONS) == {code for code, _ in APPROVED_CODES}


@pytest.mark.parametrize("code,category", APPROVED_CODES)
def test_each_approved_code_is_excluded(code, category):
    result = clean_data(make_frame([
        make_row(),
        make_row(InvoiceNo="101", StockCode=code),
    ]))

    assert result.eligible["StockCode"].tolist() == ["A1"]
    excluded = result.excluded_entries.iloc[0]
    assert excluded["StockCode"] == code
    assert excluded["category"] == category
    assert excluded["basis"] == "post_deduplication"
    assert excluded["row_count"] == 1


@pytest.mark.parametrize(
    "code",
    [
        "PADS", "DCGSSBOY", "DCGSSGIRL", "DCGS0076",
        "DCGS0004", "DCGS0070", "85123A", "post",
    ],
)
def test_unlisted_codes_and_carriage_description_are_retained(code):
    result = clean_data(make_frame([
        make_row(StockCode=code, Description="Carriage clock"),
    ]))

    assert result.eligible["StockCode"].tolist() == [code]
    assert result.excluded_entries.empty


@pytest.mark.parametrize("code", [23444, 23444.0, " 23444 ", 22016])
def test_numeric_and_whitespace_exclusion_codes(code):
    result = clean_data(make_frame([
        make_row(),
        make_row(InvoiceNo="101", StockCode=code),
    ]))

    assert len(result.eligible) == 1
    assert result.excluded_entries["row_count"].sum() == 1


def test_exclusion_diagnostics_are_post_dedup_and_partition_prices():
    positive = make_row(StockCode="POST", Quantity=2, UnitPrice=3)
    rows = [
        positive,
        positive.copy(),
        make_row(InvoiceNo="101", StockCode="POST", UnitPrice=0),
        make_row(
            InvoiceNo="102", StockCode="POST", Quantity=2, UnitPrice=-4
        ),
        make_row(
            InvoiceNo="103", StockCode="POST", Quantity="bad", UnitPrice=5
        ),
        make_row(InvoiceNo="104", StockCode="POST", UnitPrice=float("inf")),
        make_row(InvoiceNo="105"),
    ]

    result = clean_data(make_frame(rows))
    excluded = result.excluded_entries.iloc[0]

    assert excluded["row_count"] == 5
    assert excluded["positive_price_row_count"] == 1
    assert excluded["zero_price_row_count"] == 1
    assert excluded["negative_price_row_count"] == 1
    assert excluded["invalid_numeric_row_count"] == 2
    assert excluded["uncomputable_value_count"] == 2
    assert excluded["signed_value_positive_price_gbp"] == 6
    assert excluded["signed_value_nonpositive_price_gbp"] == -8

    steps = result.cleaning_summary.set_index("step")
    assert steps.loc["excluded_codes", "removed_rows"] == 5
    assert steps.loc["invalid_required_fields", "removed_rows"] == 0

    for field in AUDIT_FIELDS:
        assert steps.loc[
            "excluded_codes", f"removed_{field}"
        ] == pytest.approx(excluded[field])


def test_ordered_rejections_and_every_stage_reconcile():
    sale = make_row()
    rows = [
        sale,
        sale.copy(),
        make_row(InvoiceNo="101", StockCode="POST", UnitPrice=-2),
        make_row(InvoiceNo=" "),
        make_row(InvoiceNo="102", UnitPrice=-1),
        make_row(InvoiceNo="103", UnitPrice=0, Quantity=0),
        make_row(InvoiceNo="104", Quantity=0),
        make_row(InvoiceNo="C105", Quantity=2),
        make_row(InvoiceNo=" c106 ", Quantity=-2),
        make_row(InvoiceNo="107", Quantity=-1),
    ]

    result = clean_data(make_frame(rows))
    steps = result.cleaning_summary
    steps = steps.loc[steps["record_type"].eq("removal_step")]

    assert steps["removed_rows"].tolist() == [1, 1, 1, 1, 1, 1, 1]
    assert len(result.eligible) == 3
    assert len(rows) == steps["removed_rows"].sum() + len(result.eligible)
    assert result.eligible["transaction_category"].tolist() == [
        "positive_sale", "cancellation", "other_negative",
    ]
    assert result.eligible["signed_value_gbp"].sum() == 20

    for _, step in steps.iterrows():
        assert step["input_rows"] == (
            step["removed_rows"] + step["remaining_rows"]
        )
        for field in AUDIT_FIELDS:
            assert math.isclose(
                step[f"input_{field}"],
                step[f"removed_{field}"] + step[f"remaining_{field}"],
                rel_tol=1e-12,
                abs_tol=1e-6,
            )


@pytest.mark.parametrize(
    "changes",
    [
        {"InvoiceNo": None},
        {"StockCode": " "},
        {"InvoiceDate": "not a date"},
        {"Quantity": "not a number"},
        {"Quantity": float("inf")},
        {"Quantity": 1.5},
        {"UnitPrice": None},
        {"UnitPrice": float("-inf")},
    ],
)
def test_invalid_required_fields_are_rejected(changes):
    result = clean_data(make_frame([make_row(**changes)]))
    steps = result.cleaning_summary.set_index("step")

    assert result.eligible.empty
    assert steps.loc["invalid_required_fields", "removed_rows"] == 1


def test_missing_optional_fields_large_quantity_and_tiny_price():
    result = clean_data(make_frame([
        make_row(
            Quantity=80995,
            UnitPrice=0.001,
            CustomerID=None,
            Description=None,
            Country=" ",
        ),
    ]))

    row = result.eligible.iloc[0]
    assert pd.isna(row["CustomerID"])
    assert row["Description"] == ""
    assert row["Country"] == "Unknown"
    assert row["Quantity"] == 80995
    assert row["UnitPrice"] == 0.001
    assert row["signed_value_gbp"] == pytest.approx(80.995)
    assert row["source_row"] == 2


def test_deduplication_precedes_normalization_and_preserves_source():
    first = make_row(CustomerID=None)
    spaced = make_row(CustomerID=None, StockCode=" A1 ")
    raw = make_frame([first, first.copy(), spaced])
    before = raw.copy(deep=True)

    result = clean_data(raw)

    assert len(result.eligible) == 2
    assert result.eligible["StockCode"].tolist() == ["A1", "A1"]
    assert result.eligible["source_row"].tolist() == [2, 4]
    pd.testing.assert_frame_equal(raw, before)


def test_before_duplicate_analysis_keeps_other_rules_identical():
    sale = make_row()
    raw = make_frame([
        sale,
        sale.copy(),
        make_row(InvoiceNo="C101", Quantity=-2),
        make_row(InvoiceNo="102", Quantity=-1),
        make_row(InvoiceNo="103", StockCode="POST", UnitPrice=1000),
    ])

    before = clean_data(raw, remove_duplicates=False)
    after = clean_data(raw)

    assert len(before.eligible) == 4
    assert len(after.eligible) == 3
    assert before.eligible["signed_value_gbp"].sum() == 70
    assert after.eligible["signed_value_gbp"].sum() == 20
    assert "POST" not in before.eligible["StockCode"].tolist()


def test_cancellation_only_population_is_valid():
    result = clean_data(make_frame([
        make_row(InvoiceNo="c100", Quantity=-2),
    ]))

    assert len(result.eligible) == 1
    assert result.eligible.iloc[0]["transaction_category"] == "cancellation"
    assert result.eligible.iloc[0]["signed_value_gbp"] == -20