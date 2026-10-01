# Student manual smoke test

## Result

PASS — completed by Kanan Gurbanov (kg396) on September 30, 2026,
before the separate independent Tester stage.

Tested implementation commit:
ffb1398e3bc7a01fff910bd9caa6ad071280a607

Local environment capture: October 1, 2026 at 02:36:57 UTC
(September 30 at 10:36:57 PM EDT).

Final local/Docker comparison: October 1, 2026 at
02:47:39.398638 UTC. Final Docker visual confirmation was provided
September 30, 2026 at approximately 10:51 PM EDT.

Commands were executed by the student on the Mac and through Docker
Desktop. Observations were reported in the Builder conversation.
This is a student smoke test, not independent Tester verification.

## Environment

- Mac: macOS ARM64, Python 3.13.14.
- Docker: Docker Desktop 4.88.1, Engine 29.7.2, Linux ARM64.
- Recorded container Python: 3.13.15.
- Direct dependencies: pandas 3.0.6, openpyxl 3.1.5,
  matplotlib 3.11.2, pytest 9.1.1.
- Local setup used a fresh terminal and the existing .venv.
  It was not a completely clean dependency installation.

Input: data/Online Retail.xlsx

SHA-256:
43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d

## Commands exercised

From the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m retail_analysis --input "data/Online Retail.xlsx" --output outputs
python -m retail_analysis --input "data/does-not-exist.xlsx" --output outputs

docker build -t online-retail-analysis .
docker run --rm online-retail-analysis python -m pytest -q -rs
mkdir -p outputs-docker
docker run --rm \
  --mount "type=bind,source=$(pwd)/data,target=/data,readonly" \
  --mount "type=bind,source=$(pwd)/outputs-docker,target=/outputs" \
  online-retail-analysis \
  python -m retail_analysis --input "/data/Online Retail.xlsx" --output /outputs
```

The student also compared all nine exported CSVs using
pandas.testing.assert_frame_equal with exact comparison and checked
that the run metadata contained identical input hashes.

## Observations

| Check | Actual result |
|---|---|
| README setup in a fresh terminal | Installation exited 0; pip check reported no broken requirements |
| Local automated tests | 77 passed in 8.96 seconds; exit 0 |
| Full local analysis with explicit output | Exit 0; nine CSVs, four PNGs, metadata; 531,127 eligible rows |
| Missing input | Clear "Input workbook not found" error; expected exit 1 |
| CSV and chart inspection | Student reviewed the supplied checklist and reported "visually all looks good" |
| Product ranks and monthly coverage | Included in the student's checklist review; no issue reported |
| Exclusion basis, samples wording, duplicate assumption, net-value explanation | Included in the student's checklist review; no issue reported |
| Exclusion reconciliation | Counts and exported audit values matched exactly, as recorded below |
| Docker smoke build, tests, and analysis | Student reported exit 0 for all three commands |
| Container permission-test limitation | Earlier recorded Docker suite had 76 passed, 1 skipped; the account could bypass directory permissions. The corresponding test passed locally |
| Local/Docker CSV comparison | All nine CSVs matched exactly; input hashes matched |
| Persistence and Docker visual review | After container exit, student opened overall_summary.csv and all four PNGs; all were accessible, with readable labels and no overlap or cut-off text |

The final Docker test log is retained in
docs/evidence/smoke-docker-tests.txt. Its detailed test counts were not
repeated in the conversation; the student confirmed its zero exit code.

## Exclusion reconciliation observed

| Measure | Excluded report | Cleaning excluded-code step |
|---|---:|---:|
| Rows | 3,022 | 3,022 |
| Signed value, positive prices (GBP) | -21,918.76 | -21,918.76 |
| Signed value, nonpositive prices (GBP) | -22,124.12 | -22,124.12 |
| Uncomputable values | 0 | 0 |

These are excluded-entry diagnostic amounts, not merchandise revenue.

## Evidence

- [Environment](evidence/smoke-local-environment.txt)
- [Installation](evidence/smoke-install.txt)
- [Local tests](evidence/smoke-local-tests.txt)
- [Local analysis](evidence/smoke-local-run.txt)
- [Missing-input error](evidence/smoke-missing-input.txt)
- [Docker build](evidence/smoke-docker-build.txt)
- [Docker tests](evidence/smoke-docker-tests.txt)
- [Docker analysis](evidence/smoke-docker-run.txt)
- [Exact output comparison](evidence/smoke-comparison.txt)

Visual observations and the exclusion comparison are also recorded in
the Builder conversation, to be preserved in
docs/transcripts/kg396_builder.txt.

## Failures and follow-up

No unexpected failures were reported during this manual smoke test.
The missing-input failure was intentional.

Earlier Builder test-fixture errors and their corrections remain
documented in the README and original evidence logs.

At the time of this smoke test, independent Tester review was pending.
That review was subsequently completed on October 1, 2026, and its
report and evidence were committed in 751eb12.
See [the Tester report](test-report.md).

All three role transcript files are now committed, with disclosed
export limitations.