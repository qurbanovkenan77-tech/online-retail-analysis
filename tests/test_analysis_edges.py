"""Analysis edge cases with independently specified expected results."""

import math

import pandas as pd
import pytest

from retail_analysis.analysis import (
    build_analysis,
    customer_statistics,
    customer_summary,
    metrics,
    product_summary,
    top_products,
)
from retail_analysis.data import REQUIRED_COLUMNS, clean_data


def make_row(invoice, code="A", quantity=1, price=10, **changes):
    row = {
        "InvoiceNo": invoice,
        "StockCode": code,
        "Description": "Product",
        "Quantity": quantity,
        "InvoiceDate": "2011-01-05",
        "UnitPrice": price,
        "CustomerID": "001",
        "Country": "United Kingdom",
    }
    row.update(changes)
    return row


def raw_frame(rows):
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def eligible_rows(rows):
    return clean_data(raw_frame(rows)).eligible


def test_product_sales_and_net_ranks_differ_and_ties_use_minimum_rank():
    eligible = eligible_rows([
        make_row("1", code="A", price=100),
        make_row("C2", code="A", quantity=-1, price=90),
        make_row("3", code="TEST_B", price=80),
        make_row("4", code="C", price=80),
        make_row("C5", code="TEST_D", quantity=-1, price=5),
    ])

    products = product_summary(eligible)
    indexed = products.set_index("StockCode")

    assert indexed["positive_sales_rank"].to_dict() == {
        "A": 1, "TEST_B": 2, "C": 2, "TEST_D": 4,
    }
    assert indexed["net_value_rank"].to_dict() == {
        "A": 3, "TEST_B": 1, "C": 1, "TEST_D": 4,
    }
    assert top_products(products)["StockCode"].tolist() == ["A", "C", "TEST_B"]
    assert indexed.loc["TEST_D", "net_value_gbp"] == -5
    assert math.isnan(indexed.loc["TEST_D", "cancellation_value_rate_pct"])


def test_ranks_use_unrounded_totals():
    eligible = eligible_rows([
        make_row("1", code="A", price=1.001),
        make_row("2", code="TEST_B", price=1.002),
    ])

    products = product_summary(eligible).set_index("StockCode")

    assert products.loc["TEST_B", "positive_sales_rank"] == 1
    assert products.loc["A", "positive_sales_rank"] == 2


def test_description_frequency_ties_and_missing_label_fallback():
    eligible = eligible_rows([
        make_row("1", code="A", Description="Zebra"),
        make_row("2", code="A", Description="Apple"),
        make_row("3", code="TEST_B", Description=None),
        make_row("4", code="C", Description="Zebra"),
        make_row("5", code="C", Description="Zebra"),
        make_row("6", code="C", Description="Apple"),
    ])

    products = product_summary(eligible).set_index("StockCode")

    assert products.loc["A", "Description"] == "Apple"
    assert products.loc["TEST_B", "Description"] == "TEST_B"
    assert products.loc["C", "Description"] == "Zebra"


def test_customer_denominator_excludes_missing_ids_and_cancellations():
    eligible = eligible_rows([
        make_row("1", price=60, CustomerID="001"),
        make_row("2", price=40, CustomerID="002"),
        make_row("3", price=100, CustomerID=None),
        make_row("C4", quantity=-1, price=50, CustomerID="001"),
    ])

    customers = customer_summary(eligible)
    statistics = customer_statistics(eligible, customers)

    assert customers["CustomerID"].tolist() == ["001", "002"]
    assert customers["positive_sales_gbp"].tolist() == [60, 40]
    assert customers["share_of_identified_sales_pct"].tolist() == [60, 40]
    assert customers["is_top_10"].all()

    assert statistics["identified_positive_sales_gbp"] == 100
    assert statistics["unidentified_positive_sales_gbp"] == 100
    assert statistics["identified_sales_coverage_pct"] == 50
    assert statistics["top_10_customer_concentration_pct"] == 100


def test_customer_tie_at_tenth_selects_exactly_ten_deterministically():
    # Reverse the input order to ensure it does not decide the ranking.
    eligible = eligible_rows([
        make_row(str(index), CustomerID=f"{index:03d}")
        for index in range(11, 0, -1)
    ])

    customers = customer_summary(eligible)
    statistics = customer_statistics(eligible, customers)
    selected = customers.loc[customers["is_top_10"], "CustomerID"]

    assert selected.tolist() == [
        f"{index:03d}" for index in range(1, 11)
    ]
    assert customers["is_top_10"].sum() == 10
    assert statistics["top_10_customer_concentration_pct"] == pytest.approx(
        100 * 100 / 110
    )


