# Online Retail Merchandise Analysis — Reviewed Implementation Plan

Status: Finalized Architect plan following the student's review on September 30, 2026. Implementation, automated testing, Docker execution, the student's smoke test, and independent verification are still pending. This document does not claim those activities have occurred.

## 1. Purpose and scope

Main question: **Which products and countries contribute most to recorded merchandise sales, and how much recorded sales value is offset by cancellations?**

Also examine monthly trends and top-10 customer concentration. Deliver a small Python command-line application producing CSV summaries and four PNG charts. Keep functions short, names descriptive, and analytical rules explicit so the student can explain the code.

No dashboard, database, forecasting, machine learning, return-to-original-invoice matching, retention model, or additional service is required. Docker Compose is unnecessary because there is only one batch process.

Environment: VS Code on a Mac, Python 3.13, GitHub, and Docker. Builder must verify compatible dependency versions and actual local/container execution.

## 2. Source and completed inspection

Source: https://archive.ics.uci.edu/dataset/352/online+retail

Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. UCI lists the dataset under CC BY 4.0; retain attribution.

The Architect directly inspected the attached `Online Retail(1).xlsx`. The following are raw-file observations, before exclusions or deduplication, not final business results:

| Check | Verified observation |
| --- | ---: |
| Rows | 541,909 |
| Columns | 8 |
| Missing CustomerID | 135,080 |
| Missing Description | 1,454 |
| Exact duplicate rows beyond first occurrence | 5,268 |
| C-prefixed invoice rows | 9,288 |
| Negative-quantity rows | 10,624 |
| Negative quantities without C prefix | 1,336 |
| C-prefixed rows with nonnegative quantity | 0 |
| Zero-price rows | 2,515 |
| Negative-price rows | 2 |
| Zero-quantity rows | 0 |
| Minimum / maximum quantity | −80,995 / 80,995 |
| First timestamp | 2010-12-01 08:26:00 |
| Last timestamp | 2011-12-09 12:50:00 |

Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country. The other six columns had no missing values in this inspection. UCI identifies C-prefixed invoices as cancellations and UnitPrice as sterling. Its missing-value metadata conflicts with the workbook; report the workbook observations.

Builder must reproduce the profile on the input used for implementation and record the input filename and SHA-256 hash. Do not hardcode these observations as program outputs or assume every future input has these counts.

## 3. Reviewed student decisions

- Analyze merchandise only, with explicit excluded codes reported separately.
- Exclude manual entries, samples, and gift vouchers from headline merchandise figures. Samples are not described as free samples: their recorded prices are positive.
- Remove exact duplicates in the main analysis, retaining the first occurrence. This is an assumption because identical lines may be legitimate; there is no unique line identifier.
- Provide a before/after duplicate comparison for positive sales, cancellation value, and net value.
- Keep missing customer IDs in overall analysis. Customer concentration covers identified customers only.
- Rank the product chart by positive sales and include both positive-sales rank and net-value rank in the product CSV.
- Keep December 2011 in totals, label it partial, and exclude it from full-month growth comparisons.

Actual AI recommendation accepted: merchandise-only analysis with separately reported charges and ambiguous entries. Actual recommendation modified: the student added net-value rank to the product CSV while retaining positive-sales order in the chart. Record these accurately in the README; do not invent additional student decisions.

## 4. Approved exact exclusion map

Convert numeric stock codes to their ordinary string representation (23444, not 23444.0), trim surrounding whitespace, and match the explicit codes below. Preserve stock-code case otherwise; explicitly map both M and m. Do not exclude by alphabetic characters, prefix patterns, or description keywords.

| Exact code | Category | Reason / recorded description |
| --- | --- | --- |
| POST | delivery | POSTAGE |
| DOT | delivery | DOTCOM POSTAGE |
| C2 | delivery | CARRIAGE |
| 23444 | delivery | Next Day Carriage |
| BANK CHARGES | fee | Bank Charges |
| AMAZONFEE | fee | AMAZON FEE |
| CRUK | fee | CRUK Commission |
| D | discount | Discount adjustment |
| B | accounting_adjustment | Adjust bad debt |
| gift_0001_10 | voucher | £10 gift voucher |
| gift_0001_20 | voucher | £20 gift voucher |
| gift_0001_30 | voucher | £30 gift voucher |
| gift_0001_40 | voucher | £40 gift voucher |
| gift_0001_50 | voucher | £50 gift voucher |
| 22016 | voucher | £100 gift voucher |
| M | manual | Manual; underlying product/activity unclear |
| m | manual | Manual; underlying product/activity unclear |
| S | samples | Samples; code does not identify a specific product |

