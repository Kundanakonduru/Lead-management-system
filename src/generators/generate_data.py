import argparse
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SEED = 20261022
BASE_DATE = datetime(2026, 10, 30, 12, 0, 0)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "generated"

INDUSTRIES = [
    "IT", "Healthcare", "Finance", "Manufacturing",
    "Education", "Retail", "Telecommunications"
]

LOCATIONS = [
    ("Hyderabad", "Telangana", "India"),
    ("Bangalore", "Karnataka", "India"),
    ("Chennai", "Tamil Nadu", "India"),
    ("Mumbai", "Maharashtra", "India"),
    ("Pune", "Maharashtra", "India"),
    ("Delhi", "Delhi", "India"),
    ("Vijayawada", "Andhra Pradesh", "India"),
    ("Visakhapatnam", "Andhra Pradesh", "India")
]

SOURCES = [
    "WEBSITE", "EMAIL", "REFERRAL",
    "SOCIAL", "EVENT", "PAID_AD", "OTHER"
]

PRODUCTS = [
    ("PROD-000001", "Business Analytics", "Analytics"),
    ("PROD-000002", "Cloud Management", "Cloud"),
    ("PROD-000003", "CRM Software", "Business Software")
]


def write_csv(name, rows):
    if not rows:
        return

    path = OUTPUT / f"{name}.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"{name}: {len(rows):,} records")


