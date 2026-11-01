from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import pytest


# =========================================================
# PATHS AND CONFIGURATION
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

MASTER_DATA = ROOT / "data" / "generated"
V2_DATA = ROOT / "data" / "staging" / "generated_v2"
GROUND_TRUTH_DATA = ROOT / "data" / "staging" / "ground_truth_v2"
ANALYTICS = ROOT / "data" / "analytics"

EXPECTED_COUNTS = {
    "companies": 5000,
    "contacts": 10000,
    "campaigns": 20,
    "territories": 8,
    "products": 3,
    "sales_reps": 16,
    "sales_rep_products": 48,
    "leads": 20000,
    "activities": 85755,
    "consents": 60000,
    "score_rules": 10,
    "tasks": 19248,
    "opportunities": 3000,
    "opportunity_evidence": 3000,
    "stage_history": 8999,
}

MASTER_TABLES = [
    "companies",
    "contacts",
    "campaigns",
    "territories",
    "products",
    "sales_reps",
    "sales_rep_products",
    "leads",
]

TRANSACTION_TABLES = [
    "leads",
    "activities",
    "consents",
    "score_rules",
    "tasks",
    "opportunities",
    "opportunity_evidence",
    "stage_history",
    "data_quality_issues",
]


# =========================================================
# COMMON HELPERS
# =========================================================

def load_csv(directory, name):
    path = directory / f"{name}.csv"
    assert path.exists(), f"Missing required dataset: {path}"
    return pd.read_csv(path)


def get_column(df, *names):
    for name in names:
        if name in df.columns:
            return name

    pytest.fail(
        f"None of the expected columns {names} found. "
        f"Available columns: {list(df.columns)}"
    )


def parse_dates(series):
    return pd.to_datetime(series, errors="coerce")


def normalized(series):
    return series.astype("string").str.strip().str.upper()


def assert_unique_non_null(df, column):
    assert column in df.columns
    assert df[column].notna().all(), f"{column} contains NULL values"
    assert df[column].is_unique, f"{column} contains duplicates"


def assert_fk(child, child_column, parent, parent_column):
    assert child[child_column].notna().all(), (
        f"{child_column} contains NULL foreign keys"
    )

    invalid = ~child[child_column].isin(parent[parent_column])

    assert not invalid.any(), (
        f"{child_column} contains {int(invalid.sum())} invalid references"
    )


def find_json_file(candidates):
    for path in candidates:
        if path.exists():
            return path
    return None


# =========================================================
# DATASET FIXTURES
# =========================================================

@pytest.fixture(scope="module")
def datasets():
    data = {}

    for name in MASTER_TABLES:
        data[name] = load_csv(MASTER_DATA, name)

    for name in TRANSACTION_TABLES:
        data[name] = load_csv(V2_DATA, name)

    return data


@pytest.fixture(scope="module")
def ground_truth():
    path = find_json_file([
        GROUND_TRUTH_DATA / "ground_truth_cases.json",
        GROUND_TRUTH_DATA / "ground_truth.json",
        GROUND_TRUTH_DATA / "ground_truth_v2.json",
    ])

    assert path is not None, (
        "Ground-truth JSON file is missing. "
        "Run the V2 event generator first."
    )

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# =========================================================
# 1. DATASET COMPLETENESS
# =========================================================

def test_all_required_datasets_exist(datasets):
    expected = set(MASTER_TABLES + TRANSACTION_TABLES)
    assert expected.issubset(datasets.keys())


@pytest.mark.parametrize(
    "table,expected_count",
    EXPECTED_COUNTS.items()
)
def test_expected_dataset_row_counts(datasets, table, expected_count):
    assert len(datasets[table]) == expected_count, (
        f"{table}: expected {expected_count}, "
        f"found {len(datasets[table])}"
    )


def test_no_empty_required_datasets(datasets):
    for name, df in datasets.items():
        assert len(df) > 0, f"{name} is empty"


# =========================================================
# 2. PRIMARY KEY AND COMPOSITE KEY UNIQUENESS
# =========================================================

