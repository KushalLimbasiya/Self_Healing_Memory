"""
event_store.py — Single source of truth for all system events.
Uses built-in sqlite3. No ORM, no external dependencies.
"""
import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "shm.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables on first run. Safe to call multiple times."""
    os.makedirs("data", exist_ok=True)
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                stats     TEXT    NOT NULL,
                analysis  TEXT
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                data      TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS healing_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                stats       TEXT    NOT NULL,
                plan        TEXT,
                results     TEXT,
                validation  TEXT
            );

            CREATE TABLE IF NOT EXISTS action_scores (
                action      TEXT    PRIMARY KEY,
                score       REAL    NOT NULL DEFAULT 0.5,
                times_used  INTEGER NOT NULL DEFAULT 0,
                avg_freed   REAL    NOT NULL DEFAULT 0.0
            );
        """)
    logger.info("Database initialised at %s", DB_PATH)


# ── Memory Events ──────────────────────────────────────────────────────────────

def save_memory_event(stats: dict, analysis: Optional[dict] = None) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO memory_events (timestamp, stats, analysis) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), json.dumps(stats), json.dumps(analysis) if analysis else None),
        )


def get_recent_memory_events(limit: int = 50) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {"id": r["id"], "timestamp": r["timestamp"],
         "stats": json.loads(r["stats"]),
         "analysis": json.loads(r["analysis"]) if r["analysis"] else None}
        for r in rows
    ]


def get_memory_history_series(limit: int = 100) -> List[Dict]:
    """Return lightweight time-series suitable for charting."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT timestamp, stats FROM memory_events ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    result = []
    for r in rows:
        stats = json.loads(r["stats"])
        result.append({
            "timestamp": r["timestamp"],
            "used_percent": stats.get("used_percent", 0),
        })
    return list(reversed(result))


# ── Predictions ────────────────────────────────────────────────────────────────

def save_prediction(data: dict) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO predictions (timestamp, data) VALUES (?, ?)",
            (datetime.now().isoformat(), json.dumps(data)),
        )


def get_latest_prediction() -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    if row:
        return {"timestamp": row["timestamp"], **json.loads(row["data"])}
    return None


def get_recent_predictions(limit: int = 20) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"timestamp": r["timestamp"], **json.loads(r["data"])} for r in rows]


# ── Healing Events ─────────────────────────────────────────────────────────────

def save_healing_event(stats: dict, plan: dict, results: dict, validation: dict) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO healing_events (timestamp, stats, plan, results, validation) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(),
                json.dumps(stats),
                json.dumps(plan),
                json.dumps(results),
                json.dumps(validation),
            ),
        )


def get_recent_healing_events(limit: int = 20) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM healing_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "stats": json.loads(r["stats"]),
            "plan": json.loads(r["plan"]) if r["plan"] else None,
            "results": json.loads(r["results"]) if r["results"] else None,
            "validation": json.loads(r["validation"]) if r["validation"] else None,
        }
        for r in rows
    ]


# ── Action Scores (HealerBrain persistence) ────────────────────────────────────

def get_action_scores() -> Dict[str, Dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM action_scores").fetchall()
    return {
        r["action"]: {
            "score": r["score"],
            "times_used": r["times_used"],
            "avg_freed": r["avg_freed"],
        }
        for r in rows
    }


def update_action_score(action: str, freed_percent: float) -> None:
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT score, times_used, avg_freed FROM action_scores WHERE action = ?",
            (action,),
        ).fetchone()

        if existing:
            n = existing["times_used"] + 1
            new_avg = (existing["avg_freed"] * existing["times_used"] + freed_percent) / n
            # Exponential moving average for score (recent results weighted more)
            new_score = existing["score"] * 0.8 + (freed_percent / 100.0) * 0.2
            conn.execute(
                "UPDATE action_scores SET score=?, times_used=?, avg_freed=? WHERE action=?",
                (new_score, n, new_avg, action),
            )
        else:
            conn.execute(
                "INSERT INTO action_scores (action, score, times_used, avg_freed) VALUES (?, ?, 1, ?)",
                (action, max(0.1, freed_percent / 100.0), freed_percent),
            )
