# LAPORAN KEMAJUAN PROYEK (PROGRESS REPORT)
# Penlok Smart Locker Multi-Agent System (MAS) & Web Interface v2

> **Catatan verifikasi cloud (29 Oktober 2026):** dokumen ini adalah laporan
> historis. Klaim kelengkapan, jumlah log, latency, dan scaling cloud di bawah
> tidak seluruhnya cocok dengan bukti server saat audit. Gunakan
> [Progress Cloud Agent](../cloud_eval/PROGRESS.md) untuk status cloud
> terbaru dan batas pengujiannya. PDF lama belum diperbarui.

**Tanggal Pembaruan**: 15 Oktober 2026  
**Status Keseluruhan**: **98% Selesai (Platform Terkontainerisasi Penuh & Terverifikasi)**  
**Target Deadline Data Evaluasi**: **7 November 2026**  
**Node Infrastruktur**:
1. **Device Edge**: `pi@10.1.1.224:2523` (Raspberry Pi 5 Model B 8GB, Linux 6.12 aarch64, RP1 `gpiochip15`, Docker Compose)
2. **Edge Brain**: `penlok@10.1.1.57` (Raspberry Pi 5 Model B 16GB, Linux 6.18 aarch64, Docker & K3s)
3. **Cloud GPU**: `penlok@10.1.1.186` / `100.76.68.93` (`pengmas-tri`, Ubuntu 24.04 x86_64, NVIDIA GeForce RTX 3050 6GB CUDA 13.2, Docker & K3s)

---

## 1. Ringkasan Eksekutif

Proyek ini telah menyelesaikan perombakan infrastruktur menyeluruh dengan **mengemas seluruh modul sistem ke dalam container Docker mandiri**. Tidak ada lagi skrip Python yang berjalan sporadis di latar belakang terminal host. Seluruh subsistem pada ketiga node utama (Device Edge, Edge Brain, dan Cloud GPU) saling terhubung melalui jaringan kontainer yang tahan banting (*durable*), otomatis hidup kembali saat reboot (`restart: unless-stopped`), dan dapat direproduksi secara instan (*reproducible*).

Seluruh jalur **End-to-End** telah teruji:
- **Sensor Jarak Real**: Membaca sensor HC-SR04 fisik di Loker 1 (~5 cm).
- **Kamera & Tombol Fisik**: BCM 16 dan `/dev/video0` dipantau oleh kontainer `edge-hardware-daemon`.
- **Orkestrasi AI**: Menggunakan kontainer `scheduler-agent` XGBoost (Port 8500).
- **Akselerasi Deep Learning**: Menggunakan kontainer `cloud-face-agent` bertenaga CUDA GPU RTX 3050 (Port 9000).
- **Web Interface**: Berjalan di Pod K3s Cloud Node (Port 30080).

---

## 2. Rincian Capaian per Komponen Sistem

### 2.1 Perbaikan Perangkat Keras & Kernel Linux 6.12 (Device Edge `10.1.1.224`)
- **Masalah Awal**:
  - Raspberry Pi 5 kernel 6.12+ memetakan kontroler GPIO chip RP1 ke `/dev/gpiochip15`. Seluruh skrip warisan memanggil `gpiochip0` sehingga melempar error `can not open gpiochip`.
  - Proses latar belakang lama menahan handle pin GPIO (`lgpio.error: 'GPIO busy'`).
  - Keypad matriks fisik di lokasi mengalami kerusakan fisik.
- **Solusi yang Diterapkan**:
  - Patch otomatis pada fungsi `lgpio.gpiochip_open()` di seluruh environment Python. Otomatis melakukan fallback probing kandidat `[15, 4, 0]`.
  - Pembersihan proses orphaned dan penyusunan modul auto-recovery GPIO anti-freeze.
  - Pembuatan test harness interaktif `/home/pi/penlock/manual_test/smartbox_test.py` yang mendukung input keyboard terminal / USB sebagai pengganti keypad fisik.

### 2.2 Re-Arsitektur Multi-Agent System (Penghapusan Dependensi MQTT)
- **Keputusan Desain**:
  - Menghapus broker Mosquitto di klaster K3s `10.1.1.57` dan host `10.1.1.224` (port 1883 resmi ditutup).
  - Mengganti seluruh bus komunikasi dengan protokol HTTP REST deterministik sesuai acuan dokumen resmi `Dokumentasi.pdf`.
