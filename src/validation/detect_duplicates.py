import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"
OUTPUT = ROOT / "data" / "analytics"

OUTPUT.mkdir(parents=True, exist_ok=True)


def read_csv(filename):
    path = DATA / f"{filename}.csv"

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def normalize(value):
    return (value or "").strip().lower()


def normalize_phone(value):
    return "".join(
        character for character in (value or "")
        if character.isdigit()
    )


def detect_exact_duplicates(records, key_function, entity):
    groups = defaultdict(list)

    for record in records:
        key = key_function(record)
        if all(key):
            groups[key].append(record)

    results = []

    for key, matches in groups.items():
        if len(matches) > 1:
            original = matches[0]

            for duplicate in matches[1:]:
                results.append({
                    "entity": entity,
                    "original_id": original.get("company_id")
                        or original.get("contact_id")
                        or original.get("lead_id"),
                    "duplicate_id": duplicate.get("company_id")
                        or duplicate.get("contact_id")
                        or duplicate.get("lead_id"),
                    "matched_key": " | ".join(key),
                    "recommended_action": "FLAG_FOR_REVIEW"
                })

    return results


def detect_lead_duplicates(leads):
    groups = defaultdict(list)

    for lead in leads:
        key = (
            lead["contact_id"],
            lead["product_id"],
            lead["source"]
        )

        # Skip leads with missing duplicate-key fields
        if all(normalize(value) for value in key):
            groups[key].append(lead)

    results = []

    for key, records in groups.items():
        records.sort(key=lambda x: x["created_at"])

        original = None

        for lead in records:
            current_date = datetime.strptime(
                lead["created_at"], "%Y-%m-%d %H:%M:%S"
            )

            if original is None:
                original = lead
                continue

            original_date = datetime.strptime(
                original["created_at"], "%Y-%m-%d %H:%M:%S"
            )

            if (current_date - original_date).days <= 30:
                results.append({
                    "entity": "LEAD",
                    "original_id": original["lead_id"],
                    "duplicate_id": lead["lead_id"],
                    "matched_key": " | ".join(key),
                    "recommended_action": "FLAG_FOR_REVIEW"
                })
            else:
                original = lead

    return results


def main():
    companies = read_csv("companies")
    contacts = read_csv("contacts")
    leads = read_csv("leads")

    results = []

    # Company: normalized name + website
    # If website is missing, use normalized company name
    # as a review candidate key.
    results += detect_exact_duplicates(
        companies,
        lambda r: (
            normalize(r["company_name"]),
            normalize(r["website"])
            if normalize(r["website"])
            else "__missing_website__"
        ),
        "COMPANY"
    )

    # Contact: normalized email
    results += detect_exact_duplicates(
        contacts,
        lambda r: (normalize(r["email"]),),
        "CONTACT_EMAIL"
    )

    # Contact: normalized phone digits + company
    results += detect_exact_duplicates(
        contacts,
        lambda r: (
            normalize_phone(r["phone"]),
            normalize(r["company_id"])
        ),
        "CONTACT_PHONE"
    )

    # Lead: same contact + product + source within 30 days
    results += detect_lead_duplicates(leads)

    # Add duplicate flags to a separate enriched leads file
    duplicate_map = {
        row["duplicate_id"]: row["original_id"]
        for row in results
        if row["entity"] == "LEAD"
    }

    enriched_leads = []

    for lead in leads:
        lead_copy = lead.copy()
        original_id = duplicate_map.get(lead["lead_id"])

        lead_copy["is_duplicate"] = 1 if original_id else 0
        lead_copy["duplicate_of_lead_id"] = original_id or ""

        enriched_leads.append(lead_copy)

    enriched_path = OUTPUT / "leads_with_duplicate_flags.csv"

    with enriched_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(enriched_leads[0].keys())
        )
        writer.writeheader()
        writer.writerows(enriched_leads)

    print(f"Enriched leads file: {enriched_path}")

    audit_path = OUTPUT / "duplicate_audit.csv"

    fields = [
        "entity",
        "original_id",
        "duplicate_id",
        "matched_key",
        "recommended_action"
    ]

    with audit_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    summary = {
        "companies_checked": len(companies),
        "contacts_checked": len(contacts),
        "leads_checked": len(leads),
        "duplicate_cases_found": len(results),
        "duplicate_audit_file": str(audit_path.relative_to(ROOT))
    }

    summary_path = OUTPUT / "duplicate_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=4),
        encoding="utf-8"
    )

    print("\nDuplicate detection completed.")
    print(json.dumps(summary, indent=4))


if __name__ == "__main__":
    main()