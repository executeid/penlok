"""Delete only the cloud-api pod and measure replacement + HTTP readiness.

Run explicitly on the cloud host after deploying and verifying the new API.
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path


def kubectl(*args):
    return subprocess.check_output(["sudo", "-n", "kubectl", *args], text=True)


def main():
    pods = json.loads(kubectl("get", "pods", "-n", "cloud-agent", "-l", "app=cloud-api", "-o", "json"))["items"]
    running = [p for p in pods if not p["metadata"].get("deletionTimestamp")]
    if len(running) != 1 or running[0]["spec"]["containers"][0]["image"] != "penlok-cloud-agent:20261029-v2":
        raise RuntimeError("Expected exactly the newly deployed cloud-api pod; refusing deletion")
    old = running[0]["metadata"]
    started = time.perf_counter()
    kubectl("delete", "pod", old["name"], "-n", "cloud-agent", "--wait=false")
    report = {"old_pod": old["name"], "old_uid": old["uid"], "recovered": False}
    while time.perf_counter() - started < 90:
        pods = json.loads(kubectl("get", "pods", "-n", "cloud-agent", "-l", "app=cloud-api", "-o", "json"))["items"]
        ready = [p for p in pods if p["metadata"]["uid"] != old["uid"]
                 and not p["metadata"].get("deletionTimestamp")
                 and any(c["type"] == "Ready" and c["status"] == "True" for c in p["status"].get("conditions", []))]
        if ready:
            try:
                with urllib.request.urlopen("http://127.0.0.1:30900/ready", timeout=5) as response:
                    if response.status == 200:
                        report.update(recovered=True, new_pod=ready[0]["metadata"]["name"],
                                      new_uid=ready[0]["metadata"]["uid"],
                                      ready_response=json.loads(response.read()),
                                      recovery_seconds=round(time.perf_counter()-started, 3))
                        break
            except OSError:
                pass
        time.sleep(1)
    path = Path(__file__).resolve().parent.parent / "evidence/cloud-api-recovery.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    raise SystemExit(0 if report["recovered"] else 1)


if __name__ == "__main__":
    main()