PRIMARY_KEYS = [
    ("companies", "company_id"),
    ("contacts", "contact_id"),
    ("campaigns", "campaign_id"),
    ("territories", "territory_id"),
    ("products", "product_id"),
    ("sales_reps", "sales_rep_id"),
    ("leads", "lead_id"),
    ("activities", "activity_id"),
    ("consents", "consent_id"),
    ("score_rules", "rule_id"),
    ("tasks", "task_id"),
    ("opportunities", "opportunity_id"),
    ("opportunity_evidence", "evidence_id"),
]


@pytest.mark.parametrize("table,column", PRIMARY_KEYS)
def test_primary_keys_are_unique(datasets, table, column):
    assert_unique_non_null(datasets[table], column)


def test_sales_rep_products_composite_key_is_unique(datasets):
    df = datasets["sales_rep_products"]
    columns = ["sales_rep_id", "product_id"]

    assert df[columns].notna().all().all()
    assert not df.duplicated(subset=columns).any()


def test_stage_history_natural_key_is_unique(datasets):
    df = datasets["stage_history"]

    columns = [
        "opportunity_id",
        "new_stage",
        "changed_at",
    ]

    for column in columns:
        assert column in df.columns

    assert df[columns].notna().all().all()
    assert not df.duplicated(subset=columns).any()


# =========================================================
# 3. STRICT ID FORMAT VALIDATION
# =========================================================

ID_PATTERNS = {
    "companies": ("company_id", r"^CO-\d{6}$"),
    "contacts": ("contact_id", r"^CON-\d{6}$"),
    "territories": ("territory_id", r"^TER-\d{6}$"),
    "products": ("product_id", r"^PROD-\d{6}$"),
    "sales_reps": ("sales_rep_id", r"^REP-\d{6}$"),
    "leads": ("lead_id", r"^LEAD-2026-\d{6}$"),
    "opportunities": ("opportunity_id", r"^OPP-2026-\d{6}$"),
}


@pytest.mark.parametrize("table,definition", ID_PATTERNS.items())
def test_entity_id_formats(datasets, table, definition):
    column, pattern = definition
    values = datasets[table][column].astype(str)

    assert values.str.fullmatch(pattern).all(), (
        f"Invalid ID format in {table}.{column}"
    )


def test_activity_ids_are_valid(datasets):
    activities = datasets["activities"]

    pattern = (
        r"^ACT-LEAD-2026-\d{6}-(?:\d{3}|EX001|EX002)$"
    )

    values = activities["activity_id"].astype(str)

    assert values.str.fullmatch(pattern).all()


def test_activity_sequence_is_per_lead(datasets):
    activities = datasets["activities"].copy()

    normal = activities[
        ~activities["activity_id"].astype(str).str.endswith(
            ("EX001", "EX002")
        )
    ].copy()

    extracted = normal["activity_id"].astype(str).str.extract(
        r"^ACT-(LEAD-2026-\d{6})-(\d{3})$"
    )

    assert extracted.notna().all().all()

    normal["_id_lead"] = extracted[0]
    normal["_sequence"] = extracted[1].astype(int)

    assert (
        normal["_id_lead"] == normal["lead_id"]
    ).all()

    for lead_id, group in normal.groupby("lead_id"):
        sequence = sorted(group["_sequence"].tolist())

        assert sequence == list(range(1, len(sequence) + 1)), (
            f"Activity sequence for {lead_id} is not continuous"
        )


def test_task_ids_are_valid(datasets):
    tasks = datasets["tasks"]

    pattern = r"^TASK-LEAD-2026-\d{6}-\d{3,}$"

    values = tasks["task_id"].astype(str)

    assert values.str.fullmatch(pattern).all()


# =========================================================
# 4. FOREIGN KEY INTEGRITY
# =========================================================

def test_lead_foreign_keys(datasets):
    leads = datasets["leads"]

    assert_fk(
        leads, "company_id",
        datasets["companies"], "company_id"
    )

    assert_fk(
        leads, "contact_id",
        datasets["contacts"], "contact_id"
    )

    assert_fk(
        leads, "territory_id",
        datasets["territories"], "territory_id"
    )


