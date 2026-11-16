# Tabel Progres dan Hasil Pengujian Cloud Agent

**Tanggal verifikasi:** 29 Oktober 2026

**Snapshot akhir:** 11:54 WIB / 04:54 UTC

**Lingkup:** sisi Cloud Agent pada host `pengmas-tri`

**Acuan:** tabel `Progress Cloud Agent.docx` dan `Dokumentasi.pdf`

**Versi aplikasi:** 3.3.0, image `penlok-cloud-agent:20261029-v2`

Status di bawah berdasarkan pengujian dan evidence yang tersimpan. Dokumen
ini merangkum pengujian sebelumnya, bukan hasil pemeriksaan server yang baru.
Angka **100%** berarti fungsi komponen dalam lingkup cloud sudah terverifikasi;
bukan persentase kelulusan seluruh proyek, akurasi wajah, atau pencapaian target
performa. Persentase komponen yang belum lengkap adalah **estimasi progres
pekerjaan berdasarkan checklist** yang dijelaskan setelah tabel, bukan angka
hasil pengukuran keberhasilan atau akurasi.

## 1. Tabel progres Cloud Agent

| Komponen | Status | Progres | Hasil / catatan |
|---|---|---:|---|
| Kubernetes/K3s Cloud | Selesai | 100% | K3s aktif, node Ready; API asli berjalan dan penggantian pod telah diuji. |
| Namespace Cloud Agent | Selesai | 100% | Namespace `cloud-agent` aktif. |
| Service / NodePort | Selesai | 100% | NodePort `31161` dan `30900` menuju API asli. Health dan readiness merespons HTTP 200 dari host cloud. |
| Deployment Cloud API | Selesai | 100% | Pod dummy diganti dengan API YuNet + FaceNet CUDA. Snapshot akhir menunjukkan satu pod Ready dengan restart count 0. |
| Koneksi Edge → Cloud | Sebagian; sisi edge belum diverifikasi ulang | 50% | Endpoint cloud siap dan teruji dari host cloud. Uji koneksi terbaru dari edge belum dilakukan; dokumen awal memiliki bukti historis. |
| FastAPI Cloud Agent | Selesai | 100% | Endpoint health, readiness, migration, alias migrate, validasi request, respons JSON, dan metrik telah diuji. |
| PostgreSQL | Selesai untuk audit cloud | 100% | Database `penlok_cloud` pada host cloud port `5432` dapat diakses. Instance PostgreSQL K3s di namespace `database` merupakan instance lain. |
| API → PostgreSQL | Selesai | 100% | Query database mengonfirmasi seluruh 69 record pengujian fungsi/burst v2 dan 247 record pengujian HPA. |
| Face Recognition Cloud | Integrasi selesai | 100% | YuNet mendeteksi wajah dan FaceNet melakukan inference pada CUDA. Empat foto enrollment dikenali; gambar tanpa wajah ditolak. Akurasi independen belum diuji. |
| Migration Data Asli | Sebagian | 50% | Payload JPEG nyata berhasil diproses, tetapi berasal dari gallery cloud, bukan capture baru perangkat edge. |
| Return Hasil ke Edge | Sebagian | 50% | Kontrak respons, `task_id`, status, dan hasil inference teruji melalui HTTP. Penggunaan hasil oleh perangkat edge belum diuji ulang. |
| Monitoring / Pengujian | Sebagian | 70% | Tujuh dari sepuluh butir checklist di bawah terverifikasi. Dashboard, pencapaian SLA, dan ketahanan lanjutan masih belum selesai. |
| End-to-End | Sebagian; jalur lengkap belum diverifikasi ulang | 50% | Jalur HTTP cloud → inference → database → respons terbukti. Jalur lengkap Smart Box → scheduler → migration → cloud → relai belum diulang. |

### Dasar persentase komponen yang belum lengkap

Untuk koneksi, migrasi data, pengembalian hasil, dan end-to-end, progres
dibagi menjadi dua milestone berbobot sama: **kesiapan/pengujian segmen cloud
(50%)** dan **verifikasi integrasi aktual dengan edge (50%)**. Milestone cloud
sudah terbukti, sedangkan milestone integrasi edge belum diuji ulang. Karena
itu masing-masing dicatat **50%**, bukan dianggap belum ada implementasi.

Untuk monitoring/pengujian digunakan sepuluh butir berbobot sama (10% per
butir):

| Butir | Status | Kontribusi progres |
|---|---|---:|
| Endpoint metrik dan penyimpanan hasil scrape | Terverifikasi | 10% |
| Unit test kontrak dan fallback | Terverifikasi | 10% |
| Uji fungsi dan input negatif pada API nyata | Terverifikasi | 10% |
| Burst 10/50 request | Terverifikasi secara fungsional | 10% |
| Beban berkelanjutan dengan hasil tersimpan | Terverifikasi pada durasi uji | 10% |
| Autoscaling HPA 1 → 2 → 1 | Terverifikasi | 10% |
| Recovery pod | Terverifikasi | 10% |
| Dashboard Grafana khusus Cloud Agent | Belum terverifikasi | 0% |
| Pencapaian kedua target latensi (<15 ms inference dan P95 <400 ms) | Belum tercapai | 0% |
| Uji ketahanan lanjutan: operasi panjang, network partition, dan outage aktual | Belum lengkap | 0% |
| **Total monitoring/pengujian** | **7 dari 10 butir** | **70%** |

Checklist ini adalah dasar pelaporan progres pekerjaan yang dipakai dalam
dokumen ini, bukan bobot resmi yang tercantum pada dokumen acuan awal.

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