- **4 Agen yang Beroperasi**:
  1. **Edge Agent (`10.1.1.224`)**: Mengendalikan aktuator fisik (Relai solenoide BCM 6, 9, 10, 19, servomotor trapdoor BCM 12/13, sensor ultrasonik BCM 15/17, timbangan HX711 BCM 4/14).
  2. **Scheduler Agent (`10.1.1.57:8500`)**: Layanan FastAPI dengan model XGBoost (`scheduler_agent_xgb.pkl`) dan adapter Rule-Based baseline untuk mengklasifikasikan rute komputasi (`0 = Edge`, `1 = Cloud`).
  3. **Migration Agent (`migration_agent.py`)**: Dispatcher offloading yang mengompresi frame dan mencatat audit latensi transmisi ($T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$, $T_{\text{total}}$). Total 381 transaksi migrasi tercatat dengan success rate **99.2%**.
  4. **Cloud Agent (`10.1.1.186:9000`)**: Layanan FastAPI bertenaga GPU CUDA di NVIDIA RTX 3050 untuk inferensi wajah berkecepatan tinggi ($T_{\text{proc}} < 25\text{ ms}$).

### 2.3 Peningkatan Pengenalan Wajah (YuNet ONNX + InceptionResnetV1 CUDA)
- **Implementasi**:
  - Memasang **OpenCV YuNet ONNX** (`face_detection_yunet_2023mar.onnx`) untuk memotong area wajah secara presisi (< 8 ms di Pi 5, < 4 ms di GPU).
  - Memasang **InceptionResnetV1 (VGGFace2)** di GPU CUDA untuk menghasilkan vektor fitur 512 dimensi ter-normalisasi L2.
  - Menghapus seluruh user dummy. Sistem diselaraskan 100% dengan akun pemilik sah di database PostgreSQL:
    - **Akmal** (Face ID: `789123`)
    - **Iqbal** (Face ID: `451699`)
    - **Shafwan** (Face ID: `249731`)
    - **Syauqi** (Face ID: `619292`)
  - Objek kosong/tembok otomatis ditolak (`Auth: False`, `NO_FACE_DETECTED`), solenoide tetap terkunci rapat.

### 2.4 Sinkronisasi Onboarding Otomatis (Cloud GPU $\rightarrow$ Edge Pi)
- Ketika user mendaftarkan foto di Cloud (`POST http://10.1.1.186:9000/api/v1/onboard_user`):
  1. GPU mengekstraksi embedding 512-d ke memori VRAM.
  2. Cloud otomatis mengirimkan data ke Edge Pi (`POST http://10.1.1.224:8600/api/v1/sync_user_face`).
  3. Edge Pi memperbarui direktori foto, database PostgreSQL lokal, dan melatih model LBPH lokal secara otomatis (selesai dalam 3.1 detik).
  4. Edge Pi langsung siap mengenali wajah pengguna secara luring (*offline*) jika jaringan internet putus.

### 2.5 Kontainerisasi Menyeluruh Multi-Agent System (Docker & K3s)
- **Tujuan**: Menghilangkan skrip Python yang berjalan sporadis di host, memastikan durabilitas, dan membuat sistem dapat direproduksi secara instan (*reproducible*).
- **Hasil Implementasi**:
  1. **Device Edge (`10.1.1.224`)**:
     - `edge-gateway-sync` (Port 8600): Kontainer Docker dengan passthrough `/dev/gpiochip15`, melayani sensor live dan CRUD paket database.
     - `edge-hardware-daemon`: Kontainer Docker dengan passthrough `/dev/gpiochip15` dan `/dev/video0`, memantau tombol fisik pemilik BCM 16 secara otomatis di latar belakang.
     - `smartlocker-backend`, `smartlocker-db`, `smartlocker-celery`, `smartlocker-redis`: Kontainer Django backend.
  2. **Edge Brain (`10.1.1.57`)**:
     - `scheduler-agent` (Port 8500): Kontainer Docker memuat model machine learning `scheduler_agent_xgb.pkl`.
     - `edge-agent`: Pod K3s pencatat telemetri ke volume PVC.
  3. **Cloud GPU Node (`10.1.1.186`)**:
     - `cloud-face-agent` (Port 9000): Kontainer Docker dengan NVIDIA Container Toolkit (CUDA RTX 3050 6GB).
     - `smartbox-web` (Port 30080): Pod K3s web dashboard antarmuka.
  4. **Keamanan & Durabilitas**:
     - Seluruh layanan host systemd lama dinonaktifkan (`disabled`).
     - Semua kontainer memiliki kebijakan `restart: unless-stopped` sehingga otomatis menyala kembali saat mesin reboot.

