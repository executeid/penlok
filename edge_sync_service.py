#!/usr/bin/env python3
"""
PENLOK Edge Face Sync & IoT Data Gateway Service
Runs on: pi@10.1.1.224 (Port 8600)
Provides:
- POST /api/v1/sync_user_face
- GET /api/sensor
- GET /api/packages
- POST /api/packages
- DELETE /api/packages/{pkg_id}
- GET /api/telemetry
"""

import os
import sys
import time
import base64
import glob
from typing import List, Optional
import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import psycopg2
import psutil

app = FastAPI(title="PENLOK Edge Sync & IoT Data Gateway", version="2.1.0")

TRAIN_DIR = "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining"
HAAR_LOC = "/home/pi/penlock/software/Django-Backend-Project/apps/hasiltraining/haarcascade_frontalface_default.xml"
LBPH_SAVE = "/home/pi/penlock/software/Django-Backend-Project/apps/hasiltraining/lbph_model.xml"
LBPH_GABUNGAN = "/home/pi/penlock/pyenv3.9code/nonsudo/lbph_model.xml"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 1723)),
    "user": os.getenv("DB_USER", "smartlocker_admin"),
    "password": os.getenv("DB_PASSWORD", "penlokjaya"),
    "dbname": os.getenv("DB_NAME", "smartlocker")
}

SHARED_SECRET = os.getenv("SYNC_SECRET", "penlok-edge-sync-2026")


class FaceSyncPayload(BaseModel):
    username: str
    face_id: int
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    images: List[str]


class PackageCreatePayload(BaseModel):
    tracking_number: str
    courier_name: str
    item_name: str
    recipient: str


def retrain_local_lbph():
    face_cascade = cv2.CascadeClassifier(HAAR_LOC)
    recognizer = cv2.face.LBPHFaceRecognizer.create()

    folder_to_faceid = {}
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT username, face_id FROM users_user WHERE role = 'OWNER' AND face_id IS NOT NULL;")
        for u, f_id in cur.fetchall():
            if f_id and str(f_id).isdigit():
                folder_to_faceid[u] = int(f_id)
        conn.close()
    except Exception as e:
        print("[-] DB query error in retrain:", e)

    defaults = {"akmal": 789123, "balbal": 451699, "panpenlok": 249731, "soqisoqi": 619292}
    for k, v in defaults.items():
        if k not in folder_to_faceid:
            folder_to_faceid[k] = v

    faces = []
    labels = []

    user_dirs = [d for d in os.listdir(TRAIN_DIR) if os.path.isdir(os.path.join(TRAIN_DIR, d))]
    for folder in user_dirs:
        face_id = folder_to_faceid.get(folder)
        if not face_id:
            continue

        u_path = os.path.join(TRAIN_DIR, folder)
        imgs = glob.glob(os.path.join(u_path, "*.[jJ][pP][gG]")) + \
               glob.glob(os.path.join(u_path, "*.[pP][nN][gG]"))

        for p in imgs:
            try:
                img_pil = Image.open(p).convert("L")
                img_np = np.array(img_pil, "uint8")
                detected = face_cascade.detectMultiScale(img_np, 1.2, 5)
                if len(detected) > 0:
                    for (x, y, w, h) in detected:
                        faces.append(img_np[y:y+h, x:x+w])
                        labels.append(face_id)
                else:
                    faces.append(cv2.resize(img_np, (120, 120)))
                    labels.append(face_id)
            except Exception:
                continue

    if faces:
        recognizer.train(faces, np.array(labels))
        recognizer.save(LBPH_SAVE)
        import shutil
        shutil.copy(LBPH_SAVE, LBPH_GABUNGAN)
        print(f"[EDGE SYNC] Model LBPH updated with {len(faces)} faces.")
        return True
    return False


@app.get("/health")
def health():
    return {"status": "ok", "node": "device_edge_10.1.1.224"}


