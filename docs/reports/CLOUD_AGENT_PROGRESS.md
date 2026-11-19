# Tabel Progres dan Hasil Pengujian Cloud Agent

**Tanggal verifikasi:** 29 Oktober 2026

**Snapshot akhir:** 11:54 WIB / 04:54 UTC

**Lingkup:** sisi Cloud Agent pada host `pengmas-tri`

**Acuan:** tabel `Progress Cloud Agent.docx` dan `Dokumentasi.pdf`

**Versi aplikasi:** 3.3.0, image `penlok-cloud-agent:20261029-v2`

## Status checklist terbaru — 19 November 2026

Pengguna mengonfirmasi seluruh komponen dan checklist pada tabel progres telah
selesai. Progres terbaru: **semua item 100%**. Rincian dan angka uji pada bagian
hasil merupakan snapshot historis 29 Oktober 2026; metrik pada snapshot itu
tetap menunjukkan target latensi belum tercapai pada run tersebut.

Persentase tabel progres terkini mengikuti konfirmasi pengguna tanggal
19 November 2026 dan belum diverifikasi ulang secara independen. Bagian hasil
uji di bawah mempertahankan evidence historis bertanggal 29 Oktober 2026;
persentase progres tidak mengubah angka hasil pengukuran tersebut.

## 1. Tabel progres Cloud Agent

| Komponen | Status | Progres | Hasil / catatan |
|---|---|---:|---|
| Kubernetes/K3s Cloud | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Namespace Cloud Agent | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Service / NodePort | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Deployment Cloud API | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Koneksi Edge → Cloud | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence integrasi rinci belum diperbarui pada snapshot ini. |
| FastAPI Cloud Agent | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| PostgreSQL | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| API → PostgreSQL | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Face Recognition Cloud | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; batas evidence akurasi independen di snapshot tetap berlaku. |
| Migration Data Asli | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Return Hasil ke Edge | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |
| Monitoring / Pengujian | Selesai (konfirmasi pengguna) | 100% | Checklist terbaru dinyatakan selesai 10/10 pada 19 November 2026. |
| End-to-End | Selesai (konfirmasi pengguna) | 100% | Status progres terbaru dikonfirmasi pengguna; evidence rinci di bawah adalah snapshot 29 Oktober. |

### Checklist monitoring/pengujian terbaru

Semua item berikut dikonfirmasi selesai oleh pengguna pada 19 November 2026.
Evidence dan angka uji sebelumnya tetap tersimpan sebagai catatan historis.

| Butir | Status | Kontribusi progres |
|---|---|---:|
| Endpoint metrik dan penyimpanan hasil scrape | Selesai (konfirmasi pengguna) | 10% |
| Unit test kontrak dan fallback | Selesai (konfirmasi pengguna) | 10% |
| Uji fungsi dan input negatif pada API nyata | Selesai (konfirmasi pengguna) | 10% |
| Burst 10/50 request | Selesai (konfirmasi pengguna) | 10% |
| Beban berkelanjutan dengan hasil tersimpan | Selesai (konfirmasi pengguna) | 10% |
| Autoscaling HPA 1 → 2 → 1 | Selesai (konfirmasi pengguna) | 10% |
| Recovery pod | Selesai (konfirmasi pengguna) | 10% |
| Dashboard Grafana khusus Cloud Agent | Selesai (konfirmasi pengguna) | 10% |
| Pencapaian kedua target latensi (<15 ms inference dan P95 <400 ms) | Selesai (konfirmasi pengguna) | 10% |
| Uji ketahanan lanjutan: operasi panjang, network partition, dan outage aktual | Selesai (konfirmasi pengguna) | 10% |
| **Total monitoring/pengujian** | **10 dari 10 butir** | **100%** |

Persentase checklist adalah progres pekerjaan berdasarkan konfirmasi pengguna,
bukan angka hasil pengukuran. Metrik historis berikutnya tetap menunjukkan
hasil run 29 Oktober 2026.

## 2. Pengujian langsung pada server cloud

Pengujian berikut memakai API K3s yang berjalan di server. Foto wajah yang
digunakan adalah foto yang sudah terdaftar pada gallery.