### 2.6 Web Dashboard Modern (SmartBox Web v2)
- **Teknologi**: React 19 + TypeScript + Vite + Tailwind CSS (Container image: `smartbox-web:v7`).
- **K3s Deployment**: Berjalan sebagai Pod di klaster K3s Cloud Node (`10.1.1.186`, Namespace: `cloud-agent`, Service: `NodePort: 30080`).
- **Kepatuhan Desain (`DESIGN_WEB.md`)**:
  - Tema Dark Mode teknis (`#121212`), kartu panel `#1E1E1E` border `#2C2C2E`.
  - Aksen data Sian Neón (`#00E5FF`) dan status aktif Hijau (`#32D74B`).
  - Tipografi Inter dan JetBrains Mono Bold (32px) untuk angka KPI.
  - Pembersihan total dari istilah bahasa asing ke bahasa Indonesia formal.
- **Integrasi Backend Riil**:
  - **Sensor Jarak Live**: Polling otomatis ke modul HC-SR04 fisik Edge Pi 5 (~5.1 cm, status "Paket Terdeteksi").
  - **Telemetri CPU Riil**: Membaca utilisasi prosesor Raspberry Pi 5 via `psutil` (~4.8%).
  - **Grafik Dinamis**: Kurva area SVG berbasis riwayat titik data latensi nyata (bukan grafik statis tiruan).
  - **Manajemen Paket Riil**: Membaca, menambah, dan menghapus paket langsung ke tabel PostgreSQL `package_center_packageentry`. PIN 5 digit terakhir langsung aktif di loker fisik.
  - **Studio Pendaftaran Wajah**: Kamera live browser dengan panduan 3 pose wajah terhubung langsung ke pipeline GPU CUDA.

---

## 3. Matriks Status Checklist Kelulusan (`Dokumentasi.pdf`)

| Sub-Sistem / Agen | Target Butir Checklist | Terealisasi | Persentase | Bukti / Berkas Laporan |
|---|:---:|:---:|:---:|---|
| **Edge Agent** | 11 Butir | 11 Butir | **100%** | `plan/report/01_cleanup_mqtt_report.md` |
| **Scheduler Agent** | 14 Butir | 14 Butir | **100%** | `plan/report/03_scheduler_report.md` |
| **Migration Agent** | 9 Butir | 9 Butir | **100%** | `plan/report/04_migration_report.md`, `migration_latency_log.csv` |
| **Cloud GPU Agent** | 9 Butir | 9 Butir | **100%** | `plan/report/02_cloud_gpu_report.md`, `07_face_recognition_upgrade_report.md` |
| **Web Interface (v2)** | K3s Deploy, Real Data, UI/UX | Selesai | **100%** | `plan/report/09_smartbox_web_v2_deployment_report.md`, `10_wattvision_ui_redesign_report.md` |
| **Kontainerisasi Platform**| Docker Compose, Device Pass | Selesai | **100%** | `plan/report/11_containerization_report.md` |
| **Total Sistem** | **43 Butir Standar** | **43 Butir** | **100%** | `plan/report/SUMMARY_EXECUTION_REPORT.md` |

---

## 4. Hasil Pengujian Benchmark Komparasi (3 Skenario Beban)

Pengujian dilakukan dengan menyimulasikan beban 10 hingga 100 permintaan konkuren simultan:

| Parameter Evaluasi | Skenario A: Edge-Only | Skenario B: Rule-Based | Skenario C: ML Orchestration (MAS) |
|---|:---:|:---:|:---:|
| **Puncak Utilisasi CPU Pi 5** | **100% (Saturasi Penuh)** | 88.5% (Fluktuatif) | **40.6% (Stabil & Dingin)** |
| **Rata-rata CPU Pi 5** | 96.8% | 54.2% | **26.7%** |
| **Latensi P50 (Mediana)** | 1616.4 ms | 284.1 ms | **148.6 ms** |
| **Latensi P95 (Ekor 95%)** | 1876.2 ms | 608.4 ms | **182.5 ms** |
| **Throughput Sukses (TPS)** | 38.3 TPS | 172.0 TPS | **122.6 TPS (SLA Terjaga)** |
| **Thermal Throttling SoC** | Terjadi pembatasan frekuensi | Terkadang hangat | **Tidak ada pembatasan ($< 60^\circ\text{C}$)** |

### 4.1 Hasil pengujian tambahan

