# Evidence cloud — 29 Oktober 2026

Semua data berasal dari pengujian cloud pada host `pengmas-tri`. Tidak ada
foto, embedding, password database, atau token diekspor di direktori ini.

| Berkas | Asal / arti |
|---|---|
| `CLOUD_20261029T044248.*` | Uji fungsi dan burst v1; sebelum kegagalan OOM sustained-load. |
| `initial-load-failure.json` | Catatan observasi OOM v1 dari terminal. Ini catatan manual, bukan output generator beban yang terputus. |
| `CLOUD_20261029T045023.json` | Respons HTTP asli uji fungsi v2, termasuk kasus negatif dan ringkasan burst. |
| `CLOUD_20261029T045023_burst.csv` | 60 request burst v2: satu baris per request; RTT client, waktu inference, antrean, audit. |
| `CLOUD_20261029T045023_metrics.prom` | Scrape `/metrics` setelah uji burst v2, sebelum recovery. Counter bersifat per proses/pod. |
| `cloud-api-hpa.json` | 25 snapshot HPA/deployment; 247 respons sukses; bukti scaling 1 → 2 → 1. |
| `cloud-api-recovery.json` | UID sebelum/sesudah penghapusan pod v2 dan waktu observasi kesiapan kembali. |
| `cloud-final-state.json` | Snapshot cluster, GPU, disk, layanan lama, hash source, dan hasil query PostgreSQL. Tidak memuat isi Kubernetes Secret. |
| `unit-tests.txt` | Output 10 unit test dari container runtime dengan network dinonaktifkan. |

Uji v2 memakai kembali empat foto enrollment. Hasil ini tidak dapat dipakai
untuk mengklaim akurasi biometrik, FAR/FRR atau generalisasi ke foto baru.
RTT diukur dari host cloud, bukan edge. Tujuan pengujian adalah memverifikasi
implementasi cloud, audit database, validasi input, recovery dan HPA.

Run smoke/burst v2 menghasilkan 69 record DB: 66 success, 1 unauthorized,
2 error yang disengaja. Request schema invalid HTTP 422 ditolak sebelum
handler dan tidak membuat audit row. Run HPA menghasilkan 247 success.
Nilai total database 491 pada snapshot juga mencakup sejarah sebelum kedua run.

`passed=true` dalam smoke berarti assertion fungsional lolos; tidak berarti
SLA latency tercapai. P95 burst 50 v2 adalah 2818,558 ms, dan target <400 ms
masih belum terpenuhi. HPA menggunakan CPU dan dua pod berbagi satu GPU.
