# Progress Cloud Agent — verifikasi 29 Oktober 2026

Acuan: tabel `Progress Cloud Agent.docx` (lampiran awal) dan `Dokumentasi.pdf`.
Laporan ini membedakan bukti server saat ini, perubahan yang dikerjakan,
dan pekerjaan yang belum terbukti. Tidak ada persentase perkiraan keseluruhan.

## Kondisi awal yang terverifikasi

- K3s `v1.36.3+k3s1`, node `pengmas-tri` Ready, namespace `cloud-agent` aktif.
- Deployment K3s `cloud-api` masih `hashicorp/http-echo:1.0`, bukan FaceNet.
- Service `cloud-api`: NodePort 31161, port 8000, menuju pod dummy.
- API wajah asli berjalan pada Docker `cloud-face-agent` port 9000, CUDA aktif,
  gallery empat profil. Model nyata: YuNet + InceptionResnetV1 VGGFace2.
- PostgreSQL tujuan API: host cloud port 5432, database `penlok_cloud`.
  Query awal menemukan **23 record**, bukan 422 seperti laporan historis.
- PostgreSQL K3s lain di namespace `database` memiliki PVC Bound 10 GiB.
  Itu bukan database yang digunakan container wajah port 9000.
- Sebelum pekerjaan ini tidak ada HPA cloud yang terpasang atau resource
  `nvidia.com/gpu` yang diiklankan node.

## Tabel progres sesuai komponen dokumen awal

