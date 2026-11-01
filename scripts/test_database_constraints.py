import os
import uuid
from pathlib import Path

import pymysql
import pytest
from dotenv import load_dotenv
from pymysql.cursors import DictCursor


# =========================================================
# 1. DATABASE CONFIGURATION
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "lead_management_db"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": False,
    "connect_timeout": 10,
}


# =========================================================
# 2. EXPECTED DATABASE TABLES AND CONSTRAINTS
# =========================================================

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
    "stage_history",
]

EXPECTED_UNIQUE_CONSTRAINTS = [
    ("contacts", "email"),
    ("opportunities", "lead_id"),
]

EXPECTED_COMPOSITE_PRIMARY_KEYS = {
    "sales_rep_products": [
        "sales_rep_id",
        "product_id",
    ],
    "lead_campaigns": [
        "lead_id",
        "campaign_id",
    ],
}


# =========================================================
# 3. PYTEST FIXTURES
# =========================================================

@pytest.fixture(scope="module")
def connection():
    """
    Create one MySQL connection for this test module.

    All test transactions are rolled back.
    No test data is permanently inserted.
    """

    if not DB_CONFIG["password"]:
        pytest.fail(
            "DB_PASSWORD is missing. "
            "Check the root .env file."
        )

    conn = None

    try:
        conn = pymysql.connect(**DB_CONFIG)
        yield conn

    except pymysql.MySQLError as error:
        pytest.fail(f"MySQL connection failed: {error}")

    finally:
        if conn is not None:
            try:
                conn.rollback()
                conn.close()
            except pymysql.MySQLError:
                pass


@pytest.fixture
def cursor(connection):
    """Provide a fresh cursor for each test."""

    cur = connection.cursor()

    try:
        yield cur
    finally:
        connection.rollback()
        cur.close()


# =========================================================
# 4. DATABASE METADATA HELPERS
# =========================================================

def table_exists(cursor, table):
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND TABLE_TYPE = 'BASE TABLE'
        """,
        (table,)
    )

    return cursor.fetchone()["total"] == 1


def get_primary_key_columns(cursor, table):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY ORDINAL_POSITION
        """,
        (table,)
    )

    return [
        row["COLUMN_NAME"]
        for row in cursor.fetchall()
    ]


def get_columns(cursor, table):
    cursor.execute(
        """
        SELECT
            COLUMN_NAME,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            EXTRA,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (table,)
    )

    return cursor.fetchall()


def get_foreign_keys(cursor):
    cursor.execute(
        """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY TABLE_NAME, CONSTRAINT_NAME
        """
    )

    return cursor.fetchall()


def get_unique_indexes(cursor, table):
    cursor.execute(
        """
        SELECT
            INDEX_NAME,
            GROUP_CONCAT(
                COLUMN_NAME
                ORDER BY SEQ_IN_INDEX
            ) AS columns_list
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND NON_UNIQUE = 0
        GROUP BY INDEX_NAME
        """,
        (table,)
    )

    return cursor.fetchall()


def get_existing_record(cursor, table):
    cursor.execute(
        f"SELECT * FROM `{table}` LIMIT 1"
    )

    return cursor.fetchone()


def get_column_max_length(cursor, table, column):
    cursor.execute(
        """
        SELECT CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column)
    )

    result = cursor.fetchone()

    if not result:
        return None

    return result["CHARACTER_MAXIMUM_LENGTH"]


def make_test_id(cursor, table, column):
    """
    Generate an unused temporary primary key.

    The generated ID is only used inside a rolled-back transaction.
    """

    max_length = get_column_max_length(
        cursor,
        table,
        column
    )

    for _ in range(100):
        candidate = "TST" + uuid.uuid4().hex[:10].upper()

        if max_length is not None and len(candidate) > max_length:
            candidate = candidate[:max_length]

        cursor.execute(
            f"""
            SELECT 1
            FROM `{table}`
            WHERE `{column}` = %s
            LIMIT 1
            """,
            (candidate,)
        )

        if cursor.fetchone() is None:
            return candidate

    raise RuntimeError(
        f"Unable to create a temporary ID for {table}.{column}"
    )


def insert_record(cursor, table, record):
    columns = list(record.keys())

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

    cursor.execute(
        sql,
        tuple(record[column] for column in columns)
    )


def remove_auto_increment_fields(cursor, table, record):
    """Remove auto-increment columns from a copied database row."""

    for column in get_columns(cursor, table):
        if "auto_increment" in column["EXTRA"].lower():
            record.pop(column["COLUMN_NAME"], None)

    return record


def assert_duplicate_key_error(error):
    """MySQL error 1062 represents a duplicate-key violation."""

    assert error.args[0] == 1062, (
        f"Expected duplicate-key error 1062, "
        f"got {error.args[0]}: {error}"
    )


