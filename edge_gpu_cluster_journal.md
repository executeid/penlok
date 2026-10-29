# Multi-Agent Edge-Cloud & GPU Orchestration Journal

**Date**: 27 September 2026  
**System**: Penlok Smart Locker Multi-Agent System (MAS)  
**Targets**:
- **Device Edge**: `pi@10.1.1.224:2523` (via jump host `tcc@100.76.68.93`)
- **Edge Brain / Cluster Host**: `penlok@10.1.1.57` (`100.75.230.102` on Tailscale)
- **Cloud GPU Machine**: `penlok@100.76.68.93` (`pengmas-tri` on Tailscale)

---

## 1. Intended Architecture & Planning (The Blueprint)

As defined in project documents (`Penlok 2026.pdf`, progress reports, and architecture plans):

```
+----------------------------------------------------------------------------------------------------+
|                                    MULTI-AGENT SYSTEM (MAS)                                        |
|                                                                                                    |
|  +--------------------------------+   +--------------------------------+   +--------------------+  |
|  |     DEVICE EDGE (Raspi 1)      |   |      EDGE BRAIN (Raspi 2)      |   |   CLOUD GPU (PC)   |  |
|  |        (10.1.1.224)            |   |          (10.1.1.57)           |   |   (100.76.68.93)   |  |
|  |--------------------------------|   |--------------------------------|   |--------------------|  |
|  | • Hardware Actuation (Relays)  |   | • K3s Single-Node Cluster      |   | • RTX 3050 6GB     |  |
|  | • Sensors (Loadcell, IR, Ultra)|   | • Edge Agent (Telemetry CSV)   |   | • Cloud Agent K3s  |  |
|  | • Keypad Matrix & I2C LCD      |   | • Scheduler Agent (XGBoost)    |   | • High-Throughput  |  |
|  | • Camera Video Capture (Webcam)|   | • Mosquitto MQTT Broker        |   |   Face Matcher     |  |
|  | • Local Django Backend (:8000) |   | • Prometheus (:9090) & Grafana |   | • PostgreSQL DB    |  |
|  | • Node-Exporter (:31100)       |   | • Migration Agent (Forwarder)  |   |   (Sync/Backup)    |  |
|  +--------------------------------+   +--------------------------------+   +--------------------+  |
+----------------------------------------------------------------------------------------------------+
```

### Planned Agent Roles
1. **Edge Agent (Device & Telemetry)**:
   - Reads system hardware state (`cpu_usage`, `ram_usage`, `disk_io`, `network_bandwidth`).
   - Publishes metrics to MQTT topic `smartbox/telemetry` every 2–3s.
   - Operates physical relays upon receipt of unlock events.
2. **Scheduler Agent (AI Offload Gate)**:
   - Evaluates real-time state vector: `[CPU, RAM, Throughput, Network_Bandwidth, Priority, Latency, Queue]`.
   - Uses machine learning classifier (`XGBoost`) to predict execution target:
     - `1 = TETAP DI EDGE` (Execute lightweight verification locally).
     - `0 = MIGRASI KE CLOUD` (Offload compute-heavy vision tasks to GPU).
3. **Migration Agent (Data Forwarder)**:
   - Activates when Scheduler outputs `0`.
   - Packages image payloads and dispatches HTTP POST over Tailscale to Cloud Agent.
4. **Cloud Agent (GPU Inference Engine)**:
   - Runs on physical PC with dedicated GPU (RTX 3050).
   - Ingests incoming images, runs tensor forward pass, compares embeddings against user database, returns `{authorized: bool, user_id: int, latency_ms: float}`.

---

## 2. Current Condition & Technical Audit (As-Is)

### 2.1 Device Edge (`10.1.1.224:2523`)
- **Status**: Operational, fully patched for Linux 6.12+ (RP1 chip `gpiochip15`).
- **Hardware Loop**: `pan-piXarduino-fixed.py` handles LCD, Keypad, HC-SR04, Loadcell, Relays.
- **Backend**: Docker Compose running Django DRF (`0.0.0.0:8000`), PostgreSQL 15 (`0.0.0.0:1723`), Redis 7, Celery.
- **Monitoring**: `node-exporter` running on port `31100`, successfully scraped by Raspi 2.
- **Isolation Issue**: Local Mosquitto broker (`localhost:1883`) communicates only within Raspi 1. No active link pushes physical locker sensor state to Raspi 2.

