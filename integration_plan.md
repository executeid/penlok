# Integrasi Smart Locker Multi-Agent System (MAS) × Cloud GPU
## Analisis, Spesifikasi Arsitektur, Protokol Uji & Rencana Implementasi

**Tanggal Diperbarui**: 27 September 2026  
**Referensi Resmi**:
1. Dokumen Blueprint: `Penlok 2026.pdf` (Multi-Agent System)
2. Dokumen Rincian Teknis & Evaluasi: `Dokumentasi.pdf`
3. Jurnal Perbaikan Hardware & Audit K3s Cluster

**Batas Waktu Pengambilan Data Evaluasi (Target)**: **7 November 2026**

---

## 1. Topologi Arsitektur 3-Tier

```
+------------------------------------------------------------------------------------------------------------------+
|                                        MULTI-AGENT SYSTEM (MAS) PENLOK 2026                                      |
|                                                                                                                  |
|  +-------------------------------+      +--------------------------------+      +-----------------------------+  |
|  |     TIER 1: DEVICE EDGE       |      |     TIER 2: EDGE BRAIN         |      |    TIER 3: CLOUD GPU        |  |
|  |      (10.1.1.224:2523)        |      |       (10.1.1.57)              |      |     (100.76.68.93)          |  |
|  |-------------------------------|      |--------------------------------|      |-----------------------------|  |
|  | • 3 Smart Box Physical Locks  |      | • K3s Single-Node Cluster      |      | • NVIDIA RTX 3050 6GB       |  |
|  | • Relays (BCM 6, 9, 10, 19)   |      | • Edge-Agent (Telemetry Loop)  |      | • Cloud-Agent (FastAPI)     |  |
|  | • HX711 Loadcell (4, 14)      | ---> | • Scheduler-Agent (XGBoost)    | ---> | • Deep Learning Vision      |  |
|  | • HC-SR04 Ultra (15, 17)      |      | • Migration-Agent (Dispatcher) |      |   (PyTorch / ArcFace)       |  |
|  | • Matrix Keypad & I2C LCD     | <--- | • Mosquitto Broker (:1883)     | <--- | • Result Return Callback    |  |
|  | • Dual Servos (12, 13)        |      | • Prometheus (:9090)           |      | • PostgreSQL DB             |  |
|  | • Django Backend (:8000)      |      | • Grafana Dashboard (:30000)   |      |   (Audit & Record Logging)  |  |
|  | • Node-Exporter (:31100)      |      | • PVC Dataset Storage          |      | • HPA Scaling (1 -> 2 pods) |  |
|  +-------------------------------+      +--------------------------------+      +-----------------------------+  |
+------------------------------------------------------------------------------------------------------------------+
```

---

## 2. Definisi & Tanggung Jawab 4 Agent (MAS)

Berdasarkan standarisasi pada `Dokumentasi.pdf`:

### Standar Label Keputusan (Decision Labeling Standard)
- **`Decision = 0`**: **PROSES DI EDGE** (Beban komputasi diproses lokal di Raspberry Pi).
- **`Decision = 1`**: **MIGRASI KE CLOUD** (Beban komputasi berat/Vision dialihkan ke Cloud GPU).

---

### 1. Edge Agent (Smart Box & Monitoring Resource)
- **Host**: Tier 1 (`10.1.1.224:2523`) & Container Pod di Tier 2 (`10.1.1.57`).
- **Tanggung Jawab Utama**:
  1. Kontrol aktuator perangkat keras (4 relay solenoid, 2 motor servo trapdoor, buzzer, LED).
  2. Pembacaan sensor real-time: timbangan HX711, HC-SR04 ultrasonik, getaran SW-420, IR door sensor.
  3. Pembacaan telemetri resource: `CPU_Usage (%)`, `RAM_Usage (MB)`, `Disk_IO (MB/s)`, `Network_IO (MB/s)`, `Queue`, `Latency (ms)`.
  4. Publikasi telemetri ke topik MQTT `smartbox/telemetry` via Mosquitto Broker.
  5. Penyimpanan raw data telemetri ke berkas CSV (`dataset_smartbox.csv` di volume PVC K3s) sebagai dataset primer penelitian.
  6. Visualisasi metrik secara real-time melalui Grafana Dashboard dan Prometheus.
  7. Mekanisme local fallback: Jika koneksi cloud terputus, autentikasi tetap berjalan via keypad OTP atau Face Recognition Lite offline.