def test_contact_foreign_keys(datasets):
    contacts = datasets["contacts"]

    assert_fk(
        contacts,
        "company_id",
        datasets["companies"],
        "company_id"
    )


def test_activity_foreign_keys(datasets):
    activities = datasets["activities"]

    assert_fk(
        activities, "lead_id",
        datasets["leads"], "lead_id"
    )

    assert_fk(
        activities, "contact_id",
        datasets["contacts"], "contact_id"
    )

    campaign_column = get_column(activities, "campaign_id")

    non_null_campaigns = activities[
        activities[campaign_column].notna()
    ]

    assert_fk(
        non_null_campaigns,
        campaign_column,
        datasets["campaigns"],
        "campaign_id"
    )


def test_consent_foreign_keys(datasets):
    assert_fk(
        datasets["consents"], "lead_id",
        datasets["leads"], "lead_id"
    )


def test_opportunity_foreign_keys(datasets):
    assert_fk(
        datasets["opportunities"], "lead_id",
        datasets["leads"], "lead_id"
    )


def test_opportunity_evidence_foreign_keys(datasets):
    evidence = datasets["opportunity_evidence"]

    assert_fk(
        evidence,
        "opportunity_id",
        datasets["opportunities"],
        "opportunity_id"
    )

    assert_fk(
        evidence,
        "lead_id",
        datasets["leads"],
        "lead_id"
    )


def test_task_foreign_keys(datasets):
    assert_fk(
        datasets["tasks"], "lead_id",
        datasets["leads"], "lead_id"
    )


def test_stage_history_foreign_keys(datasets):
    assert_fk(
        datasets["stage_history"], "opportunity_id",
        datasets["opportunities"], "opportunity_id"
    )


def test_sales_rep_product_foreign_keys(datasets):
    bridge = datasets["sales_rep_products"]

    assert_fk(
        bridge, "sales_rep_id",
        datasets["sales_reps"],
        "sales_rep_id"
    )

    assert_fk(
        bridge, "product_id",
        datasets["products"],
        "product_id"
    )


# =========================================================
# 5. LEAD SCORING AND QUALIFICATION VALIDATION
# =========================================================

SCORE_COLUMNS = [
    "fit_score",
    "intent_score",
    "engagement_score",
    "total_score",
]


def test_lead_score_columns_exist(datasets):
    leads = datasets["leads"]

    for column in SCORE_COLUMNS:
        assert column in leads.columns


def test_lead_scores_are_numeric_and_finite(datasets):
    leads = datasets["leads"]

    for column in SCORE_COLUMNS:
        values = pd.to_numeric(leads[column], errors="coerce")

        assert values.notna().all(), (
            f"{column} contains non-numeric values"
        )

        assert np.isfinite(values).all(), (
            f"{column} contains infinity"
        )


def test_lead_scores_are_within_range(datasets):
    leads = datasets["leads"]

    for column in SCORE_COLUMNS:
        values = pd.to_numeric(leads[column])

        assert values.between(0, 100).all()


def test_total_score_formula(datasets):
    leads = datasets["leads"]

    expected = []

    for row in leads.itertuples(index=False):
        fit = float(getattr(row, "fit_score"))
        intent = float(getattr(row, "intent_score"))
        engagement = float(getattr(row, "engagement_score"))

        total = round(
            fit * 0.35
            + intent * 0.35
            + engagement * 0.30,
            2
        )

        expected.append(total)

    actual = pd.to_numeric(
        leads["total_score"]
    ).to_numpy(dtype=float)

    assert np.array_equal(
        actual,
        np.asarray(expected, dtype=float)
    )


def test_qualification_flag_exists_and_is_valid(datasets):
    leads = datasets["leads"]

    assert "is_qualified" in leads.columns

    flags = pd.to_numeric(
        leads["is_qualified"], errors="coerce"
    )

    assert flags.notna().all()
    assert flags.isin([0, 1]).all()


def test_exactly_3000_leads_are_qualified(datasets):
    leads = datasets["leads"]

    flags = pd.to_numeric(leads["is_qualified"])

    assert int((flags == 1).sum()) == 3000
    assert int((flags == 0).sum()) == 17000


