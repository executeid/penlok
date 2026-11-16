# PENLOK — Smart Locker Multi-Agent System (MAS) & IoT

Ekosistem Smart Locker cerdas berbasis **Multi-Agent System (MAS)** dan IoT untuk manajemen penitipan barang otomatis, kurir (*inbound delivery*), pengambilan barang marketplace (*buyer pickup*), serta akses biometrik pemilik loker (*owner biometric access*).

Beban komputasi inferensi biometrik dibagi secara dinamis antara **Device Edge** (Raspberry Pi 5) dan **Cloud GPU** (NVIDIA GeForce RTX 3050 CUDA) melalui pengklasifikasi cerdas **XGBoost**.

> 📌 **Panduan Lengkap Presentasi & Uji Coba Demo:**  
> Untuk panduan langkah demi langkah demonstrasi fisik lemari, tampilan web observatory, skenario stress testing, dan ringkasan hasil benchmark komparatif, lihat berkas:  
> 👉 **[`PANDUAN_DEMO_DAN_PENGUJIAN.md`](PANDUAN_DEMO_DAN_PENGUJIAN.md)**

---

## 1. Topologi Jaringan & Arsitektur Sistem

```
               [ KEYPAD / WEBCAM / SENSOR / RELAY ]
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │             Device Edge (Raspberry Pi 5 8GB)           │
   │               IP: 10.1.1.224 | Port: 2523              │
   │      - edge-hardware-daemon (I/O, Keypad, Relay)       │
   │      - edge-gateway-sync (Port 8600, Local Cache)      │
   └───────────────────────────┬────────────────────────────┘
                               │
               Evaluasi Keputusan Rute Komputasi
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │          Edge Brain Scheduler (Raspberry Pi 5 16GB)    │
   │               IP: 10.1.1.57 | Port: 8500               │
   │      - FastAPI Scheduler Agent                         │
   │      - Dynamic Model XGBoost + Rule-Based Fallback     │
   └───────────────────────────┬────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          ▼                                         ▼
   Keputusan: 0 (Proses di Edge)             Keputusan: 1 (Migrasi ke Cloud)
   Inferensi Lokal: LBPH Face                Offload ke Cloud GPU
                                                    │
                                                    ▼
   ┌────────────────────────────────────────────────────────┐
   │          Cloud GPU Node (Ubuntu 24.04 x86_64)          │
   │               IP: 10.1.1.186 | Tailscale: 100.76.68.93 │
   │      - NVIDIA RTX 3050 6GB CUDA 13.2                   │
   │      - FastAPI Cloud Face Agent (Port 9000)            │
   │      - OpenCV YuNet + InceptionResnetV1 (VGGFace2)     │
   │      - Database PostgreSQL (mas_decision_history)      │
   │      - Decision Observatory Web UI (NodePort 30080)    │
   └────────────────────────────────────────────────────────┘
```

---

## 2. Struktur Direktori Proyek