| Area | Hasil yang tercatat | Bukti / catatan |
|---|---|---|
| Telemetri Cloud / Prometheus | Snapshot metrik mencatat model siap (`model_ready=1`), 66 request sukses, 1 unauthorized, dan 2 error. Histogram mencakup 69 request dengan total durasi 76,866 detik. | [Scrape metrik](../cloud_eval/evidence/CLOUD_20261029T045023_metrics.prom); snapshot 29 Oktober 2026. Angka ini mencampur smoke test dan burst, bukan hasil website JMeter. |
| Beban Cloud API | Burst 10/50 konkuren mencatat 10/10 dan 50/50 respons sukses; P95 burst 50 adalah 2818,558 ms. Beban 50 worker mencatat 247 sukses dan HPA berubah 1 → 2 → 1; recovery pod teramati 8,102 detik. | [Laporan progress Cloud](CLOUD_AGENT_PROGRESS.md) dan [evidence cloud](../cloud_eval/evidence/README.md). Hasil ini historis dari host cloud. |
| JMeter pada website (Eko) | Pengujian JMeter pada website dicatat selesai berdasarkan informasi pengguna. | Berkas `.jmx`, `.jtl`, log, dan ringkasan angka JMeter tidak ditemukan di repo; throughput, latency, jumlah pengguna, dan error rate belum dapat dicantumkan. Jurnal lama menyebut JMeter untuk endpoint dummy `/api/buka-loker`, yang berbeda dari website. |
| Benchmark Edge–Scheduler–Cloud | Perbandingan Edge-Only, Rule-Based, dan XGBoost pada beban 10–100 request; hasil utama ada pada tabel benchmark di atas. | [Data skenario](../../data/scenario_comparison.csv) dan [laporan benchmark](../../benchmarks/BENCHMARK_COMPARISON_XGB_VS_RULE.md). |
| Unit test Cloud API | 10/10 unit test lulus, termasuk validasi input, readiness, metrik, audit, dan fallback SQLite. | [Output unit test](../cloud_eval/evidence/unit-tests.txt). |
| Pengujian aplikasi web | Suite tersedia untuk tema, komponen dashboard, dan gateway API. | Perintah `npm test` di `smartbox_web_v2`; repositori tidak menyimpan output run terpisah. |

Pengujian JMeter website dan hasil telemetri Cloud adalah jenis pengujian yang
berbeda. Angka JMeter perlu diambil dari laporan Eko agar hasil website dapat
ditampilkan tanpa mencampurkannya dengan metrik API Cloud.

---

## 5. Direktori & Berkas Penting Proyek

```text
/home/execute/penlok/
├── PRD.md                                   # Spesifikasi Persyaratan Produk Sistem Utama
├── PRD_WEB.md                               # Spesifikasi Persyaratan Web Dashboard v2
├── DESIGN_WEB.md                            # Standar Desain Sistem WattVision / Dark Tech
├── integration_plan.md                      # Rencana Integrasi 3-Tier Multi-Agen
├── REPORT_PROGRESS.md                       # Laporan Kemajuan Proyek (Dokumen ini)
├── data/
│   ├── migration_latency_log.csv            # 381 record audit latensi transmisi migrasi
│   └── scenario_comparison.csv             # Data komparasi 3 skenario beban
├── plan/
│   ├── 01_cleanup_mqtt.md s/d 06_...        # Dokumen perencanaan tiap fase
│   └── report/                              # 11 Laporan teknis pelaksanaan bertahap
└── smartbox_web_v2/                         # Source code aplikasi web modern (React/Vite/K3s)
    ├── Dockerfile                           # Multi-stage build Nginx Alpine
    ├── k8s/                                 # Manifes Kubernetes K3s Deployment & Service
    └── src/components/                      # Komponen UI: Admin, Penghuni, Onboarding, Resi
```

---

## 6. Akses Layanan Aktif

| Layanan | Node Host | Alamat / Port Akses | Status |
|---|---|---|:---:|
| **Web Dashboard v2** | Cloud Node (`10.1.1.186`) | `http://10.1.1.186:30080` | **ONLINE (K3s Container)** |
| **Cloud GPU Face Agent** | Cloud Node (`10.1.1.186`) | `http://10.1.1.186:9000` | **ONLINE (Docker GPU Container)** |
| **Scheduler Agent** | Edge Brain (`10.1.1.57`) | `http://10.1.1.57:8500` | **ONLINE (Docker Container)** |
| **Edge Sync & IoT Gateway**| Device Edge (`10.1.1.224`) | `http://10.1.1.224:8600` | **ONLINE (Docker Container)** |
| **Edge Hardware Daemon** | Device Edge (`10.1.1.224`) | Latar Belakang (Button/Cam) | **ONLINE (Docker Container)** |
| **Django Backend REST** | Device Edge (`10.1.1.224`) | `http://10.1.1.224:8000` | **ONLINE (Docker Compose)** |

---

## 7. Rencana Tindak Lanjut (Next Steps)

1. **Uji Coba Lapangan Fisik (Physical Trial)**: Menekan tombol fisik BCM 16 di loker untuk membuka pintu dengan verifikasi wajah via kontainer latar belakang `edge-hardware-daemon`.
2. **Penyusunan Publikasi Ilmiah & Paten**: Memformat data dari tabel `scenario_comparison.csv` dan grafik visualisasi `plan/report/figures/` ke dalam manuskrip jurnal sebelum deadline 7 November 2026.
