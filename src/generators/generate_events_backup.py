import csv
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SEED = 20261022
NOW = datetime(2026, 10, 30, 12, 0, 0)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"
TRUTH = ROOT / "data" / "ground_truth"

rng = random.Random(SEED)


def read_csv(name):
    with (DATA / f"{name}.csv").open(
        newline="", encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def write_csv(name, rows):
    if not rows:
        return
    with (DATA / f"{name}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows):,} records")


def save_truth(rows):
    TRUTH.mkdir(parents=True, exist_ok=True)
    with (TRUTH / "ground_truth.json").open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(rows, f, indent=4)


def main():
    leads = read_csv("leads")
    reps = read_csv("sales_reps")
    campaigns = read_csv("campaigns")
    products = read_csv("products")

    rep_by_territory = defaultdict(list)
    for rep in reps:
        rep_by_territory[rep["territory_id"]].append(rep)

    activities = []
    consents = []
    tasks = []
    opportunities = []
    stages = []
    lead_campaigns = []
    ground_truth = []
    score_rules = []
    data_quality_issues = []

    activity_counts = defaultdict(int)
    consent_map = {}
    assigned_reps = {}

    # 1. Transparent scoring rules
    rules = [
        ("FIT", "company_size", 0.40),
        ("FIT", "industry_match", 0.35),
        ("FIT", "employee_count", 0.25),
        ("INTENT", "demo_request", 0.50),
        ("INTENT", "form_submission", 0.30),
        ("INTENT", "high_intent_page", 0.20),
        ("ENGAGEMENT", "email_open", 0.25),
        ("ENGAGEMENT", "email_click", 0.35),
        ("ENGAGEMENT", "website_visit", 0.20),
        ("ENGAGEMENT", "meeting", 0.20)
    ]

    for i, (feature, name, weight) in enumerate(rules, 1):
        score_rules.append({
            "rule_id": f"RULE-{i:04d}",
            "rule_name": name,
            "feature_type": feature,
            "feature_name": name,
            "weight": weight,
            "effective_from": "2026-01-01 00:00:00",
            "effective_to": "",
            "active": 1
        })

    # 2. Generate consent history
    for lead in leads:
        lid = lead["lead_id"]
        created = datetime.strptime(
            lead["created_at"], "%Y-%m-%d %H:%M:%S"
        )

        email_granted = rng.random() < 0.85
        phone_granted = rng.random() < 0.75

        for kind, granted in [
            ("EMAIL_MARKETING", email_granted),
            ("PHONE_MARKETING", phone_granted),
            ("DATA_PROCESSING", True)
        ]:
            revoked = granted and rng.random() < 0.08
            revoke_date = (
                created + timedelta(days=rng.randint(10, 100))
                if revoked else None
            )

            consents.append({
                "consent_id": f"CONS-{lid}-{kind[:3]}",
                "lead_id": lid,
                "consent_type": kind,
                "consent_status": (
                    "REVOKED" if revoked
                    else "GRANTED" if granted
                    else "PENDING"
                ),
                "effective_from": created.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "effective_to": (
                    revoke_date.strftime("%Y-%m-%d %H:%M:%S")
                    if revoke_date else ""
                ),
                "recorded_at": created.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "source": "SYNTHETIC_FORM"
            })

            consent_map[(lid, kind)] = (
                granted, revoke_date
            )

    # 3. Generate activity histories
    activity_types = [
        "EMAIL_OPENED", "EMAIL_CLICKED",
        "WEBSITE_VISIT", "PAGE_VIEW",
        "BROCHURE_DOWNLOAD", "DEMO_REQUESTED",
        "PHONE_CALL", "MEETING", "FORM_SUBMITTED"
    ]

    campaign_ids = [c["campaign_id"] for c in campaigns]

    for lead in leads:
        lid = lead["lead_id"]
        created = datetime.strptime(
            lead["created_at"], "%Y-%m-%d %H:%M:%S"
        )

        count = rng.randint(2, 7)

        for _ in range(count):
            event_time = created + timedelta(
                seconds=rng.randint(
                    0, max(1, int((NOW - created).total_seconds()))
                )
            )

            kind = rng.choice(activity_types)

            # Respect marketing consent for email activity.
            if kind in ("EMAIL_OPENED", "EMAIL_CLICKED"):
                granted, revoked = consent_map[
                    (lid, "EMAIL_MARKETING")
                ]
                if not granted or (
                    revoked and event_time >= revoked
                ):
                    kind = "WEBSITE_VISIT"

            if kind == "PHONE_CALL":
                granted, revoked = consent_map[
                    (lid, "PHONE_MARKETING")
                ]
                if not granted or (
                    revoked and event_time >= revoked
                ):
                    kind = "WEBSITE_VISIT"

            activity_counts[(lid, kind)] += 1

            activities.append({
                "activity_id": f"ACT-{lid}-{len(activities)+1:03d}",
                "lead_id": lid,
                "contact_id": lead["contact_id"],
                "campaign_id": rng.choice(campaign_ids),
                "activity_type": kind,
                "activity_timestamp": event_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "activity_value": 1,
                "description": "Synthetic activity"
            })

    # 4. Calculate scores using activity history
    activity_by_lead = defaultdict(list)
    for activity in activities:
        activity_by_lead[activity["lead_id"]].append(activity)

    company_sizes = {
        "SMB": 45,
        "MID_MARKET": 75,
        "ENTERPRISE": 95
    }

    scored = []

    for lead in leads:
        lid = lead["lead_id"]
        company_id = lead["company_id"]

        company_number = int(company_id[-6:])
        fit = company_sizes[
            ["SMB", "MID_MARKET", "ENTERPRISE"][
                (company_number - 1) % 3
            ]
        ]

        events = activity_by_lead[lid]

        intent = min(100, sum(
            40 if a["activity_type"] == "DEMO_REQUESTED"
            else 20 if a["activity_type"] == "FORM_SUBMITTED"
            else 10 if a["activity_type"] == "BROCHURE_DOWNLOAD"
            else 0 for a in events
        ))

        engagement = min(100, sum(
            10 if a["activity_type"] == "EMAIL_OPENED"
            else 20 if a["activity_type"] == "EMAIL_CLICKED"
            else 5 if a["activity_type"] == "WEBSITE_VISIT"
            else 25 if a["activity_type"] == "MEETING"
            else 0 for a in events
        ))

        total = round(
            fit * 0.35 +
            intent * 0.35 +
            engagement * 0.30, 2
        )

        lead["fit_score"] = fit
        lead["intent_score"] = intent
        lead["engagement_score"] = engagement
        lead["total_score"] = total

        lead["lead_status"] = (
            "QUALIFIED" if total >= 60 else "NEW"
        )

        eligible = rep_by_territory[lead["territory_id"]]
        rep = rng.choice(eligible)
        lead["assigned_rep_id"] = rep["sales_rep_id"]
        assigned_reps[lid] = rep["sales_rep_id"]

        scored.append((total, lead))

    # 5. Select 3,000 outcomes using score ranking.
    scored.sort(key=lambda item: item[0], reverse=True)

    selected = scored[:3000]

    # 6. Create tasks only where consent permits outreach.
    for _, lead in scored:
        lid = lead["lead_id"]
        rep_id = assigned_reps[lid]

        email_ok, email_revoke = consent_map[
            (lid, "EMAIL_MARKETING")
        ]
        phone_ok, phone_revoke = consent_map[
            (lid, "PHONE_MARKETING")
        ]

        if not email_ok and not phone_ok:
            continue

        task_type = "CALL" if phone_ok else "EMAIL"

        created = datetime.strptime(
            lead["created_at"], "%Y-%m-%d %H:%M:%S"
        )

        tasks.append({
            "task_id": f"TASK-{lid}-001",
            "lead_id": lid,
            "assigned_rep_id": rep_id,
            "task_type": task_type,
            "priority": (
                "HIGH" if float(lead["total_score"]) >= 75
                else "MEDIUM"
            ),
            "due_at": (
                created + timedelta(days=2)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "task_status": "PENDING",
            "created_at": created.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "completed_at": ""
        })

    # 7. Create opportunities and stage histories.
    for index, (_, lead) in enumerate(selected, 1):
        lid = lead["lead_id"]
        oid = f"OPP-2026-{index:06d}"

        created = datetime.strptime(
            lead["created_at"], "%Y-%m-%d %H:%M:%S"
        )

        close_date = min(
            created + timedelta(days=30),
            NOW
        )

        outcome = "WON" if rng.random() < (
            0.20 + float(lead["total_score"]) / 200
        ) else "LOST"

        amount = round(rng.uniform(25000, 1500000), 2)

        opportunities.append({
            "opportunity_id": oid,
            "lead_id": lid,
            "opportunity_name": f"Opportunity {index:06d}",
            "amount": amount,
            "currency": "INR",
            "opportunity_stage": outcome,
            "created_at": created.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "closed_at": close_date.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "outcome_reason": (
                "CUSTOMER_PURCHASED" if outcome == "WON"
                else "BUDGET_OR_COMPETITOR"
            )
        })

        lead["lead_status"] = "CONVERTED"

        stages.extend([
            {
                "lead_id": lid,
                "opportunity_id": oid,
                "previous_stage": "",
                "new_stage": "QUALIFICATION",
                "changed_at": created.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "changed_by": assigned_reps[lid],
                "change_reason": "Opportunity created"
            },
            {
                "lead_id": lid,
                "opportunity_id": oid,
                "previous_stage": "QUALIFICATION",
                "new_stage": "NEEDS_ANALYSIS",
                "changed_at": (
                    created + timedelta(days=5)
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "changed_by": assigned_reps[lid],
                "change_reason": "Needs assessed"
            },
            {
                "lead_id": lid,
                "opportunity_id": oid,
                "previous_stage": "NEEDS_ANALYSIS",
                "new_stage": outcome,
                "changed_at": close_date.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "changed_by": assigned_reps[lid],
                "change_reason": "Opportunity closed"
            }
        ])

    # 8. Exception scenarios (kept separate from normal data).

    # A. Opted-out lead contacted.
    opted_out = next(
        lid for lid, kind in consent_map
        if kind == "EMAIL_MARKETING"
        and consent_map[(lid, kind)][1] is not None
    )

    revoked_at = consent_map[
        (opted_out, "EMAIL_MARKETING")
    ][1]

    activities.append({
        "activity_id": f"ACT-{opted_out}-EX001",
        "lead_id": opted_out,
        "contact_id": next(
            l["contact_id"] for l in leads
            if l["lead_id"] == opted_out
        ),
        "campaign_id": campaign_ids[0],
        "activity_type": "EMAIL_SENT",
        "activity_timestamp": (
            revoked_at + timedelta(days=1)
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "activity_value": 1,
        "description": "LABELLED CONSENT VIOLATION"
    })

    ground_truth.append({
        "issue_id": "EX-001",
        "issue_type": "OPTED_OUT_CONTACTED",
        "lead_id": opted_out,
        "expected_decision": "BLOCK_CONTACT"
    })

    # B. Post-conversion event must not affect score.
    converted = opportunities[0]
    future_lead = converted["lead_id"]
    post_time = datetime.strptime(
        converted["closed_at"], "%Y-%m-%d %H:%M:%S"
    ) + timedelta(days=1)

    activities.append({
        "activity_id": f"ACT-{future_lead}-EX002",
        "lead_id": future_lead,
        "contact_id": next(
            l["contact_id"] for l in leads
            if l["lead_id"] == future_lead
        ),
        "campaign_id": campaign_ids[0],
        "activity_type": "DEMO_COMPLETED",
        "activity_timestamp": post_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "activity_value": 1,
        "description": "POST-CONVERSION SCORING TEST"
    })

    ground_truth.append({
        "issue_id": "EX-002",
        "issue_type": "POST_CONVERSION_ACTIVITY",
        "lead_id": future_lead,
        "expected_decision": "EXCLUDE_FROM_SCORE"
    })

    # C. Wrong territory assignment.
    wrong_lead = leads[100]
    other_rep = next(
        r for r in reps
        if r["territory_id"] != wrong_lead["territory_id"]
    )

    wrong_lead["assigned_rep_id"] = other_rep["sales_rep_id"]

    ground_truth.append({
        "issue_id": "EX-003",
        "issue_type": "OUTSIDE_TERRITORY_ASSIGNMENT",
        "lead_id": wrong_lead["lead_id"],
        "expected_decision": "REJECT_ASSIGNMENT"
    })

    # D. Duplicate opportunity attempt.
    duplicate_lead = opportunities[1]["lead_id"]

    existing_opportunity = next(
        opp for opp in opportunities
        if opp["lead_id"] == duplicate_lead
    )

    data_quality_issues.append({
        "issue_id": "EX-004",
        "issue_type": "DUPLICATE_OPPORTUNITY",
        "lead_id": duplicate_lead,
        "existing_opportunity_id": existing_opportunity[
            "opportunity_id"
        ],
        "attempted_action": "CREATE_DUPLICATE_OPPORTUNITY",
        "issue_status": "REJECTED",
        "reason": (
            "Duplicate opportunity rejected by the unique "
            "lead_id constraint"
        ),
        "recorded_at": NOW.strftime("%Y-%m-%d %H:%M:%S")
    })

    ground_truth.append({
        "issue_id": "EX-004",
        "issue_type": "DUPLICATE_OPPORTUNITY",
        "lead_id": duplicate_lead,
        "expected_decision": "REJECT_DUPLICATE"
    })

    # E. Stage history gap.
    gap_lead = opportunities[2]["lead_id"]
    gap_oid = opportunities[2]["opportunity_id"]

    stages = [
        s for s in stages
        if not (
            s["lead_id"] == gap_lead
            and s["new_stage"] == "NEEDS_ANALYSIS"
        )
    ]

    ground_truth.append({
        "issue_id": "EX-005",
        "issue_type": "STAGE_HISTORY_GAP",
        "lead_id": gap_lead,
        "opportunity_id": gap_oid,
        "expected_decision": "FLAG_MISSING_TRANSITION"
    })

    # 9. Export all records.
    write_csv("leads", leads)
    write_csv("activities", activities)
    write_csv("consents", consents)
    write_csv("score_rules", score_rules)
    write_csv("tasks", tasks)
    write_csv("opportunities", opportunities)
    write_csv("stage_history", stages)
    write_csv("data_quality_issues", data_quality_issues)

    save_truth(ground_truth)

    print("\nDependent data generation completed.")
    print("Opportunities:", len(opportunities))
    print("Labelled exceptions:", len(ground_truth))
    print("Data quality issues:", len(data_quality_issues))


if __name__ == "__main__":
    main()