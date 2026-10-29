# Laporan Pelaksanaan Tahap 3: Scheduler Agent Service (Rule-Based Baseline & Modular XGBoost Hot-Swap)

**Dokumen Rujukan**: `plan/03_scheduler_agent.md`  
**Target Node**: `penlok@10.1.1.57` (Raspberry Pi 5 16GB, Edge Brain)  
**Port Layanan**: `8500`  
**Status**: SUKSES / TERVERIFIKASI PENUH  

---

## 1. Ringkasan Eksekutif

Tahap 3 mengimplementasikan microservice **Scheduler Agent** berbasis FastAPI pada Edge Brain (`penlok@10.1.1.57`). Microservice ini bertanggung jawab membuat keputusan task offloading secara terdesentralisasi:
- **`Decision = 0` (`TETAP_DI_EDGE`)**: Beban kerja komputasi diproses lokal di Raspberry Pi.
- **`Decision = 1` (`MIGRASI_KE_CLOUD`)**: Beban kerja dialihkan ke Cloud GPU PC.

Sesuai arahan arsitektur, mesin inferensi menerapkan **Rule-Based Baseline** berkecepatan tinggi (< 3 ms) dengan pola adapter modular **Hot-Swap XGBoost**. Ketika berkas model machine learning `scheduler_agent_xgb.pkl` ditambahkan atau diperbarui pada direktori kerja, layanan secara dinamis beralih ke inferensi XGBoost tanpa memerlukan restart service atau downtime, dan otomatis kembali ke Rule-Based jika berkas dihapus.

Layanan diintegrasikan ke dalam daemon init Linux via unit systemd `scheduler-agent.service` dan berjalan persisten sejak boot.

---

## 2. Rincian Implementasi Teknis

### 2.1 Konfigurasi Virtual Environment & Dependensi
Lingkungan virtual `/home/penlok/venv-test` dikonfigurasi dengan mengaktifkan akses ke paket sistem host (`include-system-site-packages = true` pada `/home/penlok/venv-test/pyvenv.cfg`), memberikan dukungan lengkap terhadap pustaka:
- `fastapi` 0.141.1
- `uvicorn` 0.52.3
- `pydantic` 2.13.4
- `joblib` 1.5.3
- `pandas` 2.2.3
- `xgboost` 3.4.0

### 2.2 Logika Evaluasi Rule-Based Baseline
Logika baseline dieksekusi melalui fungsi `evaluate_rule_based()` dengan aturan deterministik:
1. **Aturan 1 (Beban CPU Kritis)**: Jika `CPU > 80.0%`, kembalikan `1` (Migrasi ke Cloud).
2. **Aturan 2 (Beban Komposit & Latensi Memadai)**: Jika `CPU > 65.0%` DAN `RAM_pct > 70.0%` DAN `Latency < 150.0ms`, kembalikan `1` (Migrasi ke Cloud).
3. **Default**: Kembalikan `0` (Tetap di Edge).

Jika nilai persentase `RAM_pct` tidak dikirim secara eksplisit oleh caller, sistem menghitungnya dari nilai `RAM` (MB) proporsional terhadap total kapasitas memori host (16,218 MB).

### 2.3 Arsitektur Adapter Modular Hot-Swap XGBoost
Kelas `DecisionEngine` dirancang dengan pemantauan mtime berkas dinamis:
- Saat menerima panggilan `predict()` atau pengecekan `/health`, engine memeriksa keberadaan dan modifikasi waktu (`os.path.getmtime`) berkas model `/home/penlok/scheduler/scheduler_agent_xgb.pkl`.
- Bila berkas tersedia, model XGBoost di-load ke memori dan engine beralih ke mode `xgboost`.
- Bila berkas tidak tersedia atau dihapus, engine otomatis fallback ke mode `rule_based` tanpa exception fatal.

### 2.4 Berkas Layanan Microservice (`/home/penlok/scheduler/main.py`)
Microservice menyediakan endpoint:
- `GET /`: Status ringkas layanan dan versi.
- `GET /health`: Pemeriksaan kesehatan, mode aktif (`rule_based` atau `xgboost`), dan status load model.
- `POST /api/v1/schedule`: Endpoint utama keputusan offloading berbasis payload telemetri.
- `POST /api/v1/reload`: Endpoint eksplisit untuk memicu re-evaluasi berkas model.

