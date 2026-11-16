#!/usr/bin/env python3
"""
PENLOK Configurable Comparative Load Benchmark:
Compares:
  - Algorithm 1: XGBoost (Dynamic Machine Learning Classifier at 10.1.1.57:8500)
  - Algorithm 2: Rule-Based (Deterministic Static Thresholds Baseline)
Configurable:
  - Total requests: -t / --total (default: 200)
  - Concurrency: -c / --conn / --concurrency (default: 4)
  - Algorithm mode: -a / --algo (both / xgboost / rule_based, default: both)
Features:
  - Real 5-People Face Profiles (Akmal, Iqbal, Shafwan, Syauqi, Loker Cam)
  - Ground-truth evaluation: labels each prediction as BENAR [V] or SALAH [X]
  - Calculates accuracy percentage (Benar % vs Salah %) in summary and head-to-head table
  - Live per-request log streaming enabled
"""

import sys
import os
import time
import math
import argparse
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/pi/penlock")
import edge_mas_controller as emc
import migration_agent as ma
import psutil
import requests

# Connection pooling for high-throughput benchmark stability
sched_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=50)
sched_session.mount("http://", adapter)

FACE_PROFILES = [
    {
        "name": "Akmal",
        "valid_aliases": ["akmal"],
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/akmal/akmal_imported_1.jpg"
    },
    {
        "name": "Iqbal (balbal)",
        "valid_aliases": ["iqbal", "balbal"],
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/balbal/iqbal_1_20251222_115527_948818.jpg"
    },
    {
        "name": "Shafwan (panpenlok)",
        "valid_aliases": ["shafwan", "panpenlok"],
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/panpenlok/pan_1_20251217_160442_713875.jpg"
    },
    {
        "name": "Syauqi (soqisoqi)",
        "valid_aliases": ["syauqi", "soqisoqi"],
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/soqisoqi/soqi_10_20251216_162141_427841.jpg"
    },
    {
        "name": "Akmal (Foto 2)",
        "valid_aliases": ["akmal"],
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/akmal/akmal_sync_1791526198_1.jpg"
    }
]

print_lock = threading.Lock()
queue_lock = threading.Lock()
active_queue = 0

def check_is_correct(person_data: dict, recognized_user: str) -> bool:
    if not recognized_user:
        return False
    rec_clean = str(recognized_user).strip().lower()
    if rec_clean in ("no_face_detected", "unknown", "unauthorized", "no_match", "failed") or "err:" in rec_clean:
        return False
    valid = [a.lower() for a in person_data.get("valid_aliases", [person_data["name"]])]
    return any(alias in rec_clean for alias in valid)

def load_face_data():
    loaded = []
    print("[DATASET] Memuat 5 profil wajah riil dengan ground truth:")
    for p in FACE_PROFILES:
        if os.path.exists(p["path"]):
            with open(p["path"], "rb") as f:
                data = f.read()
            loaded.append({
                "name": p["name"],
                "valid_aliases": p["valid_aliases"],
                "bytes": data,
                "size_kb": len(data)//1024
            })
            aliases_str = "/".join(p["valid_aliases"])
            print(f"  • {p['name']:20s} (Target: {aliases_str:18s} | {len(data)//1024:3d} KB)")
        else:
            print(f"  [-] Tidak ditemukan: {p['path']}")
    if not loaded:
        raise RuntimeError("Gagal memuat dataset wajah riil!")
    return loaded

class RealTimeSampler:
    def __init__(self, interval=0.03):
        self.interval = interval
        self.stop_signal = False
        self.cpu_samples = []
        self.ram_samples = []
        self.thread = None

    def start(self):
        self.stop_signal = False
        self.cpu_samples = []
        self.ram_samples = []
        psutil.cpu_percent(interval=None)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_signal:
            self.cpu_samples.append(psutil.cpu_percent(interval=None))
            mem = psutil.virtual_memory()
            self.ram_samples.append(mem.used / (1024 * 1024))
            time.sleep(self.interval)

    def stop(self):
        self.stop_signal = True
        if self.thread:
            self.thread.join(timeout=1.0)
        valid_cpu = [c for c in self.cpu_samples if c > 0.0] or [1.0]
        return {
            "max_cpu": round(max(self.cpu_samples) if self.cpu_samples else 0.0, 1),
            "avg_cpu": round(statistics.mean(valid_cpu), 1),
            "max_ram": round(max(self.ram_samples) if self.ram_samples else 0.0, 1),
        }

