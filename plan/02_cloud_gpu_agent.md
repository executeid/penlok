# Tahap 2: Cloud GPU Face Recognition Agent Service

**Dokumen**: `plan/02_cloud_gpu_agent.md`  
**Target Node**: `penlok@100.76.68.93` (`pengmas-tri` via Tailscale VPN)  
**Spesifikasi Hardware**:
- OS: Ubuntu 24.04 LTS x86_64
- GPU: NVIDIA GeForce RTX 3050 6GB VRAM (Driver: 595.84, CUDA: 13.2)
- Klaster K3s: Berjalan di host

---

## 1. Tujuan & Tanggung Jawab
Membangun microservice Cloud Agent (`cloud-api`) berbasis FastAPI dan PyTorch/CUDA yang bertugas:
1. Menjadi endpoint penampung tugas offload dari Edge Agent/Migration Agent via koneksi Tailscale.
2. Mengeksekusi inferensi Face Recognition berkecepatan tinggi memanfaatkan akselerasi hardware GPU ($T_{\text{proc}} < 15\text{ms}$).
3. Mencatat riwayat pemrosesan ke basis data PostgreSQL untuk audit logging.
4. Mendukung skenario penskalaan pod horizontal (Horizontal Pod Autoscaler / HPA) di Kubernetes K3s (1 pod untuk 10 req $\rightarrow$ 2 pod untuk 50 req).

---

## 2. Arsitektur Komponen Cloud Agent

```
[Request HTTP POST dari Migration Agent]
                 │
                 ▼ (Tailscale Port :9000 atau K3s NodePort :30900)
    ┌───────────────────────────────────────────────┐
    │          FastAPI Microservice                 │
    │  Endpoint: POST /api/v1/migration             │
    └───────────────────────────────────────────────┘
                 │
                 ├─ 1. Decode Base64 / Binary JPEG Frame
                 │
                 ├─ 2. Transfer Tensor ke GPU (device = 'cuda:0')
                 │
                 ├─ 3. Deep Learning Forward Pass (ArcFace / MobileFaceNet)
                 │     • Ekstraksi 512-d Embedding Vector
                 │     • Cosine Similarity Matching vs User DB di VRAM
                 │
                 ├─ 4. Hitung Waktu Proses GPU (cloud_processing_time_ms)
                 │
                 ├─ 5. Insert Log ke PostgreSQL (Tabel: cloud_task_log)
                 │
                 ▼
    [Response JSON ke Migration Agent]
    {
      "status": "success",
      "processing_node": "cloud",
      "user_id": 13,
      "confidence": 0.94,
      "cloud_processing_time_ms": 4.8
    }
```

---

## 3. Rincian Implementasi Kode