| No. | Pengujian | Hasil aktual | Status |
|---:|---|---|---|
| 1 | Deployment dan kesiapan API | Image v2 berjalan; `/health` menunjukkan CUDA aktif, model siap dan 4 profil; `/ready` mengonfirmasi PostgreSQL tersedia. | Lulus |
| 2 | Pengenalan empat profil | Satu foto enrollment per profil Akmal, Iqbal, Shafwan dan Syauqi menghasilkan `success`, `authorized=true`, serta audit PostgreSQL. | Lulus uji fungsi |
| 3 | Gambar tanpa wajah | Gambar hitam menghasilkan `NO_FACE_DETECTED`, `unauthorized`, `authorized=false`; tersimpan di PostgreSQL. | Lulus |
| 4 | Data yang bukan gambar | Byte non-image menghasilkan HTTP 400, `authorized=false`, dan audit error. | Lulus |
| 5 | Base64 rusak | Request menghasilkan HTTP 400, `authorized=false`, dan audit error. | Lulus |
| 6 | Payload dummy / field wajib tidak lengkap | Request menghasilkan HTTP 422 sebelum masuk handler inference; tidak membuat audit row. | Lulus |
| 7 | Alias endpoint | `/api/v1/migration`, `/api/v1/migrate`, dan `/migration` menerima kontrak gambar dan mengembalikan hasil yang dapat dikorelasikan dengan `task_id`. | Lulus |
| 8 | Audit PostgreSQL | Query mengonfirmasi 66 success, 1 unauthorized, dan 2 error untuk run fungsi/burst v2; run HPA memiliki 247 success. | Lulus |
| 9 | Metrik aplikasi | `/metrics` menyediakan counter hasil dan histogram durasi; hasil scrape disimpan sebagai `.prom`. Integrasi dashboard belum diuji. | Lulus endpoint metrik |
| 10 | Burst 10 request konkuren | 10/10 respons sukses dengan audit PostgreSQL. | Lulus fungsi; target latensi belum tercapai |
| 11 | Burst 50 request konkuren | 50/50 respons sukses dengan audit PostgreSQL; P95 RTT client 2818,558 ms. | Lulus fungsi; target latensi belum tercapai |
| 12 | Beban berkelanjutan dan HPA v2 | 50 worker menghasilkan 247 respons HTTP 200/success/postgres; HPA mengubah jumlah pod 1 → 2 → 1. | Lulus pada durasi uji |
| 13 | Recovery pod v2 | Satu pod dihapus; pod pengganti dengan UID berbeda dan endpoint `/ready` tersedia kembali setelah 8,102 detik observasi. | Lulus |
| 14 | Layanan Docker lama | Health layanan port `9000` tetap menunjukkan sehat dan CUDA aktif pada pemeriksaan akhir. | Lulus pemeriksaan health |

### Hasil burst pada satu pod

| Request konkuren | Sukses | P50 RTT client | P95 RTT client | P99 RTT client | Throughput batch |
|---:|---:|---:|---:|---:|---:|
| 10 | 10/10 | 276,500 ms | 653,609 ms | 653,609 ms | 15,097 request/detik |
| 50 | 50/50 | 1535,165 ms | 2818,558 ms | 2988,601 ms | 16,489 request/detik |

Percentile dihitung menggunakan nearest-rank. Burst dijalankan sebelum uji
HPA, dari host cloud. RTT mencakup perjalanan HTTP, antrean, inference dan
penulisan audit; bukan hanya waktu eksekusi model pada GPU.

Menurut query PostgreSQL, waktu pipeline inference untuk request sukses pada
run fungsi/burst memiliki minimum **27,98 ms**, maksimum **260,58 ms**, dan
rerata **65,05 ms**. Pipeline ini mencakup dekode, deteksi dan pengenalan wajah;
angkanya tidak boleh disebut sebagai waktu forward pass GPU saja.

### Hasil autoscaling dan recovery

| Parameter | Hasil observasi |
|---|---|
| Pemicu HPA | Utilisasi CPU, target 70% terhadap request CPU 500m per pod |
| Batas replika | Minimum 1, maksimum 2 |
| Worker beban | 50 worker konkuren |
| Durasi beban sampai seluruh request yang berjalan selesai | 36,941 detik |
| Respons selama uji | 247 HTTP 200 / success / postgres |
| Waktu hingga dua pod Ready | 29,798 detik sejak awal pengujian |
| Waktu kembali ke satu pod Ready | 72,464 detik setelah worker selesai |
| Recovery pod v2 | 8,102 detik sampai pod pengganti Ready dan API siap |

Dua pod berbagi **satu GPU fisik RTX 3050**. Pengujian ini membuktikan
autoscaling pod berbasis CPU, bukan penambahan GPU, isolasi GPU antar-pod,
atau peningkatan throughput linear. Waktu recovery/scaling adalah waktu
observasi dengan polling berkala, bukan ukuran downtime berpresisi milidetik.

## 3. Pengujian terisolasi: 10/10 lulus

Pengujian dilakukan dalam container dengan network dinonaktifkan. Model dan
koneksi PostgreSQL dimock; fallback SQLite benar-benar menulis database
sementara. Pengujian ini tidak mematikan PostgreSQL produksi atau jaringan edge.

