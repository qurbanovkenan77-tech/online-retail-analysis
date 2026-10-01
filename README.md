# Online Retail Merchandise Analysis

Kanan Gurbanov · kg396 · Option 3: new online retail analysis project

## Purpose

Which products and countries contribute most to recorded merchandise sales,
and how much recorded sales value is offset by cancellations?

This Python command-line application produces nine CSV summaries, four PNG
charts, and run metadata. It also examines monthly values, duplicate
sensitivity, and top-10 identified-customer concentration.

## Data and scope

Source: Chen, D. (2015). Online Retail. UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33 — CC BY 4.0.

See [data instructions](data/README.md). The raw workbook is excluded from Git
and the Docker image.

The verified input has 541,909 rows and spans December 1, 2010 through
December 9, 2011. Its SHA-256 is:

```text
43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d
```

## Methods

The reviewed rules are in [docs/plan.md](docs/plan.md).

Cleaning proceeds in this order: exact duplicate removal, the 18 approved
code exclusions, invalid required fields, negative prices, zero prices,
zero quantities, and positive-quantity C-prefixed invoices.

Duplicates use all eight original fields before normalization. Removing
identical lines is an assumption: there is no unique line identifier, and
identical transactions may be legitimate. Duplicate sensitivity applies
the same merchandise rules before and after duplicate removal.

Exclusions use exact normalized stock codes, not description keywords or
alphabetic patterns. They cover delivery, fees, discounts, accounting
adjustments, vouchers, manual entries, and samples. Samples are not
described as free.

The excluded-entry report uses the post-deduplication population before
merchandise validity filtering. Nonpositive-price amounts are diagnostic
only. Informational raw quality checks can overlap and must not be added
to removal totals.

For eligible merchandise, signed line value is Quantity × UnitPrice:

| Metric | Definition |
|---|---|
| S: positive sales | Positive quantities on non-C invoices |
| C: cancellation value | Absolute value of negative quantities on C invoices |
| A: other-negative value | Absolute value of negative quantities on non-C invoices |
| N: net recorded value | S − C − A |
| Cancellation-value rate | 100 × C / S |
| Sales share | 100 × group S / overall S |

Net recorded merchandise value is before separately recorded discounts and
charges. It is not profit or complete accounting revenue.

Cancellation detection ignores invoice case and surrounding spaces.
Cancellations use their recorded dates and are not matched to original
purchases. The cancellation-value rate is neither an order cancellation
rate nor a physical return rate. Rates can exceed 100%; a zero denominator
produces a blank rate.

Products are grouped by StockCode. Labels use the most frequent nonblank
description, alphabetical tie-breaking, and StockCode as fallback.
Both product ranks use unrounded totals and minimum tied ranks (1, 1, 3).
The chart selects up to ten positive-sales products, breaking ties by code.

Missing customer IDs remain in overall sales. Customer concentration uses
positive sales of identified customers only, selecting exactly ten or all
if fewer exist. Ties use text CustomerID ordering. Identified-sales coverage
reports the share of overall positive sales with known IDs. Missing country
becomes Unknown. Large eligible lines are flagged, not removed.

December 2011 is designated partial under this UCI source's documented
coverage. False in is_partial_month means "not designated partial under
this source's coverage", not "verified complete". Monthly coverage_start
and coverage_end are first and last observed eligible timestamps, not
proof of complete calendar coverage. Review the December rule for another
dataset. Growth calculations are out of scope.

Calculations retain precision. GBP amounts and percentages export to two
decimals; UnitPrice retains source precision. Blank means unavailable.
Reconciliation uses unrounded values with absolute tolerance £0.000001
and relative tolerance 1e-12. Rounded group sums may differ from rounded
overall values by pennies.

## Findings from the verified run

| Measure | Result |
|---|---:|
| Eligible merchandise lines | 531,127 |
| Positive sales | £10,245,935.99 |
| Cancellation value | £475,886.16 |
| Other-negative value | £0.00 |
| Net recorded merchandise value | £9,770,049.83 |
| Cancellation-value rate | 4.64% |
| UK share of positive sales | 85.14% |
| Identified-sales coverage | 85.26% |
| Top-10 concentration within identified sales | 17.40% |