Examples retained subject to normal validity rules: PADS, DCGSSBOY, DCGSSGIRL, DCGS0076, DCGS0004, and DCGS0070. Alphabetic suffixes on numeric product codes are also valid. A product called a carriage clock must not be excluded because its description includes “carriage.”

All rows with a listed code leave the headline population, regardless of price or quantity. Report their price issues separately within the excluded-entry output. Do not silently expand this list: document and review any newly discovered ambiguous code.

## 5. Analytical definitions

All headline metrics use the same eligible, deduplicated merchandise population and GBP units. A line's signed recorded value is Quantity × UnitPrice. Keep full calculation precision internally; round exported money to two decimal places and percentages to two decimal places. Test financial comparisons with a small documented tolerance. Do not round unit prices to two decimals before multiplying because small positive prices can exist.

| Metric | Definition |
| --- | --- |
| Positive sales value S | Sum of Quantity × UnitPrice for positive-quantity, non-C invoices |
| Cancellation value C | Sum of abs(Quantity) × UnitPrice for negative-quantity, C-prefixed invoices |
| Other negative value A | Sum of abs(Quantity) × UnitPrice for negative-quantity, non-C invoices |
| Net recorded merchandise value N | S − C − A |
| Cancellation-value rate | 100 × C / S |
| Sales share | 100 × group S / overall S |

Required interpretation: **Net recorded merchandise value is before separately recorded discounts and charges. It is not profit or complete accounting revenue.** Use this wording in the README and in a subtitle/caption for the net-value chart; use a concise column name such as `net_value_gbp` with this definition documented.

The cancellation-value rate is not an order cancellation rate or a physical return rate. Negative quantities may represent cancellations or adjustments, and the file does not establish physical movement or reasons. Cancellations use their recorded invoice dates; they are not matched back to original purchases. A cancellation can concern an earlier month or a purchase outside this observation window. Rates can exceed 100%; do not cap them. A zero denominator produces a blank CSV rate, not zero or infinity.

Product grouping uses StockCode, not Description. Choose the most frequent nonblank description among eligible rows for a code, breaking ties alphabetically; fall back to StockCode if unavailable. Do not merge distinct codes based on similar descriptions or letter case.

Product ranks: descending rank with tied values receiving the same minimum rank (1, 1, 3). Rank using underlying unrounded totals. Keep cancellation-only products in the CSV. Break display-order ties by StockCode and include only positive-sales products in the top-10 chart; use fewer than 10 if necessary.

Customer concentration: sum positive merchandise sales by known CustomerID. Rank customers by positive sales, breaking ties by CustomerID; take exactly 10 or all if fewer exist. Divide their combined sales by positive sales of all identified customers. Report identified-sales coverage = identified-customer positive sales / all positive sales. Missing IDs must never be combined into a fictitious customer. With no identified positive sales, concentration and coverage-dependent customer metrics are unavailable; do not crash.

## 6. Data preparation and reconciliation

Preserve the original workbook. Read it once per run, validate the eight required columns, and keep raw columns until duplicate detection is finished. Exact duplicates are based on all eight original columns, before trimming, filling, or adding helper columns. A source Excel row number may be added for audit purposes but must not enter duplicate comparison.

Use an ordered, mutually exclusive row disposition:

1. Raw rows: profile missing values, duplicates, prices, signs, and dates.
2. Remove exact duplicates beyond the first.
3. Separate all approved excluded codes from the remaining rows.
4. From the remaining merchandise candidates, reject invalid required fields: missing/blank InvoiceNo or StockCode, invalid date, nonnumeric/nonfinite quantity or price, or nonintegral quantity.
5. Reject negative prices.
6. Separate zero prices from paid-merchandise analysis.
7. Separate zero quantities.
8. Quarantine C-prefixed invoices with positive quantities as inconsistent; do not reinterpret them as sales.
9. Remaining rows form the eligible merchandise population: positive sales, C cancellations, or other negatives.

