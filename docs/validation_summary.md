# Validation Summary

## 1. Scope

This summary records the observed development verification results
supplied during project review. Results describe the recorded runs only;
rerun checks after changing data, code, schema or configuration.

## 2. Recorded results

- V2 validation report: `data/analytics/validation_report_v2.json`
- Anomaly report: `data/analytics/anomaly_report.json`
- Evaluation report: `data/analytics/evaluation_metrics_v2.json`
- Generated-data tests: `tests/test_pipeline.py`

## 3. PASS and exception results

- V2 validation: PASS; 0 reported errors.
- Automated project tests: 180 passed.
- Ground-truth exception cases: 5.
- Anomaly detection: 5 of 5 detected; 0 missed.
- Qualified leads: 3,000.
- Opportunities: 3,000.
- WON: 1,977.
- LOST: 1,023.
- Funnel reconciliation: `true` in the recorded evaluation output.
- Original CSV/MySQL verification: all 15 loaded table counts matched.
- Total CSV records matched against MySQL: 235,863.

## 4. Intentional exceptions

The V2 validator reported one consent exception and one territory
exception. These are deliberate injected scenarios and should be
identified as expected negative cases, not silently treated as ordinary
valid records.

The five ground-truth scenarios are:

1. Opted-out lead contacted.
2. Post-conversion activity.
3. Outside-territory assignment.
4. Duplicate opportunity attempt.
5. Missing stage-history transition.

## 5. Important verification still required

- Post-conversion activity detection is demonstrated. Confirm that the
  score calculation excludes such activity in the actual scoring path;
  do not infer enforcement from anomaly detection alone.
- The SQL activity ENUM includes `DEMO_COMPLETED`; no ENUM mismatch is
  currently identified between the reviewed schema and this activity
  value.
- The `lead_campaigns` bridge table is now generated in
  `data/generated/lead_campaigns.csv` and imported separately using
  `scripts/load_lead_campaigns.py`. The dedicated import completed
  successfully with 20,000 records. The general loader should be used
  only with a fresh/empty database; do not rerun it against an already
  populated database.
- The recorded checksum comparison had 10 matching pairs, but an
  independent reviewer should perform the documented two-run process
  in `reproducibility.md`.

## 6. Re-run commands

Run from the repository root with the project's virtual environment
active:

```powershell
python src/validation/validate_data.py
python src/analytics/anomaly_analysis.py
python src/analytics/evaluation.py
pytest -v
```

For original CSV/MySQL count comparison, with the database configured
and populated:

```powershell
python scripts/verify_database.py
```

To import the `lead_campaigns` bridge table into a database where that
table is still empty:

```powershell
python scripts/load_lead_campaigns.py
```

Do not rerun this dedicated import after the records have already been
loaded; the script checks that the destination table is empty.

## 7. Interpretation

A PASS applies to the checks and data state that were actually run. It
does not guarantee that every future generation or modified
configuration will pass. Preserve the generated JSON reports and test
output as evidence.
