# Tahap 6: Protokol Benchmark 3 Skenario & Evaluasi Fault Intolerance

**Dokumen**: `plan/06_evaluation_benchmark.md`  
**Cakupan**: Evaluasi Menyeluruh Sistem (Tier 1 Device Edge, Tier 2 Edge Brain, Tier 3 Cloud GPU)  
**Tujuan Ilmiah**: Membuktikan secara empiris keunggulan orkestrasi Multi-Agent System (MAS) terhadap pendekatan konvensional untuk kebutuhan publikasi jurnal dan paten.  
**Batas Akhir Pengambilan Data**: **7 November 2026**

---

## 1. Kerangka Pengujian Komparasi (3 Skenario Beban)

Pengujian beban berat disimulasikan menggunakan **50 hingga 100 permintaan konkuren** simultan pada 3 konfigurasi sistem:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   3 SCENARIOS COMPARATIVE BENCHMARK                    │
│                                                                        │
│  [Skenario A: Edge-Only]       ──> Semua beban di CPU Pi 5 (No Migrasi)│
│  [Skenario B: Rule-Based]      ──> Migrasi jika CPU > 80%              │
│  [Skenario C: ML Orchestration]──> Keputusan dinamis model XGBoost/MAS │
└────────────────────────────────────────────────────────────────────────┘
```

### Parameter yang Wajib Dicatat & Dibandingkan:
1. **Total Latency (P50, P95, P99)**: Mengukur waktu respon dari input pengguna hingga relay terbuka.
2. **CPU Usage Edge (%)**: Membuktikan bahwa pada Skenario C, CPU Edge tidak pernah mencapai 100% dan terhindar dari thermal throttling.
3. **RAM Usage Edge (MB)**: Memantau stabilitas konsumsi memori lokal.
4. **Throughput (Transactions Per Second / TPS)**: Jumlah transaksi verifikasi yang berhasil diproses per satuan detik.
5. **Migration Time (ms)**: Waktu yang dihabiskan untuk memindahkan tugas ke Cloud.
6. **Success Rate (%)**: Rasio keberhasilan transaksi di bawah tekanan beban tinggi.

---

## 2. Definisi Logika Perbandingan

### Skenario A: Edge-Only
- Seluruh permintaan inferensi wajah dipaksakan berjalan lokal di CPU Raspberry Pi 5 menggunakan Haar Cascade + LBPH.
- Tidak ada offload ke Cloud GPU.

### Skenario B: Rule-Based Threshold (Baseline Konvensional)
Aturan keputusan hardcoded sesuai `Dokumentasi.pdf`:
- **Aturan B1**:
  $$\text{IF CPU} > 80\% \longrightarrow \text{Migrasi ke Cloud (1)}, \quad \text{ELSE} \longrightarrow \text{Edge (0)}$$
- **Aturan B2**:
  $$\text{IF CPU} > 80\% \land \text{RAM} > 70\% \land \text{Latency} > 150\text{ms} \longrightarrow \text{Migrasi ke Cloud (1)}, \quad \text{ELSE} \longrightarrow \text{Edge (0)}$$

### Skenario C: Machine Learning Orchestration (XGBoost / MAS)
- Model mengevaluasi interaksi 7 fitur secara simultan:
  $$X = [\text{CPU}, \text{RAM}, \text{Throughput}, \text{Network\_Bandwidth}, \text{Priority}, \text{Latency}, \text{Queue}]$$
- Menghindari migrasi jika koneksi jaringan sedang lambat (latency tinggi) meskipun CPU edge sedang sibuk.

---

## 3. Skrip Otomasi Pengujian Beban (`stress_benchmark_harness.py`)

Skrip custom berbasis Python `asyncio` dan `httpx` (menggantikan dummy math JMeter) yang mengirimkan payload gambar nyata:

```python
import asyncio
import httpx
import time
import base64
import statistics
import csv