```
penlok/
├── README.md                      # Dokumentasi utama proyek
├── AGENTS.md                      # Panduan & konteks otomatis untuk AI Agent
├── .gitignore                     # Filter file repositori git
├── .dockerignore                  # Filter konteks build docker
│
├── edge_package/                  # [Node 1] Device Edge (Raspberry Pi 5 @ 10.1.1.224)
│   ├── edge_mas_controller.py     # Kontroller MAS utama (Keypad, LCD, Relay, Sensor)
│   ├── decision_syncer.py         # Buffer SQLite & background syncer ke Cloud
│   ├── servo_config.json          # Parameter sudut & durasi pulsa servo continuous
│   ├── Dockerfile.edge-hardware-daemon
│   ├── docker-compose.yml
│   ├── deploy_edge.sh             # Skrip deploy otomatis langsung ke Edge
│   └── .env.example
│
├── scheduler_package/             # [Node 2] Edge Brain (Raspberry Pi 5 @ 10.1.1.57)
│   ├── main.py                    # Layanan FastAPI Scheduler Agent (Port 8500)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── cloud_package/                 # [Node 3] Cloud GPU Node (RTX 3050 CUDA @ 10.1.1.186)
│   ├── main.py                    # Layanan FastAPI Cloud Agent (Port 9000)
│   ├── setup_decision_db.py       # Inisialisasi basis data mas_decision_history
│   ├── rebuild_gallery_yunet.py   # Ekstraksi embedding 512-d galeri wajah
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── smartbox_web_v2/               # Frontend Decision Observatory (React + Vite + Tailwind)
│   ├── src/                       # Komponen UI (KPI, Timeline, Tabel Log MAS, Modal)
│   ├── nginx.conf                 # Konfigurasi reverse proxy & cache Nginx
│   ├── Dockerfile
│   └── package.json
│
├── tools/                         # Utilitas Diagnostik & Kalibrasi Fisik Lemari
│   ├── check_camera.py            # Uji webcam YuNet & live HTTP MJPEG stream (Port 8088)
│   ├── test_all_solenoids.py      # Pengujian fisik 4 relay solenoid dan buzzer
│   ├── tweak_servo.py             # Kalibrasi interaktif continuous servo trapdoor
│   └── register_face.py           # Pendaftaran wajah baru dari webcam
│
├── benchmarks/                    # Evaluasi Beban Komputasi & Laporan Riset
│   ├── benchmark_comparison.py    # Uji komparasi head-to-head XGBoost vs Rule-Based
│   ├── benchmark_concurrent_real.py # Uji beban konkurensi foto wajah nyata
│   ├── BENCHMARK_COMPARISON_XGB_VS_RULE.md  # Laporan komprehensif benchmark
│   └── BENCHMARK_COMPARISON_XGB_VS_RULE.pdf # Laporan siap cetak publikasi
│
├── tests/                         # Pengujian Integrasi & API Endpoints
│   ├── test_cloud_api.py
│   ├── test_edge_integration.py
│   └── test_query_decision.py
│
├── data/                          # Riwayat Log Latensi & Dataset Evaluasi
│   ├── migration_latency_log.csv
│   └── scenario_comparison.csv
│
├── docs/                          # Dokumentasi Spesifikasi & Laporan
│   ├── specifications/            # PRD, PRD Web, Desain UI, Integrasi Arsitektur
│   ├── journals/                  # Catatan jurnal teknis pengembangan
│   ├── reports/                   # Laporan progres berkala (WIB timezone sync, MAS)
│   └── cloud_eval/                # Bukti pengujian HPA & metrik Prometheus cloud
│
└── legacy/                        # Arsip Kode Historis & Versi Sebelumnya
    ├── smartbox_web/              # Web Laravel lama (sudah digantikan smartbox_web_v2)
    ├── cloud_versions/            # Iterasi awal kode cloud agent
    ├── old_edge/                  # Skrip edge lama sebelum modulasi edge_package
    └── progres_archive/           # Laporan dan proposal awal
```

---

## 3. Cara Membuka Web Decision Observatory

Web Decision Observatory menampilkan status node Edge, Scheduler, Cloud GPU, metrik waktu nyata, dan seluruh log riwayat keputusan MAS berzona waktu **WIB**:

- **Melalui Jaringan Lokal (LAN / WiFi Lab):**  
  👉 **`http://10.1.1.186:30080`**
- **Melalui Jaringan Jarak Jauh (VPN Tailscale):**  
  👉 **`http://100.76.68.93:30080`**

---

## 4. Pengujian & Kalibrasi Hardware Fisik

Seluruh utilitas pengujian fisik berada di direktori `tools/`:

```bash
# 1. Cek & uji semua 4 solenoid/kunci loker bergantian
python3 tools/test_all_solenoids.py A

# 2. Kalibrasi posisi buka/tutup servo trapdoor (MG996R)
python3 tools/tweak_servo.py

# 3. Ambil foto snapshot & uji deteksi wajah YuNet + Cloud GPU
python3 tools/check_camera.py

# 4. Buka live video streaming webcam lemari di browser
python3 tools/check_camera.py --stream
# Buka di browser: http://10.1.1.224:8088/
```

---

## 5. Deployment Node Edge (Raspberry Pi 5)

Sinkronisasi kode, berkas konfigurasi servo, dan deployment container ke Pi Edge dilakukan dengan satu perintah:

```bash
./edge_package/deploy_edge.sh
```

Skrip secara otomatis:
1. Mendeteksi jalur koneksi terbaik (Langsung `10.1.1.224:2523` atau lewat Jump Host Tailscale).
2. Mengirim modul `edge_mas_controller.py`, `decision_syncer.py`, dan `servo_config.json`.
3. Membangun dan merestart kontainer `edge-hardware-daemon` di Raspberry Pi.
4. Memvalidasi kesehatan sensor ultrasonik dan telemetry.
