#!/usr/bin/env python3
"""
PENLOK Edge Decision Buffer & Sync Module (WIB Timezone)
Guarantees zero-loss store-and-forward logging from Device Edge (Pi 5) to Cloud GPU.
Provides active health checking and circuit breaker capabilities in Asia/Jakarta (WIB).
"""

import os
import time
import sqlite3
import threading
import requests
import zoneinfo
from datetime import datetime
from typing import Optional, Dict, Any, List

WIB = zoneinfo.ZoneInfo("Asia/Jakarta")

def now_wib_str():
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

CLOUD_HOST = os.getenv("CLOUD_HOST", "10.1.1.186")
CLOUD_PORT = os.getenv("CLOUD_PORT", "9000")
CLOUD_FALLBACK = os.getenv("CLOUD_HOST_FALLBACK", "100.76.68.93")
DB_BUFFER_PATH = os.getenv("SQLITE_BUFFER_PATH", "/home/pi/penlock/data/edge_decision_buffer.db")

PRIMARY_CLOUD_URL = f"http://{CLOUD_HOST}:{CLOUD_PORT}"
FALLBACK_CLOUD_URL = f"http://{CLOUD_FALLBACK}:{CLOUD_PORT}"

_circuit_breaker_lock = threading.Lock()
_is_cloud_alive = False
_last_healthcheck_time = 0.0

def get_db_connection():
    os.makedirs(os.path.dirname(DB_BUFFER_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_BUFFER_PATH, timeout=5.0)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edge_decision_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            decision INTEGER NOT NULL,
            decision_label TEXT NOT NULL,
            execution_node TEXT NOT NULL,
            model_used TEXT DEFAULT 'XGBoost v2.0',
            cpu_pct REAL,
            ram_pct REAL,
            latency_ms REAL,
            priority INTEGER DEFAULT 3,
            queue_len INTEGER DEFAULT 1,
            execution_time_ms REAL NOT NULL,
            user_id TEXT,
            confidence REAL,
            status TEXT NOT NULL,
            notes TEXT,
            synced INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    return conn

def check_cloud_health(timeout: float = 0.4) -> bool:
    """Active healthcheck with circuit breaker cache (TTL 2.0s)"""
    global _is_cloud_alive, _last_healthcheck_time
    now = time.time()
    if now - _last_healthcheck_time < 2.0:
        return _is_cloud_alive

    alive = False
    for base_url in (PRIMARY_CLOUD_URL, FALLBACK_CLOUD_URL):
        try:
            r = requests.get(f"{base_url}/health", timeout=timeout)
            if r.status_code == 200 and r.json().get("status") == "healthy":
                alive = True
                break
        except Exception:
            continue

    with _circuit_breaker_lock:
        _is_cloud_alive = alive
        _last_healthcheck_time = now

    return alive

def buffer_decision(
    task_id: str,
    decision: int,
    decision_label: str,
    execution_node: str,
    cpu_pct: float,
    ram_pct: float,
    latency_ms: float,
    execution_time_ms: float,
    user_id: str = "UNKNOWN",
    confidence: float = 0.95,
    status: str = "SUCCESS",
    notes: str = "",
    priority: int = 3,
    queue_len: int = 1,
    model_used: str = "XGBoost v2.0"
):
    """Store decision log into local SQLite buffer immediately using WIB timestamp"""
    try:
        conn = get_db_connection()
        with conn:
            conn.execute("""
                INSERT INTO edge_decision_buffer
                (task_id, timestamp, decision, decision_label, execution_node, model_used, cpu_pct, ram_pct, latency_ms, priority, queue_len, execution_time_ms, user_id, confidence, status, notes, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
            """, (task_id, now_wib_str(), decision, decision_label, execution_node, model_used, cpu_pct, ram_pct, latency_ms, priority, queue_len, execution_time_ms, user_id, confidence, status, notes))
        conn.close()
    except Exception as e:
        print("[-] Local buffer error:", e)

def flush_buffer_to_cloud(batch_size: int = 25) -> int:
    """Flush un-synced decision records from local SQLite buffer to Cloud GPU PostgreSQL"""
    synced_total = 0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, task_id, decision, decision_label, execution_node, model_used, cpu_pct, ram_pct, latency_ms, priority, queue_len, execution_time_ms, user_id, confidence, status, notes
            FROM edge_decision_buffer
            WHERE synced = 0
            ORDER BY id ASC LIMIT ?;
        """, (batch_size,))
        rows = cur.fetchall()

        if not rows:
            conn.close()
            return 0

        payload = []
        row_ids = []
        for r in rows:
            row_ids.append(r[0])
            payload.append({
                "task_id": r[1],
                "decision": r[2],
                "decision_label": r[3],
                "execution_node": r[4],
                "model_used": r[5],
                "cpu_pct": r[6],
                "ram_pct": r[7],
                "latency_ms": r[8],
                "priority": r[9],
                "queue_len": r[10],
                "execution_time_ms": r[11],
                "user_id": r[12] or "UNKNOWN",
                "confidence": r[13] or 0.95,
                "status": r[14],
                "notes": r[15] or ""
            })

        success = False
        for base_url in (PRIMARY_CLOUD_URL, FALLBACK_CLOUD_URL):
            try:
                resp = requests.post(f"{base_url}/api/v1/log_decision", json=payload, timeout=2.0)
                if resp.status_code == 200:
                    success = True
                    break
            except Exception:
                continue

        if success:
            with conn:
                placeholders = ",".join("?" for _ in row_ids)
                conn.execute(f"UPDATE edge_decision_buffer SET synced = 1 WHERE id IN ({placeholders})", row_ids)
            synced_total = len(row_ids)
            print(f"[SYNCER] Successfully flushed {synced_total} decision logs to Cloud GPU.")

        conn.close()
    except Exception as e:
        print("[-] Flush buffer exception:", e)

    return synced_total

def _background_worker():
    while True:
        try:
            if check_cloud_health(timeout=0.5):
                flush_buffer_to_cloud(batch_size=50)
        except Exception:
            pass
        time.sleep(3.0)

def start_background_syncer():
    t = threading.Thread(target=_background_worker, daemon=True, name="DecisionSyncerDaemon")
    t.start()
    print("[INIT] Edge Decision Syncer daemon started.")

if __name__ == "__main__":
    print("Testing Decision Syncer WIB...")
    buffer_decision(
        task_id="TEST_BUFFER_WIB_01",
        decision=0,
        decision_label="PROSES_DI_EDGE",
        execution_node="Device Edge (Pi 5)",
        cpu_pct=21.4,
        ram_pct=31.2,
        latency_ms=12.5,
        execution_time_ms=280.0,
        user_id="Akmal",
        confidence=0.99,
        status="SUCCESS",
        notes="WIB test buffer entry"
    )
    print("Healthcheck status:", check_cloud_health())
    print("Flushed records:", flush_buffer_to_cloud())
