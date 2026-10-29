# Tahap 3: Scheduler Agent Service (Rule-Based Baseline & Slot XGBoost Ready)

**Dokumen**: `plan/03_scheduler_agent.md`  
**Target Node**: `penlok@10.1.1.57` (Raspberry Pi 5 16GB, Edge Brain)  
**Tujuan Utama**: Menyediakan REST API microservice yang bertugas mengambil keputusan offloading task (`0 = Edge`, `1 = Cloud`). Sesuai arahan, menggunakan **Rule-Based Baseline** terlebih dahulu sambil menyediakan slot modular untuk memasang model **XGBoost** jika pelatihan tim lain telah selesai.

---

## 1. Spesifikasi Standar Keputusan (`Dokumentasi.pdf`)
- **`Decision = 0`**: **PROSES DI EDGE** (Komputasi ringan / sistem tidak overload, dijalankan di Raspberry Pi).
- **`Decision = 1`**: **MIGRASI KE CLOUD** (Komputasi dialihkan ke Cloud GPU PC).

---

## 2. Logika Aturan (Rule-Based Baseline Engine)
Sesuai standar pengujian komparasi pada `Dokumentasi.pdf`:

```python
def evaluate_rule_based(telemetry: dict) -> int:
    cpu = telemetry.get("CPU", 0.0)
    ram = telemetry.get("RAM", 0.0)      # % penggunaan atau nilai MB
    ram_pct = telemetry.get("RAM_pct", 50.0)
    latency = telemetry.get("Latency", 0.0) # ms

    # Aturan 1: Lonjakan beban CPU ekstrem
    if cpu > 80.0:
        return 1  # Migrasi ke Cloud

    # Aturan 2: Kondisi komposit (CPU tinggi + RAM padat + Jaringan memadai)
    if cpu > 65.0 and ram_pct > 70.0 and latency < 150.0:
        return 1  # Migrasi ke Cloud

    # Default: Tetap diproses di Edge
    return 0
```

---

## 3. Arsitektur Adapter Modular (XGBoost Hot-Swap)

Ketika tim AI menyerahkan model `scheduler_agent_xgb.pkl` terbaru, sistem tidak perlu mengubah endpoint atau caller. Modul evaluator menggunakan pola Adapter:

```python
import os
import joblib
import pandas as pd

class DecisionEngine:
    def __init__(self, model_path="scheduler_agent_xgb.pkl"):
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"[SCHEDULER] Loaded XGBoost model from {self.model_path}")
            except Exception as e:
                print(f"[SCHEDULER] Failed to load XGBoost model: {e}. Fallback to Rule-Based.")
                self.model = None
        else:
            print("[SCHEDULER] Model file not found. Operating in Rule-Based Baseline mode.")

    def predict(self, telemetry: dict):
        # 1. Jika model XGBoost aktif, gunakan inferensi ML
        if self.model is not None:
            features = ['CPU', 'RAM', 'Throughput', 'Network_Bandwidth', 'Priority', 'Latency', 'Queue']
            df = pd.DataFrame([telemetry])[features]
            pred = int(self.model.predict(df)[0])
            proba = float(self.model.predict_proba(df)[0][pred])
            return pred, proba, "xgboost"

        # 2. Jika model belum ada, gunakan Rule-Based Baseline
        pred = evaluate_rule_based(telemetry)
        confidence = 0.95 if pred == 1 else 0.90
        return pred, confidence, "rule_based"
```

---

## 4. Implementasi REST API (`/home/penlok/scheduler/main.py`)

```python
from fastapi import FastAPI
from pydantic import BaseModel
import psutil
import time

app = FastAPI(title="PENLOK Scheduler Agent", version="2.0.0")
engine = DecisionEngine()

class TelemetryPayload(BaseModel):
    CPU: float
    RAM: float
    Throughput: float
    Network_Bandwidth: float
    Priority: int
    Latency: float
    Queue: int
    RAM_pct: float = 50.0

@app.get("/health")
def health():
    return {"status": "ok", "mode": "xgboost" if engine.model else "rule_based"}

@app.post("/api/v1/schedule")
def schedule_task(payload: TelemetryPayload):
    telemetry = payload.dict()
    decision, confidence, method = engine.predict(telemetry)
    return {
        "status": "success",
        "decision": decision,                     # 0 = Edge, 1 = Cloud
        "label": "MIGRASI_KE_CLOUD" if decision == 1 else "TETAP_DI_EDGE",
        "confidence": confidence,
        "method": method,
        "timestamp": time.time()
    }
```

---

## 5. Deployment di Edge Brain (`10.1.1.57`)

### 5.1 Opsi Systemd Service (Cepat & Ringan)
Berkas `/etc/systemd/system/scheduler-agent.service`:
```ini
[Unit]
Description=Penlok Scheduler Agent Microservice
After=network.target

[Service]
Type=simple
User=penlok
WorkingDirectory=/home/penlok/scheduler
ExecStart=/home/penlok/venv-test/bin/uvicorn main:app --host 0.0.0.0 --port 8500
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Perintah aktivasi:
```bash
sudo systemctl daemon-reload
sudo systemctl enable scheduler-agent
sudo systemctl start scheduler-agent
```

### 5.2 Pengujian Endpoint
```bash
# Uji Beban Normal (Harus menghasilkan Decision = 0 / Tetap di Edge)
curl -X POST http://10.1.1.57:8500/api/v1/schedule \
  -H "Content-Type: application/json" \
  -d '{"CPU": 25.0, "RAM": 1200.0, "Throughput": 0.5, "Network_Bandwidth": 1.2, "Priority": 2, "Latency": 25.0, "Queue": 1, "RAM_pct": 35.0}'

# Uji Beban Kritis (Harus menghasilkan Decision = 1 / Migrasi ke Cloud)
curl -X POST http://10.1.1.57:8500/api/v1/schedule \
  -H "Content-Type: application/json" \
  -d '{"CPU": 88.5, "RAM": 3200.0, "Throughput": 4.5, "Network_Bandwidth": 0.8, "Priority": 3, "Latency": 45.0, "Queue": 5, "RAM_pct": 82.0}'
```

---

## 6. Kriteria Keberhasilan (Acceptance Criteria)
1. Endpoint `http://10.1.1.57:8500/api/v1/schedule` merespon dalam waktu $< 10\text{ms}$.
2. Output `decision` mengembalikan integer `0` atau `1` secara akurat sesuai threshold.
3. Saat file model `scheduler_agent_xgb.pkl` ditambahkan ke direktori, sistem otomatis beralih ke mode `xgboost` tanpa mengubah struktur API.
