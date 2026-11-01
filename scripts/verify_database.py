import csv
import os
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv


# ==================================================
# 1. PROJECT CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"

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


# ==================================================
# 2. TABLES TO VERIFY
# ==================================================

TABLES = [
    "companies",
    "contacts",
    "campaigns",
    "territories",
    "products",
    "sales_reps",
    "sales_rep_products",
    "leads",
    "lead_campaigns",
    "consents",
    "score_rules",
    "activities",
    "tasks",
    "opportunities",
    "stage_history"
]


# ==================================================
# 3. GET CSV RECORD COUNT
# ==================================================

def get_csv_count(table):

    path = DATA_DIR / f"{table}.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(
                f"CSV headers missing: {path.name}"
            )

        return sum(1 for _ in reader)


# ==================================================
# 4. VERIFY MYSQL TABLE
# ==================================================

def get_database_count(cursor, table):

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table,)
    )

    if cursor.fetchone()["total"] == 0:
        raise RuntimeError(
            f"MySQL table '{table}' does not exist."
        )

    cursor.execute(
        f"SELECT COUNT(*) AS total FROM `{table}`"
    )

    return cursor.fetchone()["total"]


# ==================================================
# 5. MAIN VERIFICATION
# ==================================================

def main():

    if not DB_CONFIG["password"]:
        raise RuntimeError(
            "DB_PASSWORD is empty. Check your .env file."
        )

    if not DATA_DIR.is_dir():
        raise FileNotFoundError(
            f"Generated data folder missing: {DATA_DIR}"
        )

    connection = None

    total_csv = 0
    total_db = 0
    all_passed = True

    try:

        print("\nConnecting to MySQL...")

        connection = pymysql.connect(**DB_CONFIG)

        print("MySQL connection successful!")

        with connection.cursor() as cursor:

            print("\n========== DATABASE VERIFICATION ==========\n")

            for table in TABLES:

                csv_count = get_csv_count(table)

                db_count = get_database_count(
                    cursor,
                    table
                )

                passed = csv_count == db_count

                if not passed:
                    all_passed = False

                total_csv += csv_count
                total_db += db_count

                status = "PASS" if passed else "FAIL"

                print(
                    f"{table:<22} "
                    f"CSV: {csv_count:>8,} | "
                    f"MySQL: {db_count:>8,} | "
                    f"{status}"
                )

            print("\n--------------------------------------------")
            print(f"TOTAL CSV RECORDS : {total_csv:,}")
            print(f"TOTAL DB RECORDS  : {total_db:,}")

            if all_passed:
                print("\nALL TABLE COUNTS MATCH!")
            else:
                print("\nDATABASE AND CSV COUNTS DO NOT MATCH.")

            print("============================================")

    except Exception as error:

        all_passed = False

        print("\nDATABASE VERIFICATION FAILED!")
        print(f"Error: {error}")

        raise

    finally:

        if connection:
            connection.close()

    return all_passed


if __name__ == "__main__":
    main()