---

### 2. Scheduler Agent (Machine Learning Classification via XGBoost)
- **Host**: Tier 2 (`10.1.1.57`), direktori `/home/penlok`.
- **Tanggung Jawab Utama**:
  1. Pengelolaan dataset telemetri: pembersihan data, feature selection, data split (train/test), penanganan class balance.
  2. Pelatihan dan tuning hyperparameter model klasifikasi (`XGBoost Classifier` & baseline `Random Forest`).
  3. Evaluasi saintifik model:
     - Confusion Matrix (TP, TN, FP, FN).
     - Metrik performa: Accuracy, Precision, Recall, F1-Score.
     - Analisis Feature Importance (bobot pengaruh tiap metrik terhadap keputusan).
     - Kurva Loss dan Akurasi serta kurva ROC/AUC.
  4. Menyimpan model terlatih dalam berkas serialisasi (`scheduler_agent_xgb.pkl`).
  5. Melakukan inferensi real-time terhadap vektor 7 fitur:
     $$X = [\text{CPU}, \text{RAM}, \text{Throughput}, \text{Network\_Bandwidth}, \text{Priority}, \text{Latency}, \text{Queue}]$$
  6. Mengirimkan output keputusan (`0 = Edge`, `1 = Cloud`) ke topik MQTT `smartbox/decision` atau langsung ke Migration Agent.

---

### 3. Migration Agent (Eksekusi Offloading / Pengalihan Beban)
- **Host**: Layer penghubung Tier 1 $\rightarrow$ Tier 3 (Edge ke Cloud).
- **Tanggung Jawab Utama**:
  1. Mengonsumsi perintah dari Scheduler Agent saat output bernilai `1` (Migrasi).
  2. Menyiapkan payload data tugas komputasi (task payload) dan mengompresi gambar kamera.
  3. Menembak API Cloud Agent melalui protokol HTTP POST over Tailscale mesh.
  4. Merekam parameter evaluasi migrasi:
     - **Data Size**: Pengujian variasi ukuran berkas (misal: 100 KB, 500 KB, 1 MB).
     - **Upload Time ($T_{\text{upload}}$)**: Waktu transmisi data dari Edge ke Cloud.
     - **Processing Time ($T_{\text{proc}}$)**: Waktu eksekusi inferensi di Cloud GPU.
     - **Response Time ($T_{\text{resp}}$)**: Waktu transmisi hasil dari Cloud kembali ke Edge.
     - **Total Latency ($T_{\text{total}}$)**:
       $$T_{\text{total}} = T_{\text{upload}} + T_{\text{proc}} + T_{\text{resp}}$$
     - **Success Rate**:
       $$\text{Success Rate} = \left(\frac{\text{Migrasi Berhasil}}{\text{Total Percobaan}}\right) \times 100\%$$
     - **Failed Migration**: Jumlah dan log penyebab kegagalan (network timeout, API error, server down).

#### Spesifikasi Kontrak API Migration Agent
- **Endpoint**: `POST /api/v1/migration`
- **Request Body (JSON / Multipart)**:
  ```json
  {
    "device_id": "SB01",
    "task_id": "TASK001",
    "timestamp": "2026-09-27T14:30:00Z",
    "image": "<base64_or_binary>",
    "decision": 1
  }
  ```
- **Response Body**:
  ```json
  {
    "status": "success",
    "processing_node": "cloud",
    "user_id": 13,
    "confidence": 0.94,
    "cloud_processing_time_ms": 4.8
  }
  ```

---

### 4. Cloud Agent (Menerima dan Memproses Workload)
- **Host**: Tier 3 (`penlok@100.76.68.93`), arsitektur x86_64 Ubuntu 24.04.
- **Hardware Accelerator**: NVIDIA GeForce RTX 3050 6GB (CUDA 13.2).
- **Tanggung Jawab Utama**:
  1. Menyediakan endpoint API microservice (`cloud-api`) yang berjalan di klaster Kubernetes (K3s).
  2. Menerima task payload dari Migration Agent dan melakukan inferensi Deep Learning (PyTorch / ArcFace).
  3. Mencocokkan embedding 512 dimensi wajah terhadap database pengguna terdaftar di memori GPU VRAM.
  4. Penyimpanan persisten di Database (PostgreSQL):
     - Tabel logging riwayat task (`cloud_task_log`): `task_id`, `device_id`, `timestamp`, `processing_time_ms`, `status`, `result`.
  5. Pengujian Autoscaling Kubernetes (HPA):
     - Uji skalabilitas pod di bawah beban dinamis: misalnya 10 request ditangani oleh 1 pod, 50 request diskalakan otomatis menjadi 2 pod.
  6. Mengembalikan respons hasil autentikasi ke Edge untuk pembukaan fisik solenoid.

