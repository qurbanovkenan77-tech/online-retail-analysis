"""Merchandise metrics, grouped summaries, and reconciliation."""

import math

import pandas as pd

from retail_analysis.data import clean_data, require_close


VALUE_COLUMNS = [
    "positive_sales_gbp",
    "cancellation_value_gbp",
    "other_negative_value_gbp",
    "net_value_gbp",
]

METRIC_COLUMNS = [
    *VALUE_COLUMNS,
    "cancellation_value_rate_pct",
]

NET_VALUE_DEFINITION = (
    "Net recorded merchandise value is before separately recorded "
    "discounts and charges. It is not profit or complete accounting revenue."
)

PARTIAL_MONTH_NOTE = (
    "December 2011 is designated partial for the UCI Online Retail source. "
    "False means not designated partial under this source's coverage, "
    "not verified complete. Review this rule for a different dataset."
)

CUSTOMER_COLUMNS = [
    "CustomerID",
    "positive_sales_gbp",
    "share_of_identified_sales_pct",
    "display_order",
    "is_top_10",
]


def percentage(numerator, denominator):
    """An unavailable rate stays missing; never cap rates at 100%."""
    if denominator == 0:
        return float("nan")
    return 100.0 * numerator / denominator


def metrics(eligible):
    """Calculate S, C, A, and N from the same eligible population."""
    category = eligible["transaction_category"]
    values = eligible["signed_value_gbp"]

    sales = math.fsum(values.loc[category.eq("positive_sale")])
    cancellations = -math.fsum(values.loc[category.eq("cancellation")])
    other_negatives = -math.fsum(values.loc[category.eq("other_negative")])
    net = sales - cancellations - other_negatives

    require_close(
        math.fsum(values),
        net,
        "eligible signed value versus S - C - A",
    )

    return {
        "positive_sales_gbp": sales,
        "cancellation_value_gbp": cancellations,
        "other_negative_value_gbp": other_negatives,
        "net_value_gbp": net,
        "cancellation_value_rate_pct": percentage(cancellations, sales),
    }


def grouped_metrics(eligible, key):
    """Keep every eligible group, including cancellation-only groups."""
    records = [
        {key: group_name, **metrics(group)}
        for group_name, group in eligible.groupby(
            key, sort=True, dropna=False
        )
    ]

    return pd.DataFrame(records, columns=[key, *METRIC_COLUMNS])


def display_description(group):
    """Most frequent nonblank label; alphabetical tie-break."""
    descriptions = (
        group["Description"].astype("string").fillna("").str.strip()
    )
    counts = descriptions.loc[descriptions.ne("")].value_counts()

    if counts.empty:
        return str(group["StockCode"].iloc[0])

    tied_labels = counts.loc[counts.eq(counts.max())].index.tolist()
    return sorted(tied_labels)[0]


