# backend/db/db_writer.py
"""
Fire-and-forget background DB writer.
Inserts NEVER block the main pipeline.
The queue accepts jobs instantly; a daemon thread handles all writes.
"""

import queue
import threading
import os
from dotenv import load_dotenv

load_dotenv()

_DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "fleetuser"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "fleet_manager"),
}

_job_queue: queue.Queue = queue.Queue()
_started = False
_lock = threading.Lock()


# ─── Internal worker ────────────────────────────────────────────────────────

def _worker():
    """Runs in a daemon thread. Pulls jobs from queue and executes them."""
    import mysql.connector

    conn = None

    while True:
        job = _job_queue.get()          # blocks until a job arrives
        if job is None:                 # sentinel: shutdown signal
            break

        sql, params = job

        try:
            # Reconnect if needed
            if conn is None or not conn.is_connected():
                conn = mysql.connector.connect(**_DB_CONFIG)

            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            cur.close()

        except Exception as e:
            print(f"[DB_WRITER] Insert failed (non-fatal): {e}")

        finally:
            _job_queue.task_done()


def _ensure_started():
    """Start the background thread once, lazily."""
    global _started
    with _lock:
        if not _started:
            t = threading.Thread(target=_worker, daemon=True, name="db-writer")
            t.start()
            _started = True


# ─── Public API ──────────────────────────────────────────────────────────────

def log_user(user_id: str, role: str):
    """
    Insert or ignore a user record.
    Non-blocking — returns immediately.
    """
    _ensure_started()
    sql = """
        INSERT IGNORE INTO users (user_id, role)
        VALUES (%s, %s)
    """
    _job_queue.put((sql, (user_id, role)))


def log_driver_response(
    driver_id: str,
    trip_id: str,
    segment_index: int,
    severity: str,
    summary: str,
    coaching: str,
):
    """
    Queue a driver coaching response for DB insertion.
    Non-blocking — returns immediately.
    """
    _ensure_started()

    print(f"[DB_WRITER] Queuing response — coaching preview: {repr(coaching[:80]) if coaching else 'NONE/EMPTY'}")
    
    sql = """
        INSERT INTO driver_responses
            (driver_id, trip_id, segment_index, severity, summary, coaching)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    _job_queue.put((sql, (driver_id, trip_id, segment_index, severity, summary, coaching)))