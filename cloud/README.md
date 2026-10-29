# Cloud Agent: runbook dan batas verifikasi

Acuan pekerjaan: tabel dalam `progres/cloud-agent/progres-1/Progress Cloud
Agent.docx` dan `Dokumentasi.pdf`. Status terkini dicatat di [PROGRESS.md](PROGRESS.md).
Dokumen laporan lama adalah catatan historis, bukan bukti kondisi server sekarang.

## Layanan

- `main.py`: API inference-only v3.3, menggunakan deteksi YuNet dan
  InceptionResnetV1 VGGFace2 dari `cloud_app_main_full.py`.
- `cloud-agent/cloud-api`: deployment K3s pada `pengmas-tri`.
- NodePort lama `31161` dipertahankan (`service port 8000 -> target 9000`).
- NodePort `30900` juga tersedia (`service port 9000 -> target 9000`).
- Container Docker lama `cloud-face-agent:9000` tetap melayani integrasi lama
  dan onboarding. Endpoint baru tidak mengubah edge atau menggerakkan relai.
- PostgreSQL `penlok_cloud` pada host cloud port 5432 adalah audit database
  yang digunakan API. PostgreSQL K3s di namespace `database` adalah instance
  lain; keberadaannya tidak membuktikan API menulis ke instance tersebut.

## Kontrak API

`POST /api/v1/migration`, `/api/v1/migrate`, dan `/migration` menerima kontrak
gambar yang sama, bukan string dummy dari prototipe lama:

```json
{
  "task_id": "SB01_001",
  "device_id": "SB01",
  "image": "<base64 JPEG/PNG>",
  "decision": 1
}
```

Hasil menyertakan `task_id`, `device_id`, `status`, `authorized`, `user_id`,
`confidence`, `cloud_processing_time_ms`, `queue_and_decode_time_ms`,
`server_total_time_ms`, dan `audit_backend` (`postgres`, `sqlite`, `failed`).
Status wajah tidak cocok adalah `unauthorized` (HTTP 200); gambar tidak valid
HTTP 400, skema tidak valid HTTP 422, model/audit tidak tersedia HTTP 503.
Cosine similarity bukan probabilitas akurasi pengenalan wajah.

- `/health`: liveness proses dan informasi model/GPU.
- `/ready`: menguji kesiapan model, gallery, GPU, serta koneksi PostgreSQL;
  HTTP 503 bila dependensi tidak siap.
- `/metrics`: counter hasil inference dan histogram total waktu handler.
  Request yang ditolak validasi Pydantic sebelum handler tidak dihitung.
- `/docs` dan `/openapi.json`: kontrak yang dihasilkan FastAPI.

Waktu komputasi mengecualikan antrean lock dan penulisan audit. Waktu total
server mencakup keduanya. Waktu RTT client mencakup perjalanan HTTP. Tidak
ada pembagian rekaan 65% upload / 35% download dalam pengukuran baru ini.
Status `audit_backend=sqlite` adalah kondisi terdegradasi, bukan bukti berhasil
menulis ke PostgreSQL. Kegagalan kedua backend menghasilkan HTTP 503 dan
`authorized=false`.

## Build dan aset

Build bersih menggunakan `Dockerfile` + `requirements.txt`. Build tersebut
belum boleh dianggap terverifikasi hanya karena source-nya tersedia.
Build yang diuji pada host memakai `Dockerfile.cloud-runtime` dan dependensi
container lama yang sudah tersedia, tanpa mengunduh ulang stack CUDA:

```bash
docker tag <verified-old-image-id> penlok-cloud-base:<short-id>
docker build --pull=false --network=none \
  --build-arg BASE_IMAGE=penlok-cloud-base:<short-id> \
  -f Dockerfile.cloud-runtime -t penlok-cloud-agent:20261029-v2 .
docker save penlok-cloud-agent:20261029-v2 | sudo k3s ctr images import -
```

Image turunan mewarisi isi image lama dan digunakan lokal di server. Jangan
menyamakan image itu dengan image bersih yang tidak mengandung aset lama.
Source baru tidak mengunggah aset wajah atau secret ke repository.

Prasyarat deployment:

