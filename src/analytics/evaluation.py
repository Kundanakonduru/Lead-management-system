from pathlib import Path
import pandas as pd
import json
import math

ROOT = Path(__file__).resolve().parents[2]

# Read corrected V2 datasets
DATA_DIR = ROOT / "data" / "staging" / "generated_v2"
OUTPUT_DIR = ROOT / "data" / "analytics"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data(filename):
    file_path = DATA_DIR / f"{filename}.csv"

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return pd.read_csv(file_path)


def safe_percentage(numerator, denominator):
    return round(numerator / denominator * 100, 2) if denominator else 0.0


def safe_average(series):
    return round(float(series.mean()), 2) if not series.empty else 0.0


def evaluate():
    leads = load_data("leads")
    opportunities = load_data("opportunities")

    # Normalize values
    leads["lead_status"] = (
        leads["lead_status"].astype(str).str.strip().str.upper()
    )

    opportunities["opportunity_stage"] = (
        opportunities["opportunity_stage"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Validate lead scores
    leads["total_score"] = pd.to_numeric(
        leads["total_score"], errors="coerce"
    )

    if leads["total_score"].isna().any():
        raise ValueError("Missing or invalid lead scores found")

    if not leads["total_score"].map(math.isfinite).all():
        raise ValueError("Non-finite lead scores found")

    if not leads["total_score"].between(0, 100).all():
        raise ValueError("Lead scores must be between 0 and 100")

    # Validate opportunity amounts
    opportunities["amount"] = pd.to_numeric(
        opportunities["amount"], errors="coerce"
    )

    if opportunities["amount"].isna().any():
        raise ValueError("Missing or invalid opportunity amounts found")

    if not opportunities["amount"].map(math.isfinite).all():
        raise ValueError("Non-finite opportunity amounts found")

    if (opportunities["amount"] <= 0).any():
        raise ValueError("Opportunity amounts must be positive")

    # Qualification flag validation
    if "is_qualified" not in leads.columns:
        raise ValueError("Missing required column: is_qualified")

    leads["is_qualified"] = pd.to_numeric(
        leads["is_qualified"], errors="coerce"
    )

    if leads["is_qualified"].isna().any():
        raise ValueError("Invalid or missing values in is_qualified")

    if not leads["is_qualified"].isin([0, 1]).all():
        raise ValueError("is_qualified must contain only 0 or 1")

    # Lead metrics
    total_leads = len(leads)

    qualified_leads = leads[
        leads["is_qualified"] == 1
    ]

    not_qualified_leads = leads[
        leads["is_qualified"] == 0
    ]

    qualified_count = len(qualified_leads)
    not_qualified_count = len(not_qualified_leads)

    new_leads_count = int(
        (leads["lead_status"] == "NEW").sum()
    )

    # Opportunity metrics
    total_opportunities = len(opportunities)

    won = opportunities[
        opportunities["opportunity_stage"] == "WON"
    ]

    lost = opportunities[
        opportunities["opportunity_stage"] == "LOST"
    ]

    won_count = len(won)
    lost_count = len(lost)

    # Validate opportunity records
    if opportunities["lead_id"].isna().any():
        raise ValueError("Missing lead IDs in opportunity records")

    if opportunities["lead_id"].duplicated().any():
        raise ValueError(
            "Duplicate opportunity records found for a lead"
        )

    opportunity_lead_ids = set(
        opportunities["lead_id"].dropna()
    )

    qualified_lead_ids = set(
        qualified_leads["lead_id"].dropna()
    )

    all_lead_ids = set(leads["lead_id"].dropna())

    if not opportunity_lead_ids.issubset(all_lead_ids):
        raise ValueError(
            "Opportunity records contain unknown lead IDs"
        )

    if opportunity_lead_ids != qualified_lead_ids:
        raise ValueError(
            "Qualified leads and opportunity leads do not match"
        )

    if won_count + lost_count != total_opportunities:
        raise ValueError(
            "Opportunity stages do not reconcile into WON and LOST"
        )

    # Converted and lost lead metrics
    won_lead_ids = set(won["lead_id"].dropna())
    lost_lead_ids = set(lost["lead_id"].dropna())

    converted_count = len(won_lead_ids)
    lost_lead_count = len(lost_lead_ids)

    if won_lead_ids.intersection(lost_lead_ids):
        raise ValueError(
            "A lead cannot have both WON and LOST outcomes"
        )

    # Revenue and opportunity value
    won_revenue = float(won["amount"].sum())

    total_opportunity_value = float(
        opportunities["amount"].sum()
    )

    lost_opportunity_value = float(
        lost["amount"].sum()
    )

    average_deal_value = (
        won_revenue / won_count if won_count else 0
    )

    # Score comparison by outcome group
    leads["conversion_outcome"] = leads["lead_id"].isin(
        won_lead_ids
    )

    won_leads = leads[
        leads["lead_id"].isin(won_lead_ids)
    ]

    lost_leads = leads[
        leads["lead_id"].isin(lost_lead_ids)
    ]

    non_won_leads = leads[
        ~leads["conversion_outcome"]
    ]

    average_score_won = safe_average(
        won_leads["total_score"]
    )

    average_score_lost = safe_average(
        lost_leads["total_score"]
    )

    average_score_not_qualified = safe_average(
        not_qualified_leads["total_score"]
    )

    average_score_non_won = safe_average(
        non_won_leads["total_score"]
    )

    # Business evaluation
    metrics = {
        "dataset": "generated_v2",

        "total_leads": int(total_leads),
        "qualified_leads": int(qualified_count),
        "not_qualified_leads": int(not_qualified_count),
        "new_leads": int(new_leads_count),

        "qualification_rate_percent": safe_percentage(
            qualified_count, total_leads
        ),

        "leads_with_opportunities": int(
            len(opportunity_lead_ids)
        ),

        "lead_to_opportunity_rate_percent": safe_percentage(
            len(opportunity_lead_ids), total_leads
        ),

        "converted_leads": int(converted_count),
        "lost_leads": int(lost_lead_count),

        "lead_to_won_rate_percent": safe_percentage(
            converted_count, total_leads
        ),

        "total_opportunities": int(total_opportunities),
        "won_opportunities": int(won_count),
        "lost_opportunities": int(lost_count),

        "win_rate_percent": safe_percentage(
            won_count, total_opportunities
        ),

        "loss_rate_percent": safe_percentage(
            lost_count, total_opportunities
        ),

        "won_revenue": round(won_revenue, 2),

        # Clearer name for the value of all opportunities
        "total_opportunity_value": round(
            total_opportunity_value, 2
        ),

        "lost_opportunity_value": round(
            lost_opportunity_value, 2
        ),

        # Retained for backward compatibility.
        # Includes WON and LOST opportunities.
        "total_pipeline_value": round(
            total_opportunity_value, 2
        ),

        "average_won_deal_value": round(
            average_deal_value, 2
        ),

        "average_score_won_leads": average_score_won,

        "average_score_lost_leads": average_score_lost,

        "average_score_not_qualified_leads": (
            average_score_not_qualified
        ),

        # Retained for backward compatibility.
        # Includes all leads without a WON opportunity.
        "average_score_non_won_leads": average_score_non_won
    }

    # Save metrics separately from original evaluation
    output_file = OUTPUT_DIR / "evaluation_metrics_v2.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)

    print("\n========== V2 BUSINESS EVALUATION ==========")
    print(json.dumps(metrics, indent=4))
    print("============================================")
    print(f"\nMetrics saved to: {output_file}")


if __name__ == "__main__":
    evaluate()