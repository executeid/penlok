# Product Requirements Document (PRD)
# Smart Locker Multi-Agent Modern Web Interface (SmartBox Web v2)

**Document Version**: 2.0.0  
**Status**: Approved for Implementation  
**Date**: 9 Oktober 2026  
**Reference Codebase**: `smartbox_web/` (Legacy Laravel 10)  
**Deployment Target**: **Kubernetes K3s pada Cloud GPU Node (`10.1.1.186` / `pengmas-tri`)**  
**Backend Services Integration**:
- **Device Edge**: `http://10.1.1.224:8000` (Django REST Backend & PostgreSQL)
- **Edge Sync Service**: `http://10.1.1.224:8600` (LBPH & Local Photo Sync)
- **Edge Scheduler**: `http://10.1.1.57:8500` (XGBoost/Rule-Based Offload Engine)
- **Cloud GPU Face Agent**: `http://10.1.1.186:9000` (FastAPI, YuNet, PyTorch CUDA InceptionResnetV1)

---

## 1. Executive Summary & Problem Statement

### 1.1 Masalah pada Versi Lama (`smartbox_web/`)
1. **PHP/Laravel Monolith Outdated**: Bergantung pada setup lokal Windows Laragon (`C:\laragon\...`), eksekusi `exec()` python manual, dan synchronous batch script.
2. **Disconnected Architecture**: Model pengenalan wajah lama menulis ke `embeddings.json` statis lokal via insightface CPU, tidak terhubung dengan arsitektur 3-Tier Multi-Agent (Edge Pi 5 + Edge Brain + Cloud GPU RTX 3050).
3. **Double System of Record**: Backend utama locker berjalan di Django REST (`10.1.1.224:8000`) dengan database PostgreSQL, sedangkan Laravel lama mengelola SQLite/MySQL terpisah tanpa sinkronisasi transaksi real time.
4. **Poor Onboarding UX**: Pengguna mengunggah 5 foto statis tanpa live face detection validation, cropping, atau visualisasi kualitas pose wajah.

### 1.2 Visi & Solusi Baru (SmartBox Web v2)
Membangun web application modern (Next.js 14 / React + Tailwind CSS + FastAPI / Node.js BFF) yang:
- Mempertahankan alur inti (Role Admin & Penghuni, Manajemen Paket/Resi, Status Sensor Loker, Riwayat Aktivitas).
- Mengintegrasikan onboarding wajah modern (Webcam browser capture / Upload dengan live face bounding box).
- Terhubung langsung ke REST API Cloud GPU (`10.1.1.186:9000/api/v1/onboard_user`) yang otomatis mensinkronkan embedding ke VRAM GPU dan mendistribusikan ke Edge Pi (`10.1.1.224:8600/api/v1/sync_user_face`) untuk pemrosesan offline lokal.
- Menyediakan dashboard telemetri real-time (Ultrasonik, status kompartemen loker, metrik scheduler, status migrasi).
- **Native K3s Containerized Deployment**: Di-deploy sebagai Kubernetes Deployment + Service di node Cloud GPU (`10.1.1.186`) satu klaster dengan microservice cloud lainnya.

---