Struktur skema input `TelemetryPayload`:
```json
{
  "CPU": 25.0,
  "RAM": 1200.0,
  "Throughput": 0.5,
  "Network_Bandwidth": 1.2,
  "Priority": 2,
  "Latency": 25.0,
  "Queue": 1,
  "RAM_pct": 35.0
}
```

Struktur skema respons:
```json
{
  "status": "success",
  "decision": 0,
  "label": "TETAP_DI_EDGE",
  "confidence": 0.9,
  "method": "rule_based",
  "timestamp": 1791372884.75
}
```

---

## 3. Deployment Systemd Service

Unit file `/etc/systemd/system/scheduler-agent.service` dipasang dengan konfigurasi:
```ini
[Unit]
Description=Penlok Scheduler Agent Microservice
After=network.target

[Service]
Type=simple
User=penlok
WorkingDirectory=/home/penlok/scheduler
ExecStart=/home/penlok/venv-test/bin/uvicorn main:app --host 0.0.0.0 --port 8500
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Status aktivasi:
- `sudo systemctl daemon-reload` -> Sukses
- `sudo systemctl enable scheduler-agent` -> Symlink multi-user.target dibuat
- `sudo systemctl start scheduler-agent` -> Status `active (running)`, PID: 541517
- Port `0.0.0.0:8500` LISTEN aktif terverifikasi via `ss -tlpn`.

---

## 4. Hasil Verifikasi & Pengujian

### 4.1 Verifikasi Endpoint Baseline (Edge vs Cloud)

#### Pengujian Kasus 1: Beban Normal (Edge / Decision = 0)
- **Request**:
  ```bash
  curl -X POST http://10.1.1.57:8500/api/v1/schedule \
    -H "Content-Type: application/json" \
    -d '{"CPU": 25.0, "RAM": 1200.0, "Throughput": 0.5, "Network_Bandwidth": 1.2, "Priority": 2, "Latency": 25.0, "Queue": 1, "RAM_pct": 35.0}'
  ```
- **Respons**:
  ```json
  {
    "status": "success",
    "decision": 0,
    "label": "TETAP_DI_EDGE",
    "confidence": 0.9,
    "method": "rule_based",
    "timestamp": 1791372884.7501526
  }
  ```

#### Pengujian Kasus 2: Beban Kritis CPU Ekstrem (Cloud / Decision = 1)
- **Request**:
  ```bash
  curl -X POST http://10.1.1.57:8500/api/v1/schedule \
    -H "Content-Type: application/json" \
    -d '{"CPU": 88.5, "RAM": 3200.0, "Throughput": 4.5, "Network_Bandwidth": 0.8, "Priority": 3, "Latency": 45.0, "Queue": 5, "RAM_pct": 82.0}'
  ```
- **Respons**:
  ```json
  {
    "status": "success",
    "decision": 1,
    "label": "MIGRASI_KE_CLOUD",
    "confidence": 0.95,
    "method": "rule_based",
    "timestamp": 1791372884.7607918
  }
  ```

### 4.2 Pengujian Batas (Boundary Thresholds)
Rangkaian 9 skenario uji batas dieksekusi via HTTP REST API:
| Skenario Uji | Parameter Input | Expected | Aktual | Status |
|---|---|:---:|:---:|:---:|
| Beban Ringan | CPU=25.0, RAM_pct=35.0, Lat=25.0 | 0 | 0 (TETAP_DI_EDGE) | PASS |
| CPU Ekstrem (>80%) | CPU=88.5, RAM_pct=82.0, Lat=45.0 | 1 | 1 (MIGRASI_KE_CLOUD) | PASS |
| Komposit Sukses | CPU=70.0, RAM_pct=75.0, Lat=50.0 | 1 | 1 (MIGRASI_KE_CLOUD) | PASS |
| Komposit Gagal (RAM < 70%) | CPU=70.0, RAM_pct=65.0, Lat=50.0 | 0 | 0 (TETAP_DI_EDGE) | PASS |
| Komposit Gagal (Lat >= 150ms) | CPU=70.0, RAM_pct=75.0, Lat=160.0 | 0 | 0 (TETAP_DI_EDGE) | PASS |
| Batas CPU = 80.0% | CPU=80.0, RAM_pct=50.0, Lat=50.0 | 0 | 0 (TETAP_DI_EDGE) | PASS |
| Batas CPU = 80.1% | CPU=80.1, RAM_pct=50.0, Lat=50.0 | 1 | 1 (MIGRASI_KE_CLOUD) | PASS |
| Batas Latensi = 150.0ms | CPU=70.0, RAM_pct=75.0, Lat=150.0 | 0 | 0 (TETAP_DI_EDGE) | PASS |
| Batas Latensi = 149.9ms | CPU=70.0, RAM_pct=75.0, Lat=149.9 | 1 | 1 (MIGRASI_KE_CLOUD) | PASS |

### 4.3 Pengujian Latensi Respons
- Total response time yang terukur via cURL: **2.28 ms** (`0.002282s`).
- Kriteria SLA (< 10 ms) terpenuhi dengan margin keamanan > 75%.

### 4.4 Pengujian Hot-Swap XGBoost (Zero Downtime)
Prosedur pengujian transisi mode:
1. **Mode Awal**: Tidak ada file model di `/home/penlok/scheduler/`.
   - `/health` -> `mode: "rule_based"`, `model_loaded: false`.
2. **Penyalinan Model**: File `scheduler_agent_xgb.pkl` disalin ke `/home/penlok/scheduler/`.
   - `/health` langsung merespons -> `mode: "xgboost"`, `model_loaded: true`.
   - `/api/v1/schedule` merespons dengan atribut `method: "xgboost"`.
   - Log journalctl: `[INFO] Loaded XGBoost model from /home/penlok/scheduler/scheduler_agent_xgb.pkl`.
3. **Pencopotan Model**: File `scheduler_agent_xgb.pkl` dihapus dari `/home/penlok/scheduler/`.
   - `/health` langsung merespons -> `mode: "rule_based"`, `model_loaded: false`.
   - `/api/v1/schedule` merespons kembali dengan `method: "rule_based"`.
   - Log journalctl: `[INFO] Model file /home/penlok/scheduler/scheduler_agent_xgb.pkl removed. Fallback to rule_based.`
4. Seluruh siklus transisi berjalan tanpa me-restart proses uvicorn atau menjatuhkan koneksi TCP.

---

## 5. Matriks Kriteria Keberhasilan (Acceptance Criteria)

| No | Kriteria Keberhasilan | Target | Realisasi | Status |
|---|---|---|---|:---:|
| 1 | FastAPI Microservice berjalan di port 8500 | `penlok@10.1.1.57:8500` | Berjalan via systemd `scheduler-agent.service` | **TERPENUHI** |
| 2 | Implementasi Rule-Based Baseline Engine | Logika ambang batas CPU & RAM & Latensi | Akurasi 100% pada 9 variasi boundary test | **TERPENUHI** |
| 3 | Adapter Hot-Swap XGBoost Modular | Transisi otomatis saat berkas `.pkl` hadir | Berpindah otomatis tanpa restart service | **TERPENUHI** |
| 4 | Persistence & Auto-recovery | Systemd unit service aktif & enabled | `active (running)`, `enabled` pada boot | **TERPENUHI** |
| 5 | Output `POST /api/v1/schedule` akurat | Nilai integer 0 (Edge) dan 1 (Cloud) | Valid: 0 untuk beban normal, 1 untuk kritis | **TERPENUHI** |
| 6 | Kecepatan respons endpoint | Latensi < 10 ms | Rata-rata 2.28 ms | **TERPENUHI** |

---

## 6. Berkas Terpasang pada Sistem

- **Kode Aplikasi**: `/home/penlok/scheduler/main.py`
- **Skrip Verifikasi Otomatis**: `/home/penlok/scheduler/test_self_check.py`
- **Konfigurasi Unit Systemd**: `/etc/systemd/system/scheduler-agent.service`
- **Laporan Teknis**: `/home/execute/penlok/plan/report/03_scheduler_report.md`