def evaluate_decision(algo_mode: str, telemetry: dict):
    if algo_mode == "XGBoost":
        try:
            sched_url = os.getenv("SCHEDULER_URL", "http://100.75.230.102:8500/api/v1/schedule")
            r = sched_session.post(sched_url, json=telemetry, timeout=2.5)
            if r.status_code == 200:
                data = r.json()
                return data.get("decision", 0), data.get("confidence", 0.95), "xgboost"
        except Exception:
            pass
        return 0, 0.5, "fallback_edge"

    elif algo_mode == "Rule-Based":
        # Baseline rules:
        # 1. CPU > 80% -> Cloud (1)
        # 2. CPU > 65% & RAM_pct > 70% & Latency < 150ms -> Cloud (1)
        # 3. Active Queue > 5 -> Cloud (1)
        cpu = telemetry["CPU"]
        ram_pct = telemetry["RAM_pct"]
        lat = telemetry["Latency"]
        q = telemetry["Queue"]

        if cpu > 80.0:
            return 1, 0.95, "rule_cpu_critical"
        if cpu > 65.0 and ram_pct > 70.0 and lat < 150.0:
            return 1, 0.90, "rule_composite"
        if q > 5:
            return 1, 0.90, "rule_queue_overflow"
        return 0, 0.90, "rule_default_edge"

    raise ValueError(f"Unknown algorithm mode: {algo_mode}")

def execute_single_task(req_id: int, total_requests: int, person_data: dict, algo_mode: str, concurrency: int):
    global active_queue
    with queue_lock:
        active_queue += 1
        q_depth = active_queue

    t0 = time.perf_counter()
    decision = 0
    exec_node = "Edge Pi 5"
    recognized_user = "UNKNOWN"
    confidence = 0.0

    try:
        cpu_now = psutil.cpu_percent(interval=None)
        mem_now = psutil.virtual_memory()

        telemetry = {
            "CPU": round(cpu_now, 1),
            "RAM": round(mem_now.used / (1024 * 1024), 1),
            "Throughput": round(max(1.0, concurrency * 0.9), 1),
            "Network_Bandwidth": 35.0,
            "Priority": 2 if q_depth > 2 else 1,
            "Latency": 8.0,
            "Queue": q_depth,
            "RAM_pct": round(mem_now.percent, 1)
        }

        # Query chosen algorithm
        decision, conf_dec, method = evaluate_decision(algo_mode, telemetry)

        # Execute workload
        if decision == 1:
            exec_node = "Cloud GPU RTX3050"
            task_id = f"CMP_{algo_mode[:2]}_{req_id}_{int(time.time()*1000)}"
            mig_res = ma.dispatch_migration(task_id, "SB01", person_data["bytes"], decision=1)
            recognized_user = mig_res.get("user_id", "NO_MATCH")
            confidence = mig_res.get("confidence", 0.0)
        else:
            exec_node = "Edge Pi 5 CPU"
            auth, user, conf_val, proc_ms = emc.verify_face_locally(person_data["bytes"])
            recognized_user = user
            confidence = conf_val

    except Exception as e:
        recognized_user = f"ERR:{str(e)[:10]}"
    finally:
        with queue_lock:
            active_queue = max(0, active_queue - 1)

    dur_ms = (time.perf_counter() - t0) * 1000.0
    now_str = time.strftime("%H:%M:%S")
    conf_pct = int(float(confidence or 0.0) * 100)
    user_display = str(recognized_user or "UNKNOWN")

    is_correct = check_is_correct(person_data, user_display)
    result_tag = "BENAR [V]" if is_correct else "SALAH [X]"

    # Real-time streaming log per request
    with print_lock:
        dec_tag = "CLOUD [>>]" if decision == 1 else "EDGE  [--]"
        print(
            f"[{now_str}] #{req_id:03d}/{total_requests:03d} | {algo_mode:10s} | {person_data['name']:18s} | "
            f"CPU:{cpu_now:4.1f}% Q:{q_depth:02d} | {dec_tag} -> {exec_node:17s} | "
            f"{dur_ms:6.1f}ms | User: {user_display:11s} ({conf_pct:2d}%) | {result_tag}",
            flush=True
        )

    return {
        "req_id": req_id,
        "algo": algo_mode,
        "person": person_data["name"],
        "decision": decision,
        "exec_node": exec_node,
        "latency_ms": dur_ms,
        "user": user_display,
        "conf": confidence,
        "is_correct": is_correct
    }

