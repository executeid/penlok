# Hasil JMeter Website dan Offload Edge → Cloud

**Waktu:** 19 November 2026, WIB  
**Generator beban:** Device Edge `pi@100.66.41.38:2523`  
**Versi JMeter:** Apache JMeter 5.6.3, CLI  
**Payload:** JPEG netral 224×224 tanpa wajah dan telemetri sintetis CPU 95%, RAM 14.000 MB, queue 50. Payload ini menguji rute ke Cloud dan deteksi wajah; tidak menguji pengenalan identitas atau aktuasi relay.

## Uji offload 10 user × 5 iterasi

JMeter mengirim telemetri ke Scheduler (`POST /api/v1/schedule`). Bila keputusan
Scheduler adalah Cloud, test plan meneruskan gambar ke Cloud
(`POST /api/v1/migration`). Ini memodelkan cabang offload Edge → Scheduler →
Cloud; pengambilan foto kamera dan relay fisik tidak disimulasikan.

| Bagian | Hasil |
|---|---|
| Request keputusan Scheduler | 50/50 HTTP 200; seluruh 50 diteruskan ke sampler Cloud berdasarkan keputusan route. |
| Request Cloud GPU | 50/50 HTTP 200 dan `processing_node=cloud`; RTT JMeter P50 60 ms, P95 117 ms, rata-rata 71,32 ms, maksimum 119 ms. |
| Audit `cloud_task_log` | 49 hasil `unauthorized` / `NO_FACE_DETECTED`, 1 hasil aplikasi `error`. HTTP 200 sendiri tidak menandakan inferensi sukses; error aplikasi ini ditemukan lewat audit database. |
| Website smoke | Halaman `/`, proxy Scheduler, dan proxy GPU health memberi HTTP 200. Proxy Edge telemetry `/api/telemetry` memberi HTTP 504 setelah 3.056 ms. |
| Ringkasan JMeter | 104 sample dalam 12 detik, 8,7 sample/detik; satu kegagalan HTTP (proxy telemetry). Satu error aplikasi Cloud di atas tetap berstatus HTTP 200. |

## Verifikasi offload berurutan 1 user × 5 iterasi

Test dijalankan ulang dengan assertion respons Cloud. Hasilnya 5/5 keputusan
Scheduler dan 5/5 request Cloud berhasil; assertion memastikan respons berasal
dari Cloud dan statusnya `unauthorized` karena payload sengaja tidak memuat
wajah. Audit database mengonfirmasi 5 baris `unauthorized`, rata-rata proses
Cloud 1,45 ms. Scheduler tetap `healthy` dengan model XGBoost aktif; Cloud
tetap `healthy`, GPU RTX 3050 tersedia, dan database terhubung setelah uji.

## Kesimpulan dan batasan

Offload Edge → Scheduler → Cloud **berfungsi**: keputusan beban tinggi memilih
Cloud, request sampai ke GPU API, dan Cloud mencatat hasil ke audit database.
Pada profil 10 user, satu dari 50 request tercatat sebagai error aplikasi
meskipun HTTP-nya 200; profil serial 1 user lulus 5/5. Uji ini belum membuktikan
akurasi pengenalan wajah karena memakai gambar tanpa wajah.

Jalur website untuk Scheduler dan Cloud health merespons. Jalur website untuk
telemetri Edge masih 504, sementara endpoint telemetri Edge langsung merespons
JSON. Jadi koneksi offload bekerja, tetapi proxy website → Edge telemetry perlu
diperbaiki atau diarahkan ke alamat Edge yang dapat dijangkau Cloud.

Artefak: [test plan JMeter](jmeter_edge_cloud_test.jmx),
[hasil JMeter 10×5](jmeter_edge_cloud_stress_20261119.jtl), dan
[hasil verifikasi 1×5](jmeter_edge_cloud_functional_20261119.jtl).
