# Known Limitations and Assumptions

## 1. Synthetic dataset

All data described by the supplied source manifest is synthetic. It is
intended for demonstrating data relationships, scoring logic, workflow
rules and validation. It is not actual customer or sales data.

## 2. Synthetic opportunity outcomes

The V2 generator labels the top 30% of the qualified cohort WON and the
remaining 70% LOST based on score rank. These are synthetic benchmark
labels, not observed conversions or verified purchases. Do not present
the resulting win rate as a real-world sales forecast.

## 3. Intent proxy

`PAGE_VIEW` is used as a synthetic proxy for high-intent page activity.
A page view does not necessarily establish genuine buying intent.

## 4. Temporal scoring

The initial score uses events from lead creation through
`min(created_at + 30 days, NOW)`. Later events are retained for
traceability but should not retroactively alter that initial score.

## 5. SQL and generator compatibility

The SQL activity enum includes `DEMO_COMPLETED`, matching the V2
generator's activity type. No mismatch exists for this value.

## 6. Loader coverage

The `lead_campaigns` CSV is generated with `lead_id`, `campaign_id`,
and `linked_at`. Its records were imported separately into MySQL using
`scripts/load_lead_campaigns.py`.

The database verification script confirms that all 15 database tables
match their corresponding CSV row counts. The general loader and the
dedicated bridge-table loader are separate import steps.

## 7. Routing and lifecycle rules

Foreign keys ensure referenced representatives exist, but do not enforce
territory matching. SQL enums constrain values but do not enforce every
valid stage transition. Application validation is required.

## 8. Activity ID convention

The V2 generator uses a global activity counter in normal activity IDs,
whereas the challenge example shows a per-lead counter. Review and align
this convention before final submission if strict adherence is required.

## 9. Ground truth

The reviewed project tree contains JSON ground-truth files. A separate
`ground_truth.csv` was not present. Ground-truth labels must remain
separate from scoring input features.

## 10. Database persistence

The V2 event generator writes staged files and does not update MySQL.
The general MySQL loader imports the original `data/generated/` files.
The `lead_campaigns` relationship file is imported separately by
`scripts/load_lead_campaigns.py`. V2 staging files are not automatically
loaded into MySQL.

## 11. Reproducibility evidence

A fixed seed and source manifest support repeatability, but a valid
demonstration requires two independently captured runs with identical
row counts and checksums.

## 12. Future improvements

- Add explicit tests proving post-conversion events cannot affect
  scoring.
- Align activity IDs with the required naming convention.
- Add a dedicated, independently repeatable two-run checksum script.
- Add more explicit lifecycle-transition and territory-routing
  enforcement.