Cleaning removed 5,268 duplicates, 3,022 excluded-code rows, and 2,492
zero-price merchandise rows.

REGENCY CAKESTAND 3 TIER (22423) led positive sales at £174,156.54.
PAPER CRAFT , LITTLE BIRDIE (23843) ranked second by positive sales but had
£0 net value, illustrating why both ranks matter. These totals do not
establish cancellation reasons.

November 2011 had the highest monthly positive sales in this observation
window. Partial December must not be interpreted as a full-month decline.

Duplicate removal reduced positive sales by £24,213.74, cancellation value
by £2,823.02, and net value by £21,390.72.

## Local setup and usage

Use Python 3.13. Run commands from the repository root.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m retail_analysis --help
python -m retail_analysis --input "data/Online Retail.xlsx" --output outputs
```

Input and output paths are configurable. Output defaults to outputs.
The application replaces only its named reports and preserves unrelated
files. Missing/unreadable input, missing columns, no eligible merchandise,
and output-write failures return nonzero exit codes.

## Outputs

| File | Contents |
|---|---|
| overall_summary.csv | Overall metrics, coverage, customer concentration |
| product_summary.csv | Product metrics, descriptions, both ranks |
| country_summary.csv | Country metrics and sales shares |
| monthly_summary.csv | Monthly metrics, observed timestamps, partial flag |
| customer_summary.csv | Identified positive sales, shares, top-10 flags |
| duplicate_comparison.csv | Before/after S, C, N and changes |
| excluded_entries.csv | Excluded-code counts and diagnostic values |
| cleaning_summary.csv | Ordered row/value audit and informational checks |
| large_value_lines.csv | Ten largest absolute eligible values |
| top_products.png | Top products by positive sales |
| country_sales.png | All-country and non-UK panels |
| monthly_sales.png | S and N with partial December marked |
| sales_to_net.png | S/C/A/N comparison and net-value explanation |
| run_metadata.json | Input hash, environment, policies, output paths |

## Docker

Start Docker Desktop, then run from the repository root:

```bash
docker build -t online-retail-analysis .
docker run --rm online-retail-analysis python -m pytest -q -rs
mkdir -p outputs-docker
docker run --rm \
  --mount "type=bind,source=$(pwd)/data,target=/data,readonly" \
  --mount "type=bind,source=$(pwd)/outputs-docker,target=/outputs" \
  online-retail-analysis \
  python -m retail_analysis --input "/data/Online Retail.xlsx" --output /outputs
