import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
MASTER_DATA = ROOT / "data" / "generated"
DATA = ROOT / "data" / "staging" / "generated_v2"
TRUTH = ROOT / "data" / "staging" / "ground_truth_v2"
REPORT = ROOT / "data" / "analytics" / "validation_report_v2.json"

errors = []
warnings = []
metrics = {}

MASTER_FILES = {
    "companies", "contacts", "campaigns", "territories",
    "products", "sales_reps", "sales_rep_products", "lead_campaigns"
}

MASTER_SCHEMAS = {
    "companies": ["company_id", "company_name", "industry", "company_size",
        "employee_count", "annual_revenue", "country", "state", "city",
        "website", "created_at"],
    "contacts": ["contact_id", "company_id", "first_name", "last_name",
        "email", "phone", "job_title", "created_at"],
    "campaigns": ["campaign_id", "campaign_name", "campaign_type",
        "start_date", "end_date", "budget", "status"],
    "territories": ["territory_id", "territory_name", "region", "country"],
    "products": ["product_id", "product_name", "category", "active"],
    "sales_reps": ["sales_rep_id", "rep_name", "email", "territory_id",
        "active", "created_at"],
    "sales_rep_products": ["sales_rep_id", "product_id"],
    "lead_campaigns": ["lead_id", "campaign_id", "linked_at"],
    "leads": ["lead_id", "contact_id", "company_id", "source", "product_id",
        "territory_id", "lead_status", "fit_score", "intent_score",
        "engagement_score", "total_score", "created_at", "last_activity_at",
        "assigned_rep_id", "is_duplicate", "duplicate_of_lead_id"],
}

V2_SCHEMAS = {
    "leads": ["lead_id", "contact_id", "company_id", "source", "product_id",
        "territory_id", "lead_status", "fit_score", "intent_score",
        "engagement_score", "total_score", "created_at", "last_activity_at",
        "assigned_rep_id", "is_duplicate", "duplicate_of_lead_id",
        "is_qualified", "stale_status", "is_stale", "stale_since"],
    "consents": ["consent_id", "lead_id", "consent_type", "consent_status",
        "effective_from", "effective_to", "recorded_at", "source"],
    "activities": ["activity_id", "lead_id", "contact_id", "campaign_id",
        "activity_type", "activity_timestamp", "activity_value", "description"],
    "score_rules": ["rule_id", "rule_name", "feature_type", "feature_name",
        "weight", "effective_from", "effective_to", "active"],
    "tasks": ["task_id", "lead_id", "assigned_rep_id", "task_type",
        "priority", "due_at", "task_status", "created_at", "completed_at"],
    "opportunities": ["opportunity_id", "lead_id", "opportunity_name",
        "amount", "currency", "opportunity_stage", "created_at", "closed_at",
        "outcome_reason"],
    "stage_history": ["lead_id", "opportunity_id", "previous_stage",
        "new_stage", "changed_at", "changed_by", "change_reason"],
    "data_quality_issues": ["issue_id", "issue_type", "lead_id",
        "existing_opportunity_id", "attempted_action", "issue_status",
        "reason", "recorded_at"],
    "opportunity_evidence": ["evidence_id", "opportunity_id", "lead_id",
        "evidence_type", "annual_revenue_inr", "product_base_price_inr",
        "revenue_multiple_required", "required_annual_revenue_inr",
        "evidence_result", "rule_id", "evaluated_at", "evidence_source",
        "description"],
}

REQUIRED_FIELDS = {
    "companies": ["company_id", "company_name", "created_at"],
    "contacts": ["contact_id", "company_id", "first_name", "last_name", "email", "created_at"],
    "campaigns": ["campaign_id", "campaign_name", "start_date", "end_date"],
    "territories": ["territory_id", "territory_name"],
    "products": ["product_id", "product_name"],
    "sales_reps": ["sales_rep_id", "rep_name", "territory_id"],
    "sales_rep_products": ["sales_rep_id", "product_id"],
    "lead_campaigns": ["lead_id", "campaign_id", "linked_at"],
    "leads": ["lead_id", "contact_id", "company_id", "source", "product_id",
        "territory_id", "lead_status", "fit_score", "intent_score",
        "engagement_score", "total_score", "created_at"],
    "consents": ["consent_id", "lead_id", "consent_type", "consent_status",
        "effective_from", "recorded_at"],
    "activities": ["activity_id", "lead_id", "activity_type", "activity_timestamp"],
    "score_rules": ["rule_id", "rule_name", "feature_type", "feature_name", "weight", "effective_from"],
    "tasks": ["task_id", "lead_id", "task_type", "priority", "due_at", "task_status", "created_at"],
    "opportunities": ["opportunity_id", "lead_id", "opportunity_name", "amount", "currency", "opportunity_stage", "created_at"],
    "stage_history": ["lead_id", "opportunity_id", "new_stage", "changed_at", "changed_by"],
    "data_quality_issues": ["issue_id", "issue_type", "lead_id", "issue_status", "recorded_at"],
    "opportunity_evidence": ["evidence_id", "opportunity_id", "lead_id", "evidence_type", "evidence_result", "evaluated_at"],
}

