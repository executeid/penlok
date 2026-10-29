import os
import time
import base64
import sqlite3
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from psycopg2 import pool
from facenet_pytorch import InceptionResnetV1

# Device GPU (RTX 3050 cuda:0)
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# Konfigurasi Database PostgreSQL
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "dbname": os.getenv("DB_NAME", "penlok_cloud")
}
SQLITE_PATH = os.getenv("SQLITE_FALLBACK_PATH", "/home/penlok/app/cloud_task_log.db")

# Global Deep Learning Model & Embeddings
model: Optional[InceptionResnetV1] = None
gallery_embeddings = {}
USER_DISPLAY_NAMES = {
    "balbal": "Iqbal (Owner)",
    "panpenlok": "Shafwan (Owner)",
    "soqisoqi": "Syauqi (Owner)"
}

db_pool: Optional[pool.SimpleConnectionPool] = None

def init_db_pool():
    global db_pool
    try:
        db_pool = pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
        conn = db_pool.getconn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cloud_task_log (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(64) NOT NULL,
                        device_id VARCHAR(32) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processing_time_ms NUMERIC(8, 2) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        user_id VARCHAR(64),
                        confidence NUMERIC(6, 4)
                    );
                    CREATE INDEX IF NOT EXISTS idx_task_id ON cloud_task_log(task_id);
                """)
        db_pool.putconn(conn)
    except Exception as e:
        db_pool = None

def load_face_model():
    global model, gallery_embeddings
    print(f"[MODEL] Loading InceptionResnetV1 on {DEVICE}...")
    model = InceptionResnetV1(pretrained="vggface2").eval().to(DEVICE)
    
    emb_path = "/home/penlok/app/gallery_embeddings.pt"
    if os.path.exists(emb_path):
        gallery_embeddings = torch.load(emb_path, map_location=DEVICE)
        print(f"[MODEL] Loaded gallery profiles: {list(gallery_embeddings.keys())}")
    else:
        print("[WARN] Gallery embeddings not found at", emb_path)

def verify_face_on_gpu(img_bytes: bytes):
    """Deep Face Verification on RTX 3050 CUDA using InceptionResnetV1"""
    global model, gallery_embeddings
    if model is None:
        load_face_model()

    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image bytes")

    # Resize to standard FaceNet input (160x160 RGB)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (160, 160))
    tensor = torch.from_numpy(img_resized).permute(2, 0, 1).float()
    tensor = (tensor - 127.5) / 128.0
    tensor = tensor.unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        probe_emb = model(tensor)
        probe_emb = F.normalize(probe_emb, p=2, dim=1)

        best_score = -1.0
        best_user = "UNKNOWN"

        for user_key, ref_emb in gallery_embeddings.items():
            sim = torch.mm(probe_emb, ref_emb.T).item()
            if sim > best_score:
                best_score = sim
                best_user = user_key

        if DEVICE.type == "cuda":
            torch.cuda.synchronize()

    # Threshold: >= 0.70 is verified owner
    MATCH_THRESHOLD = 0.70
    is_match = (best_score >= MATCH_THRESHOLD)
    confidence = round(float(best_score), 4)
    display_user = USER_DISPLAY_NAMES.get(best_user, best_user) if is_match else "UNKNOWN"

    return display_user, confidence, is_match

def warmup_gpu():
    try:
        dummy_img = np.zeros((160, 160, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dummy_img)
        verify_face_on_gpu(buf.tobytes())
        print("[WARMUP] GPU CUDA Face recognition warmed up.")
    except Exception as e:
        print("[WARMUP] Failed:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_pool()
    load_face_model()
    warmup_gpu()
    yield
    if db_pool:
        db_pool.closeall()

app = FastAPI(title="PENLOK Cloud GPU Deep Face Agent", version="2.5.0", lifespan=lifespan)

class MigrationRequest(BaseModel):
    device_id: str = "edge_device"
    task_id: str = "task_0"
    timestamp: Optional[str] = None
    image: str
    decision: Optional[int] = 1

def log_task(task_id: str, device_id: str, proc_time: float, status: str, user_id: Optional[str], confidence: float):
    logged = False
    if db_pool:
        conn = None
        try:
            conn = db_pool.getconn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO cloud_task_log (task_id, device_id, timestamp, processing_time_ms, status, user_id, confidence) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s);",
                        (task_id, device_id, datetime.now(), proc_time, status, user_id, confidence)
                    )
            db_pool.putconn(conn)
            logged = True
            return "postgres"
        except Exception:
            if conn:
                try: db_pool.putconn(conn)
                except: pass

    if not logged:
        try:
            conn = sqlite3.connect(SQLITE_PATH, timeout=5)
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cloud_task_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        processing_time_ms REAL NOT NULL,
                        status TEXT NOT NULL,
                        user_id TEXT,
                        confidence REAL
                    )
                """)
                cur.execute(
                    "INSERT INTO cloud_task_log (task_id, device_id, timestamp, processing_time_ms, status, user_id, confidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (task_id, device_id, datetime.now().isoformat(), proc_time, status, user_id, confidence)
                )
            conn.close()
            return "sqlite"
        except Exception:
            return "failed"

@app.get("/")
def root():
    return {
        "service": "PENLOK Cloud GPU Deep Face Agent",
        "model": "InceptionResnetV1 (VGGFace2)",
        "device": str(DEVICE),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
        "registered_profiles": list(gallery_embeddings.keys()),
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "device": str(DEVICE),
        "profiles": len(gallery_embeddings)
    }

@app.post("/api/v1/migration")
@app.post("/migration")
def process_migration(req: MigrationRequest):
    t_start = time.perf_counter()
    try:
        img_str = req.image
        if "," in img_str:
            img_str = img_str.split(",", 1)[1]
        img_bytes = base64.b64decode(img_str)
        user_id, confidence, is_match = verify_face_on_gpu(img_bytes)
        status_str = "success" if is_match else "unauthorized"
    except Exception as e:
        status_str = "error"
        user_id = None
        confidence = 0.0

    t_proc = round((time.perf_counter() - t_start) * 1000, 2)
    log_task(req.task_id, req.device_id, t_proc, status_str, user_id, confidence)

    return {
        "status": status_str,
        "processing_node": "cloud",
        "user_id": user_id,
        "confidence": confidence,
        "cloud_processing_time_ms": t_proc
    }
