"""Database connection and query helpers for the RAD System prototype."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rad_seed_data.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a new database connection for each request."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        return get_db_connection()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params: tuple = (), db_path: str | None = None) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def query_one(sql: str, params: tuple = (), db_path: str | None = None) -> sqlite3.Row | None:
    conn = get_connection(db_path)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute(sql: str, params: tuple = (), db_path: str | None = None) -> int:
    """Execute a write operation. Returns lastrowid."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def execute_many(sql: str, params_list: list[tuple], db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executemany(sql, params_list)
        conn.commit()
    finally:
        conn.close()