Normalize cancellation detection by trimming InvoiceNo and testing its uppercase representation. Keep legitimate large quantities, flag the 10 largest absolute eligible line values for review, and avoid arbitrary outlier deletion. Missing CustomerID does not reject a merchandise row. Missing Description uses the label rule above. Missing/blank Country in future data becomes `Unknown`, preserving totals; do not silently drop it in grouping. Retain CustomerID as an identifier rather than a measurement.

### Excluded entries and the cleaning summary

`excluded_entries.csv` is **after exact deduplication and before merchandise validity filtering**. It includes every row removed at step 3, grouped by the exact matched code. Include `basis = post_deduplication` in the output.

For each excluded code report category, reason, total row count, positive-price row count, zero-price row count, negative-price row count, and invalid-numeric row count. Price-status counts partition total rows: classify invalid/nonfinite quantity or price first; among the remainder classify price as positive, zero, or negative.

Include `signed_value_positive_price_gbp`, summing Quantity × UnitPrice only for rows with finite quantity and finite positive price. Also include `signed_value_nonpositive_price_gbp` for computable rows with zero/negative price, clearly labeled diagnostic only. Do not include nonpositive-price values in merchandise sales or characterize negative-price amounts as reliable business revenue. Noncomputable values remain unavailable and their counts are reported.

`cleaning_summary.csv` records each ordered step's input, removed, and remaining row counts. Use the same two signed-value audit columns plus an uncomputable-value count for each step. The excluded-code step's counts and audit values must equal the sum of `excluded_entries.csv`. Missing-value and overlapping raw quality checks must be labeled informational, not added into the mutually exclusive removal totals.

Reconciliation requirements:

- Raw count = duplicate removals + excluded-code rows + merchandise rejections + eligible rows.
- Deduplicated count = excluded-code rows + merchandise rejections + eligible rows.
- Eligible count = positive-sale rows + C cancellation rows + other-negative rows.
- Eligible signed value = S − C − A.
- Product, country, and monthly S/C/A/N totals separately match overall totals.
- Identified positive sales + unidentified positive sales = overall S.
- Stage audit values and uncomputable counts reconcile between each input, removed, and remaining partition. Reconcile underlying values before presentation rounding; exported group sums may differ by pennies due to rounding, which must be explained rather than concealed.

### Duplicate sensitivity

Run the same eligibility and exclusion rules on raw rows and on exact-deduplicated rows. Export one row per metric (S, C, N) with before, after, change = after − before, and percentage change = 100 × change / before. A zero before value gives a blank percentage. A negative net baseline can make percentage direction unintuitive; interpret the absolute GBP change first. Do not compare an all-entry raw total with a merchandise-only cleaned total.

## 7. Time coverage and limitations

Use all available eligible records for overall totals. Aggregate by calendar month in chronological order. December 2011 is partial through December 9 at 12:50; include an `is_partial_month` flag and coverage dates in the monthly output. The chart must visibly mark that final point as partial. Do not extrapolate it, compare it directly with a full December, or report November-to-partial-December growth. Keep growth rates out of the minimum implementation to reduce scope.

Known limitations: no cost data for profit/margins; invoice value is not proof of cash collection; customer country is not necessarily shipping destination; missing IDs limit customer findings; wholesalers may create legitimate large orders; duplicate and code-exclusion decisions affect totals; cancellation timing does not identify the original sale; this single retailer and short history do not establish general retail trends or robust annual seasonality.

## 8. Important files