PRIMARY_KEYS = {
    "companies": "company_id", "contacts": "contact_id", "campaigns": "campaign_id",
    "territories": "territory_id", "products": "product_id",
    "sales_reps": "sales_rep_id", "leads": "lead_id", "consents": "consent_id",
    "activities": "activity_id", "score_rules": "rule_id", "tasks": "task_id",
    "opportunities": "opportunity_id", "data_quality_issues": "issue_id",
    "opportunity_evidence": "evidence_id",
}
COMPOSITE_KEYS = {
    "sales_rep_products": ["sales_rep_id", "product_id"],
    "lead_campaigns": ["lead_id", "campaign_id"],
}

# OUTCOME-001 is a deterministic evidence rule, not a score_rules row.
RELATIONSHIPS = [
    ("contacts", "company_id", "companies", "company_id", False),
    ("sales_reps", "territory_id", "territories", "territory_id", False),
    ("sales_rep_products", "sales_rep_id", "sales_reps", "sales_rep_id", False),
    ("sales_rep_products", "product_id", "products", "product_id", False),
    ("leads", "contact_id", "contacts", "contact_id", False),
    ("leads", "company_id", "companies", "company_id", False),
    ("leads", "product_id", "products", "product_id", False),
    ("leads", "territory_id", "territories", "territory_id", False),
    ("leads", "assigned_rep_id", "sales_reps", "sales_rep_id", True),
    ("leads", "duplicate_of_lead_id", "leads", "lead_id", True),
    ("lead_campaigns", "lead_id", "leads", "lead_id", False),
    ("lead_campaigns", "campaign_id", "campaigns", "campaign_id", False),
    ("activities", "lead_id", "leads", "lead_id", False),
    ("activities", "contact_id", "contacts", "contact_id", True),
    ("activities", "campaign_id", "campaigns", "campaign_id", True),
    ("consents", "lead_id", "leads", "lead_id", False),
    ("tasks", "lead_id", "leads", "lead_id", False),
    ("tasks", "assigned_rep_id", "sales_reps", "sales_rep_id", True),
    ("opportunities", "lead_id", "leads", "lead_id", False),
    ("stage_history", "lead_id", "leads", "lead_id", False),
    ("stage_history", "opportunity_id", "opportunities", "opportunity_id", False),
    ("data_quality_issues", "lead_id", "leads", "lead_id", True),
    ("data_quality_issues", "existing_opportunity_id", "opportunities", "opportunity_id", True),
    ("opportunity_evidence", "opportunity_id", "opportunities", "opportunity_id", False),
    ("opportunity_evidence", "lead_id", "leads", "lead_id", False),
]