| No. | Kasus uji | Hasil yang diperiksa |
|---:|---|---|
| 1 | Respons sukses dan alias endpoint | HTTP 200, otorisasi, task ID, informasi audit dan field waktu konsisten. |
| 2 | Tidak ada wajah | Respons tidak memberikan otorisasi. |
| 3 | Gambar Base64 tidak valid | HTTP 400 dan percobaan dicatat sebagai error. |
| 4 | Validasi skema dan routing | Decision selain 1, task ID kosong/tidak valid dan device ID terlalu panjang ditolak HTTP 422. |
| 5 | Model tidak siap | HTTP 503. |
| 6 | Kedua backend audit gagal | Respons tidak melaporkan sukses; HTTP 503 dan `authorized=false`. |
| 7 | PostgreSQL tidak tersedia | Fallback SQLite menyimpan task ID dan status yang benar. |
| 8 | Readiness ketika database gagal | HTTP 503 dan `postgres_available=false`. |
| 9 | Format metrik | Counter error dan bucket histogram tersedia. |
| 10 | Thread inference native | Pemrosesan model memakai satu thread worker yang sama. |

## 4. Kegagalan yang ditemukan dan tindak lanjutnya

Uji beban berkelanjutan pertama pada **v1** menemukan `OOMKilled` dengan batas
RAM **2 GiB**. Generator beban dihentikan sebelum menghasilkan laporan akhir;
jumlah request dan success rate percobaan yang terputus itu tidak diklaim.

Mitigasi **v2** menggunakan satu thread native khusus untuk inference serta
batas RAM **3 GiB**. Uji ulang menghasilkan 247 respons sukses dan scaling
dua pod. Hasil tersebut berlaku untuk durasi serta payload yang diuji, bukan
bukti stabilitas operasi tanpa batas. Penyebab detail OOM belum dipastikan
melalui profiling memori.

## 5. Target dan pengujian yang belum selesai

| Target / pengujian | Status berdasarkan bukti |
|---|---|
| Pipeline inference cloud <15 ms | Belum tercapai pada run fungsi/burst yang diuji; minimum request sukses 27,98 ms. |
| P95 <400 ms pada 50 request | Belum tercapai; aktual 2818,558 ms. |
| Koneksi edge → cloud melalui LAN/Tailscale | Belum diuji ulang pada pekerjaan ini. |
| End-to-end sampai pembukaan relai | Belum diuji ulang. |
| Akurasi wajah dengan foto/orang independen, FAR/FRR | Belum diuji; foto pengujian berasal dari enrollment. |
| Pemutusan jaringan edge dan outage PostgreSQL produksi | Belum diuji langsung; skenario database gagal baru diuji secara terisolasi. |
| Dashboard Grafana khusus Cloud Agent | Belum dipasang atau diverifikasi. |
| Beban jangka panjang dan skalabilitas multi-node | Belum diuji. |
| Build bersih dari base PyTorch + requirements | Belum dijalankan; deployment teruji memakai turunan image cloud yang sudah ada. |

Tidak ada klaim bahwa keseluruhan sistem selesai 100%. Yang telah terbukti
adalah fungsi cloud, audit database, validasi request, autoscaling pod dan
recovery sesuai cakupan pengujian di atas.

## 6. Bukti pengujian

| Bukti | Berkas |
|---|---|
| Respons API dan ringkasan burst v2 | [CLOUD_20261029T045023.json](cloud/evidence/CLOUD_20261029T045023.json) |
| Data 60 request burst v2 | [CLOUD_20261029T045023_burst.csv](cloud/evidence/CLOUD_20261029T045023_burst.csv) |
| Scrape metrik setelah burst | [CLOUD_20261029T045023_metrics.prom](cloud/evidence/CLOUD_20261029T045023_metrics.prom) |
| Snapshot HPA dan hasil beban berkelanjutan | [cloud-api-hpa.json](cloud/evidence/cloud-api-hpa.json) |
| UID pod dan waktu recovery | [cloud-api-recovery.json](cloud/evidence/cloud-api-recovery.json) |
| Snapshot cluster, GPU, query database dan hash source | [cloud-final-state.json](cloud/evidence/cloud-final-state.json) |
| Output 10 unit test | [unit-tests.txt](cloud/evidence/unit-tests.txt) |
| Catatan kegagalan OOM awal | [initial-load-failure.json](cloud/evidence/initial-load-failure.json) |
| Laporan cloud lebih terperinci | [cloud/PROGRESS.md](cloud/PROGRESS.md) |

API K3s menggunakan NodePort `30900` dan `31161`; layanan Docker lama tetap
pada port `9000`. Alamat LAN host adalah `10.1.1.186`, alamat Tailscale
`100.76.68.93`. Alamat tersebut merupakan konfigurasi layanan; akses terbaru
dari laptop atau perangkat edge belum diverifikasi ulang.
