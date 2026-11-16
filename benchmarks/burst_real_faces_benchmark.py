#!/usr/bin/env python3
"""
PENLOK Burst Load Benchmark with Real 5-People Face Dataset
Streams live per-request logs during the burst, displaying:
- Person Name
- System State (Real CPU%, Queue depth)
- Scheduler Decision (EDGE vs CLOUD)
- Execution Node & Processing Latency
"""

import sys
import os
import time
import argparse
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/pi/penlock")
import edge_mas_controller as emc
import migration_agent as ma
import psutil

FACE_PROFILES = [
    {
        "name": "Akmal",
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/akmal/akmal_imported_1.jpg"
    },
    {
        "name": "Iqbal (balbal)",
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/balbal/iqbal_1_20251222_115527_948818.jpg"
    },
    {
        "name": "Shafwan (panpenlok)",
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/panpenlok/pan_1_20251217_160442_713875.jpg"
    },
    {
        "name": "Syauqi (soqisoqi)",
        "path": "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining/soqisoqi/soqi_10_20251216_162141_427841.jpg"
    },
    {
        "name": "Loker Cam (Real)",
        "path": "/home/pi/penlock/test_camera.jpg"
    }
]

print_lock = threading.Lock()
queue_lock = threading.Lock()
active_queue = 0

def load_face_data():
    loaded = []
    print("[INIT] Memuat dataset foto riil 5 orang:")
    for p in FACE_PROFILES:
        if os.path.exists(p["path"]):
            with open(p["path"], "rb") as f:
                data = f.read()
            loaded.append({"name": p["name"], "bytes": data, "size_kb": len(data)//1024})
            print(f"  • {p['name']:20s}: {p['path']} ({len(data)//1024} KB)")
        else:
            print(f"  [-] Berkas tidak ditemukan: {p['path']}")
    if not loaded:
        raise RuntimeError("Tidak ada foto profil yang dapat dimuat!")
    return loaded

def execute_burst_request(req_id: int, total_requests: int, person_data: dict, concurrency: int):
    global active_queue
    with queue_lock:
        active_queue += 1
        q_depth = active_queue

    t0 = time.perf_counter()
    decision = 0
    exec_node = "Edge Pi 5"
    recognized_user = "UNKNOWN"
    confidence = 0.0
    status_label = "REJECTED"

    try:
        cpu_now = psutil.cpu_percent(interval=None)
        mem_now = psutil.virtual_memory()

        telemetry = {
            "CPU": round(cpu_now, 1),
            "RAM": round(mem_now.used / (1024 * 1024), 1),
            "Throughput": round(max(1.0, concurrency * 0.9), 1),
            "Network_Bandwidth": 35.0,
            "Priority": 2 if q_depth > 3 else 1,
            "Latency": 8.0,
            "Queue": q_depth,
            "RAM_pct": round(mem_now.percent, 1)
        }

        # Query Scheduler
        decision, sched_conf, method = emc.query_scheduler_agent(telemetry)

        if decision == 1:
            exec_node = "Cloud GPU RTX3050"
            task_id = f"BURST_{req_id}_{int(time.time()*1000)}"
            mig_res = ma.dispatch_migration(task_id, "SB01", person_data["bytes"], decision=1)
            recognized_user = mig_res.get("user_id", "NO_MATCH")
            confidence = mig_res.get("confidence", 0.0)
            status_label = mig_res.get("status", "FAILED")
        else:
            exec_node = "Edge Pi 5 CPU"
            auth, user, conf_val, proc_ms = emc.verify_face_locally(person_data["bytes"])
            recognized_user = user
            confidence = conf_val
            status_label = "AUTHORIZED" if auth else "REJECTED"

    except Exception as e:
        status_label = f"ERR:{str(e)[:15]}"
    finally:
        with queue_lock:
            active_queue = max(0, active_queue - 1)

    dur_ms = (time.perf_counter() - t0) * 1000.0
    now_str = time.strftime("%H:%M:%S")

    conf_pct = int(float(confidence or 0.0) * 100)
    user_display = str(recognized_user or "UNKNOWN")
    # Real-time streaming log per request
    with print_lock:
        dec_tag = "CLOUD [>>]" if decision == 1 else "EDGE  [--]"
        print(
            f"[{now_str}] #{req_id:02d}/{total_requests} | {person_data['name']:18s} | "
            f"CPU:{cpu_now:4.1f}% Q:{q_depth:02d} | Decision: {dec_tag} | "
            f"Node: {exec_node:17s} | {dur_ms:6.1f} ms | User: {user_display:12s} ({conf_pct:2d}%)",
            flush=True
        )

    return {
        "req_id": req_id,
        "person": person_data["name"],
        "decision": decision,
        "exec_node": exec_node,
        "latency_ms": dur_ms,
        "user": recognized_user,
        "conf": confidence,
        "status": status_label
    }

def run_burst(total_requests=40, concurrency=10):
    profiles = load_face_data()
    n_profiles = len(profiles)

    print("\n" + "="*115)
    print(f"  MEMULAI BURST STREAMING: {total_requests} REQUEST DENGAN {concurrency} WORKER KONKUREN")
    print(f"  Dataset: {n_profiles} Orang Berulang Kali (Akmal, Iqbal, Shafwan, Syauqi, Loker Cam)")
    print("="*115)
    print("Format Log Real-Time:")
    print("[JAM:MENIT:DETIK] #Req/Total | Foto Profil        | Status Edge     | Keputusan        | Node Pelaksana    | Latensi  | Hasil Pengenalan")
    print("-" * 115)

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            person = profiles[i % n_profiles]
            futures.append(executor.submit(execute_burst_request, i+1, total_requests, person, concurrency))
            # Tiny jitter to simulate realistic burst arrival rate
            time.sleep(0.02)
        results = [f.result() for f in futures]
    wall_duration = time.perf_counter() - wall_start

    # Summary
    edge_count = sum(1 for r in results if r["decision"] == 0)
    cloud_count = sum(1 for r in results if r["decision"] == 1)
    latencies = [r["latency_ms"] for r in results]

    print("-" * 115)
    print("  RINGKASAN AKHIR BURST PENGUJIAN 5 ORANG")
    print("="*115)
    print(f"Total Request Diproses  : {total_requests} request")
    print(f"Waktu Total Eksekusi    : {wall_duration:.2f} detik")
    print(f"Throughput Rata-Rata    : {total_requests / wall_duration:.2f} req / detik")
    print(f"Beban Diproses di Edge  : {edge_count:2d} ({edge_count/total_requests*100:.1f}%)")
    print(f"Beban Dialihkan ke Cloud: {cloud_count:2d} ({cloud_count/total_requests*100:.1f}%)")
    print(f"Median Latensi (P50)    : {statistics.median(latencies):.1f} ms")
    print(f"P95 Latensi             : {sorted(latencies)[int(len(latencies)*0.95)-1]:.1f} ms")
    print("="*115)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--total", type=int, default=30, help="Total request burst (default: 30)")
    parser.add_argument("-c", "--concurrency", type=int, default=8, help="Worker bersamaan (default: 8)")
    args = parser.parse_args()
    run_burst(total_requests=args.total, concurrency=args.concurrency)