# =========================================================
# 5. DATABASE AND TABLE TESTS
# =========================================================

def test_database_connection(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT DATABASE() AS db_name")

        result = cur.fetchone()

        assert result["db_name"] == DB_CONFIG["database"]


@pytest.mark.parametrize("table", TABLES)
def test_required_tables_exist(cursor, table):
    assert table_exists(cursor, table), (
        f"Required table is missing: {table}"
    )

# =========================================================
# 6. PRIMARY KEY TESTS
# =========================================================

@pytest.mark.parametrize("table", TABLES)
def test_primary_key_exists(cursor, table):
    primary_keys = get_primary_key_columns(
        cursor,
        table
    )

    assert len(primary_keys) >= 1, (
        f"{table} does not have a primary key"
    )


@pytest.mark.parametrize("table", TABLES)
def test_primary_key_values_are_not_null(cursor, table):
    primary_keys = get_primary_key_columns(
        cursor,
        table
    )

    assert primary_keys, (
        f"No primary key found for {table}"
    )

    for column in primary_keys:
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM `{table}`
            WHERE `{column}` IS NULL
            """
        )

        count = cursor.fetchone()["total"]

        assert count == 0, (
            f"{table}.{column} contains {count} NULL values"
        )


@pytest.mark.parametrize("table", TABLES)
def test_primary_key_values_are_unique(cursor, table):
    primary_keys = get_primary_key_columns(
        cursor,
        table
    )

    assert primary_keys

    group_columns = ", ".join(
        f"`{column}`" for column in primary_keys
    )

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT {group_columns}
            FROM `{table}`
            GROUP BY {group_columns}
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    )

    duplicates = cursor.fetchone()["total"]

    assert duplicates == 0, (
        f"{table} contains duplicate primary-key combinations"
    )


@pytest.mark.parametrize(
    "table, expected_columns",
    EXPECTED_COMPOSITE_PRIMARY_KEYS.items()
)
def test_composite_primary_keys_are_exact(
    cursor,
    table,
    expected_columns
):
    actual_columns = get_primary_key_columns(
        cursor,
        table
    )

    assert actual_columns == expected_columns, (
        f"{table} expected composite primary key "
        f"{expected_columns}, got {actual_columns}"
    )


# =========================================================
# 7. FOREIGN KEY STRUCTURE TESTS
# =========================================================

def test_foreign_key_constraints_exist(cursor):
    foreign_keys = get_foreign_keys(cursor)

    assert len(foreign_keys) > 0, (
        "No foreign-key constraints found"
    )


def test_foreign_keys_reference_existing_tables(cursor):
    foreign_keys = get_foreign_keys(cursor)

    assert foreign_keys

    for fk in foreign_keys:
        assert table_exists(
            cursor,
            fk["REFERENCED_TABLE_NAME"]
        ), (
            f"Referenced table missing: "
            f"{fk['REFERENCED_TABLE_NAME']}"
        )


def test_foreign_keys_have_valid_columns(cursor):
    foreign_keys = get_foreign_keys(cursor)

    assert foreign_keys

    for fk in foreign_keys:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            (
                fk["REFERENCED_TABLE_NAME"],
                fk["REFERENCED_COLUMN_NAME"]
            )
        )

        count = cursor.fetchone()["total"]

        assert count == 1, (
            f"Invalid referenced column in "
            f"{fk['TABLE_NAME']}.{fk['COLUMN_NAME']}"
        )


# =========================================================
# 8. FOREIGN KEY DATA INTEGRITY TESTS
# =========================================================

def test_existing_foreign_key_relationships_have_no_orphans(cursor):
    foreign_keys = get_foreign_keys(cursor)

    assert foreign_keys

    for fk in foreign_keys:
        child_table = fk["TABLE_NAME"]
        child_column = fk["COLUMN_NAME"]
        parent_table = fk["REFERENCED_TABLE_NAME"]
        parent_column = fk["REFERENCED_COLUMN_NAME"]

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM `{child_table}` child
            LEFT JOIN `{parent_table}` parent
              ON child.`{child_column}` = parent.`{parent_column}`
            WHERE child.`{child_column}` IS NOT NULL
              AND parent.`{parent_column}` IS NULL
            """
        )

        orphan_count = cursor.fetchone()["total"]

        assert orphan_count == 0, (
            f"Found {orphan_count} orphan records in "
            f"{child_table}.{child_column}"
        )


# =========================================================
# 9. UNIQUE CONSTRAINT TESTS
# =========================================================

@pytest.mark.parametrize(
    "table,column",
    EXPECTED_UNIQUE_CONSTRAINTS
)
def test_required_unique_constraints_exist(cursor, table, column):
    indexes = get_unique_indexes(cursor, table)

    unique_columns = [
        index["columns_list"].split(",")
        for index in indexes
    ]

    assert any(
        columns == [column]
        for columns in unique_columns
    ), (
        f"Missing unique constraint on {table}.{column}"
    )