Angka 100% hanya dipakai untuk komponen dengan kriteria fungsi cloud yang
sudah teruji. Komponen lintas edge/cloud memakai dua milestone berbobot sama:
kesiapan dan pengujian segmen cloud (50%), lalu verifikasi aktual integrasi
edge (50%). Monitoring memakai sepuluh butir berbobot sama; tujuh terverifikasi
sehingga progresnya 70%. Ini adalah estimasi progres pekerjaan berdasarkan
checklist pelaporan, bukan pengukuran akurasi atau kelulusan SLA. Rincian
checklist terdapat di [laporan utama](../CLOUD_AGENT_PROGRESS.md#dasar-persentase-komponen-yang-belum-lengkap).
Tidak ada klaim 100% untuk keseluruhan proyek atau pencapaian SLA.

| Komponen | Status sekarang | Progress | Bukti / batas hasil |
|---|---|---:|---|
| Kubernetes/K3s Cloud | Selesai | 100% | Node Ready; deployment API asli dan recovery pod teruji. |
| Namespace Cloud Agent | Selesai | 100% | `cloud-agent` aktif. |
| Service / NodePort | Selesai | 100% | 31161 dan 30900 menuju API asli; readiness HTTP 200. |
| Deployment Cloud API | Selesai | 100% | `penlok-cloud-agent:20261029-v2`, GPU CUDA, satu pod Ready pada snapshot akhir. |
| Koneksi Edge → Cloud | Sebagian; sisi edge belum diverifikasi ulang | 50% | Endpoint cloud siap dan teruji dari host cloud. Bukti koneksi edge dalam dokumen awal adalah bukti historis; pengujian terbaru dari edge belum dilakukan. |
| FastAPI Cloud Agent | Selesai | 100% | Health, readiness, migration/migrate alias, validasi, metrik dan respons JSON diuji. |
| PostgreSQL | Selesai untuk audit cloud | 100% | Koneksi aktual ke `penlok_cloud` di port 5432; bukan sekadar keberadaan manifest. |
| API → PostgreSQL | Selesai | 100% | Query langsung menemukan seluruh 69 record smoke/burst v2 dan 247 record HPA. Termasuk error/penolakan yang disengaja. |
| Face Recognition Cloud | Integrasi selesai | 100% | YuNet + FaceNet pada CUDA; empat foto enrollment dikenali, gambar kosong ditolak. Akurasi independen belum diukur. |
| Migration Data Asli | Sebagian | 50% | JPEG nyata diproses, tetapi berasal dari gallery cloud, bukan capture baru dari edge. |
| Return Hasil ke Edge | Sebagian | 50% | Kontrak respons dan korelasi task_id diuji melalui HTTP. Penerimaan/penggunaan respons oleh edge belum diuji ulang. |
| Monitoring / Pengujian | Sebagian | 70% | Tujuh dari sepuluh butir terverifikasi: metrik, unit, fungsi/negatif, burst, sustained load, HPA, recovery. Dashboard, SLA, dan ketahanan lanjutan belum lengkap. |
| End-to-End | Sebagian; jalur lengkap belum diverifikasi ulang | 50% | Cloud HTTP → GPU → DB → respons terbukti. Jalur Smart Box → scheduler → migration → cloud → relai belum diulang. |

Sumber utama: [snapshot server/DB](evidence/cloud-final-state.json),
[smoke dan burst v2](evidence/CLOUD_20261029T045023.json),
[CSV per request](evidence/CLOUD_20261029T045023_burst.csv),
[HPA](evidence/cloud-api-hpa.json), [recovery](evidence/cloud-api-recovery.json),
dan [hasil unit test](evidence/unit-tests.txt).

## Hasil akhir v2

- Waktu snapshot: **29 Oktober 2026, 11:54 WIB** (04:54 UTC).
- Pod `cloud-api-6ddb97d874-65pm9`: Running, Ready, restart count **0** pada snapshot.
- Image ID aktual: `sha256:2fccb4d1fa9673f70b982d92ac405c5a6814484b3b6ddd1b13521791de7317ff`.
- **10/10** unit test terisolasi lulus. Model dan kegagalan PostgreSQL dimock;
  fallback SQLite benar-benar menulis database sementara.
- Smoke: empat foto enrollment sukses; satu gambar tanpa wajah ditolak;
  gambar non-image dan Base64 rusak HTTP 400; payload dummy HTTP 422.
- PostgreSQL memuat 66 sukses + 1 unauthorized + 2 error untuk run
  `CLOUD_20261029T045023`. Pengujian HPA terpisah memuat 247 sukses.
  Total semua log di database saat snapshot adalah **491**, termasuk sejarah
  lama dan pengujian sebelumnya. Angka ini bukan jumlah transaksi pengguna.
- Burst memakai **satu pod**, sebelum uji HPA. Percentile memakai nearest-rank.

| Beban | Respons sukses | P50 RTT client | P95 RTT client | P99 RTT client | Throughput batch |
|---|---:|---:|---:|---:|---:|
| 10 request konkuren | 10/10 | 276,500 ms | 653,609 ms | 653,609 ms | 15,097 request/s |
| 50 request konkuren | 50/50 | 1535,165 ms | 2818,558 ms | 2988,601 ms | 16,489 request/s |

- Waktu inference sukses pada smoke/burst: minimum **27,98 ms**, maksimum
  **260,58 ms**, rerata **65,05 ms** menurut query DB. Target <15 ms **belum
  tercapai** pada pengujian ini.
- Target P95 <400 ms pada 50 request **belum tercapai**. Burst ini berasal
  dari host cloud dan tidak boleh dipresentasikan sebagai latency edge nyata.
- HPA CPU (target 70%, request CPU 500m, maksimum 2 pod) benar-benar mengubah
  satu pod menjadi **dua pod Ready** setelah **29,798 detik observasi**.
  Tercatat 247 respons HTTP 200/success/postgres selama **36,941 detik** beban
  dengan 50 worker. Setelah worker selesai, kembali menjadi satu pod Ready
  dalam **72,464 detik observasi**. Ini bukan pengukuran peningkatan throughput
  terkontrol sebelum/sesudah scaling.
- Recovery v2: hapus satu pod API, kemudian pod baru dan `/ready` tersedia
  kembali setelah **8,102 detik observasi**. Sampling dilakukan berkala;
  angka itu bukan estimasi downtime berpresisi milidetik.
- NVIDIA runtime menampilkan RTX 3050; snapshot idle memakai 731 MiB dari
  6144 MiB, termasuk layanan Docker lama. Disk host tersisa **29 GiB (88% used)**
  setelah image CUDA tersedia pada runtime K3s.

API cloud baru dapat diakses dari jaringan yang memiliki rute ke host:
`http://10.1.1.186:30900` atau NodePort lama `:31161`.
Endpoint Tailscale setara: `http://100.76.68.93:30900`.
Yang diuji saat pekerjaan ini adalah HTTP dari host cloud; akses dari laptop/
edge melalui LAN/Tailscale belum diuji ulang.

## Hasil yang sudah diketahui

1. API cloud v3.3 ditambahkan sebagai `main.py`, dengan pemeriksaan `/ready`,
   validasi gambar, audit PostgreSQL/SQLite yang transparan, dan `/metrics`.
2. API menerima gambar melalui `/api/v1/migration`, `/api/v1/migrate`,
   dan `/migration`. String dummy lama bukan payload inference yang valid.
3. Build pertama menggunakan image lokal lama sebagai base; tidak ada training
   model baru. Build bersih dari base PyTorch + requirements belum dijalankan.
4. Pod API asli berhasil menggantikan dummy di K3s. NodePort lama dipertahankan
   dan NodePort 30900 ditambahkan. Container lama port 9000 tetap berjalan.
5. Uji awal v1: empat foto enrollment dikenali; gambar kosong ditolak;
   payload rusak ditolak; 60 request burst tersimpan di PostgreSQL.
6. Uji recovery v1: pod lama dihapus dan pod pengganti + endpoint `/ready`
   tersedia kembali setelah **8,058 detik**. Ini bukan ukuran availability
   kontinu atau bukti recovery pada node/mesin berbeda.
7. Uji sustained-load v1 menemukan **OOMKilled** pada limit 2 GiB.
   Beban dihentikan. Mitigasi v2 menggunakan satu thread native inference
   dan limit RAM 3 GiB. Uji v2 menghasilkan 247 respons sukses dan scaling
   dua pod. Ini tidak membuktikan stabilitas jangka panjang tanpa batas.

## Batas yang tetap berlaku

- Pengujian dari host cloud memakai foto yang sudah ada dalam enrollment.
  Ini membuktikan fungsi jalur inference, bukan akurasi pada orang/foto baru.
- Tidak menjalankan edge, scheduler, kamera fisik, enrollment, atau relai.
  End-to-end Smart Box -> Edge -> Scheduler -> Cloud -> relai belum diulang.
- Tidak mengklaim upload/download time terukur terpisah. Client RTT, waktu
  handler server, antrean, dan waktu inference memiliki cakupan berbeda.
- Target inference <15 ms dan P95 <400 ms belum tercapai. Hasil v1 burst 50
  memiliki P95 **3064,834 ms**, sedangkan v2 **2818,558 ms**.
- HPA CPU pada satu GPU bersama bukan alokasi GPU oleh Kubernetes dan bukan
  pembuktian peningkatan kapasitas GPU linear.
- Grafana/Prometheus host memiliki layanan lain; belum ada bukti dashboard
  khusus Cloud Agent tersambung ke metrik baru.
- Aspek statistik FAR/FRR, dataset wajah independen, stress jangka panjang,
  dan pengujian network partition edge memerlukan pekerjaan lanjutan.

## Berkas implementasi

- `main.py`, `cloud_app_main_full.py`, `requirements.txt`, `Dockerfile`.
- `Dockerfile.cloud-runtime`: build turunan dari environment cloud yang ada.
- `cloud/k8s/cloud-api.yaml`, `cloud/k8s/cloud-api-hpa.yaml`.
- `tests/test_cloud_api.py`: pengujian kontrak dan fallback secara terisolasi.
- `cloud/verify_cloud.py`, `cloud/check_recovery.py`, `cloud/check_hpa.py`.
- `cloud/README.md`: langkah operasional, batasan, dan rollback.

Cadangan deployment/service sebelum perubahan tersedia di server:
`/home/penlok/cloud-agent-runtime/evidence/`.
