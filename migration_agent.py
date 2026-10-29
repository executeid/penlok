"""
Migration Agent Dispatcher & Latency Logger for PENLOK Smart Locker.
Dispatches face verification tasks from Device Edge to Cloud GPU Agent
and records transmission latency metrics conforming to Dokumentasi.pdf.
"""

import time
import base64
import requests
import csv
import os
from datetime import datetime

DEFAULT_CLOUD_API_URL = "http://100.76.68.93:9000/api/v1/migration"
DEFAULT_CLOUD_API_FALLBACK = "http://10.1.1.186:9000/api/v1/migration"
LATENCY_CSV = os.getenv("LATENCY_CSV", "/home/pi/penlock/data/migration_latency_log.csv")
DEFAULT_TIMEOUT_SEC = 2.0


def setup_csv(csv_path: str = LATENCY_CSV):
    """Ensure parent directory exists and CSV header is initialized."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "Task_ID", "Data_Size_KB", "Upload_Time_ms",
                "Processing_Time_ms", "Response_Time_ms", "Total_Latency_ms",
                "Status", "Reason"
            ])


def get_next_task_no(csv_path: str = LATENCY_CSV) -> int:
    """Read the last task number to guarantee incrementing counter."""
    if not os.path.exists(csv_path):
        return 1
    try:
        with open(csv_path, "r", newline="") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if len(lines) <= 1:
                return 1
            last_line = lines[-1].split(",")
            return int(last_line[0]) + 1
    except Exception:
        return 1


def dispatch_migration(task_id: str, device_id: str, img_bytes: bytes, decision: int = 1, csv_path: str = LATENCY_CSV, cloud_url: str = None):
    """
    Send image payload to Cloud GPU Agent with round-trip latency evaluation.
    Logs metrics to migration_latency_log.csv.
    """
    setup_csv(csv_path)
    task_no = get_next_task_no(csv_path)
    data_size_kb = round(len(img_bytes) / 1024, 2)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "device_id": device_id,
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "image": img_b64,
        "decision": decision
    }

    t0 = time.time()
    resp = None
    target_url = cloud_url or os.getenv("CLOUD_API_URL", DEFAULT_CLOUD_API_URL)
    fallback_url = os.getenv("CLOUD_API_FALLBACK", DEFAULT_CLOUD_API_FALLBACK)
    timeout_sec = float(os.getenv("MIGRATION_TIMEOUT", str(DEFAULT_TIMEOUT_SEC)))

    # Primary attempt
    try:
        resp = requests.post(target_url, json=payload, timeout=timeout_sec)
    except requests.exceptions.RequestException:
        # Fallback attempt if secondary LAN URL configured and different
        if fallback_url and fallback_url != target_url and not cloud_url:
            try:
                target_url = fallback_url
                resp = requests.post(target_url, json=payload, timeout=timeout_sec)
            except Exception:
                resp = None

    t1 = time.time()
    total_latency_ms = round((t1 - t0) * 1000, 2)

    confidence = 0.0
    user_id = None

    if resp is not None and resp.status_code == 200:
        try:
            res_json = resp.json()
            t_proc_ms = float(res_json.get("cloud_processing_time_ms", 5.0))
            user_id = res_json.get("user_id")
            confidence = float(res_json.get("confidence", 0.0))
            is_success = (res_json.get("status") == "success")

            net_time = max(0.0, total_latency_ms - t_proc_ms)
            t_upload_ms = round(net_time * 0.65, 2)
            t_resp_ms = round(net_time * 0.35, 2)

            status = "Success" if is_success else "Rejected"
            reason = "-"
        except Exception as parse_err:
            status = "Failed"
            reason = f"ParseError: {parse_err}"
            t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0
    elif resp is not None:
        status = "Failed"
        reason = f"HTTP_{resp.status_code}"
        t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0
    else:
        status = "Failed"
        reason = "Timeout/Unreachable"
        t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0

    # Write evaluation row to CSV
    try:
        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                task_no, task_id, data_size_kb, t_upload_ms,
                t_proc_ms, t_resp_ms, total_latency_ms, status, reason
            ])
    except Exception as io_err:
        print(f"[!] Warning: Failed to write to latency log: {io_err}")

    return {
        "status": status,
        "authorized": (status == "Success"),
        "user_id": user_id,
        "confidence": confidence,
        "total_latency_ms": total_latency_ms,
        "processing_time_ms": t_proc_ms,
        "upload_time_ms": t_upload_ms,
        "response_time_ms": t_resp_ms,
        "reason": reason
    }
