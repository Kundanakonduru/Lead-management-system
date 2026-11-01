# Ground Truth and Exception Labels

## 1. Purpose

Ground truth contains the expected labels/decisions for deliberately
injected exception cases. It is used to evaluate detection and handling.
It must remain separate from lead scoring input features to avoid target
leakage.

## 2. Current files

-   Original dataset ground truth: `data/ground_truth/ground_truth.json`
-   V2 exception ground truth:
    `data/staging/ground_truth_v2/ground_truth.json`

The supplied project tree contains JSON ground-truth artifacts. A
separate `ground_truth.csv` was not present in the reviewed file
listing; do not claim that a CSV is included unless one is generated and
committed.

## 3. V2 record structure

Each V2 ground-truth record includes: - `issue_id`: stable exception
identifier. - `issue_type`: exception category. - `lead_id`: affected
lead. - `expected_decision`: expected system response. -
`opportunity_id`: included for the stage-history-gap case.

Not every record contains every optional field.

## 4. Five injected cases

-   `EX-001` --- `OPTED_OUT_CONTACTED`; expected decision
    `BLOCK_CONTACT`.
-   `EX-002` --- `POST_CONVERSION_ACTIVITY`; expected decision
    `EXCLUDE_FROM_SCORE`.
-   `EX-003` --- `OUTSIDE_TERRITORY_ASSIGNMENT`; expected decision
    `REJECT_ASSIGNMENT`.
-   `EX-004` --- `DUPLICATE_OPPORTUNITY`; expected decision
    `REJECT_DUPLICATE`.
-   `EX-005` --- `STAGE_HISTORY_GAP`; expected decision
    `FLAG_MISSING_TRANSITION`.

## 5. Separation from scoring features

The generator calculates lead scores before appending the injected
anomaly events and writes the ground-truth labels to a separate JSON
file. The test suite includes
`test_ground_truth_is_not_inside_lead_features`.

For EX-002, the generator's initial score uses only activities through
`min(created_at + 30 days, NOW)`, and the injected post-conversion event
is appended after score calculation. This supports the intended
separation for the generated initial score. Keep the ground-truth file
out of feature-building and model/scoring input pipelines.

`opportunity_evidence.csv` is conceptually different: it records
evidence used to derive opportunity outcome data, while ground truth
records expected labels for exception evaluation.

## 6. Evaluation

The anomaly analysis report is written to
`data/analytics/anomaly_report.json`. The recorded development run
detected 5 of 5 injected cases. Re-run the anomaly analysis and tests
after code or data changes.

## 7. Ground-truth maintenance

When adding an exception: 1. Create a valid baseline dataset first. 2.
Inject the exception deliberately and minimally. 3. Add a ground-truth
record with an expected decision. 4. Keep the label out of scoring input
features. 5. Add a test for presence, detection and expected handling.
