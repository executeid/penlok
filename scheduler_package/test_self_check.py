import json
import urllib.request
from main import evaluate_rule_based, DecisionEngine

# --- Part 1: Local Unit Checks ---
t1 = {"CPU": 25.0, "RAM": 1200.0, "Throughput": 0.5, "Network_Bandwidth": 1.2, "Priority": 2, "Latency": 25.0, "Queue": 1, "RAM_pct": 35.0}
assert evaluate_rule_based(t1) == 0, f"Expected 0, got {evaluate_rule_based(t1)}"

t2 = {"CPU": 88.5, "RAM": 3200.0, "Throughput": 4.5, "Network_Bandwidth": 0.8, "Priority": 3, "Latency": 45.0, "Queue": 5, "RAM_pct": 82.0}
assert evaluate_rule_based(t2) == 1, f"Expected 1, got {evaluate_rule_based(t2)}"

t3 = {"CPU": 70.0, "RAM": 1500.0, "Latency": 50.0, "RAM_pct": 75.0}
assert evaluate_rule_based(t3) == 1, f"Expected 1, got {evaluate_rule_based(t3)}"

t4 = {"CPU": 70.0, "RAM": 1500.0, "Latency": 160.0, "RAM_pct": 75.0}
assert evaluate_rule_based(t4) == 0, f"Expected 0, got {evaluate_rule_based(t4)}"

engine = DecisionEngine(model_filename="non_existent_model.pkl")
assert engine.model is None
p, conf, method = engine.predict(t1)
assert p == 0 and method == "rule_based"
p, conf, method = engine.predict(t2)
assert p == 1 and method == "rule_based"

# --- Part 2: Live HTTP REST API Checks ---
URL = "http://127.0.0.1:8500/api/v1/schedule"
tests = [
    ("Normal load (Edge)", t1, 0, "TETAP_DI_EDGE"),
    ("Extreme CPU (Cloud)", t2, 1, "MIGRASI_KE_CLOUD"),
    ("Composite condition (Cloud)", t3, 1, "MIGRASI_KE_CLOUD"),
    ("Composite high latency (Edge)", t4, 0, "TETAP_DI_EDGE"),
]

for name, payload, expected_dec, expected_label in tests:
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success", "Status not success"
        assert res["decision"] == expected_dec, f"Expected {expected_dec}, got {res['decision']}"
        assert res["label"] == expected_label, f"Expected {expected_label}, got {res['label']}"
        print(f"PASS HTTP: {name:<32} -> {res['decision']} ({res['label']})")

print("ALL SELF-CHECKS AND HTTP VERIFICATIONS PASSED!")
