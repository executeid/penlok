# Master Implementation Roadmap: Penlok Multi-Agent System (No-MQTT Architecture)

**Tanggal Dibuat**: 27 September 2026  
**Referensi Standar**:
- `Penlok 2026.pdf` (Blueprint Multi-Agent System)
- `Dokumentasi.pdf` (Standarisasi API, Parameter Evaluasi, & Checklist Pengujian)
- `PRD.md` & `integration_plan.md`

**Target Selesai Data Evaluasi**: **7 November 2026**

---

## 1. Prinsip Utama & Keputusan Arsitektur
1. **Zero MQTT (HTTP REST Murni)**:
   - Menghapus ketergantungan pada broker Mosquitto.
   - Komunikasi antar agen menggunakan HTTP REST / JSON / Binary streaming yang deterministik, mudah dimonitor, dan stateless.
2. **Modular & Loose Coupling**:
   - Tiap agen memiliki kontrak API mandiri.
   - Scheduler Agent sementara menggunakan logika Rule-Based baseline sambil menunggu model XGBoost final dari tim ML.
3. **Standarisasi Keputusan**:
   - `Decision = 0`: **PROSES DI EDGE** (Eksekusi lokal di Raspberry Pi).
   - `Decision = 1`: **MIGRASI KE CLOUD** (Eksekusi berat di GPU PC via Tailscale).

---

## 2. Struktur Dokumen Rencana Kerja (`plan/`)

| Berkas | Judul Tahapan | Node Target | Status |
|---|---|---|:---:|
| [`01_cleanup_mqtt.md`](./01_cleanup_mqtt.md) | **Tahap 1: Pembersihan Dependensi MQTT** | `10.1.1.57` & `10.1.1.224` | Ready |
| [`02_cloud_gpu_agent.md`](./02_cloud_gpu_agent.md) | **Tahap 2: Cloud GPU Face Recognition Agent** | `100.76.68.93` (GPU PC) | Ready |
| [`03_scheduler_agent.md`](./03_scheduler_agent.md) | **Tahap 3: Scheduler Agent (Rule-Based & XGBoost Slot)** | `10.1.1.57` (Edge Brain) | Ready |
| [`04_migration_agent.md`](./04_migration_agent.md) | **Tahap 4: Migration Agent & Latency Evaluator** | `10.1.1.57` / `10.1.1.224` | Ready |
| [`05_edge_integration.md`](./05_edge_integration.md) | **Tahap 5: Integrasi Device Edge & Actuator Hardware** | `10.1.1.224` (Device Edge) | Ready |
| [`06_evaluation_benchmark.md`](./06_evaluation_benchmark.md) | **Tahap 6: Protokol Benchmark 3 Skenario & Fault Tolerance** | Seluruh Node | Ready |

---

## 3. Matriks Aliran Data (Data Flow Matrix)

```
[Kamera / Button di Edge 10.1.1.224]
              │
              ▼ (1. Baca Metrik Sistem: CPU, RAM, Latency, Queue)
[Scheduler Agent di 10.1.1.57: POST /api/v1/schedule]
              │
              ├─ Output = 0 (Tetap di Edge) ──> Eksekusi Haar/LBPH Lokal Pi ──> Buka Relay
              │
              └─ Output = 1 (Migrasi ke Cloud)
                        │
                        ▼ (2. Kirim Frame: POST /api/v1/migration via Tailscale)
     [Cloud GPU Agent di 100.76.68.93:9000]
                        │
                        ├─ Eksekusi CUDA Face Embedding Matching (< 5ms)
                        ├─ Catat Log Transaksi ke Database PostgreSQL
                        │
                        ▼ (3. Balas Hasil: status=success, user_id=X)
     [Migration Agent di Edge]
                        │
                        ├─ Catat Latensi (Upload, Processing, Response, Total)
                        ▼ (4. Triger Solenoid)
     [Relay Hardware 10.1.1.224 BCM 9 / BCM 10 / BCM 6]
```
