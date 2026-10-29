#!/usr/bin/env python3
"""
PENLOK 3-Scenarios Comparative Benchmark Harness
Scenarios:
  A. Edge-Only: All workload executed on Raspberry Pi 5 CPU (No Migration).
  B. Rule-Based: Migration triggered when CPU > 80% (or CPU > 65% & RAM > 70% & Latency < 150ms).
  C. ML-Orchestration: Dynamic Multi-Agent scheduling using trained XGBoost model evaluating 7 features.
Concurrency batches: [10, 25, 50, 75, 100]
Measures: Latency (P50, P95, P99), Throughput (TPS), CPU (%), RAM (MB), Migration Time (ms), Success Rate (%).
Outputs to: /home/pi/penlock/data/scenario_comparison.csv
"""

import sys
import os
import time
import math
import statistics
import threading
import csv
import json
import psutil
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/pi/penlock")
import edge_mas_controller as emc
import migration_agent as ma

CONCURRENCY_LEVELS = [10, 25, 50, 75, 100]
SAMPLE_IMAGE = "/home/pi/penlock/pyenv3.9code/nonsudo/capture_20250725_164459.jpg"
OUTPUT_CSV = "/home/pi/penlock/data/scenario_comparison.csv"

# Preload image
with open(SAMPLE_IMAGE, "rb") as f:
    IMG_BYTES = f.read()

# Warm-up call
emc.verify_face_locally(IMG_BYTES)
psutil.cpu_percent(interval=None)

class SystemSampler:
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
        max_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        avg_cpu = statistics.mean(valid_cpu) if valid_cpu else 0.0
        max_ram = max(self.ram_samples) if self.ram_samples else 0.0
        avg_ram = statistics.mean(self.ram_samples) if self.ram_samples else 0.0
        return {
            "max_cpu": round(max_cpu, 1),
            "avg_cpu": round(avg_cpu, 1),
            "max_ram": round(max_ram, 1),
            "avg_ram": round(avg_ram, 1),
        }

active_queue_counter = 0
queue_lock = threading.Lock()

def execute_single_task(scenario: str, req_id: int, concurrency: int):
    global active_queue_counter
    with queue_lock:
        active_queue_counter += 1
        current_q = active_queue_counter

    t0 = time.perf_counter()
    migration_time = 0.0
    success = False

    try:
        cpu_now = psutil.cpu_percent(interval=None)
        mem_now = psutil.virtual_memory()

        if scenario == "Edge-Only":
            auth, user, conf, proc_ms = emc.verify_face_locally(IMG_BYTES)
            total_latency = (time.perf_counter() - t0) * 1000.0
            success = bool(auth)
            migration_time = 0.0

        elif scenario == "Rule-Based":
            # Rule B1: CPU > 80% or composite
            should_migrate = (cpu_now > 80.0) or (cpu_now > 65.0 and mem_now.percent > 70.0) or (current_q > 8)
            if should_migrate:
                t_mig0 = time.perf_counter()
                mig_res = ma.dispatch_migration(f"BENCH_RB_{concurrency}_{req_id}", "SB01", IMG_BYTES, decision=1)
                migration_time = (time.perf_counter() - t_mig0) * 1000.0
                total_latency = (time.perf_counter() - t0) * 1000.0
                success = (mig_res.get("status") == "Success")
            else:
                auth, user, conf, proc_ms = emc.verify_face_locally(IMG_BYTES)
                total_latency = (time.perf_counter() - t0) * 1000.0
                success = bool(auth)
                migration_time = 0.0

        elif scenario == "ML-Orchestration":
            telemetry = {
                "CPU": round(cpu_now, 1),
                "RAM": round(mem_now.used / (1024 * 1024), 1),
                "Throughput": round(max(1.0, concurrency * 0.8), 1),
                "Network_Bandwidth": 35.0,
                "Priority": 2 if concurrency > 10 else 1,
                "Latency": 15.0,
                "Queue": current_q,
                "RAM_pct": round(mem_now.percent, 1)
            }
            decision, conf, method = emc.query_scheduler_agent(telemetry)

            if decision == 1:
                t_mig0 = time.perf_counter()
                mig_res = ma.dispatch_migration(f"BENCH_ML_{concurrency}_{req_id}", "SB01", IMG_BYTES, decision=1)
                migration_time = (time.perf_counter() - t_mig0) * 1000.0
                total_latency = (time.perf_counter() - t0) * 1000.0
                success = (mig_res.get("status") == "Success")
            else:
                auth, user, conf, proc_ms = emc.verify_face_locally(IMG_BYTES)
                total_latency = (time.perf_counter() - t0) * 1000.0
                success = bool(auth)
                migration_time = 0.0
        else:
            raise ValueError(f"Unknown scenario {scenario}")

    except Exception as e:
        total_latency = (time.perf_counter() - t0) * 1000.0
        success = False
    finally:
        with queue_lock:
            active_queue_counter = max(0, active_queue_counter - 1)

    return total_latency, migration_time, success

