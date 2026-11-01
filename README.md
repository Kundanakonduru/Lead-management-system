# Lead Management System

A Python and MySQL-based Lead Management System developed as part of the YottaFlex AI Challenge.
The project generates synthetic CRM data, calculates transparent lead scores, qualifies leads, creates follow-up tasks and opportunities, preserves event history, detects known data-quality exceptions, and produces business evaluation metrics.

«**Dataset note:** The project contains an original master-data/MySQL dataset and a separate V2 event-generation pipeline. The V2 generator writes to "data/staging/" and does not modify the original "data/generated/" files or the existing MySQL database.»

# Table of Contents

1. "Business Problem" (#business-problem)
2. "Objectives" (#objectives)
3. "Key Capabilities" (#key-capabilities)
4. "Technology Stack, Packages and Libraries" (#technology-stack-packages-and-libraries)
5. "Project Structure" (#project-structure)
6. "Data Model" (#data-model)
7. "Synthetic Data Volumes" (#synthetic-data-volumes)
8. "Lead Scoring and Qualification" (#lead-scoring-and-qualification)
9. "Opportunity Outcome Rule" (#opportunity-outcome-rule)
10. "Ground Truth and Exception Scenarios" (#ground-truth-and-exception-scenarios)
11. "Installation" (#installation)
12. "Configuration" (#configuration)
13. "Run the Project" (#run-the-project)
14. "MySQL Setup and Loading" (#mysql-setup-and-loading)
15. "Validation, Analytics and Tests" (#validation-analytics-and-tests)
16. "Reproducibility" (#reproducibility-fixed-seed-and-repeat-run-check)
17. "Current Verification Results" (#current-verification-results)
18. "AI Use Disclosure" (#ai-use-disclosure)
19. "Important Implementation Notes" (#important-implementation-notes)
20. "Limitations and Future Improvements" (#limitations-and-future-improvements)

---

# 1. Business Problem

Sales and marketing teams need a consistent way to decide which prospects deserve attention, when a follow-up should happen, which representative should own a lead, and how lead progression should be measured.

Manual or disconnected processes can lead to inconsistent qualification, missed follow-ups, consent violations, duplicate opportunities and unreliable reporting.

This project models an end-to-end lead-management workflow using related CRM entities, explicit business rules, event history, labelled exception cases and measurable outputs.

# 2. Objectives

- Generate company, contact, campaign, product, territory and sales-representative master data.
- Generate leads with source, ownership, consent and activity history.
- Calculate fit, intent and engagement scores using documented weights.
- Select a deterministic qualified-lead cohort.
- Generate follow-up tasks and opportunity records using valid parent IDs.
- Preserve consent and stage-history records.
- Identify duplicate and deliberately injected exception scenarios.
- Reconcile opportunity outcomes and produce business metrics.
- Validate keys, relationships, IDs, dates, lifecycle rules and reproducibility.

# 3. Key Capabilities

- Synthetic Data Generation: Seeded and parameterized master-data generation.
- Lead Scoring: Separate fit, intent and engagement components with an overall weighted score.
- Qualification: Deterministic ranking with a tie-break rule.
- Consent History: Consent status and effective dates are represented as records.
- Task Management: Follow-up tasks are linked to leads and representatives.
- Opportunity Management: One opportunity per qualified lead in the V2 dataset, with a documented synthetic outcome rule.
- Traceability: Activities, consent records, stage history, evidence and ground-truth labels are retained as separate data.
- Data Quality Analysis: Duplicate auditing, validation and anomaly detection.
- Business Evaluation: Qualification, conversion, win/loss and revenue metrics.
- Automated Testing: Pytest coverage for generated data and business rules, plus MySQL constraint checks.

# 4. Technology Stack, Packages and Libraries

# 4.1 Core Technologies

Technology| Purpose
Python| Data generation, validation, analytics and automated tests
MySQL| Relational database used by the original dataset and database-loading workflow
SQL| Table definitions, primary keys, foreign keys and database constraints
CSV| Generated entity and relationship datasets
JSON| Ground-truth labels, manifests, validation reports and analytics outputs
SHA-256| File checksums used in reproducibility comparisons
Git and GitHub| Version control and project submission

# 4.2 Python Third-Party Packages and Pinned Versions

# The following versions are declared in "requirements.txt". That file is the authoritative dependency list.

Package| Pinned Version| Purpose
"pandas"| "3.1.0"| Tabular data processing and CSV operations
"numpy"| "2.5.4"| Numerical operations and array handling
"SQLAlchemy"| "2.1.6"| SQL toolkit and database interaction layer
"PyMySQL"| "1.2.3"| Python connectivity to MySQL
"python-dotenv"| "1.2.4"| Load local configuration from ".env"
"pytest"| "9.2.0"| Automated test execution

# Install the declared dependencies from the repository root:

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check

# To inspect installed package versions:

python -m pip freeze

# 4.3 Python Standard-Library Modules

The code also uses Python standard-library modules where required, including "csv", "json", "os", "pathlib", "hashlib", "random", "datetime", "sqlite3" and "argparse".

These modules are included with Python and do not need separate installation. The modules actually used by a workflow depend on the script being run.

# 5. Project Structure

This tree follows the main project structure. Local runtime artifacts such as ".pytest_cache/", "__pycache__/" and "venv/" are not intended to be committed to GitHub.

5. Project Structure
```text
Lead-management-system/
│
├── data/
│   ├── analytics/
│   │   ├── anomaly_report.json
│   │   ├── checksums_after.csv
│   │   ├── checksums_audit_after.csv
│   │   ├── checksums_audit_before.csv
│   │   ├── checksums_before.csv
│   │   ├── duplicate_audit.csv
│   │   ├── duplicate_summary.json
│   │   ├── evaluation_metrics.json
│   │   ├── evaluation_metrics_v2.json
│   │   ├── leads_with_duplicate_flags.csv
│   │   └── validation_report_v2.json
│   │
│   ├── generated/
│   │   ├── activities.csv
│   │   ├── campaigns.csv
│   │   ├── companies.csv
│   │   ├── consents.csv
│   │   ├── contacts.csv
│   │   ├── data_quality_issues.csv
│   │   ├── lead_campaigns.csv
│   │   ├── leads.csv
│   │   ├── opportunities.csv
│   │   ├── products.csv
│   │   ├── sales_rep_products.csv
│   │   ├── sales_reps.csv
│   │   ├── score_rules.csv
│   │   ├── source_manifest.json
│   │   ├── stage_history.csv
│   │   ├── tasks.csv
│   │   └── territories.csv
│   │
│   ├── ground_truth/
│   │   └── ground_truth.json
│   │
│   ├── staging/
│   │   ├── generated_v2/
│   │   │   ├── activities.csv
│   │   │   ├── consents.csv
│   │   │   ├── data_quality_issues.csv
│   │   │   ├── generation_summary.json
│   │   │   ├── leads.csv
│   │   │   ├── opportunities.csv
│   │   │   ├── opportunity_evidence.csv
│   │   │   ├── score_rules.csv
│   │   │   ├── stage_history.csv
│   │   │   └── tasks.csv
│   │   │
│   │   └── ground_truth_v2/
│   │       └── ground_truth.json
│   │
│   └── validation_report.json
│
├── docs/
│   ├── business_rules.md
│   ├── data_dictionary.md
│   ├── data_provenance.md
│   ├── database_design.md
│   ├── growth_truth.md
│   ├── known-limitations.md
│   ├── reproducibility.md
│   └── validation_summary.md
│
├── prompt_history/
│   └── Development_prompts.md
│
├── scripts/
│   ├── load_lead_campaigns.py
│   ├── test_database_constraints.py
│   └── verify_database.py
│
├── src/
│   ├── analytics/
│   │   ├── anomaly_analysis.py
│   │   └── evaluation.py
│   │
│   ├── database/
│   │   ├── load_data.py
│   │   └── schema.sql
│   │
│   ├── generators/
│   │   ├── generate_data.py
│   │   ├── generate_events.py
│   │   └── generate_events_backup.py
│   │
│   └── validation/
│       ├── detect_duplicates.py
│       └── validate_data.py
│
├── tests/
│   └── test_pipeline.py
│
├── .gitignore
├── README.md
└── requirements.txt
```


Note: Runtime artifacts such as ".env", "venv/", "__pycache__/", and ".pytest_cache/" are excluded from version control.

The tree is intended to show the main project files and directories, not every generated output or local runtime artifact.

# 6. Data Model

The relational schema is defined in "src/database/schema.sql".

# 6.1 Entities and Tables

Entity/Table| Purpose
"companies"| Company master records
"contacts"| People associated with companies
"leads"| Prospect records, scores, source, status and ownership
"campaigns"| Marketing campaign master records
"activities"| Timestamped interactions associated with leads
"consents"| Consent status and effective-date history
"score_rules"| Scoring feature definitions and weights
"sales_reps"| Sales representative and territory details
"sales_rep_products"| Many-to-many representative/product eligibility bridge
"tasks"| Follow-up work assigned to representatives
"opportunities"| Commercial opportunities and outcomes
"stage_history"| Opportunity/lead stage transition history
"territories"| Territory master records
"products"| Product master records
"lead_campaigns"| Lead/campaign many-to-many bridge

# 6.2 Relationship Overview

- One company can have many contacts.
- A contact can be associated with leads; each lead references a contact and company.
- A lead can have many activities, consent records, tasks and stage-history records.
- A lead can have at most one opportunity in the supplied schema because "opportunities.lead_id" is unique.
- Sales representatives belong to territories.
- Sales representatives and products have a many-to-many relationship through "sales_rep_products".
- Leads and campaigns have a many-to-many relationship through "lead_campaigns".

Primary keys and foreign keys are declared in the SQL schema. The generated-data test suite and database constraint tests check key uniqueness and relationship integrity.

# 7. Synthetic Data Volumes

The project uses synthetic business data to simulate a lead-management workflow.

The original dataset and MySQL verification reported the following counts:

Entity| Records
Companies| 5,000
Contacts| 10,000
Campaigns| 20
Territories| 8
Products| 3
Sales representatives| 16
Sales representative–product mappings| 48
Leads| 20,000
Lead–campaign mappings| 20,000
Consents| 60,000
Score rules| 10
Activities| 89,537
Tasks| 19,222
Opportunities| 3,000
Stage-history records| 8,999

## Note: These are the original dataset/MySQL counts. The separate V2 event-generation pipeline produces its own staging outputs. Do not confuse the original dataset with the V2 staging dataset.

# 8. Lead Scoring and Qualification

Leads are evaluated using three dimensions:

1. Fit: How closely the lead matches the target customer profile.
2. Intent: Signals indicating the lead's interest in the product or service.
3. Engagement: Interactions such as calls, emails, meetings and other recorded activities.

The scoring process uses configured score rules to derive lead scores and qualification decisions.

# The resulting score supports:

- Lead prioritization.
- Identification of qualified and unqualified leads.
- Follow-up task assignment.
- Sales pipeline analysis.

Scores are validated to ensure they are numeric, finite and within the range of 0–100.

# 9. Opportunity Outcome Rule

Opportunity outcomes are derived from the project's defined business rules rather than being assigned independently at random.

The V2 pipeline uses the documented synthetic outcome rule "OUTCOME-001": an opportunity is labelled "WON" when the company's annual revenue meets the configured product-base-value threshold; otherwise, it is labelled "LOST".

The outcome labels are:

- "WON"
- "LOST"

This is a deterministic synthetic business proxy for generating and evaluating outcomes. It is not evidence of actual customer purchases or real-world sales performance.

The evaluation process uses these outcome labels to calculate win rate, loss rate and revenue-related metrics. Outcome labels are kept separate from lead-scoring inputs.

# 10. Ground Truth and Exception Scenarios

The project includes controlled exception scenarios to evaluate data-quality and anomaly-detection behavior.

Ground-truth labels identify deliberately injected exception records. These labels are maintained separately from the analytical features used by the detection process.

# The V2 event-generation pipeline includes five injected ground-truth cases:

Scenario| Expected Decision
Opted-out lead contacted| "BLOCK_CONTACT"
Post-conversion activity| "EXCLUDE_FROM_SCORE"
Outside-territory assignment| "REJECT_ASSIGNMENT"
Duplicate opportunity attempt| "REJECT_DUPLICATE"
Missing stage-history transition| "FLAG_MISSING_TRANSITION"

The validation and anomaly-analysis processes check these cases and report detected and missed cases separately.

# 11. Installation

# 11.1 Clone the Repository

git clone https://github.com/Kundanakonduru/Lead-management-system.git
cd Lead-management-system

# 11.2 Create a Virtual Environment

python -m venv venv

# Activate it in Windows PowerShell:

.\venv\Scripts\Activate.ps1

If PowerShell blocks script execution, use the appropriate execution policy for your environment or activate the environment through Command Prompt.

# 11.3 Install Dependencies

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check

# 12. Configuration

The project uses environment variables for database configuration.

Create a ".env" file in the project root and configure the database connection using the variable names expected by the database connection module.

Example configuration:

DB_HOST=localhost
DB_PORT=3306
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=lead_management_db

Use the exact variable names referenced in your database connection code if they differ from this example.

Do not commit actual database passwords or other secrets to GitHub.

# 13. Run the Project

Run commands from the project root directory.

# 13.1 Generate the Original Master Dataset

python src/generators/generate_data.py

The original generator creates the master synthetic CSV datasets under "data/generated/".

Default generation parameters:

Parameter| Default
Companies| 5,000
Contacts| 10,000
Leads| 20,000
Seed| 20261022

The generator also supports custom counts and seeds:

python src/generators/generate_data.py --companies 5000 --contacts 10000 --leads 20000 --seed 20261022

Caution: This command writes to "data/generated/". Back up existing master data before regenerating it if you need to preserve the current files.

# 13.2 Generate the V2 Event Dataset

python src/generators/generate_events.py

The V2 pipeline uses the fixed seed "20261022" and reads the original master data from "data/generated/".

It writes:

- Event outputs to "data/staging/generated_v2/".
- Ground-truth labels to "data/staging/ground_truth_v2/".

It does not modify the original "data/generated/" files or the existing MySQL database.

# 13.3 Validate the Datasets

python -m src.validation.validate_data

The validator checks dataset structure, required fields, keys, foreign-key references, ID formats, scoring consistency, opportunity reconciliation, stage history, evidence arithmetic and the five ground-truth scenarios.

# 13.4 Run Business Evaluation

python -m src.analytics.evaluation

This generates V2 business metrics in:

data/analytics/evaluation_metrics_v2.json

# 13.5 Run Anomaly Analysis

python -m src.analytics.anomaly_analysis

This compares detected exception cases with the separate ground-truth labels and writes:

data/analytics/anomaly_report.json

# 14. MySQL Setup and Loading

The project uses MySQL for relational data storage.

# 14.1 Create the Database

Open MySQL Workbench and create the database:

CREATE DATABASE lead_management_db;

Use the database name configured in your environment variables.

# 14.2 Create the Database Tables

Execute the project's database schema SQL file in MySQL Workbench:

src/database/schema.sql

Ensure that the tables and their constraints are created before loading the CSV data.

# 14.3 Configure the Database Connection

Update the ".env" file with your MySQL host, port, username, password and database name, using the exact variable names expected by the connection code.

# 14.4 Load the Original Generated Data

Run the database loader:

python src/database/load_data.py

The loader reads CSV files from "data/generated/" and inserts records into the configured MySQL database.

The loader follows a predefined table-loading order to account for dependencies between related tables.

## The documented 15-table load order is:

1. "companies"
2. "contacts"
3. "campaigns"
4. "territories"
5. "products"
6. "sales_reps"
7. "sales_rep_products"
8. "leads"
9. "lead_campaigns"
10. "consents"
11. "score_rules"
12. "activities"
13. "tasks"
14. "opportunities"
15. "stage_history"

The loader uses batch insertion and transaction handling. It commits after a successful load and rolls back if an error occurs.

Important: The original database loader reads from "data/generated/". It does not automatically load V2 staging outputs into MySQL. Before running the loader against an existing database, check the current database state and the loader's safeguards. Do not assume that rerunning a load against populated tables is safe.

# 14.5 Verify Database Record Counts

After loading, run:

python scripts/verify_database.py

This compares the original CSV record counts with the corresponding MySQL table counts.

# 14.6 Run Database Constraint Tests

python -m pytest scripts/test_database_constraints.py -v

These tests check the MySQL schema and database-level constraints. A working MySQL connection and correctly configured ".env" file are required.

# 15. Validation, Analytics and Tests

15.1 Run the Complete Test Suite

python -m pytest -q

# 15.2 Run the Database Constraint Tests

python -m pytest scripts/test_database_constraints.py -v

The database constraint tests cover:

- Required database tables.
- Primary-key existence and uniqueness.
- Composite primary keys.
- Foreign-key relationships.
- Referential integrity.
- Expected unique constraints.
- Rejection of duplicate values.
- Rejection of invalid foreign-key references.
- InnoDB table-engine requirements.

# 15.3 Run Dataset Validation

python -m src.validation.validate_data

# 15.4 Run Business Evaluation

python -m src.analytics.evaluation

# 15.5 Run Anomaly Analysis

python -m src.analytics.anomaly_analysis

# 16. Reproducibility: Fixed Seed and Repeat-Run Check

Reproducibility is important for validating synthetic datasets and analytical results.

The V2 event-generation pipeline uses the fixed seed "20261022" and supports repeat-run verification against fixed master inputs.

# The reproducibility check:

1. Uses the same fixed master input files.
2. Runs the event-generation pipeline with the same configured seed.
3. Generates the V2 output files independently.
4. Compares generated files using SHA-256 hashes.
5. Confirms whether the corresponding files are identical.

The verified V2 repeat-run check produced identical SHA-256 hashes for all 10 generated CSV/summary output files. The separate "ground_truth.json" file was also checked and matched.

# Scope: This result verifies the V2 event-generation pipeline against fixed master inputs. It is not proof that the entire master-data and event-generation pipeline has been regenerated and compared end to end.

See "docs/reproducibility.md" for the documented reproducibility approach.

# 17. Current Verification Results

The following results were obtained during project verification.

# 17.1 Automated Tests

Test Suite| Result
Database constraint tests| 89 passed
Complete pytest suite| 187 passed

Commands used:

python -m pytest scripts/test_database_constraints.py -v
python -m pytest -q

# 17.2 Master Generator and Dataset Validation

The original master generator was executed successfully:

python src/generators/generate_data.py

It generated the expected default record counts:

Dataset| Records
Companies| 5,000
Contacts| 10,000
Campaigns| 20
Territories| 8
Products| 3
Sales reps| 16
Sales rep products| 48
Leads| 20,000
Lead campaigns| 20,000

# After regeneration, the V2 validator completed successfully:

Validation Check| Result
Overall validation status| PASS
Validation errors| 0
Validation warnings| 0
Master leads| 20,000
V2 leads| 20,000
Master/V2 lead IDs match| True
Zero-padded IDs checked| 206,061
Malformed IDs| 0
Score mismatches| 0
Evidence arithmetic mismatches| 0
Ground-truth scenarios verified| 5/5

The validation report was saved to:

data/analytics/validation_report_v2.json

The validator also reported the expected injected territory, consent and stage-history exceptions separately from validation errors.

# 17.3 Database Integrity Verification

The database verification script was run after the latest master-data generation and confirmed that all 15 original CSV/MySQL table counts matched.

Verification| Result
MySQL connection| PASS
Tables checked| 15/15
Total original CSV records| 235,863
Total MySQL records| 235,863
Record-count difference| 0
Table-count comparison| PASS

Command used:
python scripts/verify_database.py

All 15 table-level record counts matched successfully, confirming consistency between the original generated CSV dataset and the corresponding MySQL tables at the time of verification.

The verified schema contains 22 foreign-key relationships.

# 17.4 V2 Pipeline Validation

# The V2 event-generation pipeline was verified with:

Entity| Records
Leads| 20,000
Activities| 85,755
Consents| 60,000
Score rules| 10
Tasks| 19,248
Opportunities| 3,000
Opportunity evidence| 3,000
Stage-history records| 8,999
Ground-truth cases| 5

# The V2 validation run reported:

- Validation status: "PASS".
- Validation errors: "0".
- Validation warnings: "0".
- All five ground-truth scenarios verified.
- Score mismatches: "0".
- Funnel reconciliation: "True".
- Evidence arithmetic mismatches: "0".
- Expected territory exceptions: "1".
- Expected consent exception: "1".
- Expected stage-history sequence gap: "1".

The expected injected exceptions are reported separately from unexpected validation errors.

# 17.5 Anomaly Analysis

Metric| Result
Ground-truth anomalies| 5
Detected anomalies| 5
Missed anomalies| 0
Detection rate| 100%
Overall status| PASS

Interpretation: The 100% detection rate applies only to the five deliberately injected and labelled ground-truth scenarios. It should not be interpreted as general real-world anomaly-detection accuracy.

# 17.6 Business Evaluation

The verified V2 evaluation output reported:

Metric| Result
Total leads| 20,000
Qualified leads| 3,000
Not-qualified leads| 17,000
Qualification rate| 15%
Leads with opportunities| 3,000
Lead-to-opportunity conversion rate| 15%
Won opportunities| 1,977
Lost opportunities| 1,023
Lead-to-won rate| 9.88%
Win rate| 65.9%
Loss rate| 34.1%
Won revenue| ₹782,378,946.67
Total opportunity value| ₹799,365,822.01
Lost opportunity value| ₹16,986,875.34
Average won deal value| ₹395,740.49

These are results from the verified evaluation run, not guaranteed values for every future dataset generation.

# 18. AI Use Disclosure

AI tools were used as development assistance during this project, including support with code debugging, implementation suggestions, validation logic, test development and documentation.

AI-generated suggestions were reviewed and tested before being incorporated. The project owner executed the generators, validation scripts, analytics and automated tests, reviewed the results, and remains responsible for the final implementation and submitted work.

The development prompt history is maintained in "prompt_history/Development_prompts.md". AI responses are not represented as independently authored project work.

# 19. Important Implementation Notes

# 19.1 Separation of Data and Ground Truth

Ground-truth anomaly labels are maintained separately from analytical input features. This separation helps prevent anomaly labels from leaking into the detection process.

# 19.2 Scoring and Outcome Separation

Lead scoring and opportunity outcome evaluation are treated as separate processes. Outcome labels are used for evaluation rather than as independent scoring inputs.

# 19.3 Database Integrity

The MySQL schema and database constraint tests enforce key relationships and uniqueness requirements. The CSV validation process and database-level validation are separate layers; passing database tests alone does not establish that every possible CSV-level relationship has been checked.

# 19.4 V2 Staging Outputs

The V2 event-generation pipeline writes to staging outputs. These outputs are not automatically inserted into MySQL by the original database loader.

# 19.5 Transactions and Loading

The database loader uses batch insertion and transaction handling. It commits after a successful load and rolls back when an error occurs.

# 20. Limitations and Future Improvements

# The project can be extended in the following areas:

1. Expanded CSV validation: Add comprehensive checks for required fields, foreign-key references and orphan records before database loading.
2. Scoring-event verification: Continue strengthening explicit checks that post-conversion activities are excluded from score inputs wherever required by the scoring design.
3. End-to-end reproducibility: Extend repeat-run verification to include master-data generation and the complete pipeline, not only V2 event generation against fixed master inputs.
4. Pipeline integration: Add a controlled process for moving validated V2 staging outputs into the database if they are required for downstream analysis.
5. Monitoring and reporting: Provide clear reports for validation failures, anomaly detection, lead scoring and opportunity outcomes.
6. Documentation maintenance: Update the README whenever scripts, schema definitions, configuration variables or data-generation behavior change.

# Conclusion

The Lead Management System demonstrates an end-to-end synthetic lead-management workflow covering lead scoring, qualification, follow-up activities, opportunity progression, data validation, anomaly detection, database integrity, automated testing and business evaluation.

The project combines Python-based data processing, MySQL relational storage, automated testing and reproducibility checks to support an auditable and measurable lead-management process.
