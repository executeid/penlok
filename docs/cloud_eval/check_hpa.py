"""Cloud-only sustained load and real HPA observation, with enrolled-photo bias.

Use only after explicitly deploying cloud-api-hpa.yaml on the lab cloud node.
Never contacts an edge node or controls hardware.
"""
import base64
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


def kubectl(*args):
    return subprocess.check_output(["sudo", "-n", "kubectl", *args], text=True)


def state():
    hpa = json.loads(kubectl("get", "hpa", "cloud-api-hpa", "-n", "cloud-agent", "-o", "json"))
    dep = json.loads(kubectl("get", "deployment", "cloud-api", "-n", "cloud-agent", "-o", "json"))
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "desired_replicas": dep["spec"]["replicas"],
            "ready_replicas": dep.get("status", {}).get("readyReplicas", 0),
            "hpa": hpa.get("status", {})}


def main():
    root = Path(__file__).resolve().parent.parent
    fixture = next(Path("/home/penlok/app/gallery/imagetraining").glob("akmal/*.jpg"))
    image = base64.b64encode(fixture.read_bytes()).decode()
    run_id = datetime.now(timezone.utc).strftime("HPA_%Y%m%dT%H%M%S")
    stop = threading.Event()
    lock = threading.Lock()
    results = Counter()
    samples = []
    serial = 0

    def worker():
        nonlocal serial
        while not stop.is_set():
            with lock:
                serial += 1
                task = serial
            body = json.dumps({"task_id": f"{run_id}_{task}", "device_id": "cloud_hpa_test",
                               "image": image, "decision": 1}).encode()
            req = urllib.request.Request("http://127.0.0.1:30900/api/v1/migration", data=body,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                    key = f'{resp.status}:{data.get("status")}:{data.get("audit_backend")}'
            except (OSError, ValueError) as exc:
                key = type(exc).__name__
            with lock:
                results[key] += 1

    initial = state()
    if initial["desired_replicas"] != 1 or initial["ready_replicas"] != 1:
        raise RuntimeError("Expected one ready cloud-api replica before the HPA test")
    started = time.perf_counter()
    scale_up = None
    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            try:
                while time.perf_counter() - started < 90:
                    current = state()
                    samples.append(current)
                    if current["desired_replicas"] == 2 and current["ready_replicas"] == 2:
                        scale_up = round(time.perf_counter() - started, 3)
                        break
                    time.sleep(3)
            finally:
                stop.set()
            for future in futures:
                future.result()
    finally:
        stop.set()
    load_seconds = round(time.perf_counter() - started, 3)
    idle_started = time.perf_counter()
    scale_down = None
    while time.perf_counter() - idle_started < 150:
        current = state()
        samples.append(current)
        if current["desired_replicas"] == 1 and current["ready_replicas"] == 1:
            scale_down = round(time.perf_counter() - idle_started, 3)
            break
        time.sleep(5)
    report = {"run_id": run_id, "initial": initial,
              "concurrent_workers": 50, "load_seconds": load_seconds,
              "results": dict(results), "scale_up_two_ready_seconds": scale_up,
              "scale_down_one_ready_seconds": scale_down,
              "gpu_allocation": "two pods share physical GPU 0; no device-plugin allocation",
              "samples": samples}
    (root / "evidence/cloud-api-hpa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}))
    raise SystemExit(0 if scale_up is not None and scale_down is not None else 1)


if __name__ == "__main__":
    main()
