# Jurnal Teknis: Implementasi Endpoint Onboarding & Sinkronisasi Wajah Otomatis (Cloud GPU ke Edge Pi)

**Tanggal**: 9 Oktober 2026  
**Node Terlibat**:
- **Cloud GPU**: `penlok@10.1.1.186:9000` (NVIDIA GeForce RTX 3050 6GB CUDA)
- **Device Edge**: `pi@10.1.1.224:8600` (Raspberry Pi 5 8GB)  
**Status**: SELESAI / AKTIF PERMANEN (Systemd Service)

---

## 1. Latar Belakang & Kebutuhan Sistem
Dalam sistem hybrid edge-cloud:
1. **Onboarding di Cloud**: Pengguna mendaftarkan wajah (unggah foto via Web/Aplikasi Mobile/Dashboard Cloud).
2. **Kebutuhan Operasi Mandiri di Edge**: Perangkat fisik Smart Locker di lokasi (Raspberry Pi 5) harus tetap dapat mengenali pengguna secara offline ketika koneksi internet atau VPN terputus.
3. **Tantangan Sebelumnya**: Tidak ada jalur otomatis untuk memindahkan data wajah dan memperbarui model Edge secara lokal tanpa intervensi manual command line.

---

## 2. Arsitektur Alur Sinkronisasi Otomatis

```
[Aplikasi Web / User Onboarding]
               │
               ▼ HTTP POST /api/v1/onboard_user
┌────────────────────────────────────────────────────────┐
│             CLOUD GPU AGENT (10.1.1.186:9000)          │
│                                                        │
│  1. Simpan foto ke direktori galeri:                   │
│     /home/penlok/app/gallery/imagetraining/<user>/     │
│  2. Deteksi & crop wajah via OpenCV YuNet ONNX         │
│  3. Ekstraksi embedding 512-d via InceptionResnetV1    │
│  4. Simpan embedding ke gallery_embeddings.pt (VRAM)   │
│  5. Otomatis kirim payload sinkronisasi ke Edge Pi     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ HTTP POST /api/v1/sync_user_face
┌────────────────────────────────────────────────────────┐
│             EDGE SYNC SERVICE (10.1.1.224:8600)        │
│                                                        │
│  6. Terima payload Base64 foto & face_id               │
│  7. Tulis foto ke direktori media lokal:               │
│     media/imagetraining/<username>/                    │
│  8. Update / Insert user ke PostgreSQL lokal          │
│     (tabel: users_user, role: OWNER, face_id: xxx)     │
│  9. Retrain / update model LBPH lokal di background   │
│     (output: pyenv3.9code/nonsudo/lbph_model.xml)      │
│  10. Balas status HTTP 200 { "status": "synced" }      │
└────────────────────────────────────────────────────────┘
```

---

## 3. Spesifikasi Kontrak API

### 3.1 Endpoint Cloud GPU Onboarding
- **URL**: `POST http://10.1.1.186:9000/api/v1/onboard_user`
- **Request Body**:
  ```json
  {
    "username": "akmal",
    "face_id": 789123,
    "first_name": "Akmal",
    "last_name": "Owner",
    "images": [
      "<base64_encoded_jpeg_string_1>",
      "<base64_encoded_jpeg_string_2>"
    ]
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "username": "akmal",
    "face_id": 789123,
    "cloud_embeddings_saved": 1,
    "edge_sync_status": "synced",
    "total_time_ms": 3652.49
  }
  ```

### 3.2 Endpoint Edge Pi Sync Service
- **URL**: `POST http://10.1.1.224:8600/api/v1/sync_user_face`
- **Service Name**: `penlock-edge-sync.service` (Systemd)
- **Response**:
  ```json
  {
    "status": "success",
    "username": "akmal",
    "face_id": 789123,
    "images_saved": 1,
    "database_updated": true,
    "lbph_model_updated": true,
    "sync_time_ms": 3179.33
  }
  ```

---

## 4. Hasil Uji Validasi Nyata
1. **Pendaftaran & Ekstraksi Cloud**:
   - Foto wajah didecode dan diekstraksi ke CUDA tensor pada NVIDIA RTX 3050.
   - Vektor embedding ter-update otomatis di `gallery_embeddings.pt`.
2. **Sinkronisasi Lintas Node**:
   - Cloud GPU menembak `http://10.1.1.224:8600/api/v1/sync_user_face`.
   - Data foto, entri database `users_user`, dan file model `lbph_model.xml` di Raspberry Pi 5 berhasil diperbarui dalam **3.1 detik**.
3. **Uji Inferensi Pasca-Sinkronisasi (Offline Edge Test)**:
   - Wajah langsung terverifikasi di Pi 5:
     `Post-Sync Local Edge Result: Auth=True, User=Akmal, Conf=1.0, Time=336ms`.
