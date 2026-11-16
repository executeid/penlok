import os
import time
import logging
import zoneinfo
from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field

WIB = zoneinfo.ZoneInfo("Asia/Jakarta")

def now_wib_str():
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler-agent")

def evaluate_rule_based(telemetry: dict) -> int:
    cpu = float(telemetry.get("CPU", 0.0))
    ram = float(telemetry.get("RAM", 0.0))
    ram_pct = telemetry.get("RAM_pct")
    if ram_pct is None:
        ram_pct = ram if ram <= 100.0 else (ram / 16218.0 * 100.0)
    else:
        ram_pct = float(ram_pct)
    latency = float(telemetry.get("Latency", 0.0))

    if cpu > 80.0:
        return 1
    if cpu > 65.0 and ram_pct > 70.0 and latency < 150.0:
        return 1
    return 0

class DecisionEngine:
    def __init__(self, model_filename="scheduler_agent_xgb.pkl"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.environ.get(
            "SCHEDULER_MODEL_PATH",
            os.path.join(self.base_dir, model_filename)
        )
        self.model = None
        self.model_mtime = None
        self.features = ['CPU', 'RAM', 'Throughput', 'Network_Bandwidth', 'Priority', 'Latency', 'Queue']
        self.check_model()

    def check_model(self):
        if os.path.exists(self.model_path):
            try:
                mtime = os.path.getmtime(self.model_path)
                if self.model is None or self.model_mtime != mtime:
                    import warnings
                    warnings.filterwarnings("ignore", category=UserWarning)
                    import joblib
                    self.model = joblib.load(self.model_path)
                    self.model_mtime = mtime
                    logger.info(f"Loaded XGBoost model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load XGBoost model from {self.model_path}: {e}. Fallback to rule_based.")
                self.model = None
                self.model_mtime = None
        else:
            if self.model is not None:
                logger.info(f"Model file {self.model_path} removed. Fallback to rule_based.")
                self.model = None
                self.model_mtime = None

    def predict(self, telemetry: dict):
        self.check_model()
        if self.model is not None:
            try:
                import pandas as pd
                df = pd.DataFrame([telemetry])[self.features]
                raw_pred = int(self.model.predict(df)[0])
                if os.environ.get("XGB_INVERT_TARGET", "false").lower() in ("true", "1"):
                    pred = 1 - raw_pred
                else:
                    pred = raw_pred
                if hasattr(self.model, "predict_proba"):
                    probas = self.model.predict_proba(df)[0]
                    confidence = float(probas[raw_pred])
                else:
                    confidence = 0.95
                return pred, confidence, "xgboost"
            except Exception as e:
                logger.error(f"XGBoost prediction error: {e}. Fallback to rule_based.")

        pred = evaluate_rule_based(telemetry)
        confidence = 0.95 if pred == 1 else 0.90
        return pred, confidence, "rule_based"

app = FastAPI(title="PENLOK Scheduler Agent", version="2.2.0")
engine = DecisionEngine()

class TelemetryPayload(BaseModel):
    CPU: float = Field(..., description="CPU utilization percentage (0-100)")
    RAM: float = Field(..., description="RAM usage in MB or %")
    Throughput: float = Field(0.0, description="Disk + Network throughput (MB/s)")
    Network_Bandwidth: float = Field(0.0, description="Network bandwidth (MB/s)")
    Priority: int = Field(1, description="Task priority")
    Latency: float = Field(0.0, description="Network latency in ms")
    Queue: int = Field(0, description="Queue length")
    RAM_pct: Optional[float] = Field(None, description="RAM utilization percentage (0-100)")

@app.get("/")
def root():
    return {
        "service": "PENLOK Scheduler Agent",
        "timezone": "Asia/Jakarta (WIB, UTC+7)",
        "current_time_wib": now_wib_str(),
        "version": "2.2.0",
        "status": "online"
    }

@app.get("/health")
def health():
    engine.check_model()
    ram_used_mb = 0.0
    ram_pct = 0.0
    try:
        with open("/proc/meminfo") as mf:
            lines = mf.readlines()
        mem_vals = {}
        for l in lines:
            parts = l.split(":")
            if len(parts) == 2:
                mem_vals[parts[0].strip()] = float(parts[1].replace("kB", "").strip())
        total = mem_vals.get("MemTotal", 16000000.0)
        avail = mem_vals.get("MemAvailable", total)
        used = total - avail
        ram_used_mb = round(used / 1024.0, 1)
        ram_pct = round((used / total) * 100.0, 1)
    except Exception:
        pass

    return {
        "status": "healthy",
        "timezone": "Asia/Jakarta (WIB, UTC+7)",
        "current_time_wib": now_wib_str(),
        "mode": "xgboost" if engine.model is not None else "rule_based",
        "model_loaded": engine.model is not None,
        "model_path": engine.model_path,
        "features_count": len(engine.features),
        "features": engine.features,
        "host_ram_used_mb": ram_used_mb,
        "host_ram_pct": ram_pct,
        "timestamp": time.time()
    }

@app.post("/api/v1/schedule")
def schedule_task(payload: TelemetryPayload):
    telemetry = payload.model_dump()
    decision, confidence, method = engine.predict(telemetry)
    return {
        "status": "success",
        "decision": decision,
        "label": "MIGRASI_KE_CLOUD" if decision == 1 else "TETAP_DI_EDGE",
        "confidence": confidence,
        "method": method,
        "current_time_wib": now_wib_str(),
        "timestamp": time.time()
    }

@app.post("/api/v1/reload")
def reload_model():
    engine.check_model()
    return {
        "status": "ok",
        "mode": "xgboost" if engine.model is not None else "rule_based",
        "model_loaded": engine.model is not None,
        "current_time_wib": now_wib_str()
    }
