from pathlib import Path
import pandas as pd
import json


# --------------------------------------------------
# 1. PATH CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

SOURCE_DATA_DIR = ROOT / "data" / "generated"
DATA_DIR = ROOT / "data" / "staging" / "generated_v2"

GROUND_TRUTH_FILE = (
    ROOT / "data" / "staging" / "ground_truth_v2" / "ground_truth.json"
)

OUTPUT_DIR = ROOT / "data" / "analytics"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. CSV LOADER AND NORMALIZATION HELPERS
# --------------------------------------------------

def load_csv(filename, directory=DATA_DIR):

    path = directory / f"{filename}.csv"

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return pd.read_csv(path, dtype="string")


def normalize_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def normalize_id(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_column(df, column):

    if column not in df.columns:
        raise ValueError(
            f"Required column '{column}' is missing."
        )

    return df[column].map(normalize_id)


def parse_dates(df, columns):

    for column in columns:

        if column not in df.columns:
            raise ValueError(
                f"Required date column '{column}' is missing."
            )

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )


def first_value(row, column, default=""):
    if column not in row.index or pd.isna(row[column]):
        return default
    return str(row[column]).strip()


# --------------------------------------------------
# 3. LOAD DATA
# --------------------------------------------------

def analyze_anomalies():

    activities = load_csv("activities")
    consents = load_csv("consents")
    leads = load_csv("leads")
    opportunities = load_csv("opportunities")
    stage_history = load_csv("stage_history")
    data_quality_issues = load_csv("data_quality_issues")

    sales_reps = load_csv(
        "sales_reps",
        SOURCE_DATA_DIR
    )

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {GROUND_TRUTH_FILE}"
        )

    with open(
        GROUND_TRUTH_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        ground_truth = json.load(file)

    if not isinstance(ground_truth, list):
        raise ValueError(
            "Ground truth must contain a list of anomaly records."
        )

    # --------------------------------------------------
    # 4. VALIDATE REQUIRED COLUMNS
    # --------------------------------------------------

    required_columns = {
        "activities": [
            "activity_id",
            "lead_id",
            "activity_type",
            "activity_timestamp"
        ],
        "consents": [
            "lead_id",
            "consent_status",
            "consent_type",
            "effective_to"
        ],
        "leads": [
            "lead_id",
            "assigned_rep_id",
            "territory_id"
        ],
        "opportunities": [
            "opportunity_id",
            "lead_id",
            "opportunity_stage",
            "closed_at"
        ],
        "stage_history": [
            "lead_id",
            "opportunity_id",
            "new_stage",
            "changed_at"
        ],
        "sales_reps": [
            "sales_rep_id",
            "territory_id"
        ],
        "data_quality_issues": [
            "issue_id",
            "issue_type",
            "lead_id",
            "issue_status",
            "existing_opportunity_id",
            "attempted_action"
        ]
    }

    datasets = {
        "activities": activities,
        "consents": consents,
        "leads": leads,
        "opportunities": opportunities,
        "stage_history": stage_history,
        "sales_reps": sales_reps,
        "data_quality_issues": data_quality_issues
    }

    for dataset_name, columns in required_columns.items():

        df = datasets[dataset_name]

        for column in columns:

            if column not in df.columns:
                raise ValueError(
                    f"{dataset_name}.csv is missing "
                    f"required column: {column}"
                )

    # --------------------------------------------------
    # 5. NORMALIZE IDENTIFIERS AND TEXT
    # --------------------------------------------------

    id_columns = {
        "activities": ["activity_id", "lead_id"],
        "consents": ["lead_id"],
        "leads": [
            "lead_id",
            "assigned_rep_id",
            "territory_id"
        ],
        "opportunities": [
            "opportunity_id",
            "lead_id"
        ],
        "stage_history": [
            "lead_id",
            "opportunity_id"
        ],
        "sales_reps": [
            "sales_rep_id",
            "territory_id"
        ],
        "data_quality_issues": [
            "issue_id",
            "lead_id",
            "existing_opportunity_id"
        ]
    }

    for dataset_name, columns in id_columns.items():

        df = datasets[dataset_name]

        for column in columns:
            df[column] = df[column].map(normalize_id)

    text_columns = {
        "activities": ["activity_type"],
        "consents": [
            "consent_status",
            "consent_type"
        ],
        "opportunities": ["opportunity_stage"],
        "stage_history": ["new_stage"],
        "data_quality_issues": [
            "issue_type",
            "issue_status",
            "attempted_action"
        ]
    }

    for dataset_name, columns in text_columns.items():

        df = datasets[dataset_name]

        for column in columns:
            df[column] = df[column].map(normalize_text)

    # --------------------------------------------------
    # 6. DATE CONVERSION
    # --------------------------------------------------

    parse_dates(
        activities,
        ["activity_timestamp"]
    )

    parse_dates(
        consents,
        ["effective_to"]
    )

    parse_dates(
        opportunities,
        ["closed_at"]
    )

    parse_dates(
        stage_history,
        ["changed_at"]
    )

    results = []

    # --------------------------------------------------
    # 7. ANALYZE EACH GROUND-TRUTH ANOMALY
    # --------------------------------------------------

    for anomaly in ground_truth:

        issue_id = normalize_id(anomaly.get("issue_id"))
        issue_type = normalize_text(anomaly.get("issue_type"))
        lead_id = normalize_id(anomaly.get("lead_id"))

        if not issue_id or not issue_type or not lead_id:

            raise ValueError(
                "Ground-truth record is missing "
                "issue_id, issue_type or lead_id."
            )

        detected = False
        evidence = ""

        lead_activities = activities[
            activities["lead_id"] == lead_id
        ]

        lead_consents = consents[
            consents["lead_id"] == lead_id
        ]

        lead_opportunities = opportunities[
            opportunities["lead_id"] == lead_id
        ]

        # --------------------------------------------------
        # EX-001: CONTACT AFTER CONSENT REVOCATION
        # --------------------------------------------------

        if issue_type == "OPTED_OUT_CONTACTED":

            contact_consent_map = {
                "EMAIL_MARKETING": [
                    "EMAIL",
                    "EMAIL_SENT",
                    "EMAIL_OPENED",
                    "EMAIL_CLICKED"
                ],
                "PHONE_MARKETING": [
                    "CALL",
                    "CALL_MADE",
                    "PHONE",
                    "PHONE_CALL",
                    "SMS",
                    "SMS_SENT"
                ]
            }

            revoked = lead_consents[
                lead_consents["consent_status"] == "REVOKED"
            ]

            evidence_messages = []

            for _, consent in revoked.iterrows():

                consent_type = consent["consent_type"]

                valid_contact_types = contact_consent_map.get(
                    consent_type,
                    []
                )

                if not valid_contact_types:
                    continue

                if pd.isna(consent["effective_to"]):

                    evidence_messages.append(
                        f"{consent_type} has no valid "
                        "effective_to revocation timestamp."
                    )

                    continue

                post_revocation = lead_activities[
                    (
                        lead_activities["activity_timestamp"]
                        > consent["effective_to"]
                    )
                    &
                    (
                        lead_activities["activity_type"].isin(
                            valid_contact_types
                        )
                    )
                ].sort_values("activity_timestamp")

                if not post_revocation.empty:

                    activity = post_revocation.iloc[0]

                    detected = True

                    evidence = (
                        f"{activity['activity_type']} "
                        f"({activity['activity_id']}) occurred at "
                        f"{activity['activity_timestamp']} after "
                        f"{consent_type} revocation at "
                        f"{consent['effective_to']}."
                    )

                    break

            if not detected and not evidence:

                evidence = (
                    "No matching marketing contact activity "
                    "after the recorded revocation timestamp."
                )

        # --------------------------------------------------
        # EX-002: ACTIVITY AFTER CONVERSION
        # --------------------------------------------------

        elif issue_type == "POST_CONVERSION_ACTIVITY":

            won_opportunities = lead_opportunities[
                lead_opportunities["opportunity_stage"] == "WON"
            ]

            expected_activity_id = normalize_id(
                anomaly.get("activity_id")
            )

            for _, opportunity in won_opportunities.iterrows():

                if pd.isna(opportunity["closed_at"]):
                    continue

                post_conversion = lead_activities[
                    lead_activities["activity_timestamp"]
                    > opportunity["closed_at"]
                ]

                if expected_activity_id:

                    post_conversion = post_conversion[
                        post_conversion["activity_id"]
                        == expected_activity_id
                    ]

                post_conversion = post_conversion.sort_values(
                    "activity_timestamp"
                )

                if not post_conversion.empty:

                    activity = post_conversion.iloc[0]

                    detected = True

                    evidence = (
                        f"Activity {activity['activity_id']} "
                        f"({activity['activity_type']}) occurred at "
                        f"{activity['activity_timestamp']} after "
                        f"opportunity "
                        f"{opportunity['opportunity_id']} "
                        f"was closed at {opportunity['closed_at']}."
                    )

                    break

            if not detected:

                evidence = (
                    "No matching post-conversion activity "
                    "was found for a WON opportunity."
                )

        # --------------------------------------------------
        # EX-003: ASSIGNMENT OUTSIDE REP TERRITORY
        # --------------------------------------------------

        elif issue_type == "OUTSIDE_TERRITORY_ASSIGNMENT":

            lead_record = leads[
                leads["lead_id"] == lead_id
            ]

            if lead_record.empty:

                evidence = f"Lead {lead_id} was not found."

            else:

                lead = lead_record.iloc[0]

                rep_id = normalize_id(lead["assigned_rep_id"])
                lead_territory = normalize_id(
                    lead["territory_id"]
                )

                if not rep_id:

                    evidence = (
                        "Lead has no assigned sales representative."
                    )

                elif not lead_territory:

                    evidence = (
                        "Lead has no territory assignment."
                    )

                else:

                    rep_record = sales_reps[
                        sales_reps["sales_rep_id"] == rep_id
                    ]

                    if rep_record.empty:

                        evidence = (
                            f"Assigned representative {rep_id} "
                            "was not found."
                        )

                    else:

                        rep_territory = normalize_id(
                            rep_record.iloc[0]["territory_id"]
                        )

                        if not rep_territory:

                            evidence = (
                                f"Representative {rep_id} "
                                "has no territory assignment."
                            )

                        elif lead_territory != rep_territory:

                            detected = True

                            evidence = (
                                f"Lead territory {lead_territory} "
                                f"differs from representative "
                                f"{rep_id} territory {rep_territory}."
                            )

                        else:

                            evidence = (
                                "Lead and representative territories match."
                            )

        # --------------------------------------------------
        # EX-004: DUPLICATE OPPORTUNITY ATTEMPT
        # --------------------------------------------------

        elif issue_type == "DUPLICATE_OPPORTUNITY":

            matching_issues = data_quality_issues[
                (
                    data_quality_issues["issue_id"] == issue_id
                )
                &
                (
                    data_quality_issues["issue_type"]
                    == "DUPLICATE_OPPORTUNITY"
                )
                &
                (
                    data_quality_issues["lead_id"] == lead_id
                )
                &
                (
                    data_quality_issues["issue_status"]
                    == "REJECTED"
                )
                &
                (
                    data_quality_issues["attempted_action"]
                    == "CREATE_DUPLICATE_OPPORTUNITY"
                )
            ]

            if matching_issues.empty:

                evidence = (
                    "No matching rejected duplicate-opportunity "
                    "audit record was found."
                )

            else:

                issue = matching_issues.iloc[0]

                existing_opportunity_id = normalize_id(
                    issue["existing_opportunity_id"]
                )

                existing_record = opportunities[
                    (
                        opportunities["opportunity_id"]
                        == existing_opportunity_id
                    )
                    &
                    (
                        opportunities["lead_id"] == lead_id
                    )
                ]

                if (
                    existing_opportunity_id
                    and not existing_record.empty
                ):

                    detected = True

                    evidence = (
                        "Duplicate opportunity creation attempt "
                        "was rejected and audited. "
                        f"Existing opportunity: "
                        f"{existing_opportunity_id}. "
                        f"Lead: {lead_id}. "
                        f"Audit status: {issue['issue_status']}. "
                        f"Reason: "
                        f"{first_value(issue, 'reason', 'Not provided')}."
                    )

                else:

                    evidence = (
                        "Rejected audit record exists, but the "
                        "referenced existing opportunity could "
                        "not be verified."
                    )

        # --------------------------------------------------
        # EX-005: MISSING OR OUT-OF-ORDER STAGE TRANSITION
        # --------------------------------------------------

        elif issue_type == "STAGE_HISTORY_GAP":

            opportunity_id = normalize_id(
                anomaly.get("opportunity_id")
            )

            lead_history = stage_history[
                stage_history["lead_id"] == lead_id
            ].copy()

            if opportunity_id:

                lead_history = lead_history[
                    lead_history["opportunity_id"]
                    == opportunity_id
                ]

            lead_history = lead_history.sort_values(
                "changed_at"
            )

            observed_stages = (
                lead_history["new_stage"].tolist()
            )

            lead_opp = lead_opportunities.copy()

            if opportunity_id:

                lead_opp = lead_opp[
                    lead_opp["opportunity_id"]
                    == opportunity_id
                ]

            if lead_opp.empty:

                evidence = (
                    "No matching opportunity was found "
                    "for this stage-history record."
                )

            else:

                final_stage = normalize_text(
                    lead_opp.iloc[0]["opportunity_stage"]
                )

                expected_stages = anomaly.get(
                    "expected_stages",
                    [
                        "QUALIFICATION",
                        "NEEDS_ANALYSIS",
                        final_stage
                    ]
                )

                expected_stages = [
                    normalize_text(stage)
                    for stage in expected_stages
                ]

                missing_stages = [
                    stage
                    for stage in expected_stages
                    if stage not in observed_stages
                ]

                stage_positions = []

                for stage in expected_stages:

                    if stage in observed_stages:

                        stage_positions.append(
                            observed_stages.index(stage)
                        )

                out_of_order = (
                    len(stage_positions) > 1
                    and stage_positions != sorted(stage_positions)
                )

                if missing_stages:

                    detected = True

                    evidence = (
                        "Missing expected stage(s): "
                        + ", ".join(missing_stages)
                    )

                elif out_of_order:

                    detected = True

                    evidence = (
                        "Expected stages exist but are not "
                        "in the required chronological order. "
                        f"Observed sequence: {observed_stages}"
                    )

                else:

                    evidence = (
                        "Expected stages are present and "
                        "their relative order is valid."
                    )

        else:

            evidence = (
                f"Unsupported anomaly type: {issue_type}"
            )

        # --------------------------------------------------
        # 8. STORE RESULT
        # --------------------------------------------------

        expected_decision = normalize_text(
            anomaly.get("expected_decision")
        )

        results.append({

            "issue_id": issue_id,
            "issue_type": issue_type,
            "lead_id": lead_id,

            "expected_decision": expected_decision,

            "detected_in_data": detected,

            "verification_status": (
                "PASS" if detected else "FAIL"
            ),

            "evidence": evidence

        })

    # --------------------------------------------------
    # 9. SUMMARY REPORT
    # --------------------------------------------------

    total_count = len(results)

    detected_count = sum(
        item["detected_in_data"]
        for item in results
    )

    failed_cases = [
        item["issue_id"]
        for item in results
        if not item["detected_in_data"]
    ]

    detection_rate = (
        round(detected_count / total_count * 100, 2)
        if total_count
        else 0
    )

    overall_status = (
        "PASS"
        if total_count > 0 and detected_count == total_count
        else "FAIL"
    )

    report = {

        "summary": {

            "overall_status": overall_status,

            "ground_truth_anomalies": total_count,

            "detected_in_data": detected_count,

            "not_detected": total_count - detected_count,

            "detection_rate_percent": detection_rate,

            "failed_issue_ids": failed_cases

        },

        "results": results

    }

    # --------------------------------------------------
    # 10. SAVE REPORT
    # --------------------------------------------------

    output_file = OUTPUT_DIR / "anomaly_report.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            default=str
        )

    # --------------------------------------------------
    # 11. DISPLAY RESULTS
    # --------------------------------------------------

    print("\n========== ANOMALY ANALYSIS ==========")

    print(json.dumps(report, indent=4, default=str))

    print("======================================")

    print(f"\nOverall status: {overall_status}")

    print(f"Detection rate: {detection_rate}%")

    print(f"Report saved to: {output_file}")


# --------------------------------------------------
# 12. EXECUTION
# --------------------------------------------------

if __name__ == "__main__":
    analyze_anomalies()