def test_qualified_leads_are_highest_ranked(datasets):
    leads = datasets["leads"].copy()

    leads["total_score"] = pd.to_numeric(
        leads["total_score"]
    )

    leads["is_qualified"] = pd.to_numeric(
        leads["is_qualified"]
    )

    expected = (
        leads.sort_values(
            by=["total_score", "lead_id"],
            ascending=[False, True],
            kind="mergesort"
        )
        .head(3000)
    )

    actual = leads[
        leads["is_qualified"] == 1
    ]

    assert set(actual["lead_id"]) == set(expected["lead_id"])


def test_lead_status_counts_reconcile(datasets):
    leads = datasets["leads"]
    opportunities = datasets["opportunities"]

    statuses = normalized(leads["lead_status"])
    stages = normalized(opportunities["opportunity_stage"])

    won_count = int((stages == "WON").sum())
    lost_count = int((stages == "LOST").sum())

    assert (statuses == "NEW").sum() == 17000
    assert (statuses == "QUALIFIED").sum() == lost_count
    assert (statuses == "CONVERTED").sum() == won_count

    assert statuses.isin(
        ["NEW", "QUALIFIED", "CONVERTED"]
    ).all()

    assert statuses.value_counts().sum() == len(leads)
# =========================================================
# 6. OPPORTUNITY VALIDATION
# =========================================================

def test_one_opportunity_per_lead(datasets):
    assert datasets["opportunities"]["lead_id"].is_unique


def test_opportunity_stages_are_valid(datasets):
    opportunities = datasets["opportunities"]

    stage_column = get_column(
        opportunities, "opportunity_stage", "stage"
    )

    valid_stages = {"WON", "LOST"}

    assert set(
        normalized(opportunities[stage_column]).dropna()
    ).issubset(valid_stages)


def test_opportunity_amounts_are_positive(datasets):
    opportunities = datasets["opportunities"]

    amount_column = get_column(
        opportunities, "amount", "opportunity_amount"
    )

    amounts = pd.to_numeric(
        opportunities[amount_column], errors="coerce"
    )

    assert amounts.notna().all()
    assert np.isfinite(amounts).all()
    assert (amounts > 0).all()


def test_opportunity_outcome_counts_reconcile(datasets):
    opportunities = datasets["opportunities"]

    stage_column = get_column(
        opportunities, "opportunity_stage", "stage"
    )

    stages = normalized(opportunities[stage_column])

    assert (stages == "WON").sum() > 0
    assert (stages == "LOST").sum() > 0

    assert stages.isin(["WON", "LOST"]).all()

    assert (
        (stages == "WON").sum()
        + (stages == "LOST").sum()
        == 3000
    )


def test_opportunities_match_qualified_leads(datasets):
    leads = datasets["leads"]
    opportunities = datasets["opportunities"]

    qualified_ids = set(
        leads.loc[
            pd.to_numeric(leads["is_qualified"]) == 1,
            "lead_id"
        ]
    )

    opportunity_ids = set(opportunities["lead_id"])

    assert len(opportunities) == 3000
    assert opportunity_ids == qualified_ids


def test_won_and_lost_outcomes_match_lead_status(datasets):
    leads = datasets["leads"]
    opportunities = datasets["opportunities"]

    stages = normalized(opportunities["opportunity_stage"])

    won_ids = set(
        opportunities.loc[stages == "WON", "lead_id"]
    )

    lost_ids = set(
        opportunities.loc[stages == "LOST", "lead_id"]
    )

    converted_ids = set(
        leads.loc[
            normalized(leads["lead_status"]) == "CONVERTED",
            "lead_id"
        ]
    )

    qualified_status_ids = set(
        leads.loc[
            normalized(leads["lead_status"]) == "QUALIFIED",
            "lead_id"
        ]
    )

    assert won_ids == converted_ids
    assert lost_ids == qualified_status_ids

    assert len(won_ids) + len(lost_ids) == 3000