| Path | Purpose |
| --- | --- |
| README.md | Question, findings after execution, setup, usage, testing, Docker, limitations, AI workflow and evidence links |
| docs/plan.md | This reviewed plan, saved before implementation |
| retail_analysis/__init__.py | Small package marker |
| retail_analysis/__main__.py | Argument parsing and pipeline orchestration |
| retail_analysis/data.py | Load, profile, exclusion map, cleaning and audit summaries |
| retail_analysis/analysis.py | Metrics, grouped tables, ranks, concentration and duplicate comparison |
| retail_analysis/charts.py | Four readable PNG charts using a noninteractive backend |
| tests/test_data.py | Data handling and exclusions |
| tests/test_analysis.py | Hand-calculated metric and ranking cases |
| tests/test_cli.py | Small temporary-workbook end-to-end run and failure cases |
| requirements.txt | Exact tested versions of pandas, openpyxl, matplotlib and pytest; one simple class-project environment |
| Dockerfile | Python 3.13 batch container |
| .dockerignore | Exclude raw data, outputs, virtual environment, Git metadata and caches from build context |
| .gitignore | Exclude raw workbook, virtual environment and caches; keep selected final outputs and evidence |
| data/README.md | Source, attribution, filename/path instructions; raw workbook is obtained separately |
| docs/smoke-test.md | Student's actual manual checks and outcomes |
| docs/test-report.md | Fresh Tester's findings, independent checks and final status |
| docs/evidence/ | Actual command logs/screenshots with dates, environment and commit references |
| `docs/transcripts/<NetID>_architect.txt` | Complete Architect conversation, including follow-ups, in the exact section 15 format |
| `docs/transcripts/<NetID>_builder.txt` | Complete fresh Builder conversation, including follow-ups, in the exact section 15 format |
| `docs/transcripts/<NetID>_tester.txt` | Complete fresh Tester conversation, including follow-ups, in the exact section 15 format |
| outputs/ | Generated CSVs and charts; optional alternate output directories via CLI |

No elaborate configuration framework or extra packaging system is needed. Store the small exclusion map once in data.py and test it against this plan. Do not create fake transcripts or evidence placeholders that look completed.

## 9. Output contract

Produce these CSVs in the requested output directory:

| Filename | Required contents |
| --- | --- |
| overall_summary.csv | S, C, A, N, cancellation-value rate, eligible row count, date coverage, identified sales, coverage %, top-10 concentration % |
| product_summary.csv | StockCode, display description, S/C/A/N, cancellation-value rate, sales share, positive-sales rank, net-value rank |
| country_summary.csv | Country, S/C/A/N, cancellation-value rate and sales share |
| monthly_summary.csv | Month, S/C/A/N, cancellation-value rate, partial-month flag and coverage dates |
| customer_summary.csv | Identified CustomerID, positive sales, share of identified positive sales, deterministic display order, top-10 flag |
| duplicate_comparison.csv | Before/after S, C, N and absolute/percentage changes |
| excluded_entries.csv | Post-deduplication code/category counts and explicitly scoped diagnostic values from section 6 |
| cleaning_summary.csv | Ordered row/value reconciliation plus clearly separated informational raw checks |
| large_value_lines.csv | Up to 10 largest absolute eligible line values, source row, invoice, code, quantity, price and transaction category |

Also write `run_metadata.json` with input hash, input filename, run timestamp, Python/dependency versions, and output paths. Monetary CSV fields are numeric GBP amounts without currency symbols. Blank means unavailable, not zero. Stable sorting makes repeated runs comparable; only run metadata timestamps should vary.

Four PNGs: `top_products.png` (top 10 by S, readable product labels); `country_sales.png` (all-country top 10 plus a clearly labeled non-UK panel); `monthly_sales.png` (S and N, partial final month marked); `sales_to_net.png` (simple labeled S/C/A/N comparison, with deductions explained). Put GBP units, period and population in titles/captions. No extra customer chart is required. Support fewer groups gracefully and avoid misleading charts when no eligible data exists.

## 10. Implementation sequence — fresh Builder conversation