---

## 3. Matriks Status Implementasi (As-Is vs To-Be)

| Komponen | Status Saat Ini (As-Is) | Target Sesuai Blueprint & Dokumentasi (To-Be) | Tindakan Lanjutan |
|---|---|---|---|
| **Hardware GPIO** | ✅ Berfungsi via RP1 `gpiochip15`. Relay, LCD, Keypad, Servos, Loadcell aktif. | Terintegrasi mulus dengan event open/close MAS. | Siap, harness manual diuji. |
| **Edge-Agent Telemetry** | ✅ Berjalan di pod K3s (`10.1.1.57`), 55.570+ baris data tersimpan di PVC. | Telemetri mencakup sensor fisik riil dari `10.1.1.224`. | Pasang MQTT bridge antar kedua Pi. |
| **Scheduler Model** | ✅ Model `scheduler_agent_xgb.pkl` tersedia. Skrip `live_test.py` siap. | Label diselaraskan: `1=Cloud, 0=Edge`. Terkoneksi otomatis ke pipeline K3s. | Standardisasi skrip ke format PDF. |
| **Migration Agent** | ⚠️ Belum ada service mandiri. | Service FastAPI/worker pengirim payload gambar dan pencatat tabel latensi. | Bangun `migration_agent.py`. |
| **Cloud GPU Node** | ⚠️ Host aktif, RTX 3050 idle, API `app.py` masih prototype string dummy. | Microservice K3s dengan akselerasi CUDA ArcFace + PostgreSQL logging + HPA. | Deploy PyTorch model ke GPU. |
| **Beban Pengujian** | ❌ Dummy math loop $\sqrt{x}$ di `dummy_api.py`. | Custom test script dengan gambar dan transaksi riil (50–100 request). | Bangun custom load generator. |

---

## 4. Protokol Pengujian Komparasi & Evaluasi Ilmiah

Sesuai arahan `Dokumentasi.pdf`, penelitian ini wajib membuktikan:
> *"Apakah keputusan XGBoost memang lebih baik daripada keputusan threshold sederhana?"*  
> *"Bagaimana keputusan XGBoost memengaruhi performa orkestrasi Edge–Cloud yang berjalan di Kubernetes?"*

### 4.1 Kerangka Evaluasi 3 Skenario (Comparative Benchmark)
Seluruh pengujian dijalankan dengan beban identik (simulasi beban berat 50–100 request simultan):

| Metrik Evaluasi | Skenario A: Edge-Only | Skenario B: Rule-Based Threshold | Skenario C: Machine Learning MAS (XGBoost) |
|---|---|---|---|
| **Definisi Logika** | Semua komputasi diproses lokal di CPU Raspberry Pi tanpa migrasi. | **Aturan 1**: $\text{CPU} > 80\% \rightarrow \text{Cloud}$, ELSE $\text{Edge}$.<br>**Aturan 2**: $\text{CPU} > 80\% \land \text{RAM} > 70\% \land \text{Latency} > 150\text{ms} \rightarrow \text{Cloud}$. | Klasifikasi cerdas multi-variabel 7 fitur oleh model XGBoost. |
| **CPU Usage Edge** | Menembus $100\%$, memicu thermal throttling ($> 75^\circ\text{C}$). | Berfluktuasi tajam (spike), lambat bereaksi terhadap antrean mendadak. | Terkendali stabil $< 70\%$, tidak pernah menyentuh $100\%$. |
| **RAM Usage Edge** | Membengkak akibat tumpukan proses OpenCV lokal. | Relatif stabil jika migrasi terpicu. | Stabil, alokasi memori lokal terjaga aman. |
| **Total Latency** | Meningkat eksponensial ($> 3500\text{ms}$) seiring antrean memanjang. | Latensi tidak stabil jika jaringan lambat namun aturan tetap memaksakan migrasi. | Latensi terendah dan paling stabil (P95 $< 350\text{ms}$). |
| **Throughput (TPS)**| Rendah, sistem mudah mengalami starvation. | Menengah. | Maksimal, throughput tinggi karena beban terdistribusi seimbang. |
| **Migration Time** | $0\text{ms}$ (tidak ada migrasi). | Tercatat, namun frekuensi migrasi kaku. | Optimal, hanya memigrasikan saat bermanfaat secara komputasi. |
| **Success Rate** | Menurun drastis saat terjadi overload request. | Menengah (rentan gagal jika jaringan sedang turun). | Tertinggi ($> 98\%$), mampu adaptif terhadap kondisi latency jaringan. |

