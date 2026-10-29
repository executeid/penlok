import os
import time
import base64
import sqlite3
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from psycopg2 import pool
import requests
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
YUNET_PATH = os.getenv("YUNET_PATH", "/home/penlok/app/face_detection_yunet_2023mar.onnx")
EDGE_SYNC_URL = os.getenv("EDGE_SYNC_URL", "http://10.1.1.224:8600/api/v1/sync_user_face")
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", "/home/penlok/app/gallery_embeddings.pt")
GALLERY_PATH = os.getenv("GALLERY_PATH", "/home/penlok/app/gallery/imagetraining")

# Global Deep Learning Model & Embeddings
model: Optional[InceptionResnetV1] = None
detector = None
gallery_embeddings = {}
USER_DISPLAY_NAMES = {
    "akmal": "Akmal",
    "balbal": "Iqbal",
    "panpenlok": "Shafwan",
    "soqisoqi": "Syauqi"
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

def load_face_models():
    global model, detector, gallery_embeddings
    print(f"[MODEL] Loading InceptionResnetV1 on {DEVICE}...")
    model = InceptionResnetV1(pretrained="vggface2").eval().to(DEVICE)
    
    print(f"[DETECTOR] Loading OpenCV YuNet Face Detector from {YUNET_PATH}...")
    if os.path.exists(YUNET_PATH):
        detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320), 0.5, 0.3, 500)
    else:
        print("[WARN] YuNet model not found at", YUNET_PATH)

    emb_path = EMBEDDINGS_PATH
    if os.path.exists(emb_path):
        gallery_embeddings = torch.load(emb_path, map_location=DEVICE, weights_only=True)
        print(f"[MODEL] Loaded gallery profiles: {list(gallery_embeddings.keys())}")
    else:
        print("[WARN] Gallery embeddings not found at", emb_path)

def verify_face_on_gpu(img_bytes: bytes):
    """Deep Face Verification on RTX 3050 CUDA using YuNet Crop + InceptionResnetV1"""
    global model, detector, gallery_embeddings
    if model is None:
        load_face_models()

    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image bytes")

    # Step 1: Detect and crop face using YuNet
    face_crop = None
    if detector is not None:
        h, w, _ = img.shape
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is not None and len(faces) > 0:
            box = faces[0][:4].astype(int)
            x, y, bw, bh = box
            pad_x = int(bw * 0.1)
            pad_y = int(bh * 0.1)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w, x + bw + pad_x)
            y2 = min(h, y + bh + pad_y)
            face_crop = img[y1:y2, x1:x2]

    # If no face detected at all, reject immediately
    if face_crop is None or face_crop.size == 0:
        return "NO_FACE_DETECTED", 0.0, False

    # Step 2: Preprocess cropped face to 160x160 RGB
    img_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (160, 160))
    tensor = torch.from_numpy(img_resized).permute(2, 0, 1).float()
    tensor = (tensor - 127.5) / 128.0
    tensor = tensor.unsqueeze(0).to(DEVICE)

    # Step 3: Extract 512-d embedding and compare cosine similarity
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

    MATCH_THRESHOLD = 0.60
    is_match = (best_score >= MATCH_THRESHOLD)
    confidence = round(float(best_score), 4)
    display_user = USER_DISPLAY_NAMES.get(best_user, best_user) if is_match else "UNAUTHORIZED"

    return display_user, confidence, is_match

def warmup_gpu():
    try:
        dummy_img = np.zeros((160, 160, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dummy_img)
        verify_face_on_gpu(buf.tobytes())
        print("[WARMUP] GPU CUDA Face recognition warmed up.")
    except Exception as e:
        print("[WARMUP] Notice:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_pool()
    load_face_models()
    warmup_gpu()
    yield
    if db_pool:
        db_pool.closeall()

app = FastAPI(title="PENLOK Cloud GPU Deep Face Agent (YuNet + FaceNet)", version="3.2.0", lifespan=lifespan)

class MigrationRequest(BaseModel):
    device_id: str = "edge_device"
    task_id: str = "task_0"
    timestamp: Optional[str] = None
    image: str
    decision: Optional[int] = 1

class UserOnboardingRequest(BaseModel):
    username: str
    face_id: int
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    images: List[str]  # Base64 encoded images

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
        "detection": "OpenCV YuNet ONNX",
        "recognition": "InceptionResnetV1 (VGGFace2)",
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
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
        "profiles": len(gallery_embeddings)
    }

@app.post("/api/v1/onboard_user")
def onboard_user(req: UserOnboardingRequest):
    """
    Onboard user di Cloud dan otomatis kirim ke Edge Pi (10.1.1.224:8600)
    """
    global gallery_embeddings
    t0 = time.time()
    user_key = req.username.strip().lower().replace(" ", "_")
    user_gallery_dir = os.path.join(GALLERY_PATH, user_key)
    os.makedirs(user_gallery_dir, exist_ok=True)

    saved_tensors = []
    for idx, b64_img in enumerate(req.images):
        try:
            if "," in b64_img:
                b64_img = b64_img.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_img)
            nparr = np.frombuffer(raw_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                fname = f"{user_key}_{int(time.time())}_{idx+1}.jpg"
                cv2.imwrite(os.path.join(user_gallery_dir, fname), img)

                h, w, _ = img.shape
                detector.setInputSize((w, h))
                _, faces = detector.detect(img)
                crop = img
                if faces is not None and len(faces) > 0:
                    bx, by, bw, bh = faces[0][:4].astype(int)
                    px, py = int(bw * 0.1), int(bh * 0.1)
                    crop = img[max(0, by-py):min(h, by+bh+py), max(0, bx-px):min(w, bx+bw+px)]

                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(rgb, (160, 160))
                t = torch.from_numpy(resized).permute(2, 0, 1).float()
                t = (t - 127.5) / 128.0
                t = t.unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    emb = model(t)
                    emb = F.normalize(emb, p=2, dim=1)
                    saved_tensors.append(emb)
        except Exception as e:
            print(f"[-] Onboarding error #{idx}:", e)

    if saved_tensors:
        mean_emb = torch.cat(saved_tensors, dim=0).mean(dim=0, keepdim=True)
        mean_emb = F.normalize(mean_emb, p=2, dim=1)
        gallery_embeddings[user_key] = mean_emb
        torch.save(gallery_embeddings, EMBEDDINGS_PATH)
        USER_DISPLAY_NAMES[user_key] = req.first_name or user_key.capitalize()

    edge_sync_status = "failed"
    try:
        r_sync = requests.post(EDGE_SYNC_URL, json=req.dict(), timeout=10.0)
        if r_sync.status_code == 200:
            edge_sync_status = "synced"
    except Exception as e:
        edge_sync_status = str(e)

    return {
        "status": "success",
        "username": user_key,
        "face_id": req.face_id,
        "cloud_embeddings_saved": len(saved_tensors),
        "edge_sync_status": edge_sync_status,
        "total_time_ms": round((time.time() - t0) * 1000, 2)
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
