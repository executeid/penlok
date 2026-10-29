# Product Requirements Document (PRD)
# Penlok Smart Locker Multi-Agent System (MAS) 2026

**Document Version**: 2.1.0  
**Status**: Approved / Active Integration  
**Date**: 27 September 2026  
**Reference Standards**:
1. `Penlok 2026.pdf` — Blueprint Arsitektur Multi-Agent System
2. `Dokumentasi.pdf` — Standarisasi Teknis, Parameter Evaluasi, & Checklist Pengujian

**Target Deployment Hardware**:
- **Device Edge (Tier 1)**: Raspberry Pi 5 Model B Rev 1.1 (8GB, Linux 6.12 aarch64, RP1 `gpiochip15`, 3-Box Locker)
- **Edge Brain (Tier 2)**: Raspberry Pi 5 Model B Rev 1.0 (16GB, Linux 6.18 aarch64, K3s Cluster, Prometheus/Grafana)
- **Cloud GPU (Tier 3)**: PC x86_64, NVIDIA GeForce RTX 3050 6GB, CUDA 13.2, Tailscale VPN Mesh

**Batas Waktu Pengambilan Data Evaluasi (Target)**: **7 November 2026**

---

## 1. Executive Summary & Product Vision

### 1.1 Background & Problem Statement
Sistem loker pintar konvensional (Smart Locker) yang hanya mengandalkan unit komputasi tunggal di edge (single SBC/microcontroller) mengalami kelemahan krusial:
1. **CPU Throttling**: Komputasi visi komputer (OpenCV Face Recognition) pada CPU ARM membebani daya komputasi hingga 100%, memicu thermal throttling dan perlambatan respon mekanik.
2. **Keterbatasan Akurasi**: CPU edge terbatas pada algoritma pengenalan wajah primitif (Haar Cascade + LBPH) yang rentan terhadap variasi pencahayaan dan sudut orientasi wajah.
3. **Ketergantungan Cloud Ekstrem**: Jika seluruh beban dialihkan ke cloud secara statis, sistem gagal beroperasi saat koneksi internet terganggu (network partition).

### 1.2 The Solution: Multi-Agent System (MAS)
Penlok 2026 mengimplementasikan arsitektur **Multi-Agent System (MAS)** cerdas 3-Tier yang membagi tugas komputasi dan kontrol secara dinamis antara **Device Edge**, **Edge Computing Brain**, dan **Cloud GPU Node**. Penempatan tugas (lokal vs offloading ke GPU) diputuskan secara real-time oleh model machine learning (**XGBoost / Random Forest**) berdasarkan kondisi telemetri sistem 7-dimensi.

### 1.3 Hardware Iteration Evolution
- **Generasi 1**: ESP32, 1 loker, autentikasi kurir/owner via keypad, tanpa pengenalan wajah.
- **Generasi 2**: Raspberry Pi 4, 1 loker, pengenalan wajah lokal (LBPH).
- **Generasi 3 (Sistem Saat Ini)**: Raspberry Pi 5, 3 kompartemen loker (Kurir, Pemilik, Marketplace Penjual/Pembeli), integrasi trapdoor otomatis, sensor timbangan HX711, klaster K3s, dan orkestrasi AI multi-agen.

---

## 2. System Actors & User Personas

| Actor | Description | Primary Interactions |
|---|---|---|
| **Kurir (Courier)** | Petugas ekspedisi yang mengantarkan barang ke loker inbound. | Scan QR Resi atau memasukkan 5 digit resi manual via keypad; memasukkan paket ke Locker 1. |
| **Pemilik Loker (Owner)** | Pemilik sah penyimpanan loker penyimpanan internal (Locker 2). | Menekan push button GPIO 16; melakukan autentikasi wajah via kamera; mengambil barang dari Locker 2. |
| **Pembeli (Buyer)** | Pengguna marketplace P2P yang mengambil barang transaksi. | Memasukkan 6-digit OTP transaksi via keypad; mengambil barang dari Locker 3. |
| **Penjual (Seller)** | Pengguna marketplace yang menitipkan barang pesanan ke loker. | Memasukkan kode deposit transaksi marketplace; menaruh barang di Locker 3. |
| **Admin / Researcher** | Pengembang dan penguji sistem. | Memantau dashboard Grafana, menginspeksi metrik Prometheus, melatih model AI, menjalankan stress-test. |

---