1. Give Builder this plan, the dataset, and assignment requirements. Builder must follow this plan and explain steps in plain language.
2. Create the project folders, save this plan first, and commit it before implementation. Preserve the original workbook; place a copy at `data/Online Retail.xlsx` for the example commands.
3. Create a Python 3.13 virtual environment; install and record compatible exact dependency versions. Verify the interpreter and dataset schema/profile.
4. Implement loading, normalization, exact deduplication, code exclusions, row classification, and cleaning reconciliation. Add the relevant small tests.
5. Implement S/C/A/N, grouped tables, duplicate sensitivity and customer concentration. Check hand-calculated examples before using the full dataset.
6. Implement four charts and the CLI with configurable input/output paths. Create output directories if absent; replace only this tool's named output files, never delete an arbitrary output directory.
7. Run automated tests and the complete dataset locally; inspect outputs and record actual results. Add the input hash and sample findings to documentation only after computing them.
8. Add Dockerfile and .dockerignore; build the image, run containerized tests, and run the dataset with mounted folders. Save actual logs and verify local/container summaries agree.
9. Write README instructions and hand the student the smoke-test checklist. Do not start the Tester stage until the student performs and records the smoke test. If it fails, Builder fixes the issue and the student reruns affected checks.
10. After the smoke test, hand the repository and evidence to a separate fresh Tester conversation. Address actual findings, retest affected behavior, and record the final revision.

## 11. Local and Docker interfaces

These are planned commands, not commands already verified. Builder must implement and verify this interface. Run commands from the repository root. The student may retain the original attachment name by passing its quoted path instead.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m retail_analysis --input "data/Online Retail.xlsx" --output outputs
```

CLI requirements: `--help`, required `--input`, configurable `--output` defaulting to outputs, clear errors and nonzero exit for missing/unreadable input, missing required columns, no eligible merchandise, or unwritable outputs. A cancellation-only eligible dataset is valid: S can be zero and rates unavailable. Small test fixtures need no external download.

Docker design: use a verified Python 3.13 slim image, `/app` working directory, install the tested requirements, copy the small package and tests, and default CMD to `python -m retail_analysis --help`. Use Matplotlib's noninteractive Agg backend. No web server, port, database, background service, or health check is needed for this batch job. Do not embed the raw workbook or outputs in the image.

```bash
docker build -t online-retail-analysis .
docker run --rm online-retail-analysis python -m pytest -q
mkdir -p outputs-docker
docker run --rm \
  --mount "type=bind,source=$(pwd)/data,target=/data,readonly" \
  --mount "type=bind,source=$(pwd)/outputs-docker,target=/outputs" \
  online-retail-analysis \
  python -m retail_analysis --input "/data/Online Retail.xlsx" --output /outputs