def test_won_revenue_is_reconcilable(datasets):
    opportunities = datasets["opportunities"]

    stage_column = get_column(
        opportunities, "opportunity_stage", "stage"
    )

    amount_column = get_column(
        opportunities, "amount", "opportunity_amount"
    )

    won = opportunities[
        normalized(opportunities[stage_column]) == "WON"
    ]

    amounts = pd.to_numeric(
        won[amount_column], errors="coerce"
    )

    assert amounts.notna().all()
    assert amounts.sum() > 0


def test_opportunity_evidence_integrity(datasets):
    evidence = datasets["opportunity_evidence"]
    opportunities = datasets["opportunities"]
    leads = datasets["leads"]

    assert len(evidence) == 3000

    assert_unique_non_null(evidence, "evidence_id")

    assert evidence["opportunity_id"].is_unique
    assert evidence["lead_id"].is_unique

    assert_fk(
        evidence,
        "opportunity_id",
        opportunities,
        "opportunity_id"
    )

    assert_fk(
        evidence,
        "lead_id",
        leads,
        "lead_id"
    )


def test_outcomes_match_independent_evidence_rule(datasets):
    opportunities = datasets["opportunities"]
    evidence = datasets["opportunity_evidence"]

    merged = opportunities.merge(
        evidence,
        on=["opportunity_id", "lead_id"],
        how="inner",
        validate="one_to_one"
    )

    assert len(merged) == 3000

    revenue = pd.to_numeric(
        merged["annual_revenue_inr"], errors="coerce"
    )

    product_price = pd.to_numeric(
        merged["product_base_price_inr"], errors="coerce"
    )

    multiple = pd.to_numeric(
        merged["revenue_multiple_required"], errors="coerce"
    )

    assert revenue.notna().all()
    assert product_price.notna().all()
    assert multiple.notna().all()

    expected = np.where(
        revenue >= product_price * multiple,
        "WON",
        "LOST"
    )

    actual = normalized(
        merged["opportunity_stage"]
    ).to_numpy()

    assert np.array_equal(actual, expected)

    assert normalized(merged["rule_id"]).eq(
        "OUTCOME-001"
    ).all()

    expected_evidence = np.where(
        expected == "WON",
        "PASS",
        "FAIL"
    )

    actual_evidence = normalized(
        merged["evidence_result"]
    ).to_numpy()

    assert np.array_equal(
        actual_evidence,
        expected_evidence
    )


# =========================================================
# 7. CONSENT VALIDATION
# =========================================================

def test_consent_statuses_are_valid(datasets):
    consents = datasets["consents"]

    column = get_column(
        consents, "consent_status", "status"
    )

    valid = {"GRANTED", "REVOKED", "PENDING"}

    assert set(
        normalized(consents[column]).dropna()
    ).issubset(valid)


def test_consent_effective_dates_are_valid(datasets):
    consents = datasets["consents"]

    start_column = get_column(
        consents, "effective_from"
    )

    end_column = get_column(
        consents, "effective_to"
    )

    starts = parse_dates(consents[start_column])
    ends = parse_dates(consents[end_column])

    assert starts.notna().all()

    invalid = ends.notna() & (ends < starts)

    assert not invalid.any()


def test_email_activities_respect_consent_at_event_time(datasets):
    activities = datasets["activities"]
    consents = datasets["consents"]

    activity_type = normalized(
        activities["activity_type"]
    )

    email_events = activities[
        activity_type.isin([
            "EMAIL_SENT",
            "EMAIL_OPENED",
            "EMAIL_CLICKED",
        ])
    ].copy()

    if email_events.empty:
        pytest.skip("No email activities found")

    activity_time_column = get_column(
        email_events, "activity_timestamp", "activity_time"
    )

    consent_type_column = get_column(
        consents, "consent_type"
    )

    consent_status_column = get_column(
        consents, "consent_status", "status"
    )

    email_consents = consents[
        normalized(consents[consent_type_column])
        == "EMAIL_MARKETING"
    ].copy()

    start_column = get_column(
        email_consents, "effective_from"
    )

    end_column = get_column(
        email_consents, "effective_to"
    )

    email_events["_event_time"] = parse_dates(
        email_events[activity_time_column]
    )

    merged = email_events.merge(
        email_consents[
            [
                "lead_id",
                consent_status_column,
                start_column,
                end_column,
            ]
        ],
        on="lead_id",
        how="left"
    )

    merged["_start"] = parse_dates(merged[start_column])
    merged["_end"] = parse_dates(merged[end_column])

    merged["_valid_consent"] = (
        normalized(merged[consent_status_column]).isin(
            ["GRANTED", "REVOKED"]
        )
        & merged["_start"].notna()
        & (merged["_event_time"] >= merged["_start"])
        & (
            merged["_end"].isna()
            | (merged["_event_time"] < merged["_end"])
        )
    )

    valid_by_activity = merged.groupby(
        "activity_id"
    )["_valid_consent"].any()

    violation_count = int((~valid_by_activity).sum())

    assert violation_count == 1, (
        "Expected exactly one intentional email-consent violation "
        f"(EX-001); found {violation_count}"
    )