@app.get("/api/v1/sensors")
@app.get("/api/sensor")
def get_live_sensors():
    dist = 14.2
    try:
        import lgpio
        for cand in (15, 4, 0):
            try:
                h = lgpio.gpiochip_open(cand)
                break
            except Exception:
                pass
        lgpio.gpio_claim_output(h, 15, 0)
        lgpio.gpio_claim_input(h, 17)
        lgpio.gpio_write(h, 15, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(h, 15, 0)
        t0 = time.time()
        while lgpio.gpio_read(h, 17) == 0 and time.time() - t0 < 0.05:
            pass
        start = time.time()
        while lgpio.gpio_read(h, 17) == 1 and time.time() - start < 0.05:
            pass
        end = time.time()
        lgpio.gpiochip_close(h)
        measured = round(((end - start) * 34300) / 2, 1)
        if 2.0 <= measured <= 400.0:
            dist = measured
    except Exception:
        pass
    return {
        "distance_cm": dist,
        "status": "PAKET TERDETEKSI (LOKER 1)" if dist <= 23.0 else "KOMPARTEMEN KOSONG",
        "threshold_cm": 23.0,
        "node": "edge_pi5"
    }


@app.get("/api/v1/packages")
@app.get("/api/packages")
def get_packages():
    pkgs = []
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tracking_number, courier, status, created_at, locker_slot, package_name
            FROM package_center_packageentry
            ORDER BY id DESC LIMIT 50;
        """)
        for row in cur.fetchall():
            num = str(row[1]) if row[1] else ""
            last5 = num[-5:] if len(num) >= 5 else num
            pkgs.append({
                "id": f"pkg_{row[0]}",
                "trackingNumber": num,
                "courierName": row[2] or "Ekspedisi",
                "itemName": row[6] or f"Paket #{row[0]}",
                "status": "DITERIMA_LOKER_1" if row[3] == "DELIVERED" else "DALAM_PERJALANAN",
                "dateAdded": str(row[4])[:16] if row[4] else "-",
                "last5Digits": last5,
                "recipient": "akmal",
                "lockerId": int(row[5]) if row[5] and str(row[5]).isdigit() else 1
            })
        conn.close()
    except Exception as e:
        print("[-] DB Packages query error:", e)
    return pkgs


@app.post("/api/v1/packages")
@app.post("/api/packages")
def create_package(p: PackageCreatePayload):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users_user WHERE username = %s LIMIT 1;", (p.recipient,))
        u = cur.fetchone()
        user_id = u[0] if u else 10
        cur.execute("""
            INSERT INTO package_center_packageentry (
                tracking_number, courier, package_name, status, created_at, updated_at, locker_slot, owner_id, receiver_name
            ) VALUES (%s, %s, %s, 'REGISTERED', NOW(), NOW(), '1', %s, %s)
            RETURNING id;
        """, (p.tracking_number, p.courier_name, p.item_name, user_id, p.recipient))
        new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return {"status": "success", "id": new_id, "pin": p.tracking_number[-5:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/packages/{pkg_id}")
@app.delete("/api/packages/{pkg_id}")
def delete_package(pkg_id: str):
    try:
        db_id = int(pkg_id.replace("pkg_", ""))
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM package_center_packageentry WHERE id = %s;", (db_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "deleted_id": db_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/telemetry")
@app.get("/api/telemetry")
def get_edge_telemetry():
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory()
    return {
        "cpu_usage": round(cpu, 1),
        "ram_mb": round(mem.used / (1024 * 1024), 1),
        "ram_pct": round(mem.percent, 1),
        "node": "edge_pi5",
        "timestamp": time.time()
    }


@app.post("/api/v1/sync_user_face")
def sync_user_face(payload: FaceSyncPayload, authorization: Optional[str] = Header(None)):
    t0 = time.time()
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        if token != SHARED_SECRET:
            raise HTTPException(status_code=401, detail="Invalid sync secret token")

    username = payload.username.strip().lower().replace(" ", "_")
    face_id = payload.face_id
    user_dir = os.path.join(TRAIN_DIR, username)
    os.makedirs(user_dir, exist_ok=True)

    saved_count = 0
    for idx, b64_img in enumerate(payload.images):
        try:
            if "," in b64_img:
                b64_img = b64_img.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_img)
            nparr = np.frombuffer(raw_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                fname = f"{username}_sync_{int(time.time())}_{idx+1}.jpg"
                fpath = os.path.join(user_dir, fname)
                cv2.imwrite(fpath, img)
                saved_count += 1
        except Exception as e:
            print(f"[-] Error decoding image #{idx}: {e}")

    db_updated = False
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users_user WHERE username = %s;", (username,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE users_user SET face_id = %s, role = 'OWNER', is_active = true WHERE username = %s;",
                (str(face_id), username)
            )
        else:
            cur.execute("""
                INSERT INTO users_user (
                    password, is_superuser, username, first_name, last_name, email,
                    is_staff, is_active, date_joined, role, face_id
                ) VALUES (
                    %s, false, %s, %s, %s, %s,
                    false, true, NOW(), 'OWNER', %s
                );
            """, ("pbkdf2_synced", username, payload.first_name or username.capitalize(),
                  payload.last_name or "Owner", f"{username}@penlok.id", str(face_id)))
        conn.commit()
        conn.close()
        db_updated = True
    except Exception as e:
        print("[-] DB Sync Error:", e)

    model_updated = retrain_local_lbph()
    elapsed_ms = round((time.time() - t0) * 1000, 2)

    return {
        "status": "success",
        "username": username,
        "face_id": face_id,
        "images_saved": saved_count,
        "database_updated": db_updated,
        "lbph_model_updated": model_updated,
        "sync_time_ms": elapsed_ms
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
