"""Hand-calculated analysis examples and approved monthly behavior."""

import pandas as pd
import pytest

from retail_analysis.analysis import (
    build_analysis,
    metrics,
    monthly_summary,
)
from retail_analysis.data import REQUIRED_COLUMNS, clean_data


def example_raw():
    return pd.DataFrame(
        [
            ["100", "A1", "Product A", 5,
             "2011-11-15 10:00:00", 10, "123", "UK"],
            ["C101", "A1", "Product A", -2,
             "2011-12-02 11:00:00", 10, "123", "UK"],
            ["102", "A1", "Product A", -1,
             "2011-12-09 12:50:00", 10, None, "UK"],
        ],
        columns=REQUIRED_COLUMNS,
    )


def test_hand_calculated_metrics():
    cleaned = clean_data(example_raw())
    result = metrics(cleaned.eligible)

    assert result["positive_sales_gbp"] == 50
    assert result["cancellation_value_gbp"] == 20
    assert result["other_negative_value_gbp"] == 10
    assert result["net_value_gbp"] == 20
    assert result["cancellation_value_rate_pct"] == 40


def test_partial_month_and_observed_timestamps_are_separate():
    cleaned = clean_data(example_raw())
    months = monthly_summary(cleaned.eligible).set_index("Month")

    # November has only a mid-month observation. That alone does not
    # designate it partial or establish complete calendar coverage.
    assert not bool(months.loc["2011-11", "is_partial_month"])
    assert bool(months.loc["2011-12", "is_partial_month"])

    assert months.loc["2011-11", "coverage_start"] == pd.Timestamp(
        "2011-11-15 10:00:00"
    )
    assert months.loc["2011-11", "coverage_end"] == pd.Timestamp(
        "2011-11-15 10:00:00"
    )
    assert months.loc["2011-12", "coverage_start"] == pd.Timestamp(
        "2011-12-02 11:00:00"
    )
    assert months.loc["2011-12", "coverage_end"] == pd.Timestamp(
        "2011-12-09 12:50:00"
    )
    assert not any("growth" in column for column in months.columns)


def test_partial_rule_is_specific_to_december_2011():
    raw = example_raw().iloc[[0]].copy()
    raw["InvoiceDate"] = "2010-12-09 12:50:00"
    months = monthly_summary(clean_data(raw).eligible)

    assert months.iloc[0]["Month"] == "2010-12"
    assert not bool(months.iloc[0]["is_partial_month"])


def test_builds_nine_tables_and_duplicate_comparison():
    raw = example_raw()
    raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)

    tables = build_analysis(raw, clean_data(raw))

    assert set(tables) == {
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

    comparison = tables["duplicate_comparison.csv"].set_index("metric")
    sales = comparison.loc["positive_sales_gbp"]
    net = comparison.loc["net_value_gbp"]

    assert sales["before_gbp"] == 100
    assert sales["after_gbp"] == 50
    assert sales["change_gbp"] == -50
    assert sales["percentage_change"] == -50
    assert net["before_gbp"] == 70
    assert net["after_gbp"] == 20

    overall = tables["overall_summary.csv"].iloc[0]
    assert overall["net_value_gbp"] == 20
    assert overall["identified_sales_coverage_pct"] == 100
    assert overall["top_10_customer_concentration_pct"] == 100


def test_empty_eligible_population_has_clear_error():
    raw = example_raw()
    raw["UnitPrice"] = 0

    with pytest.raises(ValueError, match="No eligible merchandise"):
        build_analysis(raw, clean_data(raw))