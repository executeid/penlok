"""Cloud inference API. Uses the existing YuNet/FaceNet implementation.

The K3s deployment is inference-only; enrollment continues on the existing
Docker service. Source code does not embed gallery data or credentials.
"""
import base64
import binascii
import logging
import os
import sqlite3
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import psycopg2
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

import cloud_app_main_full as engine

logger = logging.getLogger("cloud_agent")
# Run OpenCV/PyTorch on one dedicated thread. A lock across many HTTP threads
# still lets each thread retain a large native malloc arena after decoding.
INFERENCE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="face-inference")
METRICS_LOCK = threading.Lock()
COUNTS = Counter()
DURATION_SUM = 0.0
DURATION_BUCKETS = Counter()
BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
REQUIRE_GPU = os.getenv("REQUIRE_GPU", "1") == "1"
AUDIT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "3"))
SQLITE_PATH = os.getenv("SQLITE_FALLBACK_PATH", "/home/penlok/app/cloud_task_log.db")
LAST_AUDIT_BACKEND = "not_used"
DB_ERROR = None


def connect_db():
    return psycopg2.connect(**engine.DB_CONFIG, connect_timeout=AUDIT_TIMEOUT,
                            options="-c statement_timeout=3000")


def initialize_audit():
    global DB_ERROR
    conn = None
    try:
        conn = connect_db()
        with conn, conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS cloud_task_log (
                id SERIAL PRIMARY KEY, task_id VARCHAR(64) NOT NULL,
                device_id VARCHAR(32) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_time_ms NUMERIC(8,2) NOT NULL,
                status VARCHAR(32) NOT NULL, user_id VARCHAR(64),
                confidence NUMERIC(6,4))""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON cloud_task_log(task_id)")
        DB_ERROR = None
    except psycopg2.Error:
        DB_ERROR = "postgres_unavailable"
        logger.exception("PostgreSQL initialization failed; audit will try SQLite fallback")
    finally:
        if conn is not None:
            conn.close()


