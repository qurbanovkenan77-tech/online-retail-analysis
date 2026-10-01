# Independent Tester report — technical verification passed

Student: Kanan Gurbanov (kg396). Option 3. Tester: ChatGPT.
Review date: October 1, 2026.
Baseline: 6481c3882c0f28b74cf578ee0e421ece1bb4118a.

## Final technical status

PASS against the reviewed plan for the implementation and checks described
below. No analytical defect was found. Documentation and review-archive hygiene
corrections are included in the handoff. Student applied these updates and pushed commit 751eb12;
final transcript preservation and submission checks remain open.
This report records stages chronologically: earlier pending statements describe
the status at that stage and are superseded by later results.
A clean dependency installation was not repeated; the Mac used its existing
virtual environment and Docker reused cached build layers. The original
Option 3 description was not included among the eight assignment screenshots.
No claim is made about unseen requirements, transcript completeness or a grade.

## Scope and evidence boundary

Read docs/plan.md (including section 17), README.md, docs/smoke-test.md,
all four implementation modules, all five test modules, Dockerfile,
.dockerignore, and requirements.txt. Eight assignment screenshots supplied by the student were read on October 1.
They confirm role separation, plan review, pre-Tester smoke testing, independent
review, README reflection, Docker evidence, and complete role transcripts with
NetID filenames, headers, labels and markers, committed and separately uploaded
to Canvas. Both Repository A and B URLs are required. The Option 3 description
itself is not shown in these screenshots.
Builder logs and the student smoke record are historical evidence, not
independent Tester executions. No final acceptance is claimed.

## Initial review

Static review found the explicit 18-code map, raw-field deduplication,
ordered dispositions, partition audits, S/C/A/N definitions, uncapped rates,
same-population duplicate sensitivity, identified-only concentration,
minimum tied product ranks on unrounded values, and source-specific partial
December policy consistent with the reviewed plan. Existing tests cover
these main cases; reading tests does not establish that they pass now.

CLI declares all nine CSVs, four charts and metadata, stages output files,
checks source hash stability, and preserves unrelated outputs. Docker copies
only requirements, source and tests; README specifies read-only input and
persistent output bind mounts. Runtime mount behavior remains unverified by
this Tester. Chart code includes partial-month labels and net-value wording;
visual inspection of the actual charts remains pending.

## Checks actually executed by Tester

Environment: Linux x86_64, Python 3.12.14, pandas 2.2.3, openpyxl 3.1.5,
matplotlib 3.10.8. pytest and Docker are unavailable in this environment.
This differs from the required Python 3.13 and pinned dependencies.

PASS: independently calculated 5 x 10 = S 50, abs(-2) x 10 = C 20,
abs(-1) x 10 = A 10; N = 20 and cancellation rate = 40%. Executed the
application cleaning/analysis functions and asserted equality to those
constants. PASS: duplicating the sale gives before S=100, N=70 and after
S=50, N=20. See evidence/tester-hand-check.txt.

No full pytest suite, full-source analysis, or Docker command has been
executed by this Tester so far. The raw workbook is absent from the checkout.

## Findings and actions

T01 — minor documentation issue: README said Builder was ongoing and Tester
had not begun. Corrected in this checkout to state actual progress and link
this report. Changes have not been pushed or applied to the student's Mac.

T02 — verification gap, open: independently calculated real-source subtotal
with source row numbers and explicit duplicate/exclusion decisions is still
required. Committed output CSVs alone cannot prove source correctness.

T03 — verification gap, open: fresh suite execution in the target environment,
output and metadata checks, chart inspection and Docker evidence review remain.

T04 — submission gap, open: preserve this entire ongoing visible conversation
as docs/transcripts/kg396_tester.txt at completion. Do not label a partial
transcript complete. Prior role transcript completeness and original assignment
requirements have not yet been independently verified.

## Next verification step