@pytest.mark.parametrize(
    "table,column",
    EXPECTED_UNIQUE_CONSTRAINTS
)
def test_unique_columns_have_no_duplicate_values(cursor, table, column):
    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT `{column}`
            FROM `{table}`
            WHERE `{column}` IS NOT NULL
            GROUP BY `{column}`
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    )

    count = cursor.fetchone()["total"]

    assert count == 0, (
        f"{table}.{column} contains duplicate values"
    )

# =========================================================
# 10. DUPLICATE EMAIL REJECTION
# =========================================================

def test_duplicate_email_rejection(connection):
    cursor = connection.cursor()

    try:
        original = get_existing_record(
            cursor,
            "contacts"
        )

        assert original is not None, (
            "Cannot test duplicate email: contacts table is empty"
        )

        assert original.get("email") is not None, (
            "Existing contact has no email value"
        )

        record = remove_auto_increment_fields(
            cursor,
            "contacts",
            dict(original)
        )

        record["contact_id"] = make_test_id(
            cursor,
            "contacts",
            "contact_id"
        )

        # Preserve the existing email to test its UNIQUE constraint.
        record["email"] = original["email"]

        with pytest.raises(pymysql.err.IntegrityError) as error:
            insert_record(
                cursor,
                "contacts",
                record
            )

        assert_duplicate_key_error(error.value)

    finally:
        connection.rollback()
        cursor.close()


# =========================================================
# 11. DUPLICATE OPPORTUNITY REJECTION
# =========================================================

def test_duplicate_opportunity_rejection(connection):
    cursor = connection.cursor()

    try:
        original = get_existing_record(
            cursor,
            "opportunities"
        )

        assert original is not None, (
            "Cannot test duplicate opportunity: table is empty"
        )

        record = remove_auto_increment_fields(
            cursor,
            "opportunities",
            dict(original)
        )

        record["opportunity_id"] = make_test_id(
            cursor,
            "opportunities",
            "opportunity_id"
        )

        # Preserve the existing lead ID to test its UNIQUE constraint.
        record["lead_id"] = original["lead_id"]

        with pytest.raises(pymysql.err.IntegrityError) as error:
            insert_record(
                cursor,
                "opportunities",
                record
            )

        assert_duplicate_key_error(error.value)

    finally:
        connection.rollback()
        cursor.close()


# =========================================================
# 12. INVALID FOREIGN KEY INSERTION TEST
# =========================================================

def test_invalid_foreign_key_insertion_is_rejected(connection):
    cursor = connection.cursor()

    try:
        foreign_keys = get_foreign_keys(cursor)

        # Find a child foreign key with a compatible string column.
        selected = None

        for fk in foreign_keys:
            child_columns = get_columns(
                cursor,
                fk["TABLE_NAME"]
            )

            column_info = next(
                (
                    column
                    for column in child_columns
                    if column["COLUMN_NAME"] == fk["COLUMN_NAME"]
                ),
                None
            )

            if column_info is None:
                continue

            if column_info["DATA_TYPE"].lower() in {
                "char", "varchar"
            }:
                selected = fk
                break

        if selected is None:
            pytest.skip(
                "No suitable string foreign key found for insertion test"
            )

        child_table = selected["TABLE_NAME"]
        child_column = selected["COLUMN_NAME"]

        record = get_existing_record(
            cursor,
            child_table
        )

        if record is None:
            pytest.skip(
                f"{child_table} has no existing row to clone"
            )

        record = remove_auto_increment_fields(
            cursor,
            child_table,
            dict(record)
        )

        primary_keys = get_primary_key_columns(
            cursor,
            child_table
        )

        if len(primary_keys) != 1:
            pytest.skip(
                "Invalid-FK insertion test requires a single-column primary key"
            )

        pk = primary_keys[0]

        record[pk] = make_test_id(
            cursor,
            child_table,
            pk
        )

        # Use a value that should not exist in the parent table.
        invalid_value = "INVALID_FK_" + uuid.uuid4().hex[:12]

        record[child_column] = invalid_value

        with pytest.raises(
            pymysql.err.IntegrityError
        ) as error:
            insert_record(
                cursor,
                child_table,
                record
            )

        assert error.value.args[0] == 1452, (
            f"Expected foreign-key error 1452, "
            f"got {error.value.args[0]}: {error.value}"
        )

    finally:
        connection.rollback()
        cursor.close()


# =========================================================
# 13. DATABASE ENGINE CHECK
# =========================================================

@pytest.mark.parametrize("table", TABLES)
def test_tables_use_innodb(cursor, table):
    cursor.execute(
        """
        SELECT ENGINE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table,)
    )

    result = cursor.fetchone()

    assert result is not None

    assert result["ENGINE"].upper() == "INNODB", (
        f"{table} is not using InnoDB"
    )