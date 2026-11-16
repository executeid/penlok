"""Cloud-only smoke/burst checks. Never calls edge, onboarding or relays.

Run inside a cloud runtime image with existing gallery mounted read-only.
This reuses enrollment photos: results are functional checks, NOT accuracy.
"""
import argparse
import base64
import csv
import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("CLOUD_%Y%m%dT%H%M%S")
    url = args.url.rstrip("/")

    def request(path, body=None):
        encoded = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url + path, data=encoded,
                                     headers={"Content-Type": "application/json"})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as response:
            code, raw = response.code, response.read()
        elapsed = (time.perf_counter() - started) * 1000
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw.decode()
        return {"http_status": code, "client_rtt_ms": round(elapsed, 3), "response": data}

    def migration(image, suffix, endpoint="/api/v1/migration"):
        body = {"task_id": f"{run_id}_{suffix}", "device_id": "cloud_verifier",
                "image": base64.b64encode(image).decode(), "decision": 1}
        result = request(endpoint, body)
        result["task_id"] = body["task_id"]
        return result

    report = {"run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "cloud only; existing enrollment images; no accuracy claim",
              "url": url, "root": request("/"), "health": request("/health"),
              "ready": request("/ready"), "functional": [], "batches": []}
    fixtures = []
    for folder in sorted(Path(args.assets).iterdir()):
        if not folder.is_dir():
            continue
        images = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
        if not images:
            continue
        raw = images[0].read_bytes()
        fixtures.append(raw)
        check = migration(raw, f"PROFILE_{len(fixtures)}")
        check.update(fixture_sha256=hashlib.sha256(raw).hexdigest(), fixture_bytes=len(raw))
        report["functional"].append(check)

    _, blank = cv2.imencode(".jpg", np.zeros((240, 320, 3), dtype=np.uint8))
    report["no_face"] = migration(blank.tobytes(), "NO_FACE")
    report["invalid_image"] = migration(b"not a JPEG or PNG", "INVALID_IMAGE")
    report["invalid_base64"] = request("/api/v1/migration", {
        "task_id": run_id + "_BAD_BASE64", "device_id": "cloud_verifier",
        "image": "!invalid!", "decision": 1})
    report["invalid_schema"] = request("/api/v1/migration", {"data": "legacy dummy string"})
    if fixtures:
        report["alias_migrate"] = migration(fixtures[0], "ALIAS_MIGRATE", "/api/v1/migrate")
        report["alias_short"] = migration(fixtures[0], "ALIAS_SHORT", "/migration")

    rows = []
    for concurrency in (10, 50) if fixtures else ():
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            results = list(executor.map(lambda i: migration(fixtures[i % len(fixtures)],
                                                          f"BURST_{concurrency}_{i}"), range(concurrency)))
        duration = time.perf_counter() - started
        latencies = sorted(r["client_rtt_ms"] for r in results)
        statuses = Counter(str(r["response"].get("status")) for r in results)
        backends = Counter(str(r["response"].get("audit_backend")) for r in results)
        for result in results:
            data = result["response"]
            rows.append({"task_id": result["task_id"], "concurrency": concurrency,
                         "http_status": result["http_status"], "status": data.get("status"),
                         "client_rtt_ms": result["client_rtt_ms"],
                         "cloud_processing_time_ms": data.get("cloud_processing_time_ms"),
                         "queue_and_decode_time_ms": data.get("queue_and_decode_time_ms"),
                         "server_total_time_ms": data.get("server_total_time_ms"),
                         "audit_backend": data.get("audit_backend")})
        report["batches"].append({"concurrency": concurrency, "requests": len(results),
            "duration_seconds": round(duration, 3), "completed_tps": round(len(results)/duration, 3),
            "p50_client_rtt_ms": latencies[math.ceil(len(latencies)*.5)-1],
            "p95_client_rtt_ms": latencies[math.ceil(len(latencies)*.95)-1],
            "p99_client_rtt_ms": latencies[math.ceil(len(latencies)*.99)-1],
            "statuses": dict(statuses), "audit_backends": dict(backends),
            "http_statuses": dict(Counter(r["http_status"] for r in results))})

    metrics = request("/metrics")
    (output / f"{run_id}_metrics.prom").write_text(str(metrics["response"]))
    (output / f"{run_id}.json").write_text(json.dumps(report, indent=2) + "\n")
    if rows:
        with (output / f"{run_id}_burst.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    passed = (report["ready"]["http_status"] == 200 and len(fixtures) > 0
              and all(r["http_status"] == 200 and r["response"].get("status") == "success"
                      and r["response"].get("audit_backend") == "postgres" for r in report["functional"])
              and report["no_face"]["response"].get("authorized") is False
              and report["invalid_image"]["http_status"] == 400
              and report["invalid_base64"]["http_status"] == 400
              and report["invalid_schema"]["http_status"] == 422
              and all(b["statuses"] == {"success": b["requests"]}
                      and b["audit_backends"] == {"postgres": b["requests"]} for b in report["batches"]))
    print(json.dumps({"run_id": run_id, "passed": passed, "profiles_tested": len(fixtures),
                      "batches": report["batches"], "report_path": str(output / f"{run_id}.json")}))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