1. Model YuNet dan `gallery_embeddings.pt` tersedia di `/home/penlok/app`.
2. Checkpoint VGGFace2 sudah ada di `/home/penlok/.cache/torch`.
3. Direktori `/home/penlok/cloud-agent-runtime/data` tersedia untuk SQLite.
4. Secret `cloud-agent-db` menyediakan `DB_HOST`, `DB_PORT`, `DB_USER`,
   `DB_PASSWORD`, `DB_NAME`. Tidak ada nilai secret dalam manifest.
5. RuntimeClass `nvidia` sudah terpasang dan host memiliki GPU/CUDA.

`deploy_on_host.py` menyalin konfigurasi DB dari environment container lama
ke Kubernetes Secret melalui stdin. Nilainya tidak dicetak atau disimpan dalam
file evidence. Jalankan setelah mencadangkan deployment/service lama.

```bash
python3 cloud/deploy_on_host.py
sudo kubectl rollout status deployment/cloud-api -n cloud-agent --timeout=90s
curl --fail http://127.0.0.1:30900/ready
```

Manifest v2 menyediakan request CPU 500m / RAM 1 GiB dan limit CPU 2 core /
RAM 3 GiB. Decoder dan model dijalankan pada satu thread native khusus untuk
membatasi akumulasi alokasi native di banyak thread HTTP. Pengujian awal v1
dengan limit RAM 2 GiB pernah OOM; bukti kegagalan dan hasil ulang v2 tersedia
dalam PROGRESS.md.

Manifest memakai `hostPath` pada satu node laboratorium, bukan storage
multi-node. Runtime mengakses GPU 0 lewat NVIDIA_VISIBLE_DEVICES. Tidak ada
resource `nvidia.com/gpu` yang dialokasikan scheduler Kubernetes karena
device plugin belum terpasang. HPA opsional dalam `cloud-api-hpa.yaml` memakai
CPU 70% dengan 1–2 replika yang berbagi GPU 0. Hasil pengujian scaling aktual
dicatat dalam PROGRESS.md; ini bukan isolasi GPU atau autoscaling lintas node.

Endpoint `/metrics` sudah tersedia, tetapi scrape annotations saja tidak
menjamin Prometheus tertentu telah mengumpulkannya. Dashboard Grafana khusus
Cloud Agent belum dipasang atau diverifikasi.

Gallery dibaca saat startup. Setelah onboarding melalui layanan lama,
restart/rollout deployment baru diperlukan untuk memuat snapshot embedding
terbaru. Sinkronisasi hot-reload lintas kedua layanan belum diimplementasikan.

## Pengujian

`tests/test_cloud_api.py` menguji kontrak HTTP melalui ASGI dengan mock model
dan PostgreSQL, serta penulisan fallback SQLite ke database sementara. Ini
bukan uji jaringan putus nyata atau akurasi model.

```bash
python -m unittest discover -s tests -v
```

`verify_cloud.py` melakukan uji nyata melalui HTTP, membaca foto enrollment
yang sudah ada secara read-only. Tidak memanggil onboarding atau edge.
Script menulis JSON, CSV setiap request burst, dan scrape metrik:

```bash
python cloud/verify_cloud.py --url http://127.0.0.1:30900 \
  --assets /home/penlok/app/gallery/imagetraining --output cloud/evidence
```

Burst 10/50 request dari host cloud bukan pengujian latency Edge -> Tailscale
-> Cloud dan tidak membuktikan HPA. `check_hpa.py` mengamati HPA secara terpisah
dengan beban berkelanjutan 50 worker, sedangkan `check_recovery.py` menguji
penggantian satu pod cloud secara eksplisit. Kedua script terakhir memerlukan
sudo kubectl di host cloud dan mengubah workload cloud saat dijalankan.
Foto enrollment yang dipakai ulang hanya
membuktikan jalur inference bekerja; bukan dataset independen untuk FAR/FRR,
precision/recall, atau klaim akurasi wajah.

## Rollback

Cadangan awal berada di server dalam
`/home/penlok/cloud-agent-runtime/evidence/cloud-api-before.yaml` dan
`cloud-api-service-before.yaml`. Untuk mengembalikan API dummy, restore
keduanya. Alternatif `rollout undo` saja tidak mengembalikan targetPort service.
Layanan Docker port 9000 tidak dihentikan oleh pekerjaan ini.
