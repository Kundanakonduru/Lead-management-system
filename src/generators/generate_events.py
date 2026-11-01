import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261022
NOW = datetime(2026, 10, 30, 12, 0, 0)
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "generated"
OUT = ROOT / "data" / "staging" / "generated_v2"
TRUTH = ROOT / "data" / "staging" / "ground_truth_v2"
STALE_THRESHOLD_DAYS = 30
STALE_TARGET = 15667
OPEN_TARGET = 1333
OPPORTUNITY_TARGET = 3000

PRODUCT_INDUSTRIES = {
    "Business Analytics": {"Finance", "Retail", "Healthcare", "Manufacturing", "Education"},
    "Cloud Management": {"IT", "Telecommunications", "Finance", "Healthcare", "Manufacturing"},
    "CRM Software": {"Retail", "Finance", "Healthcare", "Education", "IT"},
}
FIT_W = {"company_size": .40, "industry_match": .35, "employee_count": .25}
INTENT_W = {"demo_request": .50, "form_submission": .30, "high_intent_page": .20}
ENGAGEMENT_W = {"email_open": .25, "email_click": .35, "website_visit": .20, "meeting": .20}
OVERALL_W = {"FIT": .35, "INTENT": .35, "ENGAGEMENT": .30}
QUALIFIED_AT = 60.0
PRODUCT_BASE_INR = {"Business Analytics": 180000, "Cloud Management": 240000, "CRM Software": 150000}
SIZE_MULTIPLIER = {"SMB": 1.0, "MID_MARKET": 2.5, "ENTERPRISE": 5.0}
OUTCOME_REVENUE_MULTIPLE = 20


def read_csv(name):
    path = SOURCE / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty output without a known schema: {name}")
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows):,}")


def dt(value, label):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {value!r}") from exc


def number(value, label):
    try:
        return float(value) if value not in ("", None) else 0.0
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {value!r}") from exc


def cap(count, points):
    return min(100.0, count * points)


def build_rules():
    rows = []
    number_id = 1
    for group, rules in (
        ("FIT", FIT_W), ("INTENT", INTENT_W), ("ENGAGEMENT", ENGAGEMENT_W)
    ):
        for name, weight in rules.items():
            rows.append({
                "rule_id": f"RULE-{number_id:04d}",
                "rule_name": name,
                "feature_type": group,
                "feature_name": name,
                "weight": weight,
                "effective_from": "2026-01-01 00:00:00",
                "effective_to": "",
                "active": 1,
            })
            number_id += 1
    return rows


def fit_score(company, product):
    size = company.get("company_size", "").upper()
    size_score = {"SMB": 70, "MID_MARKET": 85, "ENTERPRISE": 100}.get(size, 40)
    industry_score = (
        100 if company.get("industry") in PRODUCT_INDUSTRIES.get(
            product.get("product_name"), set()
        ) else 30
    )
    employees = number(company.get("employee_count"), "employee_count")
    employee_score = (
        0 if employees <= 0 else
        50 if employees < 50 else
        70 if employees < 250 else
        85 if employees < 1000 else 100
    )
    return round(
        size_score * FIT_W["company_size"]
        + industry_score * FIT_W["industry_match"]
        + employee_score * FIT_W["employee_count"],
        2,
    )


def score_events(events):
    kinds = [event["activity_type"] for event in events]
    intent = {
        "demo_request": cap(kinds.count("DEMO_REQUESTED"), 100),
        "form_submission": cap(kinds.count("FORM_SUBMITTED"), 100),
        "high_intent_page": cap(kinds.count("PAGE_VIEW"), 25),
    }
    engagement = {
        "email_open": cap(kinds.count("EMAIL_OPENED"), 25),
        "email_click": cap(kinds.count("EMAIL_CLICKED"), 25),
        "website_visit": cap(kinds.count("WEBSITE_VISIT"), 20),
        "meeting": cap(kinds.count("MEETING"), 50),
    }
    intent_score = round(sum(intent[key] * weight for key, weight in INTENT_W.items()), 2)
    engagement_score = round(
        sum(engagement[key] * weight for key, weight in ENGAGEMENT_W.items()), 2
    )
    return intent_score, engagement_score