```

The second mount writes directly to the Mac folder `outputs-docker`; `--rm` removes the stopped container, not that folder. Docker must have access to the selected Mac folders. Record Docker version and any environment-specific issue honestly. If Docker cannot run on the student's Mac, document the blocker and resolve it; do not mark the Docker requirement complete based only on a Dockerfile or another environment.

## 12. Meaningful automated tests

Use tiny synthetic DataFrames with manually known answers for most tests and a temporary XLSX for the CLI integration test. Do not require the full dataset for unit tests.

| Case | Expected behavior |
| --- | --- |
| Sale: 5 × £10; C cancellation: −2 × £10; non-C negative: −1 × £10 | S=50, C=20, A=10, N=20, cancellation-value rate=40% |
| Duplicate the sale row above | Before: S=100, C=20, N=70; after: S=50, C=20, N=20 |
| Duplicate with missing CustomerID | Detected using all eight raw fields; helper row numbers do not interfere |
| Similar lines differing in one original field | Both retained |
| POST, 23444, 22016, gift vouchers, M/m and S | Excluded with correct category and post-dedup audit basis |
| PADS, DCGSSBOY, alphanumeric product, carriage-clock description | Retained if otherwise valid |
| Positive sale with missing CustomerID | Included in S, excluded from identified-customer denominator |
| Missing Description and multiple descriptions per code | Stable label selection without losing sales |
| Negative/zero/nonfinite price; invalid quantity/date | Correct disposition; no silent NaNs in metrics |
| Lowercase c invoice and positive-quantity C invoice | Correct cancellation detection; inconsistent sign quarantined |
| Negative non-C quantity | Other-negative bucket, never automatically called a return |
| Very large quantity and tiny positive unit price | Retained; no arbitrary cap or premature price rounding |
| S=0, cancellation-only data | Net can be negative; rates blank, not infinity |
| Missing country | Unknown group preserves overall totals |
| Product sales rank differs from net rank; tied values | Both ranks correct, with deterministic chart selection |
| Fewer than 10 identified customers; tie at tenth; none identified | Correct numerator/denominator and deterministic selection; unavailable if denominator zero |
| December 2011 partial coverage | Included in totals and labeled partial |
| Overlapping excluded code and invalid price | Counted in code exclusion once; price issue visible in excluded diagnostics |
| Grouped and cleaning reconciliation | Counts exact and monetary totals within documented precision tolerance |
| CLI paths containing spaces; alternate output path | Writes the expected files to the chosen directory |
| Missing input/columns, empty eligible population | Clear nonzero failure without claiming a successful analysis |

Chart checks: expected PNG files exist and are nonempty in integration tests; visual readability is checked manually, not with brittle pixel-perfect tests.

## 13. Student manual smoke test — before Tester

The student performs these checks on the Mac after Builder has completed the implementation. Record date/time, commit, environment, commands, observed outcome and evidence paths in `docs/smoke-test.md`. Use pending/pass/fail accurately.

- [ ] Follow README setup in a fresh terminal and run automated tests.
- [ ] Run the analysis with the full workbook and an explicit output path.
- [ ] Open the CSVs; confirm readable numeric columns, both product ranks, and nonempty results.
- [ ] Open all four PNGs; inspect labels, GBP units, legibility, and partial December marking.
- [ ] Confirm the net-value explanation says before separately recorded discounts and charges, not profit or complete accounting revenue.
- [ ] Check excluded_entries.csv says post-deduplication and includes samples without calling them free.
- [ ] Compare its total counts and audit values with the cleaning summary's excluded-code step.
- [ ] Inspect the duplicate before/after table and its assumption statement.
- [ ] Build Docker and run the tests inside the image; save actual command output.
- [ ] Run Docker with the read-only input and writable Mac output mounts.
- [ ] After the container exits and is removed, open the CSVs and PNGs in outputs-docker on the Mac.
- [ ] Compare local and Docker metrics; they should agree within the documented rounding tolerance.
- [ ] Try a nonexistent input path and confirm a clear failure message.
- [ ] Record any failures and the results of reruns after fixes. Only then begin the fresh Tester conversation.

## 14. Fresh Tester and independent verification

Tester receives the reviewed plan, repository, source instructions, and completed student smoke-test record. Tester independently reviews assumptions and implementation, runs tests and documented commands where possible, and records environment limits rather than claiming unperformed checks.

Independent checks must include the hand-worked £50/£20/£10 example and a small real-source subtotal. For the latter, select and record an actual product/invoice subset, list the relevant source rows and duplicate/exclusion decisions, and independently calculate S/C/A/N using a calculator, spreadsheet, or separate direct calculation that does not call the application's aggregation functions. Compare it with the corresponding project output. Record the selected identifiers only after inspection; do not invent examples or results.

Review code-map behavior, duplicate comparison population, grouped reconciliation, identified-customer denominator, partial-month labels, negative-quantity wording, Docker persistence, and chart readability. Save findings and actual outcomes in docs/test-report.md. Changes following Tester findings require affected tests and, when relevant, a repeated student smoke check.

## 15. README, transcripts, and submission

README must include the business question; source/attribution; scope; setup and exact usage; output descriptions; definitions and assumptions; actual findings after execution; testing and Docker commands; actual smoke-test results; limitations; AI role separation; the accepted and modified recommendations from section 3; and independent-verification evidence.

The assignment requires exactly these three plain-text transcript files. Replace `<NetID>` with the student's actual NetID; do not invent it:

- `docs/transcripts/<NetID>_architect.txt`
- `docs/transcripts/<NetID>_builder.txt`
- `docs/transcripts/<NetID>_tester.txt`

Each file must start with the following header, in this order:

```text
STUDENT_NAME: Your Name
NETID: Your NetID
OPTION: 3
ROLE: architect, builder, or tester
AGENT_TOOL: ChatGPT
REPOSITORY_B_URL: Actual Repository B URL
===== TRANSCRIPT START =====
```

Replace `Your Name`, `Your NetID`, and `Actual Repository B URL` with the actual values. Set ROLE to exactly one corresponding lowercase value: `architect`, `builder`, or `tester`; do not put the comma-separated list in a submitted file. Retain OPTION: 3 and AGENT_TOOL: ChatGPT exactly. Obtain unknown header values from the student rather than inventing them.

Inside the transcript, label student messages `[STUDENT]` and agent messages `[AGENT]`. Preserve the complete visible conversation, including prompts, decisions, revisions, errors, and visible execution outputs, without shortening, summarizing, or rewriting it. Only private information may be replaced with `[REDACTED]`; do not omit other content. Include all follow-up exchanges in chronological order within the corresponding role transcript, including these Architect corrections, rather than requiring additional submission files. Use actual exports or faithful complete copies. The finalized plan is not a substitute for the Architect transcript.

Each file must finish with:

```text
===== TRANSCRIPT END =====
```

Commit the three completed `.txt` files under `docs/transcripts/` in Repository B. Upload the same three `.txt` files separately to Canvas, preserving the exact filenames and contents. The final submission must also include **both the actual Repository A URL and the actual Repository B URL**. The transcript header contains Repository B's URL; the requirement to submit both URLs is additional. Do not claim transcript creation, commits, or Canvas uploads are complete until they actually occur.

Commit reviewed plan, implementation, tests, documentation, complete transcripts, and selected compact final CSV/PNG outputs. Keep the raw workbook out of Git and Docker context; data/README.md must make obtaining and naming it straightforward. Retain real evidence logs. Do not claim checks passed until supported by execution or the student's recorded observation.

## 16. Acceptance criteria

- [ ] Reviewed docs/plan.md is committed before project implementation.
- [ ] Main analysis follows all 18 exact code exclusions and retains legitimate alphanumeric products.
- [ ] S/C/A/N, rates, both product ranks, monthly summaries, and customer concentration follow this plan.
- [ ] Deduplication is labeled an assumption and its before/after effect is reported on the same merchandise population.
- [ ] Excluded-entry counts/values explicitly use the post-deduplication basis and reconcile with cleaning totals.
- [ ] Missing customer IDs remain in overall sales, with identified-only concentration and coverage clearly stated.
- [ ] Partial December is visible; cancellations are not automatically described as physical returns; net value is not described as profit or complete accounting revenue.
- [ ] All nine CSVs, four readable PNGs, and run metadata are produced through configurable paths.
- [ ] Meaningful typical, edge-case, and CLI tests pass with recorded results.
- [ ] Docker build, container tests, full-data run, and Mac output persistence are demonstrated with actual evidence.
- [ ] Student smoke test is recorded before the separate fresh Tester stage.
- [ ] Fresh Tester independently verifies calculations and records findings and final status.
- [ ] README covers usage, tests, Docker, real findings, limitations, AI decisions, smoke results, and independent verification.
- [ ] Exactly three complete plain-text role transcripts use the required paths: `docs/transcripts/<NetID>_architect.txt`, `docs/transcripts/<NetID>_builder.txt`, and `docs/transcripts/<NetID>_tester.txt`, with the actual NetID substituted.
- [ ] Each transcript starts with the exact section 15 header, populated with the actual student name, NetID, corresponding lowercase role, OPTION: 3, AGENT_TOOL: ChatGPT, actual Repository B URL, and `===== TRANSCRIPT START =====`.
- [ ] Speakers are labeled `[STUDENT]` and `[AGENT]`; the complete visible conversation and all corresponding follow-up exchanges are preserved without shortening or rewriting. Only private information is replaced with `[REDACTED]`.
- [ ] Each transcript finishes with `===== TRANSCRIPT END =====`.
- [ ] The three `.txt` files are committed in Repository B, and the same three files are separately uploaded to Canvas with matching filenames and contents.
- [ ] Both the actual Repository A URL and the actual Repository B URL are included in the final submission.
- [ ] No verification, findings, or student actions are claimed without evidence.

At plan finalization, only the planning discussion, approved decisions, and Architect's read-only source inspection are complete. All implementation and acceptance checkboxes remain pending.