def database_available():
    conn = None
    try:
        conn = connect_db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
    except psycopg2.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def log_task(task_id, device_id, processing_ms, status, user_id, confidence):
    global LAST_AUDIT_BACKEND
    values = (task_id, device_id, datetime.now(timezone.utc).replace(tzinfo=None),
              processing_ms, status, user_id, confidence)
    conn = None
    try:
        conn = connect_db()
        with conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO cloud_task_log
                (task_id,device_id,timestamp,processing_time_ms,status,user_id,confidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""", values)
        LAST_AUDIT_BACKEND = "postgres"
        return "postgres"
    except psycopg2.Error:
        logger.exception("PostgreSQL audit write failed for task %s", task_id)
    finally:
        if conn is not None:
            conn.close()
    try:
        Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(SQLITE_PATH, timeout=3) as fallback:
            fallback.execute("""CREATE TABLE IF NOT EXISTS cloud_task_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                device_id TEXT NOT NULL, timestamp TEXT NOT NULL,
                processing_time_ms REAL NOT NULL, status TEXT NOT NULL,
                user_id TEXT, confidence REAL)""")
            fallback.execute("""INSERT INTO cloud_task_log
                (task_id,device_id,timestamp,processing_time_ms,status,user_id,confidence)
                VALUES (?,?,?,?,?,?,?)""", values)
        LAST_AUDIT_BACKEND = "sqlite"
        return "sqlite"
    except (sqlite3.Error, OSError):
        logger.exception("SQLite audit also failed for task %s", task_id)
        LAST_AUDIT_BACKEND = "failed"
        return "failed"


def model_ready():
    return (engine.model is not None and engine.detector is not None
            and bool(engine.gallery_embeddings)
            and (not REQUIRE_GPU or engine.DEVICE.type == "cuda"))


@asynccontextmanager
async def lifespan(app):
    engine.torch.set_num_threads(1)
    engine.cv2.setNumThreads(1)
    initialize_audit()
    engine.load_face_models()
    if not model_ready():
        raise RuntimeError("Model/detector/gallery/GPU is not ready; refusing inference startup")
    # Warm the actual recognition network; a blank image would bypass this pass.
    with engine.torch.inference_mode():
        engine.model(engine.torch.zeros((1, 3, 160, 160), device=engine.DEVICE))
        if engine.DEVICE.type == "cuda":
            engine.torch.cuda.synchronize()
    try:
        yield
    finally:
        INFERENCE_EXECUTOR.shutdown(wait=True)


app = FastAPI(title="PENLOK Cloud Agent", version="3.3.0", lifespan=lifespan)


class MigrationRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    device_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.:-]+$")
    timestamp: str | None = None
    image: str = Field(min_length=1, max_length=((MAX_IMAGE_BYTES + 2) // 3) * 4 + 128)
    decision: Literal[1] = 1


def decode_image(value):
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image") from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Empty or oversized image")
    return raw


def record_request(status, elapsed):
    global DURATION_SUM
    with METRICS_LOCK:
        COUNTS[status] += 1
        DURATION_SUM += elapsed
        for boundary in BUCKETS:
            if elapsed <= boundary:
                DURATION_BUCKETS[boundary] += 1


def infer_image(raw, started):
    queue_ms = (time.perf_counter() - started) * 1000
    compute_started = time.perf_counter()
    user_id, confidence, authorized = engine.verify_face_on_gpu(raw)
    return user_id, confidence, authorized, queue_ms, (time.perf_counter() - compute_started) * 1000


@app.get("/")
def root():
    return {"service": "PENLOK Cloud GPU Deep Face Agent", "version": app.version,
            "detection": "OpenCV YuNet ONNX", "recognition": "InceptionResnetV1 (VGGFace2)",
            "device": str(engine.DEVICE), "profiles": len(engine.gallery_embeddings),
            "inference_only": True}


@app.get("/health")
def health():
    return {"status": "healthy", "gpu_available": engine.torch.cuda.is_available(),
            "device": str(engine.DEVICE), "models_ready": model_ready(),
            "profiles": len(engine.gallery_embeddings), "version": app.version}


@app.get("/ready")
def ready(response: Response):
    models = model_ready()
    database = database_available()
    if not models or not database:
        response.status_code = 503
    return {"status": "ready" if models and database else "not_ready",
            "models_ready": models, "postgres_available": database,
            "last_audit_backend": LAST_AUDIT_BACKEND}


@app.get("/metrics")
def metrics():
    with METRICS_LOCK:
        lines = ["# TYPE cloud_agent_requests_total counter"]
        for status in ("success", "unauthorized", "error"):
            lines.append(f'cloud_agent_requests_total{{status="{status}"}} {COUNTS[status]}')
        lines += ["# TYPE cloud_agent_request_duration_seconds histogram"]
        for boundary in BUCKETS:
            lines.append(f'cloud_agent_request_duration_seconds_bucket{{le="{boundary}"}} {DURATION_BUCKETS[boundary]}')
        lines += [f'cloud_agent_request_duration_seconds_bucket{{le="+Inf"}} {sum(COUNTS.values())}',
                  f'cloud_agent_request_duration_seconds_count {sum(COUNTS.values())}',
                  f'cloud_agent_request_duration_seconds_sum {DURATION_SUM}',
                  "# TYPE cloud_agent_model_ready gauge",
                  f'cloud_agent_model_ready {int(model_ready())}']
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.post("/api/v1/migrate")
@app.post("/api/v1/migration")
@app.post("/migration")
def migration(req: MigrationRequest):
    started = time.perf_counter()
    proc_ms = 0.0
    queue_ms = 0.0
    user_id = None
    confidence = 0.0
    error = None
    code = 200
    try:
        raw = decode_image(req.image)
        if not model_ready():
            raise HTTPException(503, "Face models are not ready")
        user_id, confidence, authorized, queue_ms, proc_ms = INFERENCE_EXECUTOR.submit(
            infer_image, raw, started).result()
        status = "success" if authorized else "unauthorized"
    except ValueError as exc:
        status, code, error = "error", 400, str(exc)
    except HTTPException as exc:
        status, code, error = "error", exc.status_code, exc.detail
    except Exception:
        logger.exception("Inference failed for task %s", req.task_id)
        status, code, error = "error", 500, "Face inference failed"
    audit_backend = log_task(req.task_id, req.device_id, round(proc_ms, 2), status, user_id, confidence)
    elapsed = time.perf_counter() - started
    payload = {"task_id": req.task_id, "device_id": req.device_id, "status": status,
               "processing_node": "cloud", "authorized": status == "success",
               "user_id": user_id, "confidence": confidence,
               "cloud_processing_time_ms": round(proc_ms, 2),
               "queue_and_decode_time_ms": round(queue_ms, 2),
               "server_total_time_ms": round(elapsed * 1000, 2),
               "audit_backend": audit_backend}
    if audit_backend == "failed":
        code = 503
        payload.update(status="error", authorized=False, error="Audit persistence failed")
    if error:
        payload["error"] = error
    record_request(payload["status"], elapsed)
    from fastapi.responses import JSONResponse
    return JSONResponse(payload, status_code=code)