### 2.2 Edge Brain (`10.1.1.57`)
- **K3s Cluster**: Version `v1.36.2+k3s1` on Debian 13 (Linux 6.18 arm64). Single-node `edge-penlok`. Passwordless `kubectl` configured.
- **Active Pods**:
  - `edge-agent-79cf96b45c-9xdlw`: Up 46+ hours. Generating telemetry and dumping to PVC `edge-agent-data-pvc` (`dataset_smartbox.csv` has **55,570+ rows**).
  - `mqtt-broker-6544d5bfc4-j8lw2`: Mosquitto running as `ClusterIP: 10.43.17.173:1883` (isolated inside cluster).
  - `prometheus-7f5888b4c-rldfn`: Scraping `node-exporter:9100` (Raspi 2) and `10.1.1.224:31100` (Raspi 1) every 15s. All targets UP.
  - `grafana-86dbbdf645-wws5m`: Exposed on `NodePort: 30000`.
- **Scheduler Model**: `scheduler_agent_xgb.pkl` present on host (`/home/penlok`).
  - Input: 7 features `['CPU', 'RAM', 'Throughput', 'Network_Bandwidth', 'Priority', 'Latency', 'Queue']`.
  - Target labels: `0` (Cloud) vs `1` (Edge).
  - Current inference script `live_test.py` runs manually as CLI script, not yet integrated into K3s request pipeline.
- **Synthetic Gap**: Telemetry labels in `dataset_smartbox.csv` were generated via rule-based threshold (`cpu > 65%` or `exec > 3.5s` or `cpu > 45% & prio=3`) driven by JMeter hitting math dummy `dummy_api.py` (calculating $\sqrt{x}$ loops).

### 2.3 Cloud GPU Machine (`100.76.68.93`)
- **Hardware**: Ubuntu 24.04 LTS x86_64, NVIDIA GeForce RTX 3050 6GB (Driver 595.84, CUDA 13.2). Current GPU usage 0%, 55MB VRAM used (idle).
- **Cluster**: K3s installed, currently running legacy microservices (SmartPJU, Ollama, pgAdmin).
- **Cloud Agent Prototype**:
  - Code present at `/home/penlok/app/app.py`.
  - Accepts dummy string payload (`MigrationRequest(device_id, data)`), returns mock timestamp and elapsed milliseconds.
  - Not currently running as persistent systemd or K3s deployment.
  - No OpenCV, PyTorch, or CUDA face model integrated yet.

---

## 3. Next Steps Execution Plan

### Step 1: Network & Broker Interconnection
1. **Bridge MQTT Brokers**:
   - Configure Mosquitto bridge between Raspi 1 (`10.1.1.224:1883`) and Raspi 2 (`10.1.1.57:1883`).
   - Change K3s `mqtt-broker` service from `ClusterIP` to `NodePort: 31883` (or hostPort).
   - Forward topics `smartbox/#` and `penlok/command` bidirectionally.

### Step 2: Implement Real GPU Vision Service on `100.76.68.93`
1. **Create Containerized Face Service**:
   - Replace dummy FastAPI with PyTorch/ONNX Runtime CUDA service:
     `POST /api/v1/face/verify` (accepts multipart/form-data JPEG frame + optional user_id).
   - Model options: MobileFaceNet (1.5ms on RTX 3050) or ArcFace ResNet50 (4ms on RTX 3050).
   - Load registered owner face embeddings from SQLite/PostgreSQL into GPU memory at startup.
2. **Deploy as K3s Deployment**:
   - Set up `cloud-face-agent` deployment with NVIDIA runtime (`runtimeClassName: nvidia` or GPU pass-through).
   - Expose via `NodePort: 30900`.