def opportunity_amount(company, product):
    name = product.get("product_name", "")
    amount = (
        PRODUCT_BASE_INR.get(name, 120000)
        * SIZE_MULTIPLIER.get(company.get("company_size", "").upper(), 1)
    )
    revenue = number(company.get("annual_revenue"), "annual_revenue")
    if revenue > 0:
        amount = min(amount, revenue * .01)
    return round(max(amount, 0.0), 2)


def main():
    rng = random.Random(SEED)
    leads = read_csv("leads")
    companies = read_csv("companies")
    contacts = read_csv("contacts")
    reps = read_csv("sales_reps")
    rep_products = read_csv("sales_rep_products")
    campaigns = read_csv("campaigns")
    products = read_csv("products")

    if not all((leads, companies, contacts, reps, rep_products, campaigns, products)):
        raise ValueError("All source datasets, including sales_rep_products, must contain records.")

    company_map = {row["company_id"]: row for row in companies}
    product_map = {row["product_id"]: row for row in products}
    contact_ids = {row["contact_id"] for row in contacts}
    campaign_ids = sorted(row["campaign_id"] for row in campaigns)

    def is_active(rep):
        return str(rep.get("active", "1")).strip().lower() in ("1", "true", "yes", "y")

    active_rep_ids = {rep["sales_rep_id"] for rep in reps if is_active(rep)}
    rep_product_set = {
        (row["sales_rep_id"], row["product_id"])
        for row in rep_products
        if row.get("sales_rep_id") in active_rep_ids
    }
    reps_by_territory = defaultdict(list)
    for rep in reps:
        if is_active(rep):
            reps_by_territory[rep["territory_id"]].append(rep)
    for rep_rows in reps_by_territory.values():
        rep_rows.sort(key=lambda row: row["sales_rep_id"])

    activities, consents, tasks, opportunities, stages = [], [], [], [], []
    opportunity_evidence = []
    truth, quality = [], []
    consent_map = {}
    events_by_lead = defaultdict(list)
    score_events_by_lead = defaultdict(list)
    assigned = {}

    # Generate consent records deterministically.
    for lead in leads:
        lead_id = lead["lead_id"]
        created = dt(lead["created_at"], "lead.created_at")
        email_ok, phone_ok = rng.random() < .85, rng.random() < .75

        for kind, granted in (
            ("EMAIL_MARKETING", email_ok),
            ("PHONE_MARKETING", phone_ok),
            ("DATA_PROCESSING", True),
        ):
            revoked = granted and kind != "DATA_PROCESSING" and rng.random() < .08
            revoke_at = (
                min(created + timedelta(days=rng.randint(10, 100)), NOW)
                if revoked else None
            )
            consents.append({
                "consent_id": f"CONS-{lead_id}-{kind[:3]}",
                "lead_id": lead_id,
                "consent_type": kind,
                "consent_status": (
                    "REVOKED" if revoked else "GRANTED" if granted else "PENDING"
                ),
                "effective_from": created.strftime("%Y-%m-%d %H:%M:%S"),
                "effective_to": revoke_at.strftime("%Y-%m-%d %H:%M:%S") if revoke_at else "",
                "recorded_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                "source": "SYNTHETIC_FORM",
            })
            consent_map[(lead_id, kind)] = (granted, revoke_at)

    event_types = [
        "EMAIL_OPENED", "EMAIL_CLICKED", "WEBSITE_VISIT", "PAGE_VIEW",
        "BROCHURE_DOWNLOAD", "DEMO_REQUESTED", "PHONE_CALL", "MEETING",
        "FORM_SUBMITTED",
    ]

    # Fixed volume: 85,753 normal events plus two labelled anomaly events.
    # Lifecycle events are excluded from the initial scoring snapshot.
    for lead in leads:
        lead_id = lead["lead_id"]
        created = dt(lead["created_at"], "lead.created_at")
        if created > NOW:
            raise ValueError(f"{lead_id} is dated after configured NOW.")

        lead_number = int(lead_id.rsplit("-", 1)[1])
        activity_count = 5 if lead_number <= 5753 else 4
        scoring_count = activity_count - 1
        score_end = max(
            created,
            min(created + timedelta(days=30), NOW - timedelta(days=STALE_THRESHOLD_DAYS)),
        )
        score_span = max(0, int((score_end - created).total_seconds()))

        for activity_number in range(1, scoring_count + 1):
            when = created + timedelta(seconds=rng.randint(0, score_span))
            kind = rng.choice(event_types)

            if kind in ("EMAIL_OPENED", "EMAIL_CLICKED"):
                granted, revoked_at = consent_map[(lead_id, "EMAIL_MARKETING")]
                if not granted or (revoked_at and when >= revoked_at):
                    kind = "WEBSITE_VISIT"

            if kind == "PHONE_CALL":
                granted, revoked_at = consent_map[(lead_id, "PHONE_MARKETING")]
                if not granted or (revoked_at and when >= revoked_at):
                    kind = "WEBSITE_VISIT"

            activity = {
                "activity_id": f"ACT-{lead_id}-{activity_number:03d}",
                "lead_id": lead_id,
                "contact_id": lead["contact_id"],
                "campaign_id": rng.choice(campaign_ids),
                "activity_type": kind,
                "activity_timestamp": when.strftime("%Y-%m-%d %H:%M:%S"),
                "activity_value": 1,
                "description": (
                    "Synthetic high-intent product page view"
                    if kind == "PAGE_VIEW" else "Synthetic scoring-window activity"
                ),
            }
            activities.append(activity)
            events_by_lead[lead_id].append(activity)
            score_events_by_lead[lead_id].append(activity)

        lifecycle = {
            "activity_id": f"ACT-{lead_id}-{activity_count:03d}",
            "lead_id": lead_id,
            "contact_id": lead["contact_id"],
            "campaign_id": campaign_ids[(lead_number - 1) % len(campaign_ids)],
            "activity_type": "WEBSITE_VISIT",
            "activity_timestamp": "",
            "activity_value": 1,
            "description": (
                "Synthetic lifecycle/re-engagement event; "
                "excluded from initial score snapshot"
            ),
        }
        activities.append(lifecycle)
        events_by_lead[lead_id].append(lifecycle)

    # Score leads using company/product attributes and pre-exception events.
    for lead in leads:
        lead_id = lead["lead_id"]
        company = company_map.get(lead["company_id"])
        product = product_map.get(lead["product_id"])
        if company is None or product is None:
            raise ValueError(f"{lead_id} has a missing company or product reference.")
        if product.get("active", "1") not in ("1", "True", "true"):
            raise ValueError(f"{lead_id} references an inactive product.")

        fit = fit_score(company, product)
        intent, engagement = score_events(score_events_by_lead[lead_id])
        total = round(
            fit * OVERALL_W["FIT"]
            + intent * OVERALL_W["INTENT"]
            + engagement * OVERALL_W["ENGAGEMENT"],
            2,
        )
        lead.update({
            "fit_score": fit,
            "intent_score": intent,
            "engagement_score": engagement,
            "total_score": total,
            "lead_status": "QUALIFIED" if total >= QUALIFIED_AT else "NEW",
        })

        eligible = [
            rep for rep in reps_by_territory.get(lead["territory_id"], [])
            if (rep["sales_rep_id"], lead["product_id"]) in rep_product_set
        ]
        if not eligible:
            raise ValueError(
                f"No active representative covers both territory {lead['territory_id']} "
                f"and product {lead['product_id']} for lead {lead_id}."
            )

        lead_number = int(lead_id.rsplit("-", 1)[1])
        rep = eligible[(lead_number - 1) % len(eligible)]
        lead["assigned_rep_id"] = rep["sales_rep_id"]
        assigned[lead_id] = rep["sales_rep_id"]

    # Create follow-up tasks only where consent remains valid at due time.
    for lead in leads:
        lead_id = lead["lead_id"]
        created = dt(lead["created_at"], "lead.created_at")
        due = created + timedelta(days=2)
        email_ok, email_revoked = consent_map[(lead_id, "EMAIL_MARKETING")]
        phone_ok, phone_revoked = consent_map[(lead_id, "PHONE_MARKETING")]
        phone_valid = phone_ok and (phone_revoked is None or due < phone_revoked)
        email_valid = email_ok and (email_revoked is None or due < email_revoked)

        if not phone_valid and not email_valid:
            continue

        tasks.append({
            "task_id": f"TASK-{lead_id}-001",
            "lead_id": lead_id,
            "assigned_rep_id": assigned[lead_id],
            "task_type": "CALL" if phone_valid else "EMAIL",
            "priority": "HIGH" if float(lead["total_score"]) >= 75 else "MEDIUM",
            "due_at": due.strftime("%Y-%m-%d %H:%M:%S"),
            "task_status": "PENDING",
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": "",
        })

    # Qualification cohort: exactly 3,000 highest-scoring leads.
    # Ties are resolved deterministically using the zero-padded lead_id.
    qualified = sorted(
        leads,
        key=lambda row: (-float(row["total_score"]), row["lead_id"]),
    )[:OPPORTUNITY_TARGET]

    qualified_ids = {row["lead_id"] for row in qualified}
    for lead in leads:
        lead["is_qualified"] = 1 if lead["lead_id"] in qualified_ids else 0

    if len(qualified) != OPPORTUNITY_TARGET:
        raise RuntimeError(
            f"Expected {OPPORTUNITY_TARGET} qualified leads; got {len(qualified)}."
        )

    # OUTCOME-001 is a synthetic financial-capacity proxy, not actual sales proof.
    for index, lead in enumerate(qualified, 1):
        lead_id = lead["lead_id"]
        company = company_map[lead["company_id"]]
        product = product_map[lead["product_id"]]
        created = dt(lead["created_at"], "lead.created_at")

        product_name = product.get("product_name", "")
        base_price = PRODUCT_BASE_INR.get(product_name, 120000)
        annual_revenue = number(company.get("annual_revenue"), "annual_revenue")
        required_revenue = base_price * OUTCOME_REVENUE_MULTIPLE
        evidence_passed = annual_revenue >= required_revenue
        outcome = "WON" if evidence_passed else "LOST"

        closed = min(created + timedelta(days=30), NOW)
        opportunity_id = f"OPP-2026-{index:06d}"

        opportunity_evidence.append({
            "evidence_id": f"EVD-{index:06d}",
            "opportunity_id": opportunity_id,
            "lead_id": lead_id,
            "evidence_type": "SYNTHETIC_FINANCIAL_CAPACITY_CHECK",
            "annual_revenue_inr": round(annual_revenue, 2),
            "product_base_price_inr": base_price,
            "revenue_multiple_required": OUTCOME_REVENUE_MULTIPLE,
            "required_annual_revenue_inr": round(required_revenue, 2),
            "evidence_result": "PASS" if evidence_passed else "FAIL",
            "rule_id": "OUTCOME-001",
            "evaluated_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
            "evidence_source": "SYNTHETIC_COMPANY_FINANCIAL_DATA",
            "description": (
                "Synthetic financial-capacity proxy; "
                "not proof of an actual purchase."
            ),
        })

        opportunities.append({
            "opportunity_id": opportunity_id,
            "lead_id": lead_id,
            "opportunity_name": f"Opportunity {index:06d}",
            "amount": opportunity_amount(company, product),
            "currency": "INR",
            "opportunity_stage": outcome,
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
            "outcome_reason": (
                "SYNTHETIC_FINANCIAL_CAPACITY_RULE_MET"
                if evidence_passed
                else "SYNTHETIC_FINANCIAL_CAPACITY_RULE_NOT_MET"
            ),
        })

        lead["lead_status"] = "CONVERTED" if outcome == "WON" else "QUALIFIED"

        stages.extend([
            {
                "lead_id": lead_id,
                "opportunity_id": opportunity_id,
                "previous_stage": "",
                "new_stage": "QUALIFICATION",
                "changed_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                "changed_by": assigned[lead_id],
                "change_reason": "Qualified lead entered opportunity pipeline",
            },
            {
                "lead_id": lead_id,
                "opportunity_id": opportunity_id,
                "previous_stage": "QUALIFICATION",
                "new_stage": "NEEDS_ANALYSIS",
                "changed_at": min(created + timedelta(days=5), closed).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "changed_by": assigned[lead_id],
                "change_reason": "Needs assessed",
            },
            {
                "lead_id": lead_id,
                "opportunity_id": opportunity_id,
                "previous_stage": "NEEDS_ANALYSIS",
                "new_stage": outcome,
                "changed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
                "changed_by": assigned[lead_id],
                "change_reason": "Opportunity closed using OUTCOME-001",
            },
        ])

    # Derive stale/open/closed status from the latest actual activity.
    cutoff = NOW - timedelta(days=STALE_THRESHOLD_DAYS)
    closed_lead_ids = {row["lead_id"] for row in opportunities}
    non_closed = [row for row in leads if row["lead_id"] not in closed_lead_ids]

    stale_candidates = sorted(
        (
            row for row in non_closed
            if dt(row["created_at"], "lead.created_at") <= cutoff
        ),
        key=lambda row: (row["created_at"], row["lead_id"]),
    )
    if len(stale_candidates) < STALE_TARGET:
        raise RuntimeError(
            f"Only {len(stale_candidates)} non-closed leads can be stale by {cutoff}; "
            f"need {STALE_TARGET}. Check source lead creation dates."
        )

    stale_ids = {row["lead_id"] for row in stale_candidates[:STALE_TARGET]}
    if len(non_closed) - len(stale_ids) != OPEN_TARGET:
        raise RuntimeError(
            f"Expected {OPEN_TARGET} OPEN leads after stale assignment, got "
            f"{len(non_closed) - len(stale_ids)}."
        )

    activity_by_lead = defaultdict(list)
    for activity in activities:
        activity_by_lead[activity["lead_id"]].append(activity)

    for lead in leads:
        lead_id = lead["lead_id"]
        created = dt(lead["created_at"], "lead.created_at")

        if lead_id in closed_lead_ids:
            status = "CLOSED"
            last_activity = max(created, NOW - timedelta(days=1))
        elif lead_id in stale_ids:
            status = "STALE"
            last_activity = min(
                cutoff, max(created, cutoff - timedelta(seconds=1))
            )
        else:
            status = "OPEN"
            last_activity = max(created, NOW - timedelta(days=1))

        lead_number = int(lead_id.rsplit("-", 1)[1])
        lifecycle_number = 5 if lead_number <= 5753 else 4
        lifecycle = next(
            activity for activity in activity_by_lead[lead_id]
            if activity["activity_id"].endswith(f"-{lifecycle_number:03d}")
        )
        lifecycle["activity_timestamp"] = last_activity.strftime("%Y-%m-%d %H:%M:%S")

        actual_latest = max(
            dt(activity["activity_timestamp"], "activity_timestamp")
            for activity in activity_by_lead[lead_id]
            if activity["activity_timestamp"]
        )
        lead["last_activity_at"] = actual_latest.strftime("%Y-%m-%d %H:%M:%S")
        lead["stale_status"] = status
        lead["is_stale"] = 1 if status == "STALE" else 0
        lead["stale_since"] = (
            (actual_latest + timedelta(days=STALE_THRESHOLD_DAYS)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if status == "STALE" else ""
        )

    # Validate stale labels against the latest activity timestamp.
    for lead in leads:
        latest = dt(lead["last_activity_at"], "last_activity_at")
        if lead["stale_status"] == "STALE" and latest > cutoff:
            raise ValueError(f"Stale lead {lead['lead_id']} has recent activity.")
        if lead["stale_status"] == "OPEN" and latest <= cutoff:
            raise ValueError(
                f"Open lead {lead['lead_id']} does not have recent activity."
            )
        if lead["stale_status"] == "CLOSED" and lead["is_stale"] != 0:
            raise ValueError(
                f"Closed lead {lead['lead_id']} was incorrectly marked stale."
            )

    if len(opportunities) < 3:
        raise RuntimeError(
            "Fewer than three qualified leads; cannot inject all opportunity-related test cases."
        )

    # Injected anomalies are appended after scoring and are not scoring inputs.
    revoked_ids = sorted(
        lead_id
        for (lead_id, kind), (_, revoked) in consent_map.items()
        if kind == "EMAIL_MARKETING"
        and revoked is not None
        and revoked < (NOW - timedelta(days=STALE_THRESHOLD_DAYS))
    )
    lead_map = {row["lead_id"]: row for row in leads}
    revoked_ids = [
        lead_id for lead_id in revoked_ids
        if lead_map[lead_id]["stale_status"] != "OPEN"
        and consent_map[(lead_id, "EMAIL_MARKETING")][1] <= cutoff - timedelta(days=1)
    ]
    if not revoked_ids:
        raise RuntimeError(
            "No suitable revoked-consent lead exists for EX-001 without changing OPEN/STALE status."
        )

    ex1 = revoked_ids[0]
    revoke_at = consent_map[(ex1, "EMAIL_MARKETING")][1]
    activities.append({
        "activity_id": f"ACT-{ex1}-EX001",
        "lead_id": ex1,
        "contact_id": lead_map[ex1]["contact_id"],
        "campaign_id": campaign_ids[0],
        "activity_type": "EMAIL_SENT",
        "activity_timestamp": (revoke_at + timedelta(days=1)).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "activity_value": 1,
        "description": "LABELLED CONSENT VIOLATION; EXCLUDED FROM SCORING",
    })
    truth.append({
        "issue_id": "EX-001",
        "issue_type": "OPTED_OUT_CONTACTED",
        "lead_id": ex1,
        "expected_decision": "BLOCK_CONTACT",
    })

    first_won = next(
        (row for row in opportunities if row["opportunity_stage"] == "WON"),
        None,
    )
    if first_won is None:
        raise RuntimeError(
            "OUTCOME-001 produced no WON opportunity; cannot create post-conversion test case."
        )
    ex2 = first_won["lead_id"]
    ex2_time = dt(first_won["closed_at"], "closed_at") + timedelta(days=1)
    activities.append({
        "activity_id": f"ACT-{ex2}-EX002",
        "lead_id": ex2,
        "contact_id": lead_map[ex2]["contact_id"],
        "campaign_id": campaign_ids[0],
        "activity_type": "DEMO_COMPLETED",
        "activity_timestamp": ex2_time.strftime("%Y-%m-%d %H:%M:%S"),
        "activity_value": 1,
        "description": "POST-CONVERSION TEST; EXCLUDED FROM SCORING",
    })
    truth.append({
        "issue_id": "EX-002",
        "issue_type": "POST_CONVERSION_ACTIVITY",
        "lead_id": ex2,
        "expected_decision": "EXCLUDE_FROM_SCORE",
    })

    # --------------------------------------------------
    # SCORING DATA LEAKAGE VALIDATION
    # --------------------------------------------------

    scoring_activity_ids = {
        activity["activity_id"]
        for lead_events in score_events_by_lead.values()
        for activity in lead_events
    }

    injected_activity_ids = {
        f"ACT-{ex1}-EX001",
        f"ACT-{ex2}-EX002",
    }

    leaked_activities = scoring_activity_ids & injected_activity_ids

    if leaked_activities:
        raise ValueError(
            "Scoring data leakage detected: "
            f"{sorted(leaked_activities)}"
        )

    ex2_activity_id = f"ACT-{ex2}-EX002"

    if ex2_activity_id in scoring_activity_ids:
        raise ValueError(
            "Post-conversion activity entered the scoring snapshot."
        )

    print("Scoring leakage validation: PASS")

    # Refresh latest activity values after injecting the two labelled events.
    for lead_id in (ex1, ex2):
        latest = max(
            dt(activity["activity_timestamp"], "activity_timestamp")
            for activity in activities if activity["lead_id"] == lead_id
        )
        lead_map[lead_id]["last_activity_at"] = latest.strftime("%Y-%m-%d %H:%M:%S")
        if lead_map[lead_id]["stale_status"] == "STALE":
            lead_map[lead_id]["stale_since"] = (
                latest + timedelta(days=STALE_THRESHOLD_DAYS)
            ).strftime("%Y-%m-%d %H:%M:%S")

    # EX-003: one intentionally wrong-territory assignment.
    wrong = leads[100]
    wrong_rep = sorted(
        (
            rep for rep in reps
            if is_active(rep)
            and rep["territory_id"] != wrong["territory_id"]
            and (rep["sales_rep_id"], wrong["product_id"]) in rep_product_set
        ),
        key=lambda row: row["sales_rep_id"],
    )
    if not wrong_rep:
        raise RuntimeError(
            "Cannot create EX-003: no active rep in another territory covers "
            f"product {wrong['product_id']}."
        )
    wrong["assigned_rep_id"] = wrong_rep[0]["sales_rep_id"]
    truth.append({
        "issue_id": "EX-003",
        "issue_type": "OUTSIDE_TERRITORY_ASSIGNMENT",
        "lead_id": wrong["lead_id"],
        "expected_decision": "REJECT_ASSIGNMENT",
    })

    # EX-004: record a rejected duplicate opportunity attempt.
    duplicate = opportunities[1]
    quality.append({
        "issue_id": "EX-004",
        "issue_type": "DUPLICATE_OPPORTUNITY",
        "lead_id": duplicate["lead_id"],
        "existing_opportunity_id": duplicate["opportunity_id"],
        "attempted_action": "CREATE_DUPLICATE_OPPORTUNITY",
        "issue_status": "REJECTED",
        "reason": "Duplicate opportunity rejected by unique lead_id constraint",
        "recorded_at": NOW.strftime("%Y-%m-%d %H:%M:%S"),
    })
    truth.append({
        "issue_id": "EX-004",
        "issue_type": "DUPLICATE_OPPORTUNITY",
        "lead_id": duplicate["lead_id"],
        "expected_decision": "REJECT_DUPLICATE",
    })

    # EX-005: remove one transition to create a stage-history gap.
    gap = opportunities[2]
    stages = [
        row for row in stages
        if not (
            row["opportunity_id"] == gap["opportunity_id"]
            and row["new_stage"] == "NEEDS_ANALYSIS"
        )
    ]
    truth.append({
        "issue_id": "EX-005",
        "issue_type": "STAGE_HISTORY_GAP",
        "lead_id": gap["lead_id"],
        "opportunity_id": gap["opportunity_id"],
        "expected_decision": "FLAG_MISSING_TRANSITION",
    })

    # Lightweight FK and assignment checks before staged export.
    lead_ids = {row["lead_id"] for row in leads}
    opportunity_ids = {row["opportunity_id"] for row in opportunities}
    rep_ids = {row["sales_rep_id"] for row in reps}

    if len({row["lead_id"] for row in opportunities}) != len(opportunities):
        raise ValueError("Duplicate lead_id in opportunities.")

    for activity in activities:
        if (
            activity["lead_id"] not in lead_ids
            or activity["contact_id"] not in contact_ids
            or activity["campaign_id"] not in campaign_ids
        ):
            raise ValueError(f"Broken activity reference: {activity['activity_id']}")

    for task in tasks:
        if task["lead_id"] not in lead_ids or task["assigned_rep_id"] not in rep_ids:
            raise ValueError(f"Broken task reference: {task['task_id']}")

    # EX-003 is the sole intentional territory exception.
    ex3_lead_id = wrong["lead_id"]
    rep_map = {row["sales_rep_id"]: row for row in reps}
    for lead in leads:
        rep_id = lead["assigned_rep_id"]
        rep = rep_map.get(rep_id)
        if rep is None or not is_active(rep):
            raise ValueError(
                f"Lead {lead['lead_id']} is assigned to a missing/inactive rep {rep_id}."
            )
        if (rep_id, lead["product_id"]) not in rep_product_set:
            raise ValueError(
                f"Lead {lead['lead_id']} is assigned to rep {rep_id}, "
                f"who does not cover product {lead['product_id']}."
            )
        if lead["lead_id"] != ex3_lead_id and rep["territory_id"] != lead["territory_id"]:
            raise ValueError(
                f"Lead {lead['lead_id']} is assigned outside territory: "
                f"lead={lead['territory_id']}, rep={rep['territory_id']}."
            )

    for stage in stages:
        if stage["lead_id"] not in lead_ids or stage["opportunity_id"] not in opportunity_ids:
            raise ValueError("Broken stage-history reference.")

    rules = build_rules()
    for name, rows in (
        ("leads", leads),
        ("activities", activities),
        ("consents", consents),
        ("score_rules", rules),
        ("tasks", tasks),
        ("opportunities", opportunities),
        ("opportunity_evidence", opportunity_evidence),
        ("stage_history", stages),
        ("data_quality_issues", quality),
    ):
        write_csv(name, rows)

    TRUTH.mkdir(parents=True, exist_ok=True)
    with (TRUTH / "ground_truth.json").open("w", encoding="utf-8") as file:
        json.dump(truth, file, indent=2, sort_keys=True)

    summary = {
        "seed": SEED,
        "as_of": NOW.strftime("%Y-%m-%d %H:%M:%S"),
        "qualification_threshold": QUALIFIED_AT,
        "overall_weights": OVERALL_W,
        "outcome_rule": {
            "rule_id": "OUTCOME-001",
            "description": (
                "WON when annual revenue is at least 20 times "
                "the product base price; otherwise LOST."
            ),
            "revenue_multiple": OUTCOME_REVENUE_MULTIPLE,
            "source": "SYNTHETIC_COMPANY_FINANCIAL_DATA",
            "limitation": (
                "Synthetic financial-capacity proxy, not verified purchase "
                "or actual sales evidence."
            ),
        },
        "product_industry_assumptions": {
            key: sorted(value) for key, value in PRODUCT_INDUSTRIES.items()
        },
        "counts": {
            "leads": len(leads),
            "activities": len(activities),
            "consents": len(consents),
            "tasks": len(tasks),
            "qualified_leads": sum(row["is_qualified"] == 1 for row in leads),
            "opportunities": len(opportunities),
            "opportunity_evidence": len(opportunity_evidence),
            "won": sum(row["opportunity_stage"] == "WON" for row in opportunities),
            "lost": sum(row["opportunity_stage"] == "LOST" for row in opportunities),
            "stage_history": len(stages),
            "ground_truth_cases": len(truth),
            "stale": sum(row["stale_status"] == "STALE" for row in leads),
            "open": sum(row["stale_status"] == "OPEN" for row in leads),
            "closed": sum(row["stale_status"] == "CLOSED" for row in leads),
            "data_quality_issues": len(quality),
        },
        "rules": {
            "fit": (
                "40% company size + 35% product-industry match "
                "+ 25% employee-count suitability"
            ),
            "intent": (
                "50% demo request + 30% form submission "
                "+ 20% PAGE_VIEW proxy"
            ),
            "engagement": (
                "25% email open + 35% email click + 20% website visit "
                "+ 20% meeting"
            ),
            "overall": "35% fit + 35% intent + 30% engagement",
            "qualification": (
                f"top {OPPORTUNITY_TARGET} leads ranked by total_score; "
                "ties break by lead_id"
            ),
            "staleness": (
                f"STALE when latest activity is at least {STALE_THRESHOLD_DAYS} "
                "days old; CLOSED when an opportunity exists; "
                "remaining leads are OPEN"
            ),
            "won": (
                "WON when annual_revenue >= product_base_price * "
                "OUTCOME_REVENUE_MULTIPLE; otherwise LOST; "
                "independent of lead-score rank and marketing activity"
            ),
            "amount": (
                "product base value x company-size multiplier, capped at "
                "1% of annual revenue when available; no floor overrides the cap"
            ),
            "ground_truth": (
                "injected anomaly labels are separate and are not scoring inputs"
            ),
        },
        "output_directory": str(OUT.relative_to(ROOT)),
        "ground_truth_directory": str(TRUTH.relative_to(ROOT)),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "generation_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, sort_keys=True)

    print("\nStaged generation completed.")
    print(json.dumps(summary["counts"], indent=2))
    print("Existing data/generated files and MySQL were NOT modified.")


if __name__ == "__main__":
    main()