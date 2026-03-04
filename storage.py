"""
storage.py — Persistance des runs dans SQLite
Tables :
  - runs       : un enregistrement par run (timestamp, summary JSON)
  - test_cases : résultats individuels de chaque test d'un run
"""

import sqlite3
import json
import os

# Chemin de la base de données (adaptable via variable d'env)
DB_PATH = os.environ.get("DB_PATH", "runs.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                api       TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                passed    INTEGER NOT NULL,
                failed    INTEGER NOT NULL,
                total     INTEGER NOT NULL,
                error_rate    REAL NOT NULL,
                latency_avg   REAL NOT NULL,
                latency_p95   REAL NOT NULL,
                availability  REAL NOT NULL,
                tests_json    TEXT NOT NULL
            )
        """)
        conn.commit()


def save_run(run: dict) -> int:
    """
    Sauvegarde un run complet dans SQLite.
    Retourne l'id du run inséré.
    """
    init_db()
    s = run["summary"]
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs
              (api, timestamp, passed, failed, total, error_rate,
               latency_avg, latency_p95, availability, tests_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run["api"],
                run["timestamp"],
                s["passed"],
                s["failed"],
                s["total"],
                s["error_rate"],
                s["latency_ms_avg"],
                s["latency_ms_p95"],
                s["availability"],
                json.dumps(run["tests"], ensure_ascii=False),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_runs(limit: int = 20) -> list:
    """
    Retourne les `limit` derniers runs (du plus récent au plus ancien).
    Chaque run est un dict avec les champs de la table + tests désérialisés.
    """
    init_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    result = []
    for row in rows:
        r = dict(row)
        r["tests"] = json.loads(r["tests_json"])
        del r["tests_json"]
        result.append(r)
    return result


def get_last_run() -> dict | None:
    """Retourne le dernier run ou None si aucun run enregistré."""
    runs = list_runs(limit=1)
    return runs[0] if runs else None