## 3. Product Architecture & Multi-Agent Roles

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MULTI-AGENT WORKFLOW TOPOLOGY                                  │
│                                                                                                  │
│   ┌─────────────────────┐                                                                        │
│   │    EDGE AGENT       │ ──(1. Push Telemetry setiap 2s)──> ┌───────────────────────────────┐   │
│   │  (Device Control)   │                                    │        SCHEDULER AGENT        │   │
│   │                     │ <──(4. Execute Relay Command)───── │        (AI Inference)         │   │
│   └─────────────────────┘                                    │                               │   │
│              │                                               │ • Model: XGBoost Classifier   │   │
│    (2. Event Capture: Frame)                                 │ • Input: 7 Fitur Telemetri    │   │
│              │                                               │ • Output: 0=Edge, 1=Cloud     │   │
│              ▼                                               └───────────────────────────────┘   │
│   ┌─────────────────────┐                                                    │                   │
│   │   MIGRATION AGENT   │ <───────────(3. Perintah Offload jika Output=1)────┘                   │
│   │  (Payload Forward)  │                                                                        │
│   └─────────────────────┘                                                                        │
│              │                                                                                   │
│    (5. Binary Frame Stream via Tailscale)                                                        │
│              │                                                                                   │
│              ▼                                                                                   │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                      CLOUD AGENT                                         │   │
│   │                               (RTX 3050 GPU Accelerator)                                 │   │
│   │                                                                                          │   │
│   │ • Framework: PyTorch / CUDA 13.2 ArcFace Model                                            │   │
│   │ • Feature Vector: 512-d Embedding Matching                                               │   │
│   │ • Latency: < 5ms per tensor pass                                                         │   │
│   │ • Database Sync: Log verifikasi dan audit access ke PostgreSQL                           │   │
│   │ • Kubernetes Autoscaling (HPA): 1 pod (10 req) -> 2 pods (50 req)                        │   │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Standar Label Keputusan (Decision Labeling Standard)
Berdasarkan spesifikasi `Dokumentasi.pdf`:
- **`Decision = 0`**: **PROSES DI EDGE** (Diproses lokal di CPU Raspberry Pi).
- **`Decision = 1`**: **MIGRASI KE CLOUD** (Dialihkan ke GPU PC melalui Migration Agent).

---

### 3.2 Agen 1: Edge Agent (Smart Box & Resource Monitoring)
- **Komponen**: Driver hardware (`lgpio`, `gpiozero`, `RPLCD`), background daemon `pan-piXarduino-fixed.py`, collector telemetri `app/main.py`.
- **Fungsi**:
  1. Kontrol aktuator fisik (4 relay solenoid, 2 motor servo trapdoor, buzzer, LED).
  2. Pembacaan sensor: HX711 loadcell, HC-SR04 ultrasonik, getaran SW-420, IR door sensor.
  3. Membaca metrik utilisasi: CPU, RAM, Disk I/O, Network delta, Queue, Latency.
  4. Publikasi telemetri ke MQTT `smartbox/telemetry` dan penyimpanan raw CSV (`dataset_smartbox.csv`).
  5. Visualisasi metrik live via Prometheus dan Grafana Dashboard (:30000).

### 3.3 Agen 2: Scheduler Agent (Machine Learning Classification)
- **Komponen**: Model serialisasi `scheduler_agent_xgb.pkl`, inferensi engine `live_test.py`.
- **Fungsi**:
  1. Menerima vektor 7 fitur:
     $$X = [\text{CPU}, \text{RAM}, \text{Throughput}, \text{Network\_Bandwidth}, \text{Priority}, \text{Latency}, \text{Queue}]$$
  2. Klasifikasi tugas: `0 = Edge`, `1 = Cloud`.
  3. Publikasi keputusan ke MQTT topik `smartbox/decision` dalam waktu $< 15\text{ms}$.

### 3.4 Agen 3: Migration Agent (Eksekusi Offloading)
- **Komponen**: Service dispatcher API (`migration_agent.py`).
- **Fungsi**:
  1. Menerima sinyal `Decision = 1` dari Scheduler Agent.
  2. Mengemas payload tugas dan frame kamera gambar (JPEG binary).
  3. Mengirimkan data via HTTP POST ke endpoint Cloud Agent melalui Tailscale VPN.
  4. Mengukur dan mencatat metrik latensi migrasi: Upload Time, Processing Time, Response Time, Total Latency, Success Rate, Failed Migration log.

