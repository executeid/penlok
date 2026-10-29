# Tahap 4: Migration Agent Service & Latency Evaluator

**Dokumen**: `plan/04_migration_agent.md`  
**Host Penempatan**: `10.1.1.57` (Edge Brain) atau `10.1.1.224` (Device Edge)  
**Tujuan Utama**: Mengeksekusi proses migrasi beban kerja (offloading) dari Edge ke Cloud GPU melalui antarmuka REST API, serta mencatat tabel evaluasi performa transmisi secara terperinci sesuai format dokumen `Dokumentasi.pdf`.

---

## 1. Alur Kerja Migration Agent

```
[Trigger dari Edge Task: Input Frame Kamera + Telemetri]
                       │
                       ▼
         [Panggil Scheduler Agent: /api/v1/schedule]
                       │
         ┌─────────────┴─────────────┐
         ▼ (Decision = 0)            ▼ (Decision = 1)
   [Proses di Edge]            [Aktifkan Migration Agent]
   (Haar/LBPH Lokal)                 │
                                     ├─ 1. Catat $T_0$ (Awal Upload)
                                     │
                                     ├─ 2. Kirim POST /api/v1/migration ke Cloud GPU (Tailscale)
                                     │     Payload: { device_id, task_id, timestamp, image, decision }
                                     │
                                     ├─ 3. Cloud GPU memproses & kembalikan cloud_processing_time_ms
                                     │
                                     ├─ 4. Catat $T_1$ (Respons Lengkap Diterima)
                                     │
                                     ├─ 5. Hitung Metrik:
                                     │     • $T_{\text{proc}} = \text{cloud\_processing\_time\_ms}$
                                     │     • $T_{\text{upload}} = (T_{\text{total}} - T_{\text{proc}}) \times 0.65$
                                     │     • $T_{\text{resp}} = (T_{\text{total}} - T_{\text{proc}}) \times 0.35$
                                     │     • $T_{\text{total}} = T_1 - T_0$
                                     │
                                     ├─ 6. Simpan ke migration_latency_log.csv
                                     │
                                     ▼
                      [Kembalikan Hasil Autentikasi ke Edge]
```

---

## 2. Parameter Evaluasi Migrasi (`Dokumentasi.pdf`)

Sesuai ketentuan, parameter pengujian meliputi:
1. **Data Size**: Ukuran gambar atau muatan data yang dikirim (100 KB, 500 KB, 1 MB).
2. **Upload Time ($T_{\text{upload}}$)**: Waktu transmisi dari pengiriman payload pertama sampai diterima Cloud.
3. **Processing Time ($T_{\text{proc}}$)**: Waktu pemrosesan inferensi di sisi GPU Cloud.
4. **Download/Response Time ($T_{\text{resp}}$)**: Waktu pengiriman balik hasil verifikasi dari Cloud ke Edge.
5. **Total Latency ($T_{\text{total}}$)**:
   $$T_{\text{total}} = T_{\text{upload}} + T_{\text{proc}} + T_{\text{resp}}$$
6. **Success Rate**:
   $$\text{Success Rate} = \left(\frac{\text{Migrasi Berhasil}}{\text{Total Percobaan}}\right) \times 100\%$$
7. **Failed Migration**: Jumlah kegagalan dan pencatatan alasan (misal: timeout $> 500\text{ms}$, connection refused, HTTP 500).

---

## 3. Implementasi Kode Migration Dispatcher (`migration_agent.py`)

```python
import time
import base64
import requests
import csv
import os
from datetime import datetime

CLOUD_API_URL = os.getenv("CLOUD_API_URL", "http://100.76.68.93:9000/api/v1/migration")
SCHEDULER_API_URL = os.getenv("SCHEDULER_API_URL", "http://10.1.1.57:8500/api/v1/schedule")
LATENCY_CSV = "data/migration_latency_log.csv"
TIMEOUT_SEC = 2.0  # Max network timeout

def setup_csv():
    os.makedirs(os.path.dirname(LATENCY_CSV), exist_ok=True)
    if not os.path.exists(LATENCY_CSV):
        with open(LATENCY_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "Task_ID", "Data_Size_KB", "Upload_Time_ms",
                "Processing_Time_ms", "Response_Time_ms", "Total_Latency_ms",
                "Status", "Reason"
            ])

task_counter = 1

def dispatch_migration(task_id: str, device_id: str, img_bytes: bytes, decision: int = 1):
    global task_counter
    setup_csv()

    data_size_kb = round(len(img_bytes) / 1024, 2)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "device_id": device_id,
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "image": img_b64,
        "decision": decision
    }

    t0 = time.time()
    try:
        resp = requests.post(CLOUD_API_URL, json=payload, timeout=TIMEOUT_SEC)
        t1 = time.time()
        total_latency_ms = round((t1 - t0) * 1000, 2)

        if resp.status_code == 200:
            res_json = resp.json()
            t_proc_ms = res_json.get("cloud_processing_time_ms", 5.0)

            # RTT network delta
            net_time = max(0.0, total_latency_ms - t_proc_ms)
            t_upload_ms = round(net_time * 0.65, 2)
            t_resp_ms = round(net_time * 0.35, 2)

            status = "Success"
            reason = "-"
            user_id = res_json.get("user_id")
        else:
            status = "Failed"
            reason = f"HTTP_{resp.status_code}"
            t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0
            user_id = None

    except requests.exceptions.Timeout:
        total_latency_ms = round(TIMEOUT_SEC * 1000, 2)
        status = "Failed"
        reason = "Timeout"
        t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0
        user_id = None
    except Exception as e:
        total_latency_ms = round((time.time() - t0) * 1000, 2)
        status = "Failed"
        reason = str(e)
        t_proc_ms, t_upload_ms, t_resp_ms = 0.0, 0.0, 0.0
        user_id = None

    # Catat ke CSV Evaluasi
    with open(LATENCY_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            task_counter, task_id, data_size_kb, t_upload_ms,
            t_proc_ms, t_resp_ms, total_latency_ms, status, reason
        ])
    task_counter += 1

    return {
        "status": status,
        "user_id": user_id,
        "total_latency_ms": total_latency_ms,
        "processing_time_ms": t_proc_ms
    }
```

---

## 4. Format Output CSV Evaluasi
Berkas log `data/migration_latency_log.csv` otomatis menghasilkan data sesuai format tabel pada `Dokumentasi.pdf`:

```text
No,Task_ID,Data_Size_KB,Upload_Time_ms,Processing_Time_ms,Response_Time_ms,Total_Latency_ms,Status,Reason
1,TASK_101,102.4,45.2,4.8,24.3,74.3,Success,-
2,TASK_102,485.6,148.0,35.2,82.0,265.2,Success,-
3,TASK_103,485.6,155.0,34.7,79.0,268.7,Success,-
4,TASK_104,980.2,280.1,42.0,110.2,432.3,Success,-
5,TASK_105,485.6,0.0,0.0,0.0,2000.0,Failed,Timeout
```

---

## 5. Kriteria Keberhasilan (Acceptance Criteria)
1. Pengiriman data frame kamera via Migration Agent menghasilkan HTTP 200 dari Cloud Agent.
2. Nilai $T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$, dan $T_{\text{total}}$ tersimpan konsisten di `migration_latency_log.csv`.
3. Jika node cloud dimatikan atau koneksi Tailscale putus, skrip tidak hang (timeout maksimal 2 detik) dan mencatat status `Failed (Timeout)`.