# =========================================================
# 8. ACTIVITY TIMING AND LIFECYCLE VALIDATION
# =========================================================

def test_activity_timestamps_are_valid(datasets):
    activities = datasets["activities"]

    time_column = get_column(
        activities, "activity_timestamp", "activity_time"
    )

    timestamps = parse_dates(activities[time_column])

    assert timestamps.notna().all()


def test_no_activity_occurs_before_lead_creation(datasets):
    activities = datasets["activities"]
    leads = datasets["leads"]

    activity_time_column = get_column(
        activities, "activity_timestamp", "activity_time"
    )

    lead_created_column = get_column(
        leads, "created_at", "created_date", "lead_created_at"
    )

    merged = activities.merge(
        leads[["lead_id", lead_created_column]],
        on="lead_id",
        how="left"
    )

    event_times = parse_dates(
        merged[activity_time_column]
    )

    created_times = parse_dates(
        merged[lead_created_column]
    )

    assert (event_times >= created_times).all()


def test_post_conversion_activity_exception_is_present(datasets):
    activities = datasets["activities"]
    opportunities = datasets["opportunities"]

    stage_column = get_column(
        opportunities, "opportunity_stage", "stage"
    )

    close_column = get_column(
        opportunities, "closed_at", "close_date", "close_timestamp"
    )

    activity_time_column = get_column(
        activities, "activity_timestamp", "activity_time"
    )

    won = opportunities[
        normalized(opportunities[stage_column]) == "WON"
    ].copy()

    won["_closed"] = parse_dates(won[close_column])

    merged = activities.merge(
        won[["lead_id", "_closed"]],
        on="lead_id",
        how="inner"
    )

    merged["_activity_time"] = parse_dates(
        merged[activity_time_column]
    )

    post_conversion = merged[
        merged["_activity_time"] > merged["_closed"]
    ]

    assert not post_conversion.empty


# =========================================================
# 9. TERRITORY VALIDATION
# =========================================================

def test_wrong_territory_exception_is_preserved(datasets):
    leads = datasets["leads"]
    reps = datasets["sales_reps"]

    lead = leads[
        leads["lead_id"] == "LEAD-2026-000101"
    ]

    assert len(lead) == 1

    assigned_rep_column = get_column(
        leads, "assigned_rep_id", "sales_rep_id"
    )

    rep = reps[
        reps["sales_rep_id"] == lead.iloc[0][assigned_rep_column]
    ]

    assert len(rep) == 1

    assert (
        lead.iloc[0]["territory_id"]
        != rep.iloc[0]["territory_id"]
    )
# =========================================================
# 10. TASK VALIDATION
# =========================================================

def test_task_due_dates_are_valid(datasets):
    tasks = datasets["tasks"]

    due_column = get_column(
        tasks, "due_date", "due_at", "due_timestamp"
    )

    due_dates = parse_dates(tasks[due_column])

    assert due_dates.notna().all()


def test_task_lead_relationships_are_valid(datasets):
    assert_fk(
        datasets["tasks"],
        "lead_id",
        datasets["leads"],
        "lead_id"
    )


# =========================================================
# 11. STAGE HISTORY VALIDATION
# =========================================================