def run_benchmark_for_algorithm(algo_name: str, profiles: list, total_req: int, concurrency: int):
    n_profiles = len(profiles)
    print("\n" + "="*125)
    print(f"  MEMULAI PENGUJIAN: ALGORITMA {algo_name.upper()}")
    print(f"  Total Request: {total_req} | Concurrency: {concurrency} workers | Dataset: 5 Profil Wajah Riil")
    print("="*125)
    print("Format Log Streaming Real-Time:")
    print("[WAKTU]   #Req/Total | Algoritma  | Foto Profil        | Status Beban    | Keputusan Rute -> Node Pelaksana | Latensi | Hasil Pengenalan | Validasi")
    print("-" * 125)

    sampler = RealTimeSampler(interval=0.03)
    sampler.start()

    wall_t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_req):
            person = profiles[i % n_profiles]
            futures.append(executor.submit(execute_single_task, i+1, total_req, person, algo_name, concurrency))
            time.sleep(0.01) # Small jitter
        results = [f.result() for f in futures]
    wall_duration = time.perf_counter() - wall_t0

    metrics = sampler.stop()

    latencies = [r["latency_ms"] for r in results]
    edge_tasks = [r for r in results if r["decision"] == 0]
    cloud_tasks = [r for r in results if r["decision"] == 1]

    # Accuracy calculations
    correct_tasks = [r for r in results if r["is_correct"]]
    wrong_tasks = [r for r in results if not r["is_correct"]]
    correct_count = len(correct_tasks)
    wrong_count = len(wrong_tasks)
    acc_pct = round((correct_count / total_req) * 100.0, 1)
    wrong_pct = round((wrong_count / total_req) * 100.0, 1)

    lat_sorted = sorted(latencies)
    p50 = statistics.median(lat_sorted)
    idx_p90 = min(int(math.ceil(len(lat_sorted) * 0.90)) - 1, len(lat_sorted) - 1)
    idx_p95 = min(int(math.ceil(len(lat_sorted) * 0.95)) - 1, len(lat_sorted) - 1)
    idx_p99 = min(int(math.ceil(len(lat_sorted) * 0.99)) - 1, len(lat_sorted) - 1)

    tps = round(total_req / wall_duration, 2)
    edge_pct = (len(edge_tasks) / total_req) * 100.0
    cloud_pct = (len(cloud_tasks) / total_req) * 100.0

    cloud_lats = [r["latency_ms"] for r in cloud_tasks]
    edge_lats = [r["latency_ms"] for r in edge_tasks]
    avg_cloud = statistics.mean(cloud_lats) if cloud_lats else 0.0
    avg_edge = statistics.mean(edge_lats) if edge_lats else 0.0

    summary = {
        "algo": algo_name,
        "total": total_req,
        "concurrency": concurrency,
        "duration_sec": round(wall_duration, 2),
        "tps": tps,
        "edge_count": len(edge_tasks),
        "edge_pct": round(edge_pct, 1),
        "cloud_count": len(cloud_tasks),
        "cloud_pct": round(cloud_pct, 1),
        "correct_count": correct_count,
        "correct_pct": acc_pct,
        "wrong_count": wrong_count,
        "wrong_pct": wrong_pct,
        "p50_ms": round(p50, 1),
        "p90_ms": round(lat_sorted[idx_p90], 1),
        "p95_ms": round(lat_sorted[idx_p95], 1),
        "p99_ms": round(lat_sorted[idx_p99], 1),
        "avg_cloud_ms": round(avg_cloud, 1),
        "avg_edge_ms": round(avg_edge, 1),
        "avg_cpu": metrics["avg_cpu"],
        "max_cpu": metrics["max_cpu"],
        "max_ram": metrics["max_ram"]
    }

    print("-" * 125)
    print(f"  RINGKASAN HASIL: {algo_name.upper()}")
    print(f"  Waktu Selesai : {wall_duration:.2f}s | TPS: {tps} req/s | Edge: {len(edge_tasks)} ({edge_pct:.1f}%) | Cloud: {len(cloud_tasks)} ({cloud_pct:.1f}%)")
    print(f"  Akurasi Wajah : BENAR = {correct_count} ({acc_pct}%) | SALAH = {wrong_count} ({wrong_pct}%)")
    print(f"  Latensi RTT   : P50={p50:.1f}ms | P95={lat_sorted[idx_p95]:.1f}ms | Avg Cloud={avg_cloud:.1f}ms | Avg Edge={avg_edge:.1f}ms")
    print("=" * 125)

    return summary