def run_benchmark_batch(scenario: str, concurrency: int):
    print(f" -> Running [{scenario}] Concurrency={concurrency} ...", flush=True)
    sampler = SystemSampler(interval=0.03)
    sampler.start()

    wall_t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(execute_single_task, scenario, i, concurrency) for i in range(concurrency)]
        results = [f.result() for f in futures]
    wall_duration = time.perf_counter() - wall_t0

    metrics = sampler.stop()

    latencies = [r[0] for r in results]
    migration_times = [r[1] for r in results if r[1] > 0]
    successes = [r[2] for r in results]

    lat_sorted = sorted(latencies)
    p50 = statistics.median(lat_sorted)
    idx_p95 = min(int(math.ceil(len(lat_sorted) * 0.95)) - 1, len(lat_sorted) - 1)
    idx_p99 = min(int(math.ceil(len(lat_sorted) * 0.99)) - 1, len(lat_sorted) - 1)
    p95 = lat_sorted[idx_p95]
    p99 = lat_sorted[idx_p99]

    tps = round(concurrency / wall_duration, 2)
    success_rate = round((sum(successes) / len(successes)) * 100.0, 1)
    avg_migration_ms = round(statistics.mean(migration_times), 2) if migration_times else 0.0

    record = {
        "scenario": scenario,
        "concurrency": concurrency,
        "tps": tps,
        "p50_latency_ms": round(p50, 1),
        "p95_latency_ms": round(p95, 1),
        "p99_latency_ms": round(p99, 1),
        "avg_cpu_pct": metrics["avg_cpu"],
        "peak_cpu_pct": metrics["max_cpu"],
        "ram_mb": metrics["max_ram"],
        "avg_migration_ms": avg_migration_ms,
        "success_rate_pct": success_rate,
        "duration_sec": round(wall_duration, 2)
    }

    print(f"    Done: TPS={tps} | P50={p50:.1f}ms | P95={p95:.1f}ms | PeakCPU={metrics['max_cpu']}% | Success={success_rate}% | Dur={wall_duration:.2f}s", flush=True)
    return record

def main():
    print("="*75)
    print("  PENLOK 3-SCENARIOS COMPARATIVE BENCHMARK HARNESS")
    print("="*75)

    scenarios = ["Edge-Only", "Rule-Based", "ML-Orchestration"]
    all_results = []

    for sc in scenarios:
        print(f"\n==================== SCENARIO: {sc} ====================")
        for c in CONCURRENCY_LEVELS:
            res = run_benchmark_batch(sc, c)
            all_results.append(res)
            time.sleep(1.5)  # Thermal recovery

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scenario", "concurrency", "tps", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms",
            "avg_cpu_pct", "peak_cpu_pct", "ram_mb", "avg_migration_ms", "success_rate_pct", "duration_sec"
        ])
        writer.writeheader()
        writer.writerows(all_results)

    print("\n" + "="*75)
    print(f"  BENCHMARK COMPLETE. Saved to {OUTPUT_CSV}")
    print("="*75)

if __name__ == "__main__":
    main()
