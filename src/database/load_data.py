import csv
import os
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv


# ==================================================
# 1. PROJECT CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parents[2]
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

BATCH_SIZE = 1000


# ==================================================
# 2. FOREIGN KEY LOAD ORDER
# ==================================================

LOAD_ORDER = [
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
# 3. READ CSV SAFELY
# ==================================================

def read_csv_rows(path):

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

        columns = reader.fieldnames

        if len(columns) != len(set(columns)):
            raise ValueError(
                f"Duplicate CSV columns: {path.name}"
            )

        # Read records while the file is still open.
        rows = list(reader)

    return columns, rows


# ==================================================
# 4. VALIDATE DATABASE TABLE
# ==================================================

def validate_table(cursor, table, columns):

    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table,)
    )

    existing_columns = {
        row["COLUMN_NAME"]
        for row in cursor.fetchall()
    }

    if not existing_columns:
        raise RuntimeError(
            f"Table '{table}' does not exist."
        )

    missing = set(columns) - existing_columns

    if missing:
        raise RuntimeError(
            f"Missing columns in {table}: {missing}"
        )


# ==================================================
# 5. LOAD TABLE USING BATCH INSERTS
# ==================================================

def load_table(cursor, table):

    path = DATA_DIR / f"{table}.csv"

    columns, rows = read_csv_rows(path)

    validate_table(cursor, table, columns)

    # Prevent duplicate imports.
    cursor.execute(
        f"SELECT COUNT(*) AS total FROM `{table}`"
    )

    existing = cursor.fetchone()["total"]

    if existing > 0:
        raise RuntimeError(
            f"Table '{table}' already contains "
            f"{existing} records. Use an empty database "
            "for a fresh import."
        )

    column_sql = ", ".join(
        f"`{column}`" for column in columns
    )

    placeholders = ", ".join(
        ["%s"] * len(columns)
    )

    sql = (
        f"INSERT INTO `{table}` "
        f"({column_sql}) VALUES ({placeholders})"
    )

    total = 0

    for start in range(0, len(rows), BATCH_SIZE):

        batch_rows = rows[start:start + BATCH_SIZE]

        batch = [
            tuple(
                None if value is None or value == ""
                else value
                for value in row.values()
            )
            for row in batch_rows
        ]

        cursor.executemany(sql, batch)

        total += len(batch)

        print(
            f"  {table}: {total:,}/{len(rows):,}",
            end="\r"
        )

    print(f"{table}: {total:,} records imported")

    return total


# ==================================================
# 6. MAIN IMPORT PROCESS
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

    try:

        print("\nConnecting to MySQL...")

        connection = pymysql.connect(**DB_CONFIG)

        print("MySQL connection successful!\n")

        imported = {}

        with connection.cursor() as cursor:

            for table in LOAD_ORDER:

                print(f"\nLoading {table}...")

                imported[table] = load_table(
                    cursor,
                    table
                )

        connection.commit()

        print("\n" + "=" * 45)
        print("DATABASE IMPORT SUCCESSFUL")
        print("=" * 45)

        for table, count in imported.items():
            print(f"{table:<25} {count:>10,}")

        print("=" * 45)

        print(
            f"TOTAL RECORDS: {sum(imported.values()):,}"
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print("\nDATABASE IMPORT FAILED!")
        print(f"Error: {error}")

        raise

    finally:

        if connection:
            connection.close()


if __name__ == "__main__":
    main()