def generate(companies_count, contacts_count, leads_count, seed):
    rng = random.Random(seed)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # 1. COMPANIES
    companies = []

    for i in range(1, companies_count + 1):
        city, state, country = rng.choice(LOCATIONS)
        size = rng.choices(
            ["SMB", "MID_MARKET", "ENTERPRISE"],
            weights=[60, 30, 10]
        )[0]

        employees = {
            "SMB": rng.randint(5, 100),
            "MID_MARKET": rng.randint(101, 1000),
            "ENTERPRISE": rng.randint(1001, 20000)
        }[size]

        companies.append({
            "company_id": f"CO-{i:06d}",
            "company_name": f"Company {i:06d}",
            "industry": rng.choice(INDUSTRIES),
            "company_size": size,
            "employee_count": employees,
            "annual_revenue": round(
                employees * rng.uniform(10000, 50000), 2
            ),
            "country": country,
            "state": state,
            "city": city,
            "website": f"https://company{i:06d}.example.com",
            "created_at": (
                BASE_DATE - timedelta(days=rng.randint(30, 1000))
            ).strftime("%Y-%m-%d %H:%M:%S")
        })

    write_csv("companies", companies)

    # 2. CONTACTS
    contacts = []
    company_contacts = defaultdict(list)

    for i in range(1, contacts_count + 1):
        company_index = (i - 1) % companies_count
        company_id = companies[company_index]["company_id"]

        contact_id = f"CON-{i:06d}"

        contacts.append({
            "contact_id": contact_id,
            "company_id": company_id,
            "first_name": f"First{i:06d}",
            "last_name": f"Last{i:06d}",
            "email": f"contact{i:06d}@example.com",
            "phone": f"+91{9000000000 + i:010d}"[-13:],
            "job_title": rng.choice([
                "IT Manager", "Director", "CEO",
                "HR Manager", "Business Analyst",
                "Software Engineer"
            ]),
            "created_at": (
                BASE_DATE - timedelta(days=rng.randint(10, 900))
            ).strftime("%Y-%m-%d %H:%M:%S")
        })

        company_contacts[company_id].append(contact_id)

    write_csv("contacts", contacts)

    # 3. CAMPAIGNS
    campaigns = []

    campaign_types = [
        "EMAIL", "WEBINAR", "SOCIAL",
        "PAID_AD", "EVENT", "OTHER"
    ]

    for i in range(1, 21):
        start = BASE_DATE.date() - timedelta(days=rng.randint(60, 500))
        campaigns.append({
            "campaign_id": f"CAMP-{i:06d}",
            "campaign_name": f"Campaign {i:03d}",
            "campaign_type": rng.choice(campaign_types),
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=30)).isoformat(),
            "budget": round(rng.uniform(10000, 500000), 2),
            "status": "COMPLETED"
        })

    write_csv("campaigns", campaigns)

    # 4. TERRITORIES
    territories = []
    territory_locations = LOCATIONS

    for i, (city, state, country) in enumerate(
        territory_locations, start=1
    ):
        territories.append({
            "territory_id": f"TER-{i:06d}",
            "territory_name": city.upper(),
            "region": state,
            "country": country
        })

    write_csv("territories", territories)

    # 5. PRODUCTS
    products = [
        {
            "product_id": pid,
            "product_name": name,
            "category": category,
            "active": 1
        }
        for pid, name, category in PRODUCTS
    ]

    write_csv("products", products)

    # 6. SALES REPRESENTATIVES
    sales_reps = []
    rep_products = []

    for i in range(1, 17):
        territory = territories[(i - 1) % len(territories)]

        rep_id = f"REP-{i:06d}"

        sales_reps.append({
            "sales_rep_id": rep_id,
            "rep_name": f"Sales Representative {i:03d}",
            "email": f"rep{i:03d}@example.com",
            "territory_id": territory["territory_id"],
            "active": 1,
            "created_at": BASE_DATE.strftime("%Y-%m-%d %H:%M:%S")
        })

        for product in products:
            rep_products.append({
                "sales_rep_id": rep_id,
                "product_id": product["product_id"]
            })

    write_csv("sales_reps", sales_reps)
    write_csv("sales_rep_products", rep_products)

    # 7. LEADS
    leads = []

    contacts_by_id = {
        contact["contact_id"]: contact for contact in contacts
    }

    company_by_id = {
        company["company_id"]: company for company in companies
    }

    for i in range(1, leads_count + 1):
        contact = contacts[(i - 1) % contacts_count]
        company = company_by_id[contact["company_id"]]

        location = next(
            loc for loc in LOCATIONS
            if loc[0] == company["city"]
        )

        territory_index = LOCATIONS.index(location)
        territory = territories[territory_index]

        product = rng.choice(products)

        created = BASE_DATE - timedelta(
            days=rng.randint(1, 700),
            hours=rng.randint(0, 23)
        )

        leads.append({
            "lead_id": f"LEAD-2026-{i:06d}",
            "contact_id": contact["contact_id"],
            "company_id": company["company_id"],
            "source": rng.choice(SOURCES),
            "product_id": product["product_id"],
            "territory_id": territory["territory_id"],
            "lead_status": "NEW",
            "fit_score": 0,
            "intent_score": 0,
            "engagement_score": 0,
            "total_score": 0,
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "last_activity_at": "",
            "assigned_rep_id": "",
            "is_duplicate": 0,
            "duplicate_of_lead_id": ""
        })

    write_csv("leads", leads)

    # 8. LEAD-CAMPAIGN RELATIONSHIPS
    lead_campaigns = []

    for lead in leads:
        campaign = rng.choice(campaigns)

        lead_campaigns.append({
            "lead_id": lead["lead_id"],
            "campaign_id": campaign["campaign_id"],
            "linked_at": lead["created_at"]
        })

    write_csv("lead_campaigns", lead_campaigns)

    # Reproducibility manifest
    manifest = {
        "seed": seed,
        "companies": companies_count,
        "contacts": contacts_count,
        "leads": leads_count,
        "campaigns": len(campaigns),
        "territories": len(territories),
        "products": len(products),
        "sales_reps": len(sales_reps),
        "generator_version": "1.0",
        "generated_at": BASE_DATE.isoformat()
    }

    import json

    (OUTPUT / "source_manifest.json").write_text(
        json.dumps(manifest, indent=4),
        encoding="utf-8"
    )

    print("\nMaster data generation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--companies", type=int, default=5000)
    parser.add_argument("--contacts", type=int, default=10000)
    parser.add_argument("--leads", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=SEED)

    args = parser.parse_args()

    if min(args.companies, args.contacts, args.leads) <= 0:
        parser.error("Record counts must be positive.")

    if args.contacts > 0 and args.companies <= 0:
        parser.error("Companies are required.")

    generate(
        args.companies,
        args.contacts,
        args.leads,
        args.seed
    )