def test_stage_history_dates_are_valid(datasets):
    history = datasets["stage_history"]

    time_column = get_column(
        history,
        "changed_at",
        "stage_timestamp",
        "created_at",
        "event_timestamp",
    )

    timestamps = parse_dates(history[time_column])

    assert timestamps.notna().all()


def test_stage_history_gap_exception_is_preserved(datasets):
    history = datasets["stage_history"]

    exception = history[
        history["opportunity_id"] == "OPP-2026-000003"
    ]

    stages = set(
        normalized(exception["new_stage"]).dropna()
    )

    assert "QUALIFICATION" in stages
    assert "NEEDS_ANALYSIS" not in stages


# =========================================================
# 12. DUPLICATE OPPORTUNITY AUDIT
# =========================================================

def test_duplicate_opportunity_is_audited(datasets):
    issues = datasets["data_quality_issues"]

    issue_id_column = get_column(
        issues, "issue_id"
    )

    status_column = get_column(
        issues, "issue_status", "status"
    )

    type_column = get_column(
        issues, "issue_type", "type"
    )

    record = issues[
        issues[issue_id_column] == "EX-004"
    ]

    assert len(record) == 1

    assert normalized(
        record[status_column]
    ).iloc[0] == "REJECTED"

    assert normalized(
        record[type_column]
    ).iloc[0] == "DUPLICATE_OPPORTUNITY"


# =========================================================
# 13. GROUND TRUTH AND ANOMALY VALIDATION
# =========================================================

def test_ground_truth_has_five_cases(ground_truth):
    assert isinstance(ground_truth, list)
    assert len(ground_truth) == 5


def test_ground_truth_contains_all_required_exceptions(ground_truth):
    assert isinstance(ground_truth, list)

    issue_ids = {
        str(item.get("issue_id", "")).upper()
        for item in ground_truth
        if isinstance(item, dict)
    }

    assert issue_ids == {
        "EX-001",
        "EX-002",
        "EX-003",
        "EX-004",
        "EX-005",
    }


def test_ground_truth_is_not_inside_lead_features(datasets):
    leads = datasets["leads"]

    forbidden_columns = {
        "ground_truth",
        "ground_truth_label",
        "is_injected_anomaly",
        "anomaly_type",
        "exception_id",
        "injected_exception",
    }

    actual_columns = {
        column.lower() for column in leads.columns
    }

    assert not (
        forbidden_columns & actual_columns
    )


def test_all_anomalies_are_detected():
    report_path = find_json_file([
        ANALYTICS / "anomaly_report_v2.json",
        ANALYTICS / "anomaly_report.json",
    ])

    assert report_path is not None

    with open(report_path, "r", encoding="utf-8") as file:
        report = json.load(file)

    summary = report.get("summary", {})

    assert summary.get("ground_truth_anomalies") == 5
    assert summary.get("detected_in_data") == 5

    assert float(
        summary.get("detection_rate_percent", 0)
    ) == 100.0

    results = report.get("results", [])

    assert len(results) == 5

    for result in results:
        assert result.get("detected_in_data") is True
        assert result.get("evidence")


# =========================================================
# 14. DATA QUALITY VALIDATION
# =========================================================

def test_no_duplicate_opportunity_leads(datasets):
    opportunities = datasets["opportunities"]

    assert not opportunities["lead_id"].duplicated().any()


def test_no_null_required_lead_fields(datasets):
    leads = datasets["leads"]

    required = [
        "lead_id",
        "company_id",
        "contact_id",
        "territory_id",
        "fit_score",
        "intent_score",
        "engagement_score",
        "total_score",
    ]

    for column in required:
        assert leads[column].notna().all(), (
            f"Required lead field {column} contains NULL"
        )


# =========================================================
# 15. REPRODUCIBILITY VALIDATION
# =========================================================

def calculate_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def test_reproducibility_checksum_files_exist():
    before = ANALYTICS / "checksums_before.csv"
    after = ANALYTICS / "checksums_after.csv"

    assert before.exists()
    assert after.exists()