## 2. Arsitektur Sistem & Alur Integrasi

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SMARTBOX WEB INTERFACE (v2)                     │
│               (Modern React / Next.js + Tailwind CSS)                  │
│             [Deployed inside K3s Pod: smartbox-web-app]                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       GATEWAY / API CONTROLLER                         │
├───────────────────────────────────┬────────────────────────────────────┤
│ 1. Autentikasi & Data Master      │ Django REST / PostgreSQL           │
│    (User, Role, Paket Resi, OTP)  │ (http://10.1.1.224:8000)           │
├───────────────────────────────────┼────────────────────────────────────┤
│ 2. Sensor & Status Loker Live     │ Hardware Polling / IoT API         │
│    (Ultrasonik, IR, Loadcell)     │ (http://10.1.1.224:8000/api/v1/iot)│
├───────────────────────────────────┼────────────────────────────────────┤
│ 3. Onboarding & Embeddings        │ Cloud GPU Agent (RTX 3050)         │
│    (Capture -> CUDA Embeddings)   │ (http://10.1.1.186:9000)           │
│                                   │                 │                  │
│                                   │                 ▼ (Auto Sync)      │
│                                   │ Edge Pi Sync Service (:8600)       │
├───────────────────────────────────┼────────────────────────────────────┤
│ 4. Telemetri Multi-Agent & AI     │ Edge Brain Scheduler (:8500) &     │
│    (Metrik CPU, Offload Decision) │ Prometheus Scrapes                 │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## 3. User Personas & Role Matrix

| Fitur / Halaman | Admin | Penghuni / Owner | Kurir (Public Kiosk) |
|---|:---:|:---:|:---:|
| **Login / Logout (JWT / Session)** | ✅ | ✅ | ❌ |
| **Dashboard Ringkasan & Sensor Live** | ✅ (Semua Loker) | ✅ (Status Loker Saya) | ❌ |
| **Live Telemetri MAS (Edge/Cloud)** | ✅ | ❌ | ❌ |
| **Manajemen Penghuni (CRUD & Face ID)** | ✅ | ❌ | ❌ |
| **Trigger Regenerate All Embeddings** | ✅ | ❌ | ❌ |
| **Onboarding Wajah (Capture/Upload)** | ✅ (Bisa bantu user) | ✅ (Wajah Sendiri) | ❌ |
| **Daftar Paket & Input Nomor Resi** | ✅ (Lihat Semua) | ✅ (Paket Saya) | ❌ |
| **Log Aktivitas & Riwayat Akses** | ✅ (Global) | ✅ (Riwayat Akun) | ❌ |

---

## 4. Rincian Kebutuhan Fungsional (Functional Requirements)

### 4.1 Modul Autentikasi & Akun
- **FR-01.1**: Form login responsif dengan validasi username/email dan password.
- **FR-01.2**: Autentikasi berbasis JWT Token atau Secure Cookie Session terhubung dengan database `users_user` PostgreSQL.
- **FR-01.3**: Role-based redirect otomatis: Admin diarahkan ke `/admin/dashboard`, Penghuni diarahkan ke `/penghuni/dashboard`.

### 4.2 Modul Onboarding Wajah Modern (Core Differentiator)
- **FR-02.1**: **Pilihan Input Fleksibel**:
  - *Mode 1 (Webcam Browser Capture)*: Mengakses kamera laptop/HP pengguna dengan antarmuka video stream langsung. Memandu pengguna untuk mengambil 3–5 pose wajah (Tampak Depan, Miring Kanan Sedikit, Miring Kiri Sedikit, Senyum).
  - *Mode 2 (File Upload)*: Mengunggah 1 hingga 5 berkas foto wajah (format JPG/PNG, ukuran maks 5 MB per berkas).
- **FR-02.2**: **Client-side Pre-Validation**: Deteksi apakah wajah berada di area pandang sebelum tombol capture aktif.
- **FR-02.3**: **Kirim ke Cloud Onboarding Pipeline**:
  - Mengirim payload ke `POST http://10.1.1.186:9000/api/v1/onboard_user`.
  - Cloud GPU otomatis mendeteksi wajah dengan OpenCV YuNet, menghitung embedding InceptionResnetV1 CUDA, dan menyimpannya di VRAM.
  - Cloud GPU otomatis meneruskan data ke Edge Pi (`http://10.1.1.224:8600/api/v1/sync_user_face`) untuk memperbarui model lokal LBPH secara instan.
- **FR-02.4**: **Feedback Visual Progres**:
  - Status langkah: `1. Mengunggah Foto` $\rightarrow$ `2. Ekstraksi AI di GPU Cloud` $\rightarrow$ `3. Sinkronisasi Offline ke Smart Locker` $\rightarrow$ `Selesai (Siap Digunakan)`.

### 4.3 Modul Dashboard & Monitoring Sensor Live
- **FR-03.1**: **Widget Monitoring Sensor Ultrasonik**:
  - Menampilkan jarak deteksi kompartemen Loker 1 secara real time (interval polling 2–3 detik).
  - Indikator status visual:
    - Hijau: `Kosong (Jarak > 23 cm)`.
    - Kuning: `Paket Terdeteksi (Jarak <= 23 cm)`.
- **FR-03.2**: **Widget Status 3 Kompartemen Loker**:
  - Loker 1 (Inbound Kurir): Tersedia / Terisi Paket / Pintu Terbuka.
  - Loker 2 (Storage Pemilik): Terkunci Aman / Membuka.
  - Loker 3 (Marketplace): Siap Ambil (OTP Aktif) / Selesai.
- **FR-03.3**: **Widget Telemetri AI Multi-Agent (Khusus Admin)**:
  - Utilisasi CPU Edge Pi 5 saat ini.
  - Keputusan Scheduler Agent terakhir (`0 = Edge`, `1 = Cloud`).
  - Total latency rata-rata inferensi ($T_{\text{total}}$).

### 4.4 Modul Manajemen Paket & Nomor Resi (Penghuni)
- **FR-04.1**: Tabel daftar paket milik penghuni dengan kolom: No, Nomor Resi, Status Kurir, Tanggal Input, dan Aksi.
- **FR-04.2**: Tambah paket baru dengan memasukkan nomor resi tracking ekspedisi (misal: SPX, J&T, SiCepat) dan nama barang.
- **FR-04.3**: Badge status paket dinamis:
  - `Dalam Perjalanan` (Badge Kuning)
  - `Diterima di Loker 1` (Badge Biru)
  - `Tersimpan di Loker 2` (Badge Hijau)
  - `Sudah Diambil` (Badge Primer)
  - `Dibatalkan` (Badge Merah)
- **FR-04.4**: Tombol batalkan paket jika paket masih berstatus `Dalam Perjalanan`.

### 4.5 Modul Manajemen Penghuni (Khusus Admin)
- **FR-05.1**: Tabel seluruh penghuni terdaftar: Nama Lengkap, Username, Email, Face ID (6 digit numerik unik), Status Wajah (`Belum Upload`, `Menunggu Generate`, `Selesai Generate`), Jumlah Paket Aktif.
- **FR-05.2**: Tambah penghuni baru (otomatis men-generate Face ID unik).
- **FR-05.3**: Tombol *Generate Ulang Seluruh Data Wajah* (Batch Sync ke GPU & Edge).
- **FR-05.4**: Hapus atau nonaktifkan akun penghuni.

### 4.6 Modul Riwayat & Audit Log
- **FR-06.1**: Tabel log aktivitas terperinci: Waktu, Nama Pengguna, Tipe Aktivitas (Buka Loker, Input Resi, Onboarding Wajah, Autentikasi Wajah), Lokasi Node Pemrosesan (`Edge` atau `Cloud GPU`), dan Status (`Berhasil` / `Gagal`).
- **FR-06.2**: Filter berdasarkan rentang tanggal dan status.

---

## 5. Rencana Stack Teknologi & K3s Containerization

### 5.1 Pilihan Framework
- **Frontend / Application Framework**: **Next.js 14 (App Router, Node.js v22 Standalone Output)** + **Tailwind CSS** + **Lucide Icons**.
  - Mengapa Standalone Output? Next.js menghasilkan build mandiri super-ringkas (~80 MB) yang sangat ideal untuk container Docker K3s tanpa perlu membawa seluruh `node_modules`.
- **Runtime**: Node.js 22 Alpine / Slim Container.

### 5.2 Strategi Deployment Kubernetes (K3s Cloud Node `10.1.1.186`)
- **Namespace Target**: `cloud-agent` (bergabung satu ekosistem dengan `cloud-api` dan `postgres`).
- **Service Type**: `NodePort: 30080` (atau Traefik Ingress Route pada `http://10.1.1.186/web`).
- **Manifes Kubernetes**:
  1. `smartbox-web-deployment.yaml`: Replicas 1 (autoscalable via HPA jika traffic tinggi), liveness & readiness probe.
  2. `smartbox-web-service.yaml`: NodePort mapping port internal container 3000 ke port host 30080.
  3. `smartbox-web-configmap.yaml`: Environment variables (`NEXT_PUBLIC_CLOUD_API_URL`, `NEXT_PUBLIC_EDGE_API_URL`).

---

## 6. Struktur Navigasi & Tampilan Antarmuka (Sitemap)

```
/
├── /login                         # Halaman Login Utama
├── /admin
│   ├── /dashboard                 # Ringkasan Loker, Sensor Live, Telemetri MAS
│   ├── /penghuni                  # Data Penghuni, Tambah User, Status Face ID
│   ├── /paket                     # Seluruh Paket Semua Penghuni
│   ├── /monitoring                # Telemetri Edge-Cloud & Grafana Embed
│   └── /history                   # Audit Log Global
└── /penghuni
    ├── /dashboard                 # Status Loker, Status Wajah Saya, Notifikasi
    ├── /onboarding-wajah          # Webcam / Upload Foto Wajah (3 Pose)
    ├── /paket                     # Daftar Paket Saya & Input Nomor Resi
    └── /history                   # Riwayat Aktivitas Akun Saya
```

---

## 7. Kriteria Keberhasilan (Acceptance Criteria)

1. Web app ter-deploy dan berjalan sehat sebagai Pod di klaster K3s Cloud Node (`kubectl get pods -n cloud-agent` menunjukkan `smartbox-web` running).
2. Web interface dapat diakses langsung oleh browser via `http://10.1.1.186:30080` atau Tailscale mesh.
3. Form onboarding wajah dapat menangkap frame webcam browser atau mengunggah foto, lalu mengirimkannya ke `http://10.1.1.186:9000/api/v1/onboard_user`.
4. Foto yang didaftarkan langsung terdistribusi otomatis ke Cloud GPU (embedding 512-d) dan Edge Pi 5 (LBPH offline update).
5. Data sensor jarak ultrasonik dan status loker ter-update secara berkala tanpa me-refresh halaman (*live polling*).
6. Input nomor resi oleh penghuni langsung tersimpan di database loker `package_center_packageentry`, sehingga kurir di hardware loker fisik langsung dapat membuka Loker 1 menggunakan 5 digit resi tersebut.
