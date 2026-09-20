import os

import psycopg
from psycopg.rows import dict_row


def _dsn() -> str:
    return (
        f"host={os.environ.get('DB_HOST', 'db')} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ.get('DB_NAME', 'lds_gisdb')} "
        f"user={os.environ.get('DB_USER', 'CBS')} "
        f"password={os.environ.get('DB_PASSWORD', 'cbs_lab_pw')} "
        f"connect_timeout=5"
    )


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with psycopg.connect(_dsn(), row_factory=dict_row, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Pass None (not an empty tuple) when there are no parameters so
            # literal '%' characters in the query are not treated as
            # placeholders by psycopg.
            cur.execute(sql, params or None)
            return cur.fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