ENUM_RULES = {
    ("consents", "consent_type"): {"EMAIL_MARKETING", "PHONE_MARKETING", "DATA_PROCESSING"},
    ("consents", "consent_status"): {"GRANTED", "PENDING", "REVOKED"},
    ("tasks", "priority"): {"LOW", "MEDIUM", "HIGH"},
    ("tasks", "task_status"): {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"},
    ("opportunities", "opportunity_stage"): {"WON", "LOST"},
    ("score_rules", "feature_type"): {"FIT", "INTENT", "ENGAGEMENT"},
    ("opportunities", "currency"): {"INR"},
}

ID_PATTERNS = {
    "companies": ("company_id", r"CO-\d{6}"),
    "contacts": ("contact_id", r"CON-\d{6}"),
    "territories": ("territory_id", r"TER-\d{6}"),
    "products": ("product_id", r"PROD-\d{6}"),
    "sales_reps": ("sales_rep_id", r"REP-\d{6}"),
    "leads": ("lead_id", r"LEAD-2026-\d{6}"),
    "consents": ("consent_id", r"CONS-LEAD-2026-\d{6}-(?:EMA|PHO|DAT)"),
    "activities": ("activity_id", r"ACT-LEAD-2026-\d{6}-(?:\d{3}|EX001|EX002)"),
    "tasks": ("task_id", r"TASK-LEAD-2026-\d{6}-\d{3}"),
    "score_rules": ("rule_id", r"RULE-\d{4}"),
    "opportunities": ("opportunity_id", r"OPP-2026-\d{6}"),
    "data_quality_issues": ("issue_id", r"EX-\d{3}"),
    "opportunity_evidence": ("evidence_id", r"EVD-\d{6}"),
}


def is_blank(value):
    return value is None or str(value).strip() == ""


def load_csv(path, label):
    if not path.exists():
        errors.append(f"Missing CSV file: {path}")
        return [], []
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if not headers:
                errors.append(f"{label}: missing CSV header")
                return [], []
            if len(headers) != len(set(headers)):
                errors.append(f"{label}: duplicate column names in header")
            return list(reader), headers
    except (OSError, csv.Error, UnicodeError) as exc:
        errors.append(f"{label}: unable to read CSV: {exc}")
        return [], []


def load_all():
    tables, headers = {}, {}
    for name in MASTER_FILES:
        tables[name], headers[name] = load_csv(MASTER_DATA / f"{name}.csv", f"master.{name}")
    tables["master_leads"], headers["master_leads"] = load_csv(
        MASTER_DATA / "leads.csv", "master.leads")
    for name in V2_SCHEMAS:
        tables[name], headers[name] = load_csv(DATA / f"{name}.csv", f"v2.{name}")
    return tables, headers


def check_schema(headers, expected, label):
    actual = list(headers)
    missing, extra = sorted(set(expected) - set(actual)), sorted(set(actual) - set(expected))
    if missing:
        errors.append(f"{label}: missing columns {missing}")
    if extra:
        errors.append(f"{label}: unexpected columns {extra}")
    metrics[f"{label}_column_count"] = len(actual)


def check_required(rows, fields, name):
    count = 0
    for rn, row in enumerate(rows, 2):
        for field in fields:
            if field not in row or is_blank(row.get(field)):
                count += 1
                if count <= 10:
                    errors.append(f"{name}, row {rn}: missing required field '{field}'")
    metrics[f"{name}_missing_required"] = count


def check_unique(rows, fields, name):
    if isinstance(fields, str):
        fields = [fields]
    seen, duplicates, blanks = set(), 0, 0
    for row in rows:
        key = tuple(str(row.get(f, "")).strip() for f in fields)
        if any(not v for v in key):
            blanks += 1
        elif key in seen:
            duplicates += 1
        else:
            seen.add(key)
    if blanks:
        errors.append(f"{name}: {blanks} blank key combinations")
    if duplicates:
        errors.append(f"{name}: {duplicates} duplicate key combinations")
    metrics[f"{name}_duplicate_keys"] = duplicates
    metrics[f"{name}_blank_keys"] = blanks


def check_fk(child, field, parent, parent_field, name, optional=False):
    valid = {str(r.get(parent_field, "")).strip() for r in parent if not is_blank(r.get(parent_field))}
    invalid = blank = 0
    for row in child:
        value = str(row.get(field, "")).strip()
        if not value:
            if not optional:
                blank += 1
        elif value not in valid:
            invalid += 1
    if invalid:
        errors.append(f"{name}: {invalid} invalid foreign keys")
    if blank:
        errors.append(f"{name}: {blank} blank required foreign keys")
    metrics[f"{name}_invalid_fk"] = invalid
    metrics[f"{name}_blank_fk"] = blank


def parse_datetime(value, field, record_id):
    if is_blank(value):
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
    except (ValueError, TypeError, OverflowError):
        errors.append(f"{record_id}: invalid date in {field}: {value}")
        return None


def check_number(value, field, record_id, minimum=None, maximum=None):
    try:
        number = float(value)
    except (ValueError, TypeError):
        errors.append(f"{record_id}: {field} must be numeric")
        return None
    if not math.isfinite(number):
        errors.append(f"{record_id}: {field} must be finite")
        return None
    if minimum is not None and number < minimum:
        errors.append(f"{record_id}: {field} is below {minimum}")
    if maximum is not None and number > maximum:
        errors.append(f"{record_id}: {field} exceeds {maximum}")
    return number


def check_enum(rows, field, allowed, name):
    invalid = Counter(str(r.get(field, "")).strip() for r in rows
                      if not is_blank(r.get(field)) and str(r.get(field)).strip() not in allowed)
    if invalid:
        errors.append(f"{name}.{field}: invalid values {dict(invalid)}")
    metrics[f"{name}_{field}_invalid"] = sum(invalid.values())


def validate_zero_padded_ids(tables):
    checked = malformed = 0
    for table, (field, pattern) in ID_PATTERNS.items():
        for row in tables[table]:
            value = str(row.get(field, "")).strip()
            if not value:
                continue
            checked += 1
            if re.fullmatch(pattern, value) is None:
                malformed += 1
                if malformed <= 30:
                    errors.append(f"{table}: ID '{value}' does not match {pattern}")
    # Campaign prefix is not hard-coded; enforce one prefix and one suffix width.
    campaign_ids = [str(r.get("campaign_id", "")).strip() for r in tables["campaigns"]
                    if not is_blank(r.get("campaign_id"))]
    matches = [re.fullmatch(r"(.+?)(\d+)", value) for value in campaign_ids]
    if any(m is None for m in matches):
        errors.append("campaigns: one or more campaign IDs lack a numeric suffix")
        malformed += sum(m is None for m in matches)
    elif matches:
        if len({m.group(1) for m in matches}) != 1 or len({len(m.group(2)) for m in matches}) != 1:
            errors.append("campaigns: ID prefix or numeric suffix width is inconsistent")
            malformed += 1
        checked += len(matches)
    metrics["zero_padded_ids_checked"] = checked
    metrics["zero_padded_ids_malformed"] = malformed


def validate_master_v2_lead_alignment(tables):
    master = {r.get("lead_id", "").strip() for r in tables["master_leads"] if not is_blank(r.get("lead_id"))}
    v2 = {r.get("lead_id", "").strip() for r in tables["leads"] if not is_blank(r.get("lead_id"))}
    metrics["master_lead_count"] = len(tables["master_leads"])
    metrics["v2_lead_count"] = len(tables["leads"])
    metrics["master_v2_lead_ids_match"] = master == v2
    if master != v2:
        errors.append(f"Master/V2 lead ID mismatch: {len(master-v2)} missing in V2; {len(v2-master)} extra in V2.")


def validate_date_order(tables):
    for row in tables["campaigns"]:
        start = parse_datetime(row.get("start_date"), "start_date", row.get("campaign_id", "UNKNOWN"))
        end = parse_datetime(row.get("end_date"), "end_date", row.get("campaign_id", "UNKNOWN"))
        if start and end and start > end:
            errors.append(f"{row.get('campaign_id')}: campaign starts after end date")
    for row in tables["consents"]:
        start = parse_datetime(row.get("effective_from"), "effective_from", row.get("consent_id", "UNKNOWN"))
        end = parse_datetime(row.get("effective_to"), "effective_to", row.get("consent_id", "UNKNOWN"))
        if start and end and start > end:
            errors.append(f"{row.get('consent_id')}: consent end precedes start")
    lead_dates = {r.get("lead_id"): parse_datetime(r.get("created_at"), "created_at", r.get("lead_id", "UNKNOWN"))
                  for r in tables["leads"]}
    for row in tables["activities"]:
        at = parse_datetime(row.get("activity_timestamp"), "activity_timestamp", row.get("activity_id", "UNKNOWN"))
        created = lead_dates.get(row.get("lead_id"))
        if at and created and at < created:
            errors.append(f"{row.get('activity_id')}: activity precedes lead creation")
    for row in tables["opportunities"]:
        created = parse_datetime(row.get("created_at"), "created_at", row.get("opportunity_id", "UNKNOWN"))
        closed = parse_datetime(row.get("closed_at"), "closed_at", row.get("opportunity_id", "UNKNOWN"))
        if created and closed and closed < created:
            errors.append(f"{row.get('opportunity_id')}: close date precedes creation")
        if row.get("opportunity_stage") in {"WON", "LOST"} and closed is None:
            errors.append(f"{row.get('opportunity_id')}: closed opportunity has no close date")
    for row in tables["tasks"]:
        created = parse_datetime(row.get("created_at"), "created_at", row.get("task_id", "UNKNOWN"))
        completed = parse_datetime(row.get("completed_at"), "completed_at", row.get("task_id", "UNKNOWN"))
        if created and completed and completed < created:
            errors.append(f"{row.get('task_id')}: task completion precedes creation")
    opp_dates = {r.get("opportunity_id"): parse_datetime(r.get("created_at"), "created_at", r.get("opportunity_id", "UNKNOWN"))
                 for r in tables["opportunities"]}
    for row in tables["opportunity_evidence"]:
        evaluated = parse_datetime(row.get("evaluated_at"), "evaluated_at", row.get("evidence_id", "UNKNOWN"))
        created = opp_dates.get(row.get("opportunity_id"))
        if evaluated and created and evaluated < created:
            errors.append(f"{row.get('evidence_id')}: evidence evaluated before opportunity creation")


def validate_scores(tables):
    checked = mismatches = 0
    for row in tables["leads"]:
        lid = row.get("lead_id", "UNKNOWN")
        vals = [check_number(row.get(f), f, lid, 0, 100)
                for f in ("fit_score", "intent_score", "engagement_score", "total_score")]
        if any(v is None for v in vals):
            continue
        fit, intent, engagement, total = vals
        expected = round(fit * .35 + intent * .35 + engagement * .30, 2)
        checked += 1
        if abs(expected - total) > .01:
            mismatches += 1
            if mismatches <= 20:
                errors.append(f"{lid}: score mismatch; expected {expected}, found {total}")
    metrics["score_records_checked"] = checked
    metrics["score_mismatches"] = mismatches


def validate_numeric_fields(tables):
    rules = {
        "companies": {"employee_count": (0, None), "annual_revenue": (0, None)},
        "campaigns": {"budget": (0, None)}, "score_rules": {"weight": (0, 1)},
        "activities": {"activity_value": (0, None)}, "opportunities": {"amount": (.01, None)},
        "opportunity_evidence": {"annual_revenue_inr": (0, None),
            "product_base_price_inr": (0, None), "revenue_multiple_required": (0, None),
            "required_annual_revenue_inr": (0, None)},
    }
    for table, fields in rules.items():
        for row in tables[table]:
            rid = next((row.get(k) for k in ("company_id", "campaign_id", "rule_id",
                "activity_id", "opportunity_id", "evidence_id") if row.get(k)), "UNKNOWN")
            for field, (lo, hi) in fields.items():
                if not is_blank(row.get(field)):
                    check_number(row[field], field, rid, lo, hi)


def validate_territory_routing(tables):
    rep_territory = {r.get("sales_rep_id"): r.get("territory_id") for r in tables["sales_reps"]}
    violations = {r.get("lead_id") for r in tables["leads"]
                  if not is_blank(r.get("assigned_rep_id"))
                  and rep_territory.get(r.get("assigned_rep_id")) != r.get("territory_id")}
    metrics["territory_violations"] = len(violations)
    metrics["territory_violation_lead_ids"] = sorted(violations)
    return violations


def validate_consent(tables):
    consent_map = defaultdict(list)
    for row in tables["consents"]:
        consent_map[(row.get("lead_id"), row.get("consent_type"))].append(row)
    event_to_consent = {"EMAIL_SENT": "EMAIL_MARKETING", "EMAIL_OPENED": "EMAIL_MARKETING",
        "EMAIL_CLICKED": "EMAIL_MARKETING", "PHONE_CALL": "PHONE_MARKETING"}
    violations = set()
    for activity in tables["activities"]:
        ctype = event_to_consent.get(activity.get("activity_type"))
        if not ctype:
            continue
        at = parse_datetime(activity.get("activity_timestamp"), "activity_timestamp",
                            activity.get("activity_id", "UNKNOWN"))
        if at is None:
            continue
        authorized = False
        for consent in consent_map.get((activity.get("lead_id"), ctype), []):
            start = parse_datetime(consent.get("effective_from"), "effective_from",
                                   consent.get("consent_id", "UNKNOWN"))
            end = parse_datetime(consent.get("effective_to"), "effective_to",
                                 consent.get("consent_id", "UNKNOWN"))
            status = str(consent.get("consent_status", "")).strip().upper()
            # REVOKED row retains the historical interval [effective_from, effective_to).
            # PENDING never grants permission; after effective_to, contact is prohibited.
            if status in {"GRANTED", "REVOKED"} and start and at >= start and (end is None or at < end):
                authorized = True
                break
        if not authorized:
            violations.add(activity.get("activity_id"))
    metrics["consent_violations"] = len(violations)
    metrics["consent_violation_activity_ids"] = sorted(violations)
    return violations


def validate_opportunities(tables):
    rows = tables["opportunities"]
    won = sum(r.get("opportunity_stage") == "WON" for r in rows)
    lost = sum(r.get("opportunity_stage") == "LOST" for r in rows)
    other = len(rows) - won - lost
    metrics.update({"won": won, "lost": lost, "other_opportunity_stages": other,
                    "total_opportunities": len(rows), "funnel_reconciles": won + lost == len(rows)})
    if other:
        errors.append(f"{other} opportunities have an unrecognized outcome stage.")
    if won + lost != len(rows):
        errors.append("Opportunity funnel does not reconcile.")


def validate_stage_history(tables):
    grouped, exact = defaultdict(list), set()
    duplicates = 0
    for row in tables["stage_history"]:
        changed = parse_datetime(row.get("changed_at"), "changed_at", row.get("opportunity_id", "UNKNOWN"))
        if changed is None:
            continue
        key = (row.get("opportunity_id"), row.get("previous_stage"),
               row.get("new_stage"), changed, row.get("changed_by"))
        if key in exact:
            duplicates += 1
        exact.add(key)
        grouped[row.get("opportunity_id")].append((changed, row))
    gaps = set()
    for oid, records in grouped.items():
        records.sort(key=lambda x: x[0])
        for i in range(1, len(records)):
            if records[i-1][1].get("new_stage") != records[i][1].get("previous_stage"):
                gaps.add(oid)
    metrics["stage_history_opportunities"] = len(grouped)
    metrics["duplicate_stage_transitions"] = duplicates
    metrics["stage_history_sequence_gaps"] = len(gaps)
    metrics["stage_history_gap_opportunity_ids"] = sorted(gaps)
    if duplicates:
        errors.append(f"{duplicates} duplicate stage-history events.")


def validate_evidence_arithmetic(tables):
    checked = mismatches = 0
    rule_ids = set()
    for row in tables["opportunity_evidence"]:
        rule_ids.add(str(row.get("rule_id", "")).strip())
        rid = row.get("evidence_id", "UNKNOWN")
        base = check_number(row.get("product_base_price_inr"), "product_base_price_inr", rid, 0)
        multiple = check_number(row.get("revenue_multiple_required"), "revenue_multiple_required", rid, 0)
        required = check_number(row.get("required_annual_revenue_inr"), "required_annual_revenue_inr", rid, 0)
        actual = check_number(row.get("annual_revenue_inr"), "annual_revenue_inr", rid, 0)
        if None in (base, multiple, required, actual):
            continue
        checked += 1
        expected_required = base * multiple
        if abs(expected_required - required) > max(.01, abs(expected_required) * 1e-8):
            mismatches += 1
            if mismatches <= 20:
                errors.append(f"{rid}: required revenue does not equal base price × multiple")
        result = str(row.get("evidence_result", "")).strip().upper()
        expected_result = "PASS" if actual >= required else "FAIL"
        if result != expected_result:
            errors.append(f"{rid}: evidence_result {result}; expected {expected_result}")
    metrics["evidence_arithmetic_records_checked"] = checked
    metrics["evidence_arithmetic_mismatches"] = mismatches
    metrics["outcome_rule_id_present"] = rule_ids == {"OUTCOME-001"}
    if rule_ids != {"OUTCOME-001"}:
        errors.append(f"opportunity_evidence: expected only OUTCOME-001; found {sorted(rule_ids)}")


def validate_ground_truth(tables):
    path = TRUTH / "ground_truth.json"
    if not path.exists():
        errors.append(f"Missing ground-truth file: {path}")
        return
    try:
        with path.open(encoding="utf-8") as f:
            truth = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Unable to read ground_truth.json: {exc}")
        return
    if not isinstance(truth, list):
        errors.append("ground_truth.json must contain a list of issue records.")
        return
    expected = {
        "EX-001": ("OPTED_OUT_CONTACTED", "BLOCK_CONTACT"),
        "EX-002": ("POST_CONVERSION_ACTIVITY", "EXCLUDE_FROM_SCORE"),
        "EX-003": ("OUTSIDE_TERRITORY_ASSIGNMENT", "REJECT_ASSIGNMENT"),
        "EX-004": ("DUPLICATE_OPPORTUNITY", "REJECT_DUPLICATE"),
        "EX-005": ("STAGE_HISTORY_GAP", "FLAG_MISSING_TRANSITION"),
    }
    by_id = {r.get("issue_id"): r for r in truth if isinstance(r, dict)}
    if len(truth) != 5 or len(by_id) != 5 or set(by_id) != set(expected):
        errors.append("Ground truth must contain exactly EX-001 through EX-005 once each.")
    for iid, (itype, decision) in expected.items():
        row = by_id.get(iid)
        if row is not None and (row.get("issue_type") != itype or row.get("expected_decision") != decision):
            errors.append(f"{iid}: ground-truth type/expected decision mismatch")
    metrics["ground_truth_cases"] = len(truth)
    metrics["ground_truth_issue_types"] = len({r.get("issue_type") for r in truth if isinstance(r, dict)})

    # EX-001: exactly one EMAIL_SENT with EX001 suffix after email consent expiry.
    ex1 = by_id.get("EX-001", {})
    lead1 = ex1.get("lead_id")
    acts1 = [a for a in tables["activities"] if a.get("lead_id") == lead1
             and a.get("activity_type") == "EMAIL_SENT"
             and str(a.get("activity_id", "")).endswith("-EX001")]
    revoked_after = False
    for a in acts1:
        at = parse_datetime(a.get("activity_timestamp"), "activity_timestamp", a.get("activity_id", "EX-001"))
        for c in tables["consents"]:
            if c.get("lead_id") == lead1 and c.get("consent_type") == "EMAIL_MARKETING":
                end = parse_datetime(c.get("effective_to"), "effective_to", c.get("consent_id", "EX-001"))
                if at and end and at >= end:
                    revoked_after = True
    consent_violations = set(metrics.get("consent_violation_activity_ids", []))
    ids1 = {a.get("activity_id") for a in acts1}
    s1 = len(acts1) == 1 and revoked_after and consent_violations == ids1

    # EX-002: labelled DEMO_COMPLETED must occur after a WON close.
    ex2 = by_id.get("EX-002", {})
    lead2 = ex2.get("lead_id")
    acts2 = [a for a in tables["activities"] if a.get("lead_id") == lead2
             and a.get("activity_type") == "DEMO_COMPLETED"
             and str(a.get("activity_id", "")).endswith("-EX002")]
    opps2 = [o for o in tables["opportunities"] if o.get("lead_id") == lead2]
    s2 = False
    for a in acts2:
        at = parse_datetime(a.get("activity_timestamp"), "activity_timestamp", a.get("activity_id", "EX-002"))
        for o in opps2:
            closed = parse_datetime(o.get("closed_at"), "closed_at", o.get("opportunity_id", "EX-002"))
            if at and closed and at > closed and o.get("opportunity_stage") == "WON":
                s2 = True
    s2 = s2 and len(acts2) == 1

    # EX-003: exactly the labelled lead is out of territory.
    ex3lead = by_id.get("EX-003", {}).get("lead_id")
    rep_territory = {r.get("sales_rep_id"): r.get("territory_id") for r in tables["sales_reps"]}
    lead3 = next((r for r in tables["leads"] if r.get("lead_id") == ex3lead), None)
    violations3 = set(metrics.get("territory_violation_lead_ids", []))
    s3 = (lead3 is not None and violations3 == {ex3lead}
          and rep_territory.get(lead3.get("assigned_rep_id")) != lead3.get("territory_id"))

    # EX-004: one duplicate-opportunity audit event, not five duplicated labels.
    audit4 = [r for r in tables["data_quality_issues"]
              if r.get("issue_id") == "EX-004" and r.get("issue_type") == "DUPLICATE_OPPORTUNITY"]
    s4 = len(audit4) == 1

    # EX-005: exactly one stage-history gap, linked to the labelled opportunity.
    ex5opp = by_id.get("EX-005", {}).get("opportunity_id")
    gaps = set(metrics.get("stage_history_gap_opportunity_ids", []))
    s5 = bool(ex5opp) and gaps == {ex5opp}

    checks = {"EX-001": s1, "EX-002": s2, "EX-003": s3, "EX-004": s4, "EX-005": s5}
    for iid, passed in checks.items():
        if not passed:
            errors.append(f"{iid}: injected exception failed its scenario-specific validation.")
    metrics["scenario_verification"] = checks
    metrics["all_ground_truth_scenarios_verified"] = all(checks.values())


def validate_duplicate_leads(tables):
    by_id = {r.get("lead_id"): r for r in tables["leads"] if not is_blank(r.get("lead_id"))}
    bad_refs = bad_flags = 0
    for row in tables["leads"]:
        flag = str(row.get("is_duplicate", "")).strip().lower()
        anchor = row.get("duplicate_of_lead_id")
        if flag in {"1", "true", "yes"}:
            if is_blank(anchor) or anchor not in by_id or anchor == row.get("lead_id"):
                bad_refs += 1
        elif flag in {"0", "false", "no"} and not is_blank(anchor):
            bad_flags += 1
    metrics["duplicate_lead_invalid_references"] = bad_refs
    metrics["duplicate_lead_flag_conflicts"] = bad_flags
    if bad_refs:
        errors.append(f"{bad_refs} duplicate leads have missing/invalid anchor references.")
    if bad_flags:
        errors.append(f"{bad_flags} non-duplicate leads have duplicate anchor references.")


def validate_baseline_counts(tables):
    minimums = {"companies": 5000, "contacts": 10000, "leads": 20000, "opportunities": 3000}
    for name, minimum in minimums.items():
        actual = len(tables[name])
        metrics[f"{name}_minimum_required"] = minimum
        if actual < minimum:
            errors.append(f"{name}: expected at least {minimum} rows; found {actual}")


def main():
    tables, headers = load_all()
    for name, rows in tables.items():
        metrics[f"{name}_rows"] = len(rows)

    for name, schema in MASTER_SCHEMAS.items():
        if name == "leads":
            check_schema(headers.get("master_leads", []), schema, "master.leads")
        else:
            check_schema(headers.get(name, []), schema, f"master.{name}")
    for name, schema in V2_SCHEMAS.items():
        check_schema(headers.get(name, []), schema, f"v2.{name}")

    for name, fields in REQUIRED_FIELDS.items():
        check_required(tables[name], fields, f"v2.{name}")
    master_required = {
        "companies": ["company_id", "company_name", "created_at"],
        "contacts": ["contact_id", "company_id", "first_name", "last_name", "email", "created_at"],
        "campaigns": ["campaign_id", "campaign_name", "start_date", "end_date"],
        "territories": ["territory_id", "territory_name"],
        "products": ["product_id", "product_name"],
        "sales_reps": ["sales_rep_id", "rep_name", "territory_id"],
    }
    for name, fields in master_required.items():
        check_required(tables[name], fields, f"master.{name}")

    for name, field in PRIMARY_KEYS.items():
        check_unique(tables[name], field, f"v2.{name}")
    for name, fields in COMPOSITE_KEYS.items():
        check_unique(tables[name], fields, f"master.{name}")
    check_unique(tables["master_leads"], "lead_id", "master.leads")

    for child, field, parent, parent_field, optional in RELATIONSHIPS:
        check_fk(tables[child], field, tables[parent], parent_field, f"{child}.{field}", optional)
    check_unique(tables["opportunities"], "lead_id", "opportunities.lead_id")

    for (table, field), allowed in ENUM_RULES.items():
        check_enum(tables[table], field, allowed, table)

    validate_master_v2_lead_alignment(tables)
    validate_baseline_counts(tables)
    validate_zero_padded_ids(tables)
    validate_scores(tables)
    validate_numeric_fields(tables)
    validate_date_order(tables)
    validate_duplicate_leads(tables)
    validate_territory_routing(tables)
    validate_consent(tables)
    validate_opportunities(tables)
    validate_stage_history(tables)
    validate_evidence_arithmetic(tables)
    validate_ground_truth(tables)

    # The five documented exceptions are expected test fixtures. They are
    # reported as metrics and do not become warnings/errors when verified.
    # Unexpected or missing exceptions are caught by scenario-specific checks.
    if errors:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    report = {"status": status, "metrics": metrics, "errors": errors, "warnings": warnings}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=4), encoding="utf-8")

    print("\n========== VALIDATION REPORT ==========")
    print("Status:", status)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print("\nErrors:", len(errors))
    for item in errors[:40]:
        print("-", item)
    print("\nWarnings:", len(warnings))
    for item in warnings[:30]:
        print("-", item)
    print("\nReport saved:", REPORT)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()