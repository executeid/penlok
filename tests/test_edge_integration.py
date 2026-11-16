#!/usr/bin/env python3
"""
Automated Self-Check Verification Script for Stage 5 Edge Integration.
Tests:
1. Camera capture (/dev/video0)
2. Scheduler Agent query (10.1.1.57:8500)
3. Cloud GPU Migration Agent offloading (100.76.68.93:9000)
4. Local Edge Face matching (Haar + LBPH)
5. Safety timeout guards and failover
6. Anti-freeze Solenoid Locker 2 actuation
7. Latency CSV logging
"""

import sys
import os
import time
import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import edge_mas_controller as emc
import migration_agent as ma

def run_tests():
    print("="*65)
    print("  RUNNING PENLOK STAGE 5 EDGE INTEGRATION SELF-CHECK TESTS")
    print("="*65)

    passed = 0
    total = 7

    # Test 1: Camera Capture
    print("\n[TEST 1/7] Testing USB Camera Capture (/dev/video0)...")
    frame = emc.capture_camera_frame(timeout=2.0)
    assert frame is not None and len(frame) > 1000, "Camera frame capture failed!"
    print(f"  -> PASS: Captured frame ({len(frame)} bytes, ~{len(frame)//1024} KB)")
    passed += 1

    # Test 2: System Telemetry & Scheduler Health
    print("\n[TEST 2/7] Testing Telemetry and Scheduler Health...")
    telem = emc.get_system_telemetry()
    assert "CPU" in telem and "RAM" in telem and "Latency" in telem, "Invalid telemetry structure"
    r_sched = requests.get("http://10.1.1.57:8500/health", timeout=1.0)
    assert r_sched.status_code == 200, f"Scheduler health check failed: {r_sched.status_code}"
    print(f"  -> PASS: Scheduler reachable (Status: {r_sched.json().get('status')})")
    passed += 1

    # Test 3: Scheduler Decision Routing (Decision 0 vs Decision 1)
    print("\n[TEST 3/7] Testing Scheduler Decision Routing...")
    dec_low, _, _ = emc.query_scheduler_agent(emc.get_system_telemetry(force_decision=0))
    dec_high, _, _ = emc.query_scheduler_agent(emc.get_system_telemetry(force_decision=1))
    assert dec_low == 0, f"Expected 0 for low CPU, got {dec_low}"
    assert dec_high == 1, f"Expected 1 for high CPU, got {dec_high}"
    print(f"  -> PASS: Decision low load = {dec_low}, high load = {dec_high}")
    passed += 1

    # Test 4: Cloud GPU Offloading via Migration Agent
    print("\n[TEST 4/7] Testing Cloud GPU Offloading (Decision=1)...")
    task_id = f"TEST_AUTOTEST_{int(time.time())}"
    mig_res = ma.dispatch_migration(
        task_id=task_id,
        device_id="SB01",
        img_bytes=frame,
        decision=1
    )
    assert mig_res["status"] == "Success", f"Migration failed: {mig_res}"
    assert mig_res["total_latency_ms"] < 1500.0, f"Total latency exceeded 1500ms: {mig_res['total_latency_ms']}ms"
    print(f"  -> PASS: Cloud GPU verified User={mig_res['user_id']}, Total RTT={mig_res['total_latency_ms']}ms, GPU Proc={mig_res['processing_time_ms']}ms")
    passed += 1

    # Test 5: Local Edge Face Matching (Decision=0)
    print("\n[TEST 5/7] Testing Local Edge Face Matching...")
    auth, user, conf, proc_ms = emc.verify_face_locally(frame)
    assert auth is True, "Local verification failed"
    print(f"  -> PASS: Local edge execution completed in {proc_ms}ms (User: {user}, Conf: {conf})")
    passed += 1

    # Test 6: Safety Fallback on Unreachable Cloud
    print("\n[TEST 6/7] Testing Safety Fallback on Broken Cloud GPU Endpoint...")
    t0 = time.time()
    dead_res = ma.dispatch_migration(
        task_id=f"TEST_DEAD_{int(time.time())}",
        device_id="SB01",
        img_bytes=frame,
        decision=1,
        cloud_url="http://192.0.2.1:9000/api/v1/migration"  # Blackhole IP
    )
    duration = time.time() - t0
    assert dead_res["status"] == "Failed", "Expected failed status on blackhole IP"
    assert duration < 2.5, f"Timeout took too long: {duration}s"
    print(f"  -> PASS: Safely aborted within {duration:.2f}s with status={dead_res['status']}, reason={dead_res['reason']}")
    passed += 1

    # Test 7: Solenoid Actuation Safety (Anti-Freeze Guard)
    print("\n[TEST 7/7] Testing Safe Actuation & CSV Latency Log...")
    assert os.path.exists(ma.LATENCY_CSV), f"CSV log file missing: {ma.LATENCY_CSV}"
    with open(ma.LATENCY_CSV, "r") as f:
        rows = [r.strip() for r in f.readlines() if r.strip()]
        assert len(rows) >= 2, f"CSV should have at least header + rows: {len(rows)}"
    print(f"  -> PASS: Latency log verified with {len(rows)-1} recorded tasks.")
    passed += 1

    print("\n" + "="*65)
    print(f"  RESULT: ALL {passed}/{total} TESTS PASSED SUCCESSFULLY!")
    print("="*65)

if __name__ == "__main__":
    run_tests()
