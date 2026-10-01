"""Four static charts for the eligible merchandise population."""

from pathlib import Path
from textwrap import fill

import matplotlib

# Works in Docker and terminals without a graphical display.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from retail_analysis.analysis import NET_VALUE_DEFINITION, top_products


CHART_FILENAMES = [
    "top_products.png",
    "country_sales.png",
    "monthly_sales.png",
    "sales_to_net.png",
]

BLUE = "#2563A6"
GREEN = "#258065"
RED = "#BC4749"
GRAY = "#68717D"


def gbp_ticks(value, position):
    return f"{value:,.0f}"


def period_label(tables):
    overall = tables["overall_summary.csv"].iloc[0]
    start = overall["coverage_start"].strftime("%Y-%m-%d")
    end = overall["coverage_end"].strftime("%Y-%m-%d")
    return f"{start} to {end} | Eligible deduplicated merchandise"


def save_chart(fig, output, filename, caption):
    fig.text(
        0.02, 0.02, caption,
        ha="left", va="bottom", fontsize=9, color="#444444",
    )
    fig.tight_layout(rect=(0, 0.15, 1, 0.92))
    path = output / filename
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def horizontal_sales(ax, labels, values, title):
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("Positive sales (GBP)")
    ax.xaxis.set_major_formatter(FuncFormatter(gbp_ticks))

    if len(values) == 0:
        ax.text(
            0.5, 0.5, "No positive merchandise sales",
            transform=ax.transAxes, ha="center", va="center",
        )
        ax.set_yticks([])
        return

    positions = list(range(len(values)))
    ax.barh(positions, values, color=BLUE)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(left=0)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)


def plot_products(tables, output):
    products = top_products(tables["product_summary.csv"])
    labels = [
        fill(f"{row.StockCode} — {row.Description}", width=42)
        for row in products.itertuples(index=False)
    ]

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.suptitle(
        "Top products by positive merchandise sales",
        fontsize=15, fontweight="bold",
    )
    horizontal_sales(
        ax,
        labels,
        products["positive_sales_gbp"].tolist(),
        period_label(tables),
    )

    return save_chart(
        fig, output, "top_products.png",
        "Up to 10 positive-sales products; ties ordered by StockCode.\n"
        "Ranked by positive sales, before cancellations and other negatives.",
    )


def plot_countries(tables, output):
    countries = tables["country_summary.csv"]
    positive = countries.loc[countries["positive_sales_gbp"].gt(0)]
    overall_top = positive.head(10)
    non_uk_top = positive.loc[
        positive["Country"].ne("United Kingdom")
    ].head(10)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(
        "Country positive merchandise sales\n" + period_label(tables),
        fontsize=14, fontweight="bold",
    )

    for ax, data, title in [
        (axes[0], overall_top, "Top 10 — all countries"),
        (axes[1], non_uk_top, "Top 10 — excluding United Kingdom"),
    ]:
        horizontal_sales(
            ax,
            data["Country"].tolist(),
            data["positive_sales_gbp"].tolist(),
            title,
        )
        ax.tick_params(axis="x", labelrotation=30)

    return save_chart(
        fig, output, "country_sales.png",
        "Panels use separate GBP scales to show non-UK differences clearly.\n"
        "Country is the recorded customer country, not necessarily shipping destination.",
    )


def plot_months(tables, output):
    months = tables["monthly_summary.csv"]
    positions = list(range(len(months)))
    partial = months["is_partial_month"].tolist()

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.suptitle(
        "Monthly recorded merchandise values\n" + period_label(tables),
        fontsize=14, fontweight="bold",
    )

    for column, label, color in [
        ("positive_sales_gbp", "Positive sales (S)", BLUE),
        ("net_value_gbp", "Net recorded value (N)", GREEN),
    ]:
        values = months[column].tolist()

        # Individual segments let us distinguish links to partial months.
        for index in range(1, len(months)):
            style = "--" if partial[index] or partial[index - 1] else "-"
            ax.plot(
                positions[index - 1:index + 1],
                values[index - 1:index + 1],
                color=color,
                linestyle=style,
            )

        ax.plot(
            positions, values, linestyle="none",
            marker="o", color=color, label=label,
        )

    labels = [
        month + ("\nPARTIAL" if is_partial else "")
        for month, is_partial in zip(months["Month"], partial)
    ]
    ax.set_xticks(positions, labels, rotation=45, ha="right")

    for index, is_partial in enumerate(partial):
        if is_partial:
            ax.axvspan(index - 0.35, index + 0.35, color="#F3C969", alpha=0.3)

    ax.set_ylabel("Recorded value (GBP)")
    ax.yaxis.set_major_formatter(FuncFormatter(gbp_ticks))
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.grid(axis="y", alpha=0.2)
    ax.legend()

    return save_chart(
        fig, output, "monthly_sales.png",
        "December 2011 is partial under this UCI source's documented coverage; "
        "do not interpret its drop as full-month growth.\n"
        "Other months are not designated partial, not verified complete. "
        "Net value is before separately recorded discounts and charges.",
    )


def plot_sales_to_net(tables, output):
    overall = tables["overall_summary.csv"].iloc[0]
    values = [
        overall["positive_sales_gbp"],
        -overall["cancellation_value_gbp"],
        -overall["other_negative_value_gbp"],
        overall["net_value_gbp"],
    ]
    values = [0.0 if value == 0 else value for value in values]
    labels = [
        "Positive sales\nS",
        "Cancellation deduction\n−C",
        "Other-negative deduction\n−A",
        "Net recorded value\nN",
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.suptitle(
        "Positive sales and deductions: N = S − C − A\n"
        + period_label(tables),
        fontsize=14, fontweight="bold",
    )

    bars = ax.bar(labels, values, color=[BLUE, RED, GRAY, GREEN])
    ax.bar_label(
        bars,
        labels=[f"£{value:,.2f}" for value in values],
        padding=5,
        fontsize=10,
    )
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.set_ylabel("Recorded value / deduction (GBP)")
    ax.yaxis.set_major_formatter(FuncFormatter(gbp_ticks))
    ax.margins(y=0.2)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)

    return save_chart(
        fig, output, "sales_to_net.png",
        fill(NET_VALUE_DEFINITION, width=125)
        + "\nDeductions are shown below zero; cancellations are not automatically physical returns.",
    )


def create_charts(tables, output):
    """Write only the four named chart files; keep other files untouched."""
    if tables["overall_summary.csv"].iloc[0]["eligible_row_count"] == 0:
        raise ValueError("Cannot chart an empty eligible population.")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    with plt.rc_context({"font.size": 10}):
        return [
            plot_products(tables, output),
            plot_countries(tables, output),
            plot_months(tables, output),
            plot_sales_to_net(tables, output),
        ]