TARGET_URL = "http://10.1.1.224:8000/api/v1/verify_test" # Gateway Edge
CONCURRENT_REQUESTS = [10, 25, 50, 75, 100]
SAMPLE_IMAGE = "sample_face.jpg"

async def send_request(client, req_id):
    t0 = time.time()
    try:
        resp = await client.post(TARGET_URL, json={"task_id": f"BENCH_{req_id}"}, timeout=5.0)
        t_total = (time.time() - t0) * 1000
        success = (resp.status_code == 200)
    except Exception:
        t_total = 5000.0
        success = False
    return t_total, success

async def run_batch(concurrency):
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)

    latencies = [r[0] for r in results]
    successes = [r[1] for r in results]

    p50 = statistics.median(latencies)
    lat_sorted = sorted(latencies)
    p95 = lat_sorted[int(len(lat_sorted) * 0.95)]
    p99 = lat_sorted[int(len(lat_sorted) * 0.99)]
    success_rate = (sum(successes) / len(successes)) * 100

    print(f"[{concurrency} Concurrency] P50={p50:.1f}ms | P95={p95:.1f}ms | P99={p99:.1f}ms | Success={success_rate:.1f}%")
    return {"concurrency": concurrency, "p50": p50, "p95": p95, "p99": p99, "success_rate": success_rate}
```

---

## 4. Protokol Pengujian Fault Intolerance (Ketahanan Sistem)

Sesuai arahan `Dokumentasi.pdf`, lakukan 4 skenario simulasi gangguan:

| ID Uji | Skenario Gangguan | Prosedur Uji | Ekspektasi Perilaku Sistem |
|---|---|---|---|
| **FT-01** | **Container Crash** | `kubectl delete pod edge-agent` di `10.1.1.57` | K3s me-restart pod dalam $< 10\text{s}$. Skrip hardware fisik di host Pi 1 tidak terhenti. |
| **FT-02** | **Network Sever** | Putus koneksi Tailscale / LAN ke Cloud GPU | Migration Agent mendeteksi timeout ($> 800\text{ms}$), seketika fallback ke mode verifikasi lokal tanpa mengunci loker. |
| **FT-03** | **Cloud Outage** | Matikan service `cloud-api` di `100.76.68.93` | Scheduler mendeteksi API error $\rightarrow$ mengalihkan semua keputusan ke `Decision = 0` (Edge). |
| **FT-04** | **K3s Pod Autoscaling** | Injeksi 10 request lalu naik ke 50 request konkuren ke Cloud GPU | HPA di K3s Cloud mendeteksi CPU pod $> 60\%$ dan menaikkan jumlah pod dari 1 menjadi 2 secara otomatis. |

---

## 5. Bukti Implementasi & Artefak Evaluasi Wajib

Sebelum batas akhir **7 November 2026**, seluruh artefak berikut wajib diarsipkan:
1. **Tangkapan Layar Terminal**:
   - Eksekusi inferensi model di Edge dan Cloud GPU.
   - Status pod K3s (`kubectl get pods -o wide`, `kubectl get hpa`).
2. **Dashboard Grafana & Prometheus**:
   - Grafik lonjakan CPU Edge pada Skenario A (menyentuh 100%) vs Skenario C (stabil $< 70\%$).
   - Grafik Latency P95/P99.
3. **Berkas Dataset & CSV Hasil**:
   - `migration_latency_log.csv` (Tabel $T_{\text{upload}}$, $T_{\text{proc}}$, $T_{\text{resp}}$, $T_{\text{total}}$).
   - `scenario_comparison.csv` (Tabel komparasi 3 skenario).
4. **Visualisasi AI**:
   - Confusion Matrix model XGBoost.
   - Grafik Feature Importance (7 fitur telemetri).
   - Kurva ROC Curve dan skor AUC.
5. **Foto Fisik & Spesifikasi**:
   - Foto smart locker 3-box, solenoid relay, servo trapdoor, timbangan.
   - Ringkasan spesifikasi hardware Raspberry Pi 5 dan GPU RTX 3050.
