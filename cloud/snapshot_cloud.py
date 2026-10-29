"""Collect reduced cloud infrastructure/DB evidence without exporting secrets."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def command(*args):
    return subprocess.check_output(args, text=True)


def kube(kind, name=None):
    args = ["sudo", "-n", "kubectl", "get", kind]
    if name:
        args.append(name)
    return json.loads(command(*args, "-n", "cloud-agent", "-o", "json"))


def main():
    root = Path(__file__).resolve().parent.parent
    dep = kube("deployment", "cloud-api")
    pods = kube("pods")["items"]
    services = kube("services")["items"]
    hpa = kube("hpa", "cloud-api-hpa")
    node = json.loads(command("sudo", "-n", "kubectl", "get", "node", "pengmas-tri", "-o", "json"))
    events = kube("events")["items"]
    inspected = json.loads(command("docker", "inspect", "cloud-face-agent"))[0]
    latest = sorted((root / "evidence").glob("CLOUD_*.json"))[-1]
    run_id = json.loads(latest.read_text())["run_id"]
    sql_code = '''import os,json,sys,psycopg2
c=psycopg2.connect(host=os.environ["DB_HOST"],port=os.environ["DB_PORT"],user=os.environ["DB_USER"],password=os.environ["DB_PASSWORD"],dbname=os.environ["DB_NAME"],connect_timeout=3)
q=c.cursor()
out={}
for prefix in sys.argv[1:]:
 q.execute("SELECT status,count(*),min(processing_time_ms)::float,max(processing_time_ms)::float,avg(processing_time_ms)::float FROM cloud_task_log WHERE task_id LIKE %s GROUP BY status ORDER BY status",(prefix+"%",))
 out[prefix]=[dict(zip(["status","count","min_processing_ms","max_processing_ms","avg_processing_ms"],r)) for r in q.fetchall()]
q.execute("SELECT count(*) FROM cloud_task_log")
out["total_rows"]=q.fetchone()[0]
print(json.dumps(out));c.close()
'''
    hpa_run = json.loads((root / "evidence/cloud-api-hpa.json").read_text())["run_id"]
    database = json.loads(command("docker", "exec", "cloud-face-agent", "python", "-c", sql_code, run_id, hpa_run))
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "node": {"name": node["metadata"]["name"], "conditions": node["status"]["conditions"],
                 "allocatable": node["status"]["allocatable"]},
        "deployment": {"name": dep["metadata"]["name"], "spec_replicas": dep["spec"]["replicas"],
                       "status": dep["status"], "image": dep["spec"]["template"]["spec"]["containers"][0]["image"],
                       "resources": dep["spec"]["template"]["spec"]["containers"][0]["resources"]},
        "pods": [{"name": p["metadata"]["name"], "uid": p["metadata"]["uid"], "status": p["status"]}
                 for p in pods if p["metadata"]["labels"].get("app") == "cloud-api"],
        "services": [{"name": s["metadata"]["name"], "ports": s["spec"]["ports"]}
                     for s in services if s["metadata"]["name"] in ("cloud-api", "cloud-api-svc")],
        "hpa": {"spec": hpa["spec"], "status": hpa["status"]},
        "events": [{"reason": e.get("reason"), "message": e.get("message"),
                    "firstTimestamp": e.get("firstTimestamp"), "lastTimestamp": e.get("lastTimestamp"),
                    "count": e.get("count"), "object": e["involvedObject"]["name"]}
                   for e in events if e["involvedObject"]["name"].startswith("cloud-api")],
        "database": database,
        "legacy_container": {"name": inspected["Name"], "image_id": inspected["Image"],
                             "state": inspected["State"]},
        "source_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                          for name in ("main.py", "cloud_app_main_full.py")},
        "gpu": command("nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader").strip(),
        "disk": command("df", "-h", "/").strip(),
    }
    (root / "evidence/cloud-final-state.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"image": report["deployment"]["image"], "database": database,
                      "pods": [{"name": p["name"], "phase": p["status"]["phase"],
                                "restart_counts": [c["restartCount"] for c in p["status"].get("containerStatuses", [])]}
                               for p in report["pods"]]}))


if __name__ == "__main__":
    main()
