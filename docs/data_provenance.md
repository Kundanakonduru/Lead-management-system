# Data Provenance and Source Manifest

## 1. Data origin

The reviewed datasets are generated synthetically by this project's
Python generators. The supplied source manifest contains no external
dataset URLs, licenses or retrieval dates. Therefore, this documentation
does not claim that external datasets were used.

## 2. Master-data source manifest

Location: `data/generated/source_manifest.json`

Recorded metadata:

-   Seed: `20261022`
-   Generator version: `1.0`
-   Generated at: `2026-10-30T12:00:00`
-   Companies: 5,000
-   Contacts: 10,000
-   Leads: 20,000
-   Campaigns: 20
-   Territories: 8
-   Products: 3
-   Sales representatives: 16

The master generator also creates `data/generated/lead_campaigns.csv`
with 20,000 lead/campaign relationship records. The CSV was verified
separately after generation. The supplied manifest's recorded count list
above does not include a `lead_campaigns` entry.

## 3. External source details

-   External dataset/source URL: Not applicable; none recorded in the
    supplied manifest.
-   External license: Not applicable; no external dataset is recorded.
-   External retrieval date: Not applicable; no external retrieval is
    recorded.
-   Attribution: Not applicable to the synthetic records described by
    this manifest.

If external data is introduced later, record source name, URL, dataset
version, retrieval date, license/redistribution terms, attribution,
transformations and fields discarded. Do not use data unless access and
redistribution are legally permitted.

## 4. Generator/output locations

-   Master data: `src/generators/generate_data.py` → `data/generated/`
  - Includes `lead_campaigns.csv` (20,000 relationship records in the
    reviewed generation).
-   V2 events: `src/generators/generate_events.py` →
    `data/staging/generated_v2/`
-   V2 ground truth: `data/staging/ground_truth_v2/ground_truth.json`
-   V2 run metadata: `data/staging/generated_v2/generation_summary.json`

The V2 event generator reads master CSV files from `data/generated/` and
is documented in code as staged generation that does not modify MySQL.

The `lead_campaigns.csv` file represents generated lead-to-campaign
associations. Its presence does not establish that a lead opened, clicked
or otherwise engaged with a campaign. The bridge table is imported into
MySQL separately with `scripts/load_lead_campaigns.py`; the dedicated
loader successfully imported 20,000 records in the reviewed database
setup. This import is separate from V2 staged event generation.

## 5. Provenance limitation

The master source manifest describes master-data counts and generation
metadata. It does not provide checksums or complete V2 event counts. V2
run details are recorded separately in `generation_summary.json`. See
`reproducibility.md` for checksum verification.