---

### 4.2 Format Tabel Data Evaluasi Migration Agent (Dokumentasi.pdf)
Setiap percobaan migrasi wajib dicatat dalam format tabel standar berikut:

| No | Data Size | Upload Time (ms) | Processing Time (ms) | Response Time (ms) | Total Latency (ms) | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 100 KB | ... | ... | ... | ... | Success |
| 2 | 500 KB | 148 | 352 | 82 | 582 | Success |
| 3 | 500 KB | 155 | 347 | 79 | 581 | Success |
| 4 | 1 MB | ... | ... | ... | ... | Success |
| ... | 500 KB | ... | ... | ... | ... | Failed (Timeout) |

---

### 4.3 Pengujian Fault Tolerance / Fault Intolerance
Mengevaluasi keandalan dan mekanisme failover otomatis sistem terhadap kondisi kegagalan:

1. **Uji Container Crash**:
   - Mematikan pod backend atau edge agent secara tiba-tiba: `kubectl delete pod <pod_name>`.
   - Mengukur waktu pemulihan otomatis K3s (*recovery time*) dan memastikan hardware tidak freeze.
2. **Uji Pemutusan Jaringan (Network Sever)**:
   - Memutus koneksi Tailscale/LAN ke Cloud GPU secara mendadak.
   - Sistem wajib otomatis beralih (*failover*) ke verifikasi lokal (keypad OTP / Face Recognition Lite) tanpa kegagalan mekanik.
3. **Uji Cloud Service Outage**:
   - Mematikan endpoint Cloud Agent di `100.76.68.93`.
   - Scheduler Agent mendeteksi latency tinggi / API error $\rightarrow$ menahan komputasi di edge (`Decision = 0`).
4. **Uji Scaling Kubernetes Cloud (HPA)**:
   - Menginjeksi lonjakan traffic dari 10 request ke 50 request konkuren.
   - Menguji transisi penskalaan pod dari 1 pod ke 2 pod di klaster K3s Cloud.

---

## 5. Checklist Verifikasi Setiap Agent (Dokumentasi.pdf)

Sesuai dokumen panduan, proyek dinyatakan tuntas jika seluruh item checklist berikut terpenuhi:

### Checklist Edge Agent
- [x] Hardware teridentifikasi (Raspberry Pi 5 RP1 `gpiochip15`).
- [x] Smart Box berjalan (mekanik relay, servo trapdoor, timbangan loadcell, ultrasonic).
- [x] Container K3s berjalan (`edge-agent`, `mosquitto`, `prometheus`, `grafana`).
- [x] CPU terbaca via telemetri (`psutil`).
- [x] RAM terbaca via telemetri.
- [x] Queue terbaca via telemetri.
- [x] Latency terbaca via telemetri (ping measurement).
- [x] Telemetry dikirim ke broker MQTT (`smartbox/telemetry`).
- [x] Raw CSV tersedia di PVC (`dataset_smartbox.csv`).
- [x] Grafana dashboard tersedia dan visualisasi aktif (:30000).
- [ ] Script custom testing beban realistis menggantikan dummy JMeter.

### Checklist Scheduler Agent
- [x] Dataset tersedia (`dataset_smartbox_clean.csv`, `dataset_seimbang_final.csv`).
- [x] Feature dijelaskan (7 variabel: CPU, RAM, Throughput, Net Bandwidth, Priority, Latency, Queue).
- [x] Label dijelaskan (`0 = Edge`, `1 = Cloud`).
- [x] Dataset bersih dan seimbang.
- [x] XGBoost & Random Forest berhasil di-training.
- [x] Model disimpan (`scheduler_agent_xgb.pkl`).
- [ ] Evaluasi matematis dicatat: Confusion Matrix, Accuracy, Precision, Recall, F1-Score.
- [ ] Analisis Feature Importance divisualisasikan.
- [x] Script inference berjalan (`live_test.py`).
- [ ] Integrasi otomatis pengiriman output Decision ke Migration Agent via MQTT/API.

