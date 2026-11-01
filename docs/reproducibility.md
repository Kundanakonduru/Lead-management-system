# Reproducibility Procedure

## 1. Fixed generation settings

The supplied generators use seed `20261022`. The V2 event generator also
defines `NOW = 2026-10-30 12:00:00`. The master source manifest records
generator version `1.0` and the master-data counts.

Reproducibility requires the same generator code, seed, parameters and
unchanged input master files.

## 2. Generate the datasets

Run from the project root:

```powershell
python src/generators/generate_data.py
python src/generators/generate_events.py
```

The master generator writes CSV files to `data/generated/`, including
`lead_campaigns.csv`. The V2 generator reads those master CSVs and writes
staged outputs to `data/staging/generated_v2/` and
`data/staging/ground_truth_v2/`.

**Warning:** `generate_data.py` refreshes/replaces generated master CSV
outputs. Preserve any files you need before running it. Do not load
regenerated CSVs into an already populated MySQL database.

The `lead_campaigns` bridge table is imported separately into MySQL by
running `python scripts/load_lead_campaigns.py`. This database import is
not part of the deterministic CSV generation procedure. Run the
dedicated loader only when the destination `lead_campaigns` table is
empty; it is not intended to be rerun after a successful import.

## 3. Capture the first row-count and checksum manifest

Capture this before the second generation run:

```powershell
$paths = @("data/generated", "data/staging/generated_v2", "data/staging/ground_truth_v2")

Get-ChildItem $paths -File -Recurse |
    Where-Object { $_.Name -ne "checksums_before.csv" -and $_.Name -ne "checksums_after.csv" } |
    Sort-Object FullName |
    ForEach-Object {
        $hash = Get-FileHash $_.FullName -Algorithm SHA256
        [PSCustomObject]@{
            Path = $_.FullName.Substring((Get-Location).Path.Length + 1)
            Bytes = $_.Length
            SHA256 = $hash.Hash
            Rows = if ($_.Extension -eq ".csv") { (Import-Csv $_.FullName).Count } else { "" }
        }
    } |
    Export-Csv data/analytics/checksums_before.csv -NoTypeInformation
```

## 4. Regenerate with the same settings

```powershell
python src/generators/generate_data.py
python src/generators/generate_events.py
```

## 5. Capture the second manifest

Run the same manifest-capture command, changing the output filename to
`data/analytics/checksums_after.csv`.

## 6. Compare the manifests

```powershell
$before = Import-Csv data/analytics/checksums_before.csv
$after = Import-Csv data/analytics/checksums_after.csv
$diff = Compare-Object $before $after -Property Path, Bytes, SHA256, Rows

if ($diff) {
    $diff
    Write-Host "REPRODUCIBILITY CHECK: FAIL"
} else {
    Write-Host "REPRODUCIBILITY CHECK: PASS"
}
```

The comparison should show identical relative paths, file sizes, SHA-256
hashes and CSV row counts. Preserve the before manifest until the
comparison is complete.

## 7. Evidence and limitations

The development review recorded 10 matching checksum pairs. This is a
historical result for the files captured at that time. A fresh
independent demonstration requires capturing the first manifest before
regeneration and the second after regeneration using the same procedure.
Do not describe the historical 10 matching pairs as a new two-run
verification.

The master source manifest is `data/generated/source_manifest.json`. V2
run metadata is `data/staging/generated_v2/generation_summary.json`.

The database verification run recorded 15 loaded tables with matching
CSV and MySQL row counts (235,863 records in total). This is a separate
database consistency check; it does not replace the two-run checksum
procedure above.