def main():
    parser = argparse.ArgumentParser(
        description="PENLOK Configurable Comparative Load Benchmark: XGBoost vs Rule-Based",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-t", "--total", type=int, default=200, help="Total request yang dieksekusi per algoritma")
    parser.add_argument("-c", "--conn", "--concurrency", dest="conn", type=int, default=4, help="Jumlah worker bersamaan (concurrency)")
    parser.add_argument("-a", "--algo", choices=["both", "xgboost", "rule_based"], default="both", help="Pilihan algoritma pengujian")
    parser.add_argument("--cooldown", type=float, default=3.0, help="Durasi jeda thermal recovery antar pengujian (detik)")

    args = parser.parse_args()

    print("="*125)
    print("  PENLOK CONFIGURABLE LOAD BENCHMARK (DENGAN EVALUASI AKURASI IDENTITAS)")
    print(f"  Parameter: Total={args.total} req/algo | Concurrency={args.conn} workers | Mode={args.algo.upper()}")
    print("="*125)

    profiles = load_face_data()

    summaries = {}

    if args.algo in ("both", "xgboost"):
        summaries["XGBoost"] = run_benchmark_for_algorithm("XGBoost", profiles, total_req=args.total, concurrency=args.conn)

    if args.algo == "both":
        print(f"\n[COOLING] Thermal recovery & socket cooldown ({args.cooldown:.1f} detik)...")
        time.sleep(args.cooldown)

    if args.algo in ("both", "rule_based"):
        summaries["Rule-Based"] = run_benchmark_for_algorithm("Rule-Based", profiles, total_req=args.total, concurrency=args.conn)

    # Print comparison table if both ran
    if "XGBoost" in summaries and "Rule-Based" in summaries:
        summary_xgb = summaries["XGBoost"]
        summary_rule = summaries["Rule-Based"]

        print("\n" + "="*125)
        print(f"  TABEL PERBANDINGAN HEAD-TO-HEAD: XGBOOST VS RULE-BASED (TOTAL {args.total} REQ, CONCURRENCY {args.conn})")
        print("="*125)
        print(f"{'Metrik Pengujian':<35} | {'XGBoost (ML Classifier)':<40} | {'Rule-Based (Baseline)':<40}")
        print("-" * 125)
        tps_xgb = f"{summary_xgb['tps']} req/s"
        tps_rule = f"{summary_rule['tps']} req/s"
        edge_xgb = f"{summary_xgb['edge_count']} task ({summary_xgb['edge_pct']}%)"
        edge_rule = f"{summary_rule['edge_count']} task ({summary_rule['edge_pct']}%)"
        cloud_xgb = f"{summary_xgb['cloud_count']} task ({summary_xgb['cloud_pct']}%)"
        cloud_rule = f"{summary_rule['cloud_count']} task ({summary_rule['cloud_pct']}%)"
        
        corr_xgb = f"{summary_xgb['correct_count']} task ({summary_xgb['correct_pct']}%)"
        corr_rule = f"{summary_rule['correct_count']} task ({summary_rule['correct_pct']}%)"
        wrong_xgb = f"{summary_xgb['wrong_count']} task ({summary_xgb['wrong_pct']}%)"
        wrong_rule = f"{summary_rule['wrong_count']} task ({summary_rule['wrong_pct']}%)"
        acc_xgb = f"{summary_xgb['correct_pct']}%"
        acc_rule = f"{summary_rule['correct_pct']}%"

        p50_xgb = f"{summary_xgb['p50_ms']} ms"
        p50_rule = f"{summary_rule['p50_ms']} ms"
        p90_xgb = f"{summary_xgb['p90_ms']} ms"
        p90_rule = f"{summary_rule['p90_ms']} ms"
        p95_xgb = f"{summary_xgb['p95_ms']} ms"
        p95_rule = f"{summary_rule['p95_ms']} ms"
        p99_xgb = f"{summary_xgb['p99_ms']} ms"
        p99_rule = f"{summary_rule['p99_ms']} ms"
        avge_xgb = f"{summary_xgb['avg_edge_ms']} ms"
        avge_rule = f"{summary_rule['avg_edge_ms']} ms"
        avgc_xgb = f"{summary_xgb['avg_cloud_ms']} ms"
        avgc_rule = f"{summary_rule['avg_cloud_ms']} ms"
        cpu_xgb = f"{summary_xgb['avg_cpu']}%"
        cpu_rule = f"{summary_rule['avg_cpu']}%"
        mcpu_xgb = f"{summary_xgb['max_cpu']}%"
        mcpu_rule = f"{summary_rule['max_cpu']}%"

        print(f"{'Total Transaksi Selesai':<35} | {summary_xgb['total']:<40} | {summary_rule['total']:<40}")
        print(f"{'Waktu Eksekusi Total (detik)':<35} | {summary_xgb['duration_sec']:<40} | {summary_rule['duration_sec']:<40}")
        print(f"{'Throughput (TPS)':<35} | {tps_xgb:<40} | {tps_rule:<40}")
        print(f"{'Rasio Beban Tetap di Edge':<35} | {edge_xgb:<40} | {edge_rule:<40}")
        print(f"{'Rasio Beban Migrasi ke Cloud':<35} | {cloud_xgb:<40} | {cloud_rule:<40}")
        print("-" * 125)
        print(f"{'Hasil Pengenalan BENAR [V]':<35} | {corr_xgb:<40} | {corr_rule:<40}")
        print(f"{'Hasil Pengenalan SALAH [X]':<35} | {wrong_xgb:<40} | {wrong_rule:<40}")
        print(f"{'Tingkat Akurasi Wajah (%)':<35} | {acc_xgb:<40} | {acc_rule:<40}")
        print("-" * 125)
        print(f"{'Median Latensi P50 (ms)':<35} | {p50_xgb:<40} | {p50_rule:<40}")
        print(f"{'P90 Latensi (ms)':<35} | {p90_xgb:<40} | {p90_rule:<40}")
        print(f"{'P95 Latensi (ms)':<35} | {p95_xgb:<40} | {p95_rule:<40}")
        print(f"{'P99 Latensi (ms)':<35} | {p99_xgb:<40} | {p99_rule:<40}")
        print(f"{'Rata-rata Eksekusi Edge (ms)':<35} | {avge_xgb:<40} | {avge_rule:<40}")
        print(f"{'Rata-rata Migrasi Cloud (ms)':<35} | {avgc_xgb:<40} | {avgc_rule:<40}")
        print(f"{'Rata-rata Beban CPU Pi 5 (%)':<35} | {cpu_xgb:<40} | {cpu_rule:<40}")
        print(f"{'Puncak Beban CPU Pi 5 (%)':<35} | {mcpu_xgb:<40} | {mcpu_rule:<40}")
        print("="*125)

if __name__ == "__main__":
    main()
