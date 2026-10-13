import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "brandshield.db"


def get_db_connection():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()

    # Create tables if they do not already exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL,
            official_username TEXT NOT NULL,
            official_website TEXT DEFAULT '',
            social_usernames TEXT DEFAULT '',
            official_apps TEXT DEFAULT '',
            brand_identifiers TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            scan_type TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            candidate_url TEXT DEFAULT '',
            platform TEXT DEFAULT '',
            risk_level TEXT NOT NULL,
            similarity_score REAL DEFAULT 0,
            reason TEXT DEFAULT '',
            recommended_action TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id)
                REFERENCES brands(id) ON DELETE CASCADE
        );
    """)

    # Check existing columns in the brands table
    cursor = conn.execute("PRAGMA table_info(brands)")
    existing_columns = {
        row["name"] for row in cursor.fetchall()
    }

    # Add missing columns to older databases
    required_columns = {
        "official_website": "TEXT DEFAULT ''",
        "social_usernames": "TEXT DEFAULT ''",
        "official_apps": "TEXT DEFAULT ''",
        "brand_identifiers": "TEXT DEFAULT ''",
        "logo_path": "TEXT DEFAULT ''"
    }

    for column, definition in required_columns.items():
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE brands ADD COLUMN "
                f"{column} {definition}"
            )

    conn.commit()
    conn.close()


def get_brands():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM brands ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def get_brand(brand_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM brands WHERE id = ?",
        (brand_id,)
    ).fetchone()
    conn.close()
    return row


def save_scan_result(
    brand_id,
    scan_type,
    candidate_name,
    candidate_url,
    platform,
    risk_level,
    similarity_score,
    reason,
    recommended_action
):
    conn = get_db_connection()

    conn.execute("""
        INSERT INTO scan_results (
            brand_id,
            scan_type,
            candidate_name,
            candidate_url,
            platform,
            risk_level,
            similarity_score,
            reason,
            recommended_action,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open')
    """, (
        brand_id,
        scan_type,
        candidate_name,
        candidate_url,
        platform,
        risk_level,
        similarity_score,
        reason,
        recommended_action
    ))

    conn.commit()
    conn.close()


# Initialize and update the database
init_db()