Student runs a fresh baseline capture and pytest suite on the Mac, recording
commit, working-tree status, Python/dependency versions, and actual exit code.
Results are pending and must be attributed to the student when received.

## Student-executed fresh Mac baseline — PASS

Student pasted terminal output for October 1, 2026 at 16:55:32 UTC, baseline
commit 6481c3882c0f28b74cf578ee0e421ece1bb4118a. Python 3.13.14; pandas 3.0.6,
openpyxl 3.1.5, matplotlib 3.11.2, pytest 9.1.1 match requirements.txt.
pip check: No broken requirements found. pytest -q -rs: 77 passed in 8.90s,
PYTEST_EXIT_CODE=0. Working tree listed only the newly created baseline log.
Evidence on student's Mac: docs/evidence/tester-mac-baseline.txt. This is
a fresh student execution during Tester review, not execution by ChatGPT.
It reused .venv and does not establish a clean dependency installation.

The provided screenshots support the workflow currently being followed;
final verification, README reflection and complete transcripts remain open.
Next: inspect actual source rows for a small product subtotal and independently
calculate values without calling application aggregation functions.

## Real-source product subtotal — PASS

Student executed the direct workbook inspection on the Mac and pasted its
output. Input SHA-256: 43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d.
Selected StockCode 23843 (PAPER CRAFT , LITTLE BIRDIE), two source rows:

| Excel row | Invoice | Quantity | UnitPrice | Exact duplicate removed | Disposition |
|---|---|---:|---:|---|---|
| 540423 | 581483 | 80995 | 2.08 | False | Positive sale |
| 540424 | C581484 | -80995 | 2.08 | False | Cancellation |

Both have valid dates on December 9, 2011, positive finite prices and integral
quantities. Code 23843 is not in the approved exclusion map. Neither is an
exact duplicate. Large quantities remain eligible under the reviewed plan.
Tester independently calculated using Python Decimal (no application functions):
80995 * 2.08 = 168469.60; S=168469.60, C=168469.60, A=0, N=0, C/S*100=100%.
All five values match the product output pasted by the student.
Source inspection evidence on Mac: docs/evidence/tester-source-subset.txt and
docs/evidence/tester-source-subset.csv. Source bytes were inspected by the
student's command; Tester reviewed the pasted rows and executed the arithmetic.
This does not establish the cause of cancellation or physical return of goods.
Rank 2, net rank 3898 and share 1.64% require full-population verification;
they are not established by this two-row calculation. T02 is closed for the
plan's required real-source subtotal. Full fresh output verification remains open.

## Fresh full-source CLI run on Mac — PASS (execution)

Student pasted actual output dated October 1, 2026, 17:15:28 UTC, at commit
6481c3882c0f28b74cf578ee0e421ece1bb4118a. Executed:
python -m retail_analysis --input "data/Online Retail.xlsx" --output outputs-tester
Reported 9 CSVs, 4 PNGs and run_metadata.json, 531,127 eligible merchandise
rows, ANALYSIS_EXIT_CODE=0. Evidence on Mac: docs/evidence/tester-full-run.txt.
This establishes successful student execution; file contents, charts and
metadata from this fresh run have not yet been independently inspected.
Next: obtain the fresh outputs and exact input workbook for independent
full-population calculations and visual checks.

## Full-workbook independent oracle — PASS

Tester directly executed docs/evidence/tester_independent_check.py against
the workbook and outputs-tester supplied in tester-review.zip. The script
imports no retail_analysis functions. Environment: Linux Python 3.12.14,
pandas 2.2.3. The received workbook hash matches the recorded source hash.
Execution completed with exit 0. Actual results: evidence/tester-independent-check.txt.

