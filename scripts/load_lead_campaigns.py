import csv
import os
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data" / "generated" / "lead_campaigns.csv"

load_dotenv(ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "lead_management_db"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": False
}


def main():

    if not DB_CONFIG["password"]:
        raise RuntimeError("DB_PASSWORD is empty. Check your .env file.")

    if not CSV_FILE.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_FILE}")

    with CSV_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        expected_columns = ["lead_id", "campaign_id", "linked_at"]

        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"Unexpected CSV columns: {reader.fieldnames}"
            )

        rows = [
            (row["lead_id"], row["campaign_id"], row["linked_at"])
            for row in reader
        ]

    if not rows:
        raise ValueError("CSV contains no records.")

    if any(not all(value for value in row) for row in rows):
        raise ValueError("CSV contains empty required values.")

    if len({(row[0], row[1]) for row in rows}) != len(rows):
        raise ValueError("Duplicate lead-campaign relationships found.")

    connection = None

    try:
        connection = pymysql.connect(**DB_CONFIG)

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT COUNT(*) AS total FROM lead_campaigns"
            )
            existing = cursor.fetchone()["total"]

            if existing > 0:
                raise RuntimeError(
                    f"lead_campaigns already contains {existing} rows. "
                    "Import cancelled."
                )

            sql = """
                INSERT INTO lead_campaigns
                (lead_id, campaign_id, linked_at)
                VALUES (%s, %s, %s)
            """

            cursor.executemany(sql, rows)

        connection.commit()

        print("LEAD_CAMPAIGNS IMPORT SUCCESSFUL")
        print(f"Records imported: {len(rows):,}")

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()