def test_no_identified_customers_has_no_fictitious_customer():
    eligible = eligible_rows([
        make_row("1", CustomerID=None),
        make_row("2", CustomerID=" "),
    ])

    customers = customer_summary(eligible)
    statistics = customer_statistics(eligible, customers)

    assert customers.empty
    assert statistics["identified_positive_sales_gbp"] == 0
    assert statistics["unidentified_positive_sales_gbp"] == 20
    assert statistics["identified_sales_coverage_pct"] == 0
    assert math.isnan(statistics["top_10_customer_sales_gbp"])
    assert math.isnan(statistics["top_10_customer_concentration_pct"])


def test_cancellation_only_data_builds_all_tables_with_missing_rates():
    raw = raw_frame([
        make_row("C1", quantity=-2, price=10),
    ])
    tables = build_analysis(raw, clean_data(raw))
    overall = tables["overall_summary.csv"].iloc[0]

    assert overall["positive_sales_gbp"] == 0
    assert overall["cancellation_value_gbp"] == 20
    assert overall["net_value_gbp"] == -20
    assert math.isnan(overall["cancellation_value_rate_pct"])
    assert math.isnan(overall["identified_sales_coverage_pct"])
    assert math.isnan(overall["top_10_customer_concentration_pct"])
    assert tables["customer_summary.csv"].empty
    assert top_products(tables["product_summary.csv"]).empty

    comparison = tables["duplicate_comparison.csv"].set_index("metric")
    assert math.isnan(
        comparison.loc["positive_sales_gbp", "percentage_change"]
    )


def test_cancellation_value_rate_can_exceed_one_hundred_percent():
    eligible = eligible_rows([
        make_row("1", price=10),
        make_row("C2", quantity=-2, price=10),
    ])

    result = metrics(eligible)

    assert result["cancellation_value_rate_pct"] == 200
    assert result["net_value_gbp"] == -10


def test_group_totals_reconcile_and_unknown_country_is_preserved():
    raw = raw_frame([
        make_row("1", code="A", price=50, Country=None),
        make_row(
            "C2", code="TEST_B", quantity=-1, price=20,
            InvoiceDate="2011-02-05", Country="France",
        ),
        make_row(
            "3", code="C", quantity=-1, price=10,
            InvoiceDate="2011-03-05", Country=" ",
        ),
    ])

    tables = build_analysis(raw, clean_data(raw))
    expected = {
        "positive_sales_gbp": 50,
        "cancellation_value_gbp": 20,
        "other_negative_value_gbp": 10,
        "net_value_gbp": 20,
    }

    for filename in [
        "product_summary.csv",
        "country_summary.csv",
        "monthly_summary.csv",
    ]:
        for column, value in expected.items():
            assert tables[filename][column].sum() == pytest.approx(value)

    countries = tables["country_summary.csv"].set_index("Country")
    assert countries.loc["Unknown", "positive_sales_gbp"] == 50
    assert countries.loc["Unknown", "other_negative_value_gbp"] == 10


def test_duplicate_comparison_with_negative_net_baseline():
    cancellation = make_row("C1", quantity=-1, price=20)
    raw = raw_frame([
        make_row("1", price=10),
        cancellation,
        cancellation.copy(),
    ])

    tables = build_analysis(raw, clean_data(raw))
    comparison = tables["duplicate_comparison.csv"].set_index("metric")
    net = comparison.loc["net_value_gbp"]

    assert net["before_gbp"] == -30
    assert net["after_gbp"] == -10
    assert net["change_gbp"] == 20
    assert net["percentage_change"] == pytest.approx(-100 * 20 / 30)


def test_large_value_review_selects_ten_without_removing_transactions():
    raw = raw_frame([
        make_row(str(index), price=index)
        for index in range(1, 13)
    ])

    tables = build_analysis(raw, clean_data(raw))
    large = tables["large_value_lines.csv"]

    assert len(large) == 10
    assert large["absolute_line_value_gbp"].tolist() == list(
        range(12, 2, -1)
    )
    assert tables["overall_summary.csv"].iloc[0]["eligible_row_count"] == 12
    assert tables["overall_summary.csv"].iloc[0]["positive_sales_gbp"] == 78