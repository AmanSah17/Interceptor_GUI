"""
database.py
SQLite persistence layer for Interceptor GCS.

Tables
------
  flight_sessions   - one row per server boot session
  telemetry_log     - 1 Hz sampled telemetry snapshots
  mode_history      - every mode change event
  detection_log     - bounding-box events per frame
"""

import sqlite3
import time
import threading
from pathlib import Path

# DB lives next to this file
DB_PATH = Path(__file__).parent / "interceptor_gcs.db"

# Thread-local connections (SQLite is not thread-safe by default)
_local = threading.local()


def _conn() -> sqlite3.Connection:
    """Return a per-thread connection, creating it on first use."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")   # better write concurrency
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_db():
    """Create all tables if they don't exist."""
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS flight_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  REAL    NOT NULL,
            ended_at    REAL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS telemetry_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            ts          REAL    NOT NULL,
            mode        TEXT    NOT NULL,
            altitude    REAL    NOT NULL,
            speed       REAL    NOT NULL,
            heading     REAL    NOT NULL,
            vspeed      REAL    NOT NULL,
            battery     REAL    NOT NULL,
            signal      REAL    NOT NULL,
            lat         REAL    NOT NULL,
            lon         REAL    NOT NULL,
            distance    REAL    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES flight_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS mode_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            ts          REAL    NOT NULL,
            old_mode    TEXT    NOT NULL,
            new_mode    TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES flight_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS detection_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            ts          REAL    NOT NULL,
            label       TEXT    NOT NULL,
            confidence  REAL    NOT NULL,
            box_x       REAL    NOT NULL,
            box_y       REAL    NOT NULL,
            box_w       REAL    NOT NULL,
            box_h       REAL    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES flight_sessions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_telem_session ON telemetry_log(session_id);
        CREATE INDEX IF NOT EXISTS idx_telem_ts      ON telemetry_log(ts);
        CREATE INDEX IF NOT EXISTS idx_mode_ts       ON mode_history(ts);
    """)
    con.commit()
    print(f"[DB] Database ready: {DB_PATH}")


# ── Session management ────────────────────────────────────────────────────────
_session_id: int | None = None


def start_session() -> int:
    global _session_id
    con = _conn()
    cur = con.execute(
        "INSERT INTO flight_sessions (started_at) VALUES (?)", (time.time(),)
    )
    con.commit()
    _session_id = cur.lastrowid
    print(f"[DB] Flight session #{_session_id} started")
    return _session_id


def end_session():
    global _session_id
    if _session_id is None:
        return
    con = _conn()
    con.execute(
        "UPDATE flight_sessions SET ended_at=? WHERE id=?",
        (time.time(), _session_id)
    )
    con.commit()
    print(f"[DB] Flight session #{_session_id} ended")
    _session_id = None


def get_session_id() -> int | None:
    return _session_id


# ── Telemetry write ───────────────────────────────────────────────────────────
_last_log_ts: float = 0.0
LOG_INTERVAL = 1.0  # write one row per second max


def log_telemetry(data: dict):
    """Throttled write — stores at most 1 row/second."""
    global _last_log_ts
    if _session_id is None:
        return
    now = time.time()
    if now - _last_log_ts < LOG_INTERVAL:
        return
    _last_log_ts = now
    con = _conn()
    con.execute("""
        INSERT INTO telemetry_log
          (session_id, ts, mode, altitude, speed, heading, vspeed,
           battery, signal, lat, lon, distance)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        _session_id, now,
        data["mode"],   data["altitude"], data["speed"],
        data["heading"],data["vspeed"],   data["battery"],
        data["signal"], data["lat"],      data["lon"],
        data["distance"],
    ))

    # Also log detections
    for b in data.get("boxes", []):
        con.execute("""
            INSERT INTO detection_log
              (session_id, ts, label, confidence, box_x, box_y, box_w, box_h)
            VALUES (?,?,?,?,?,?,?,?)
        """, (_session_id, now, b["label"], b["conf"],
              b["x"], b["y"], b["w"], b["h"]))
    con.commit()


# ── Mode change write ─────────────────────────────────────────────────────────
def log_mode_change(old_mode: str, new_mode: str):
    if _session_id is None:
        return
    con = _conn()
    con.execute("""
        INSERT INTO mode_history (session_id, ts, old_mode, new_mode)
        VALUES (?,?,?,?)
    """, (_session_id, time.time(), old_mode, new_mode))
    con.commit()
    print(f"[DB] Mode change: {old_mode} -> {new_mode}")


# ── Query helpers ─────────────────────────────────────────────────────────────
def get_recent_telemetry(limit: int = 100) -> list[dict]:
    """Return the last N telemetry rows for the current session."""
    if _session_id is None:
        return []
    con = _conn()
    rows = con.execute("""
        SELECT * FROM telemetry_log
        WHERE session_id=?
        ORDER BY ts DESC LIMIT ?
    """, (_session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_mode_history(limit: int = 50) -> list[dict]:
    if _session_id is None:
        return []
    con = _conn()
    rows = con.execute("""
        SELECT * FROM mode_history
        WHERE session_id=?
        ORDER BY ts DESC LIMIT ?
    """, (_session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_session_stats() -> dict:
    """Quick stats for the current session."""
    if _session_id is None:
        return {}
    con = _conn()
    row = con.execute("""
        SELECT
          COUNT(*)                          AS total_logs,
          AVG(altitude)                     AS avg_altitude,
          MAX(altitude)                     AS max_altitude,
          AVG(speed)                        AS avg_speed,
          MAX(speed)                        AS max_speed,
          MIN(battery)                      AS min_battery,
          MIN(ts)                           AS first_ts,
          MAX(ts)                           AS last_ts
        FROM telemetry_log WHERE session_id=?
    """, (_session_id,)).fetchone()
    return dict(row) if row else {}