### Checklist Migration Agent
- [ ] Menerima decision dari Scheduler Agent (`Decision = 1`).
- [ ] API endpoint tersedia (`POST /api/v1/migration`).
- [ ] Data binary/frame gambar dapat dikirim via Tailscale.
- [ ] Cloud Agent menerima data payload.
- [ ] Response hasil diterima kembali di Edge.
- [ ] Migration Time tercatat terpisah ($T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$).
- [ ] Success Rate tercatat (persentase keberhasilan).
- [ ] Failure log tercatat (kegagalan dan penyebabnya).
- [ ] Container / service Migration Agent berjalan.

### Checklist Cloud Agent
- [x] Server aktif di PC GPU (`pengmas-tri` via Tailscale `100.76.68.93`).
- [x] Driver NVIDIA & CUDA aktif (RTX 3050 6GB, Driver 595.84, CUDA 13.2).
- [x] Klaster K3s Cloud aktif.
- [ ] Endpoint inferensi deep learning aktif (`POST /api/v1/face/verify`).
- [ ] Request gambar diterima dan diproses pada GPU CUDA.
- [ ] Database (PostgreSQL) berjalan dan tabel log tersimpan.
- [ ] Data transaksi dan audit verification tersimpan di database.
- [ ] Response hasil dikembalikan ke Edge dalam waktu $< 15\text{ms}$.
- [ ] Cloud processing time tercatat akurat.
- [ ] Pengujian HPA Scaling pod Kubernetes berhasil (1 pod $\rightarrow$ 2 pod).

---

## 6. Rencana Eksekusi Bertahap (Roadmap to 7 November 2026)

```
[Fase 1: Interkoneksi Broker & Pipeline Data]
       │
       ▼
[Fase 2: Deploy Cloud GPU Vision Service & DB]
       │
       ▼
[Fase 3: Implementasi Migration Agent & Scheduler Hook]
       │
       ▼
[Fase 4: Benchmark 3 Skenario & Pengujian Fault Tolerance]
       │
       ▼
[Fase 5: Penarikan Bukti & Penyusunan Laporan/Jurnal Ilmiah]
```

### Fase 1: Interkoneksi Broker & Pipeline Data (Oktober Minggu 1)
1. Ekspor service MQTT di K3s Raspi 2 (`10.1.1.57`) menjadi `NodePort: 31883`.
2. Konfigurasikan bridge Mosquitto dua arah di Raspi 1 (`10.1.1.224`).
3. Selaraskan label keputusan di seluruh codebase (`0 = Edge`, `1 = Cloud`).

### Fase 2: Deploy Cloud GPU Vision Service & DB (Oktober Minggu 2)
1. Bangun microservice FastAPI di GPU PC (`100.76.68.93`) dengan inferensi PyTorch ArcFace di CUDA.
2. Setup tabel PostgreSQL `cloud_task_log` untuk mencatat riwayat pemrosesan.
3. Konfigurasikan K3s Deployment + HPA scaling (1 ke 2 pod).

### Fase 3: Implementasi Migration Agent & Scheduler Hook (Oktober Minggu 3)
1. Buat service `migration_agent.py` di edge yang mendengarkan event verifikasi wajah.
2. Sambungkan inferensi `scheduler_agent_xgb.pkl` ke aliran tugas kamera.
3. Ukur dan verifikasi $T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$ pada tabel latensi.

### Fase 4: Benchmark 3 Skenario & Pengujian Fault Tolerance (Oktober Minggu 4)
1. Jalankan pengujian 50–100 request konkuren pada 3 kondisi (Edge-Only, Rule-Based, XGBoost).
2. Rekam metrik utilisasi CPU, RAM, Throughput, dan Latency ke Prometheus/Grafana.
3. Jalankan 4 skenario fault intolerance (container kill, network cut, service stop, pod scaling).

### Fase 5: Penarikan Bukti & Laporan Ilmiah (Awal November - Deadline 7 Nov 2026)
1. Ekspor data evaluasi, screenshot terminal, dashboard Grafana, dan kurva ROC/AUC.
2. Finalisasi manuskrip jurnal dan dokumen paten.