```

The input mount is read-only. Outputs persist in the Mac outputs-docker
folder after --rm removes the container. Docker Desktop must have access
to these folders. Running the image without a command displays help.

The tested base tag was python:3.13-slim; this tag can change. Actual Python
and dependency versions are recorded in run metadata and evidence.

## Verification status

Builder-stage commands were executed by Kanan on the Mac and through its
Docker Desktop installation; these are not claims of execution inside
ChatGPT's environment.

- Local: Python 3.13.14, macOS ARM64; 77 tests passed.
- Docker: Python 3.13.15, Linux ARM64; 76 passed, 1 skipped.
- The Docker permission test skipped because its account can bypass
  directory permissions; it passed locally.
- Full local and Docker runs succeeded. All nine exported CSVs matched
  exactly, with identical input hashes.
- Kanan reviewed the four local charts and reported no overlapping labels.
- Docker files persisted on the Mac after the container exited.
- Final README-based manual smoke test: passed on September 30, 2026,
  against commit ffb1398e3bc7a01fff910bd9caa6ad071280a607.
  Setup, 77 local tests, and local analysis succeeded; missing input
  correctly returned exit 1. Docker smoke commands exited 0, all nine
  CSVs matched exactly, and the student opened the persisted Docker CSV
  and all four charts with readable labels and no overlap or cut-off text.
  See [the smoke-test record](docs/smoke-test.md). Local setup reused .venv.
- Independent Tester technical verification: passed on October 1, 2026,
  against commit 6481c3882c0f28b74cf578ee0e421ece1bb4118a.
  Kanan executed fresh Mac tests (77 passed, exit 0), a full-data run,
  a cached Docker build (exit 0), and fresh container tests (76 passed,
  1 expected permission-test skip, exit 0).
- Tester directly executed a separate workbook calculation in Linux
  Python 3.12.14 / pandas 2.2.3 without importing application functions.
  Cleaning audits, exclusions, grouped metrics, both product ranks,
  customer concentration, duplicate sensitivity, and largest lines matched
  the fresh Mac CSVs at their export precision. Input hash and metadata
  checks passed; all four supplied local charts were visually readable.
- A hand-calculated S=50, C=20, A=10, N=20 example passed. Real-source
  product 23843 had two eligible rows: 80,995 x GBP 2.08 in sales and
  the same cancellation value, giving S=C=GBP 168,469.60 and N=0.
  Tester checked this subtotal separately using Decimal.
- Kanan's fresh Docker run rejected writes to the read-only input mount,
  exited 0, and left all outputs accessible after container removal.
  All nine Docker CSVs matched the reviewed local CSVs byte-for-byte;
  input hashes matched. Docker PNG signatures/sizes and persistence passed.
- No analytical defect was found. README status wording and review-archive
  exclusion were corrected. A clean dependency installation was not repeated.
  Final documentation handoff and complete transcript submission remain.
  See [test report](docs/test-report.md),
  [independent calculations](docs/evidence/tester-independent-check.txt),
  [Mac baseline](docs/evidence/tester-mac-baseline.txt),
  [Docker tests](docs/evidence/tester-docker-build-tests.txt), and
  [Docker persistence](docs/evidence/tester-docker-persistence.txt).

Evidence:
[local tests](docs/evidence/cli-tests-initial.txt),
[analysis checkpoint](docs/evidence/analysis-checkpoint.txt),
[Docker build](docs/evidence/docker-build-initial.txt),
[Docker tests](docs/evidence/docker-tests-initial.txt),
[Docker run](docs/evidence/docker-run-initial.txt),
[comparison](docs/evidence/local-docker-comparison.txt).

During Builder testing, synthetic codes B and D mistakenly collided with
approved exclusions. The fixtures were renamed, then the tie-order
expectation was corrected. Original failure logs and successful reruns
are retained in docs/evidence/.

## Limitations

There are no costs for calculating profit or margins; invoice value is not
proof of cash collection. Customer country need not be shipping destination.
Missing IDs limit customer findings. Wholesalers can create legitimate
large orders. Duplicate and exclusion assumptions affect totals.
Cancellation timing may refer to earlier purchases, including purchases
outside the observation window. This single retailer and short history
do not establish general retail trends or robust annual seasonality.

## AI roles and reviewed decisions

- Architect: developed the reviewed plan and analytical decisions.
- Builder: supplied implementation, tests, explanations, and fixes.
  Kanan ran commands, shared actual results, and reviewed charts.
- Tester: independently reviewed the plan, implementation and test suite;
  recalculated the workbook, inspected charts, and evaluated fresh Mac and
  Docker results. Identified stale documentation and review-archive hygiene
  issues and supplied corrections with a test report and calculation evidence.

Accepted recommendation: merchandise-only analysis with separately
reported charges and ambiguous entries.

Modified recommendation: Kanan added net-value rank to the product CSV
while retaining positive-sales ordering in the chart.

Builder clarification: Kanan approved the source-specific partial-month
policy recorded in section 17 of the plan.

Complete role conversations belong in:
docs/transcripts/kg396_architect.txt,
docs/transcripts/kg396_builder.txt, and
docs/transcripts/kg396_tester.txt.

Builder and technical Tester verification are complete; final documentation
and transcript handoff remain.
Transcript completeness has not yet been independently established.
Submission requires the three complete transcripts plus both actual
Repository A and Repository B URLs.