#### Kontrak API Migration Agent (`Dokumentasi.pdf`)
- **Endpoint**: `POST /api/v1/migration`
- **Request Body**:
  ```json
  {
    "device_id": "SB01",
    "task_id": "TASK001",
    "timestamp": "2026-09-27T14:30:00Z",
    "image": "<base64_or_binary_data>",
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

### 3.5 Agen 4: Cloud Agent (Cloud GPU Ingestion & Autoscaling)
- **Komponen**: K3s Microservice FastAPI di host GPU (`penlok@100.76.68.93`).
- **Fungsi**:
  1. Menerima request dari Migration Agent.
  2. Mengeksekusi model Deep Learning (PyTorch / ArcFace) pada GPU NVIDIA RTX 3050 (CUDA 13.2).
  3. Mencocokkan embedding wajah 512 dimensi terhadap database pengguna dalam VRAM.
  4. Menyimpan data transaksi ke PostgreSQL: `task_id`, `device_id`, `timestamp`, `processing_time_ms`, `status`, `result`.
  5. Pengujian Autoscaling Kubernetes (HPA): Menguji skalabilitas dari 1 pod (beban 10 request) menjadi 2 pod (beban 50 request).

---

## 4. Functional Requirements (FR)

### FR-01: Kurir Drop-Off Paket (Inbound Locker 1)
- **FR-01.1**: Antarmuka LCD I2C menampilkan opsi: `4. Kirim Paket` $\rightarrow$ `4. Scan QR` atau `5. Masukkan Resi`.
- **FR-01.2**: Jika QR dipilih, kamera membaca barcode/QR melalui `cobav2.py` / `pyzbar`.
- **FR-01.3**: Jika manual dipilih, pengguna menginput 5 digit terakhir resi via keypad/keyboard.
- **FR-01.4**: Sistem memvalidasi resi pada database `package_center_packageentry`.
- **FR-01.5**: Jika valid, buzzer berbunyi sukses dan Relay 3 (BCM GPIO 10) aktif selama 2.5 detik membuka Locker 1.

### FR-02: Mekanisme Pemindahan Otomatis (Trapdoor Locker 1 $\rightarrow$ Locker 2)
- **FR-02.1**: Sensor ultrasonik HC-SR04 memonitor jarak di Locker 1 (Threshold $< 23\text{cm}$).
- **FR-02.2**: Saat paket terdeteksi, sistem memantau penutupan pintu via sensor IR (BCM GPIO 26).
- **FR-02.3**: Saat pintu tertutup, skrip `servo2.py` menggerakkan sepasang motor servo (BCM 12 & 13) selama 0.45 detik membuka trapdoor.
- **FR-02.4**: Paket jatuh ke Locker 2; servo berputar balik menutup trapdoor selama 0.5 detik dan langsung detach PWM untuk mencegah jitter.
- **FR-02.5**: Timbangan HX711 membaca berat paket baru di Locker 2 dan melaporkan ke log.

### FR-03: Pengambilan Paket Marketplace (Locker 3)
- **FR-03.1**: Pembeli memilih opsi `5. Ambil Paket` pada LCD.
- **FR-03.2**: Pembeli menginput 6 digit OTP transaksi marketplace.
- **FR-03.3**: Sistem memvalidasi OTP terhadap tabel `marketplace_transaction` (`status = 'AWAITING_PICKUP'`).
- **FR-03.4**: Jika cocok, Relay 1 (BCM GPIO 6) aktif membuka solenoid Locker 3 selama 3 detik, status diupdate menjadi `COMPLETED`, dan notifikasi dikirim ke penjual.

### FR-04: Autentikasi Biometrik Pemilik (Locker 2)
- **FR-04.1**: Pemilik menekan tombol push button fisik (BCM GPIO 16).
- **FR-04.2**: Kamera menangkap frame wajah dan meminta keputusan dari Scheduler Agent:
  - **Jalur Edge (`Decision = 0`)**: Jalankan Haar Cascade + LBPH matcher lokal di Raspberry Pi 5.
  - **Jalur Cloud GPU (`Decision = 1`)**: Migration Agent mengirimkan frame ke Cloud Agent (`100.76.68.93`). Model ArcFace di GPU mencocokkan embedding wajah dalam $< 5\text{ms}$.
- **FR-04.3**: Jika terverifikasi, Relay 2 (BCM GPIO 9) aktif membuka solenoid Locker 2.

### FR-05: Pengumpulan Telemetri Real-Time
- **FR-05.1**: Edge Agent mengumpulkan metrik performa setiap 2 detik: CPU, RAM, Disk I/O, Network Bandwidth, Priority (1-3), Latency (ms), Queue Length.
- **FR-05.2**: Telemetri dipublikasikan ke topik MQTT `smartbox/telemetry` dan dicatat ke persistent storage PVC (`dataset_smartbox.csv`).

### FR-06: Dynamic ML Task Scheduling
- **FR-06.1**: Scheduler Agent memuat model terlatih `scheduler_agent_xgb.pkl`.
- **FR-06.2**: Model melakukan inferensi deterministik:
  $$\text{Prediksi} \in \{0, 1\} \quad (0 = \text{Tetap di Edge}, 1 = \text{Migrasi ke Cloud})$$
- **FR-06.3**: Hasil inferensi dipublikasikan ke topik MQTT `smartbox/decision` dalam waktu $< 15\text{ms}$.

### FR-07: Fault Intolerance & Failover Otomatis
- **FR-07.1**: Jika koneksi jaringan ke Cloud Agent mengalami timeout ($> 500\text{ms}$) atau terputus total, sistem secara instan mengalihkan verifikasi ke mode offline (Local Haar/LBPH atau keypad PIN fallback).
- **FR-07.2**: Kegagalan container K3s (pod crash) tidak boleh mengunci aktuator fisik atau mematikan skrip hardware utama di host Raspberry Pi 1.

---

## 5. Non-Functional Requirements (NFR)

### NFR-01: Performance & Latency SLA
- **NFR-01.1**: Waktu pembukaan relay fisik sejak input selesai tidak boleh melebihi **1.5 detik**.
- **NFR-01.2**: Waktu pemrosesan inferensi wajah di sisi Cloud GPU tidak boleh melebihi **15 ms** per frame.
- **NFR-01.3**: P95 end-to-end latency pada sistem dengan ML Orchestration harus berada di bawah **400 ms** pada kondisi 50 request bersamaan.

### NFR-02: Edge Resource Protection
- **NFR-02.1**: Utilisasi CPU pada Raspberry Pi 1 & 2 tidak boleh menyentuh 100% secara berkelanjutan saat diuji beban tinggi (target maksimal: $< 75\%$).
- **NFR-02.2**: Suhu SoC Raspberry Pi 5 harus terjaga di bawah ambang batas thermal throttling ($< 75^\circ\text{C}$).

### NFR-03: Security & Network Isolation
- **NFR-03.1**: Seluruh komunikasi antar-node wajib terenkripsi menggunakan Tailscale WireGuard mesh VPN (`100.x.x.x`).
- **NFR-03.2**: Port SSH non-standar `2523` digunakan pada Device Edge dengan otentikasi kunci kriptografi.
- **NFR-03.3**: Broker MQTT tidak boleh diekspos secara terbuka ke internet publik; hanya melayani traffic internal subnet dan Tailscale.

### NFR-04: Hardware Safety & Electrical Reliability
- **NFR-04.1**: Setiap solenoid relay wajib diproteksi dengan flyback diode (1N4007) untuk mencegah arus balik induktif merusak pin GPIO.
- **NFR-04.2**: Seluruh claim GPIO wajib menggunakan helper probing dinamis (`_get_gpio_chip()`) untuk kompatibilitas chip RP1 Linux 6.12+ (`/dev/gpiochip15`).

---

## 6. Hardware Pinout & Wiring Specifications

Semua nomor pin mengacu pada standar penomoran **Broadcom (BCM) GPIO**:

| Komponen Hardware | Pin BCM | Mode Pin | Rangkaian / Protokol | Fungsi Sistem |
|---|---|---|---|---|
| **Relay 1** | GPIO 6 | Output | Active LOW | Solenoid Lock Kompartemen 3 (Marketplace) |
| **Relay 2** | GPIO 9 | Output | Active LOW | Solenoid Lock Kompartemen 2 (Penyimpanan Internal) |
| **Relay 3** | GPIO 10 | Output | Active LOW | Solenoid Lock Kompartemen 1 (Inbound Kurir) |
| **Relay 4** | GPIO 19 | Output | Active LOW | Solenoid Latch Aux / Pintu Atas RFID |
| **Servo Left** | GPIO 13 | PWM Output | `gpiozero.Servo` | Mekanisme Trapdoor Loker 1 $\rightarrow$ Loker 2 |
| **Servo Right** | GPIO 12 | PWM Output | `gpiozero.Servo` | Counter-rotation Trapdoor Loker 1 $\rightarrow$ Loker 2 |
| **I2C LCD 20x4** | SDA/SCL | I2C Bus 1 | PCF8574 (`0x27`) | UI Antarmuka Menu "BoxInAja" |
| **Keypad Matrix (Kolom)** | GPIO 8, 25, 11 | Output | Strobe Scanning | Pemindai Kolom Keypad 3x4 |
| **Keypad Matrix (Baris)** | GPIO 5, 1, 0, 7 | Input | Pull-Down | Pembaca Baris Keypad 3x4 |
| **HC-SR04 (Ultrasonik)** | TRIG: 15, ECHO: 17 | Output/Input | Digital Timing | Deteksi Keberadaan Paket di Loker 1 |
| **Sensor Inframerah (IR)** | GPIO 26 | Input | Pull-Down | Deteksi Status Pintu Loker 1 (Tertutup / Terbuka) |
| **Load Cell (HX711)** | DOUT: 4, SCK: 14 | Input/Output | Bit-Bang SPI | Pemantauan Berat Paket Real-time |
| **Sensor Getar (SW-420)**| GPIO 24 | Input | Pull-Down | Deteksi Upaya Pembobolan / Anomali Getaran |
| **Push Button (Owner)** | GPIO 16 | Input | Pull-Up | Pemicu Verifikasi Kamera Wajah Pemilik |
| **Push Button (QR)** | GPIO 20 | Input | Pull-Up | Pemicu Kamera Pemindai Resi QR |
| **Buzzer** | GPIO 21 | Output | Active HIGH | Umpan Balik Suara (Beep Terima / Tolak) |
| **LED Indikator Merah** | GPIO 23, 18 | Output | Active LOW | Sinyal Visual Kesalahan / Ditolak |
| **LED Indikator Hijau** | GPIO 22, 27 | Output | Active LOW | Sinyal Visual Berhasil / Diterima |

---

## 7. Research Evaluation & Verification Plan (`Dokumentasi.pdf`)

### 7.1 Pengujian Komparasi 3 Skenario Beban (Comparative Benchmark)
Simulasi beban berat (50–100 request simultan) membandingkan 3 skenario:
1. **Skenario A (Edge-Only)**: Seluruh tugas diproses di Raspberry Pi tanpa migrasi.
2. **Skenario B (Rule-Based Threshold)**:
   - *Aturan 1*: $\text{IF CPU} > 80\% \rightarrow \text{Migrasi ke Cloud, ELSE Edge}$.
   - *Aturan 2*: $\text{IF CPU} > 80\% \land \text{RAM} > 70\% \land \text{Latency} > 150\text{ms} \rightarrow \text{Migrasi ke Cloud, ELSE Edge}$.
3. **Skenario C (AI Orchestration MAS)**: Keputusan klasifikasi dinamis oleh model XGBoost 7-fitur.

**Parameter Perbandingan Wajib Dicatat**:
- Total Latency (P50, P95, P99).
- CPU Usage Edge (%).
- RAM Usage Edge (MB).
- Throughput (TPS).
- Migration Time (ms).
- Success Rate (%).

---

### 7.2 Format Pencatatan Migration Agent
Tabel pengukuran wajib pada pengujian migrasi:

| No | Data Size | Upload Time (ms) | Processing Time (ms) | Response Time (ms) | Total Latency (ms) | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 100 KB | ... | ... | ... | ... | Success |
| 2 | 500 KB | 148 | 352 | 82 | 582 | Success |
| 3 | 500 KB | 155 | 347 | 79 | 581 | Success |
| 4 | 1 MB | ... | ... | ... | ... | Success |
| ... | 500 KB | ... | ... | ... | ... | Failed (Timeout) |

Rumus:
$$\text{Total Latency} = \text{Upload Time} + \text{Processing Time} + \text{Response Time}$$
$$\text{Success Rate} = \left(\frac{\text{Migrasi Berhasil}}{\text{Total Percobaan}}\right) \times 100\%$$

---

### 7.3 Pengujian Fault Tolerance / Fault Intolerance
1. **Container Mati**: Simulasi `kubectl delete pod` pada pod edge agent. Verifikasi recovery otomatis K3s.
2. **Network Putus**: Simulasi pemutusan koneksi Tailscale/LAN. Sistem wajib failover otomatis ke mode lokal tanpa delay relay.
3. **Cloud Service Mati**: Simulasi shutdown endpoint Cloud Agent. Scheduler menahan komputasi di edge (`Decision = 0`).
4. **Pod Cloud Mati**: Simulasi crash pod di klaster K3s Cloud dan uji penskalaan HPA (1 pod $\rightarrow$ 2 pod).

---

## 8. Checklist Verifikasi Kelulusan Setiap Agent

### Edge Agent Checklist
- [x] Hardware teridentifikasi (RPi 5 RP1 `gpiochip15`).
- [x] Smart Box berjalan (mekanik relay, servo trapdoor, timbangan loadcell, ultrasonic).
- [x] Container K3s berjalan (`edge-agent`, `mosquitto`, `prometheus`, `grafana`).
- [x] CPU, RAM, Queue, Latency terbaca via telemetri.
- [x] Telemetri terkirim ke MQTT `smartbox/telemetry`.
- [x] Raw CSV tersedia di PVC (`dataset_smartbox.csv`).
- [x] Grafana dashboard tersedia (:30000).
- [ ] Script custom testing beban realistis menggantikan dummy JMeter.

### Scheduler Agent Checklist
- [x] Dataset tersedia (`dataset_smartbox_clean.csv`, `dataset_seimbang_final.csv`).
- [x] Feature dan label dijelaskan (`0 = Edge`, `1 = Cloud`).
- [x] Dataset bersih dan seimbang.
- [x] XGBoost & Random Forest berhasil di-training.
- [x] Model disimpan (`scheduler_agent_xgb.pkl`).
- [ ] Confusion Matrix, Accuracy, Precision, Recall, F1-Score tercatat.
- [ ] Feature Importance divisualisasikan.
- [x] Script inference berjalan (`live_test.py`).
- [ ] Output decision otomatis terkirim ke Migration Agent.

### Migration Agent Checklist
- [ ] Menerima decision dari Scheduler Agent (`Decision = 1`).
- [ ] API endpoint tersedia (`POST /api/v1/migration`).
- [ ] Data frame gambar dapat dikirim via Tailscale.
- [ ] Cloud Agent menerima data payload.
- [ ] Response hasil diterima kembali di Edge.
- [ ] Migration Time tercatat terpisah ($T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$).
- [ ] Success Rate tercatat (%).
- [ ] Failure log tercatat.
- [ ] Container / service Migration Agent berjalan.

### Cloud Agent Checklist
- [x] Server aktif di PC GPU (`pengmas-tri` via Tailscale `100.76.68.93`).
- [x] Driver NVIDIA & CUDA aktif (RTX 3050 6GB, Driver 595.84, CUDA 13.2).
- [x] Klaster K3s Cloud aktif.
- [ ] Endpoint inferensi deep learning aktif (`POST /api/v1/face/verify`).
- [ ] Request gambar diproses pada GPU CUDA.
- [ ] Database PostgreSQL berjalan dan tabel log tersimpan.
- [ ] Data transaksi tersimpan di database.
- [ ] Response hasil dikembalikan ke Edge dalam waktu $< 15\text{ms}$.
- [ ] Cloud processing time tercatat akurat.
- [ ] Pengujian HPA Scaling pod Kubernetes berhasil (1 pod $\rightarrow$ 2 pod).

---

## 9. Project Timeline & Milestones (Roadmap to 7 November 2026)

| Periode | Milestone Deliverables | Target Status |
|---|---|---|
| **Juni – Agustus 2026** | Hardware Wiring, K3s Cluster Setup, Containerization Dasar. | Selesai (100%) |
| **September 2026** | Perbaikan Driver GPIO RPi 5 Kernel 6.12, Manual Test Harness, Aligning PRD & Integration Plan. | Selesai (100%) |
| **Oktober Minggu 1** | Interkoneksi Broker MQTT dua arah, Penyelarasan Label Decision (`0=Edge`, `1=Cloud`). | Terjadwal |
| **Oktober Minggu 2** | Deploy Cloud GPU PyTorch ArcFace Service, Database Logging PostgreSQL, HPA Setup. | Terjadwal |
| **Oktober Minggu 3** | Implementasi Migration Agent Service, Hook Scheduler Real-time ke Kamera. | Terjadwal |
| **Oktober Minggu 4** | Eksekusi Benchmark 3 Skenario (Edge-Only vs Rule-Based vs XGBoost) & Fault Intolerance. | Terjadwal |
| **1 – 7 November 2026** | **FINAL DATA EVALUATION DEADLINE**: Penarikan bukti, grafik ROC/AUC, penyusunan laporan akhir dan paten. | Target Kunci |
| **Desember 2026** | Pensasi / Uji Akhir Produk dan Serah Terima Sistem. | Target Akhir |