Verified raw-to-eligible row counts and all cleaning-stage signed-value audits;
excluded-code row counts and price partitions; every product, country and
monthly S/C/A/N and rate; sales shares; every product description and both
unrounded minimum ranks; deterministic product ordering; monthly coverage
and partial flags; all customer amounts, shares, ordering and top-ten flags;
overall customer coverage/concentration; duplicate sensitivity; top-ten
large-value line selection and amounts; expected file inventory; metadata
hash, filename, output paths, dependency versions, raw missing/duplicate counts.
CSV comparisons allow half a cent/0.005 percentage point for two-decimal
export rounding, plus 0.000001 numerical slack. Counts/ranks/order matched.
This export comparison allowance is separate from the application's internal
unrounded reconciliation tolerance.

Unrounded independent S=10245935.993, C=475886.16000000003, A=0,
N=9770049.833. Identified positive sales=8736027.643, top-ten sales=1519899.12,
concentration=17.398057585335874%. Fresh metadata timestamp:
2026-10-01T17:15:48.172601+00:00. No analytical discrepancy found.

Tester visually inspected all four supplied PNGs. Labels and captions are
readable without overlap/cutoff; product order is consistent with the CSV;
country panels distinguish non-UK sales and disclose separate scales;
December 2011 is visibly partial; the net chart includes the required
net-value definition. Visual check PASS.

Existing smoke Docker evidence was inspected: 76 passed, 1 permission-test
skip in 11.00s; full run produced 531127 eligible rows; nine CSV comparisons
and input hashes passed. These remain historical student executions. Fresh
Docker verification and direct read-only mount enforcement check are next.

T05 — review-artifact hygiene: tester-review.zip contains the raw workbook.
Added that exact archive name to .gitignore in the Tester checkout so this
temporary review package is not accidentally committed. Student must apply
the change on the Mac before staging final deliverables.

## Fresh Docker build and suite on student's Mac — PASS

Student pasted actual output dated October 1, 2026, 17:23:51 UTC. Docker
Desktop desktop-linux build completed with DOCKER_BUILD_EXIT_CODE=0.
Build layers, including dependency installation, were cached: this is not
evidence of a new clean dependency installation. Base image resolved to
python:3.13-slim@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b.
Fresh container suite: 76 passed, 1 skipped in 11.02s; DOCKER_TEST_EXIT_CODE=0.
The directory-write-permission test skipped because the container account
can bypass directory permissions. The fresh Mac suite passed all 77 tests.
Evidence on Mac: docs/evidence/tester-docker-build-tests.txt. No Docker
execution is attributed to ChatGPT. Read-only bind enforcement and fresh
output persistence/comparison remain pending.

## Fresh Docker mounts and persistent outputs — PASS

Student executed the Tester-provided command on the Mac at October 1, 2026,
17:32:34 UTC and pasted its output. Attempting a temporary write inside the
input mount returned EROFS, proving the read-only filesystem rejected writes
even under the container account. Full analysis exited 0 with 531,127 eligible
rows. After --rm container exit, the host comparison confirmed all nine CSVs
matched the independently reviewed local outputs byte-for-byte; both metadata
input hashes matched the source workbook. Nine CSVs, four valid nonempty PNGs
and metadata persisted on the Mac. COMPARISON_EXIT_CODE=0.
Evidence on Mac: docs/evidence/tester-docker-persistence.txt. Docker PNGs were
checked for signature/size and persistence; visual review was performed on
the local PNGs, not a separate fresh inspection of Docker PNG pixels.

## Resolution and handoff

- T01: stale README role/status wording corrected in handoff; applied on the Mac and committed in 751eb12.
- T02: real-source subtotal completed and independently verified.
- T03: full data, charts, metadata and fresh student Docker checks completed.
- T04: submission/transcript completeness remains open until the conversations
  are preserved in full, committed, and uploaded separately to Canvas.
- T05: tester-review.zip excluded in handoff .gitignore; applied on the Mac and committed in 751eb12.

No application source changes were needed, so no post-fix analytical rerun is
required. The documentation and ignore-file changes require a diff review.
Retain student-created evidence logs already on the Mac. The handoff also
provides the independently executed calculation script, actual output log,
and hand-check log. It does not overwrite historical smoke-test evidence.