def test_reproducibility_checksums_match():
    before = pd.read_csv(
        ANALYTICS / "checksums_before.csv"
    )

    after = pd.read_csv(
        ANALYTICS / "checksums_after.csv"
    )

    assert {"Path", "Hash"}.issubset(before.columns)
    assert {"Path", "Hash"}.issubset(after.columns)

    before = before.sort_values(
        "Path"
    ).reset_index(drop=True)

    after = after.sort_values(
        "Path"
    ).reset_index(drop=True)

    pd.testing.assert_frame_equal(
        before[["Path", "Hash"]],
        after[["Path", "Hash"]],
        check_dtype=False
    )


# =========================================================
# 16. VALIDATION REPORT
# =========================================================

def test_validation_report_passes():
    report_path = ANALYTICS / "validation_report_v2.json"

    assert report_path.exists()

    with open(report_path, "r", encoding="utf-8") as file:
        report = json.load(file)

    assert str(
        report.get("status", "")
    ).upper() == "PASS"

    assert report.get("errors") == []


# =========================================================
# 17. STALE LEAD CLASSIFICATION
# =========================================================

STALE_THRESHOLD_DAYS = 30
AS_OF_DATE = pd.Timestamp("2026-10-30 12:00:00")


def test_stale_lead_columns_exist(datasets):
    leads = datasets["leads"]

    required = [
        "last_activity_at",
        "stale_status",
        "is_stale",
        "stale_since",
    ]

    for column in required:
        assert column in leads.columns


def test_stale_lead_status_values_are_valid(datasets):
    leads = datasets["leads"]

    valid_statuses = {"STALE", "OPEN", "CLOSED"}

    assert set(
        normalized(leads["stale_status"]).dropna()
    ).issubset(valid_statuses)


def test_stale_leads_have_correct_flag(datasets):
    leads = datasets["leads"]

    stale = leads[
        normalized(leads["stale_status"]) == "STALE"
    ]

    assert len(stale) > 0
    assert (pd.to_numeric(stale["is_stale"]) == 1).all()


def test_open_leads_are_not_stale(datasets):
    leads = datasets["leads"]

    open_leads = leads[
        normalized(leads["stale_status"]) == "OPEN"
    ]

    assert (pd.to_numeric(open_leads["is_stale"]) == 0).all()


def test_closed_leads_are_not_stale(datasets):
    leads = datasets["leads"]

    closed = leads[
        normalized(leads["stale_status"]) == "CLOSED"
    ]

    assert len(closed) == 3000
    assert (pd.to_numeric(closed["is_stale"]) == 0).all()


def test_stale_threshold_is_30_days(datasets):
    leads = datasets["leads"]

    stale = leads[
        normalized(leads["stale_status"]) == "STALE"
    ].copy()

    last_activity = parse_dates(
        stale["last_activity_at"]
    )

    inactivity_days = (
        AS_OF_DATE - last_activity
    ).dt.total_seconds() / 86400

    assert last_activity.notna().all()
    assert (inactivity_days >= STALE_THRESHOLD_DAYS).all()


def test_open_leads_have_activity_within_30_days(datasets):
    leads = datasets["leads"]

    open_leads = leads[
        normalized(leads["stale_status"]) == "OPEN"
    ]

    last_activity = parse_dates(
        open_leads["last_activity_at"]
    )

    inactivity_days = (
        AS_OF_DATE - last_activity
    ).dt.total_seconds() / 86400

    assert last_activity.notna().all()
    assert (inactivity_days < STALE_THRESHOLD_DAYS).all()


def test_stale_since_date_is_correct(datasets):
    leads = datasets["leads"]

    stale = leads[
        normalized(leads["stale_status"]) == "STALE"
    ].copy()

    last_activity = parse_dates(
        stale["last_activity_at"]
    )

    stale_since = parse_dates(
        stale["stale_since"]
    )

    expected = last_activity + pd.Timedelta(days=30)

    assert stale_since.notna().all()
    assert (stale_since == expected).all()


def test_stale_classification_counts_reconcile(datasets):
    leads = datasets["leads"]

    counts = normalized(
        leads["stale_status"]
    ).value_counts()

    assert counts["STALE"] == 15667
    assert counts["OPEN"] == 1333
    assert counts["CLOSED"] == 3000

    assert counts.sum() == len(leads)