### Step 3: Integrate Scheduler & Migration Agent into the Pipeline
1. **Connect `live_test.py` logic to live event queue**:
   - When Raspi 1 captures face image, it queries Scheduler Agent on Raspi 2:
     - Edge sends current local metrics: `{cpu, ram, latency, priority=3, queue}`.
     - Scheduler runs `model.predict(X)`.
   - If `1` (Edge): Raspi 1 runs local OpenCV LBPH matcher.
   - If `0` (Cloud): Migration Agent streams JPEG bytes over Tailscale to `http://100.76.68.93:30900/api/v1/face/verify`.
2. **Actuation Callback**:
   - Cloud returns `{authorized: true, user_id: 13}`.
   - Result published to `penlok/command` $\rightarrow$ Raspi 1 fires Relay 2 (BCM GPIO 9) to unlock Locker 2.

### Step 4: Trace-Driven Realistic Stress Testing (Replace JMeter)
1. **Develop `locker_workload_generator.py`**:
   - Runs asynchronous worker pool simulating 1 to 20 concurrent smart locker terminals.
   - Sends real images from `Datawajahnew` dataset over network instead of synthetic math loops.
2. **Stress Profiles**:
   - Profile 1: Low-load baseline (1 request every 10s) $\rightarrow$ Expected 100% Edge execution.
   - Profile 2: Courier burst (5 concurrent QR scans + 3 face authentications) $\rightarrow$ Scheduler starts offloading face tasks to GPU.
   - Profile 3: Spike overload (15 concurrent face auth requests) $\rightarrow$ 100% Vision tasks offloaded to GPU; Raspi 1 CPU stays below 50%; total unlock latency remains $< 150\text{ms}$.

---

## 4. Do's and Don'ts Recommendations

### DO
1. **DO use binary image streaming with standard MIME types (`multipart/form-data`)**:
   - Stream raw JPEG bytes. Do not convert images to Base64 in JSON; Base64 adds ~33% network and serialization overhead, causing latency spikes on edge CPUs.
2. **DO implement fail-open/fallback to local PIN on network partition**:
   - If Tailscale latency to GPU $> 500\text{ms}$ or timeout occurs, hardware loop must automatically fall back to Keypad OTP/PIN without blocking physical relays.
3. **DO cache embeddings in GPU VRAM**:
   - Precompute 512-d feature vectors of all registered owners and keep them on CUDA memory (`[N, 512]` matrix). Matrix multiplication `torch.mm` takes $< 0.1\text{ms}` for thousands of users.
4. **DO monitor end-to-end P95 and P99 latency**:
   - Add Prometheus counters: `request_duration_seconds{step="capture"}`, `{step="schedule"}`, `{step="network_transfer"}`, `{step="gpu_inference"}`.
5. **DO set container resource limits in K3s**:
   - Always specify `resources.limits` and `resources.requests` for CPU and Memory in all manifests to prevent K3s from starving node OS processes.

### DON'T
1. **DON'T use synthetic CPU burners (e.g. `dummy_api.py` sqrt loops) for final research evaluation**:
   - CPU math loops do not stress memory bandwidth, PCIe bus, or network sockets like real image decoding (`cv2.imdecode`) and tensor transfers do. Reviewers will reject synthetic results.
2. **DON'T block the hardware polling thread**:
   - Never call synchronous HTTP requests (`requests.post()`) inside `read_key()` or sensor scanning loops. Always dispatch network calls in separate worker threads or async queues.
3. **DON'T expose unauthenticated MQTT brokers to public interfaces**:
   - Keep Mosquitto accessible only within local subnet (`10.1.1.0/24`) and Tailscale mesh (`100.x.x.x`). Do not open port 1883 to the public internet.
4. **DON'T retrain XGBoost without feature normalization and stratified cross-validation**:
   - Telemetry dataset contains imbalanced classes (idle vs burst). Always balance dataset using SMOTE or stratified sampling before compiling `scheduler_agent_xgb.pkl` to prevent model overfitting.
5. **DON'T hardcode GPIO chip numbers**:
   - Never write `lgpio.gpiochip_open(0)` in application code. Use dynamic detection probing `[15, 4, 0]` to ensure cross-compatibility between Raspberry Pi 4 (BCM2711) and Pi 5 (RP1).