### 3.1 Skrip Service FastAPI (`/home/penlok/app/main.py`)
```python
import time
import base64
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import psycopg2

app = FastAPI(title="PENLOK Cloud GPU Agent", version="2.0.0")

# Inisialisasi Device GPU
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# Konfigurasi Koneksi Database
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password",
    "dbname": "penlok_cloud"
}

class MigrationRequest(BaseModel):
    device_id: str
    task_id: str
    timestamp: str
    image: str  # Base64 string encoded frame
    decision: int

# Simulasi database embedding user terdaftar di VRAM
# Format: [N_users, 512] normalisasi float32
REGISTERED_EMBEDDINGS = torch.randn(10, 512, device=DEVICE)
REGISTERED_EMBEDDINGS = F.normalize(REGISTERED_EMBEDDINGS, p=2, dim=1)
USER_MAP = {i: f"USER_{100 + i}" for i in range(10)}

def verify_face_on_gpu(img_bytes: bytes):
    """Proses gambar menggunakan CUDA Tensor"""
    # 1. Decode byte ke array OpenCV
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image bytes")

    # 2. Preprocessing & transform ke CUDA Tensor [1, 3, 112, 112]
    img_resized = cv2.resize(img, (112, 112))
    tensor = torch.from_numpy(img_resized).permute(2, 0, 1).float()
    tensor = (tensor - 127.5) / 128.0
    tensor = tensor.unsqueeze(0).to(DEVICE)

    # 3. Ekstraksi feature dummy / model forward pass
    # (Menggunakan representasi deterministik berbasis hash tensor untuk pengujian)
    with torch.no_grad():
        feature = torch.sin(tensor.mean(dim=[2, 3]) * 10.0).repeat(1, 512 // 3 + 1)[:, :512]
        feature = F.normalize(feature, p=2, dim=1)

        # 4. Pencocokan kemiripan kosinus
        similarities = torch.mm(feature, REGISTERED_EMBEDDINGS.T)[0]
        best_score, best_idx = torch.max(similarities, dim=0)

    score = float(best_score.cpu().item())
    idx = int(best_idx.cpu().item())
    is_match = score > 0.40
    user_id = USER_MAP.get(idx, "UNKNOWN") if is_match else "UNKNOWN"
    return user_id, round(score, 4), is_match

@app.post("/api/v1/migration")
@app.post("/migration")
def process_migration(req: MigrationRequest):
    t_start = time.time()
    try:
        img_bytes = base64.b64decode(req.image)
        user_id, confidence, is_match = verify_face_on_gpu(img_bytes)
        status_str = "success" if is_match else "unauthorized"
    except Exception as e:
        status_str = "error"
        user_id = None
        confidence = 0.0

    t_proc = round((time.time() - t_start) * 1000, 2)

    # Logging ke DB
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cloud_task_log (task_id, device_id, timestamp, processing_time_ms, status, user_id, confidence) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s);",
            (req.task_id, req.device_id, datetime.now(), t_proc, status_str, user_id, confidence)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return {
        "status": status_str,
        "processing_node": "cloud",
        "user_id": user_id,
        "confidence": confidence,
        "cloud_processing_time_ms": t_proc
    }
```

---

## 4. Skema Database PostgreSQL (`cloud_task_log`)

```sql
CREATE DATABASE penlok_cloud;

\c penlok_cloud;

CREATE TABLE cloud_task_log (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms NUMERIC(8, 2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    user_id VARCHAR(64),
    confidence NUMERIC(6, 4)
);

CREATE INDEX idx_task_id ON cloud_task_log(task_id);
```

---

## 5. Deployment di Kubernetes K3s & HPA Autoscaling

### 5.1 Dockerfile (`/home/penlok/app/Dockerfile`)
```dockerfile
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
```

### 5.2 Manifes Deployment & Service (`cloud-api.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-api
  namespace: cloud-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloud-api
  template:
    metadata:
      labels:
        app: cloud-api
    spec:
      containers:
        - name: cloud-api
          image: cloud-api:latest
          imagePullPolicy: IfNotPresent
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2000m"
              memory: "4Gi"
          ports:
            - containerPort: 9000
---
apiVersion: v1
kind: Service
metadata:
  name: cloud-api-svc
  namespace: cloud-agent
spec:
  type: NodePort
  selector:
    app: cloud-api
  ports:
    - port: 9000
      targetPort: 9000
      nodePort: 30900
```

### 5.3 Manifes Horizontal Pod Autoscaler (`cloud-api-hpa.yaml`)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cloud-api-hpa
  namespace: cloud-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cloud-api
  minReplicas: 1
  maxReplicas: 3
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```
*Catatan Uji HPA*: Menjalankan 10 request simultan menjaga pod tetap 1. Lonjakan 50 request konkuren memicu HPA menaikkan replika menjadi 2 pod.

---

## 6. Kriteria Keberhasilan (Acceptance Criteria)
1. Endpoint `curl -X POST http://100.76.68.93:9000/api/v1/migration` merespon dengan `status: success`.
2. Model PyTorch berjalan di GPU NVIDIA RTX 3050 (`nvidia-smi` menunjukkan alokasi memori proses python).
3. Metrik `cloud_processing_time_ms` berada di bawah 15ms.
4. Record pengujian tersimpan rapi di tabel PostgreSQL `cloud_task_log`.
5. HPA berhasil melakukan scaling pod di klaster K3s Cloud.