def product_summary(eligible):
    result = grouped_metrics(eligible, "StockCode")
    overall_sales = metrics(eligible)["positive_sales_gbp"]

    descriptions = {
        code: display_description(group)
        for code, group in eligible.groupby("StockCode", sort=True)
    }
    result.insert(
        1, "Description", result["StockCode"].map(descriptions)
    )

    result["sales_share_pct"] = result["positive_sales_gbp"].map(
        lambda value: percentage(value, overall_sales)
    )
    result["positive_sales_rank"] = (
        result["positive_sales_gbp"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    result["net_value_rank"] = (
        result["net_value_gbp"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    return result.sort_values(
        ["positive_sales_gbp", "StockCode"],
        ascending=[False, True],
    ).reset_index(drop=True)


def top_products(products, limit=10):
    """Select chart rows using unrounded sales and stable code ordering."""
    return (
        products.loc[products["positive_sales_gbp"].gt(0)]
        .sort_values(
            ["positive_sales_gbp", "StockCode"],
            ascending=[False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )


def country_summary(eligible):
    result = grouped_metrics(eligible, "Country")
    overall_sales = metrics(eligible)["positive_sales_gbp"]

    result["sales_share_pct"] = result["positive_sales_gbp"].map(
        lambda value: percentage(value, overall_sales)
    )

    return result.sort_values(
        ["positive_sales_gbp", "Country"],
        ascending=[False, True],
    ).reset_index(drop=True)


def monthly_summary(eligible):
    """Observed timestamps and source-specific partial-month designation."""
    working = eligible.copy()
    working["Month"] = (
        working["InvoiceDate"].dt.to_period("M").astype(str)
    )

    result = grouped_metrics(working, "Month")
    coverage = (
        working.groupby("Month", sort=True)["InvoiceDate"]
        .agg(coverage_start="min", coverage_end="max")
        .reset_index()
    )

    result = result.merge(coverage, on="Month", how="left")
    result["is_partial_month"] = result["Month"].eq("2011-12")

    return result.sort_values("Month").reset_index(drop=True)


def customer_summary(eligible):
    """Rank identified customers using positive sales only."""
    positive = eligible.loc[
        eligible["transaction_category"].eq("positive_sale")
    ]
    identified = positive.loc[positive["CustomerID"].notna()]

    records = [
        {
            "CustomerID": customer_id,
            "positive_sales_gbp": math.fsum(group["signed_value_gbp"]),
        }
        for customer_id, group in identified.groupby(
            "CustomerID", sort=True
        )
    ]

    result = pd.DataFrame(
        records, columns=["CustomerID", "positive_sales_gbp"]
    )
    result = result.sort_values(
        ["positive_sales_gbp", "CustomerID"],
        ascending=[False, True],
    ).reset_index(drop=True)

    identified_sales = math.fsum(result["positive_sales_gbp"])
    result["share_of_identified_sales_pct"] = (
        result["positive_sales_gbp"].map(
            lambda value: percentage(value, identified_sales)
        )
    )
    result["display_order"] = range(1, len(result) + 1)
    result["is_top_10"] = result["display_order"].le(10)

    return result.loc[:, CUSTOMER_COLUMNS]


def customer_statistics(eligible, customers):
    positive = eligible.loc[
        eligible["transaction_category"].eq("positive_sale")
    ]

    identified_sales = math.fsum(customers["positive_sales_gbp"])
    unidentified_sales = math.fsum(
        positive.loc[
            positive["CustomerID"].isna(), "signed_value_gbp"
        ]
    )
    overall_sales = math.fsum(positive["signed_value_gbp"])

    require_close(
        identified_sales + unidentified_sales,
        overall_sales,
        "identified plus unidentified positive sales",
    )

    top_10_sales = math.fsum(
        customers.loc[customers["is_top_10"], "positive_sales_gbp"]
    )

    return {
        "identified_positive_sales_gbp": identified_sales,
        "unidentified_positive_sales_gbp": unidentified_sales,
        "identified_sales_coverage_pct": percentage(
            identified_sales, overall_sales
        ),
        "top_10_customer_sales_gbp": (
            top_10_sales if identified_sales > 0 else float("nan")
        ),
        "top_10_customer_concentration_pct": percentage(
            top_10_sales, identified_sales
        ),
        "identified_positive_customer_count": len(customers),
    }


def overall_summary(eligible, customers):
    return pd.DataFrame([{
        **metrics(eligible),
        "eligible_row_count": len(eligible),
        "coverage_start": eligible["InvoiceDate"].min(),
        "coverage_end": eligible["InvoiceDate"].max(),
        **customer_statistics(eligible, customers),
    }])


def duplicate_comparison(raw, deduplicated_eligible):
    """Compare the same merchandise rules with and without deduplication."""
    before_eligible = clean_data(
        raw, remove_duplicates=False
    ).eligible

    before = metrics(before_eligible)
    after = metrics(deduplicated_eligible)

    records = []
    for metric in [
        "positive_sales_gbp",
        "cancellation_value_gbp",
        "net_value_gbp",
    ]:
        change = after[metric] - before[metric]
        records.append({
            "metric": metric,
            "before_gbp": before[metric],
            "after_gbp": after[metric],
            "change_gbp": change,
            "percentage_change": percentage(change, before[metric]),
        })

    return pd.DataFrame(records)


def large_value_lines(eligible):
    """Flag large values for review without removing them."""
    result = eligible.copy()
    result["absolute_line_value_gbp"] = result["signed_value_gbp"].abs()

    result = result.sort_values(
        ["absolute_line_value_gbp", "source_row"],
        ascending=[False, True],
    ).head(10)

    return result[[
        "source_row",
        "InvoiceNo",
        "StockCode",
        "Description",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
        "transaction_category",
        "signed_value_gbp",
        "absolute_line_value_gbp",
    ]].reset_index(drop=True)


def reconcile_grouped_tables(overall, tables):
    """Check S, C, A, and N separately before export rounding."""
    for table_name, table in tables.items():
        for column in VALUE_COLUMNS:
            require_close(
                math.fsum(table[column]),
                overall[column],
                f"{table_name}: {column}",
            )


def build_analysis(raw, cleaned):
    """Build all nine CSV tables; file writing belongs to the CLI."""
    eligible = cleaned.eligible

    if eligible.empty:
        raise ValueError(
            "No eligible merchandise remains after cleaning."
        )

    products = product_summary(eligible)
    countries = country_summary(eligible)
    months = monthly_summary(eligible)
    customers = customer_summary(eligible)
    overall = overall_summary(eligible, customers)

    reconcile_grouped_tables(
        overall.iloc[0],
        {
            "products": products,
            "countries": countries,
            "months": months,
        },
    )

    return {
        "overall_summary.csv": overall,
        "product_summary.csv": products,
        "country_summary.csv": countries,
        "monthly_summary.csv": months,
        "customer_summary.csv": customers,
        "duplicate_comparison.csv": duplicate_comparison(raw, eligible),
        "excluded_entries.csv": cleaned.excluded_entries,
        "cleaning_summary.csv": cleaned.cleaning_summary,
        "large_value_lines.csv": large_value_lines(eligible),
    }