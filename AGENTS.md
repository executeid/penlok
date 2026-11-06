# PENLOK Smart Locker - AGENTS Context & Guidelines

> Dokumen konteks proyek otomatis untuk Pi Coding Agent (`pi`) dan AI Agent lainnya di direktori `/home/execute/penlok`.

---

## 1. Ringkasan Proyek
**Penlok** adalah ekosistem Smart Locker cerdas berbasis **Multi-Agent System (MAS)** dan IoT untuk manajemen penitipan barang otomatis, akses kurir (*inbound delivery*), pengambilan barang marketplace (*buyer pickup*), serta akses biometrik pemilik loker (*owner biometric access*).

Arsitektur sistem membagi beban komputasi secara dinamis antara **Edge** (Raspberry Pi 5) dan **Cloud GPU** (NVIDIA RTX 3050 CUDA) menggunakan model klasifikasi rute **XGBoost**.

---

## 2. Topologi Jaringan & Node Infrastruktur

| Peran Node | Hostname / IP LAN | IP Tailscale | Akun & Kredensial | Tugas Utama |
|---|---|---|---|---|
| **Device Edge (Loker)** | `10.1.1.224:2523` | `100.75.230.102` | `pi` (RPi 5 8GB, Linux 6.12 aarch64) | Kontrol aktuator (Relay, Servo, Keypad, LCD, Kamera, Ultrasonik). Daemon Docker: `edge-hardware-daemon`, `edge-gateway-sync`. |
| **Edge Brain / Scheduler** | `10.1.1.57:22` | `100.112.209.30` | `penlok` (sudo: `123`) (RPi 5 16GB, K3s) | Scheduler Agent FastAPI (Port 8500), model XGBoost perutean komputasi Cloud vs Edge. |
| **Cloud GPU Node** | `10.1.1.186:22` | `100.76.68.93` | `tcc` (sudo: `jawir`) / `penlok` (`pengmas-tri`, Ubuntu 24.04 x86_64) | NVIDIA RTX 3050 6GB CUDA 13.2, FastAPI Cloud Agent (Port 9000), FaceNet 512-d embeddings, database cloud PostgreSQL. |
| **Development Host** | `localhost` | - | `execute` (`/home/execute/penlok`) | Repository source code, testing scripts, deployment control. |

---

## 3. Detail Hardware & Pinout GPIO (Raspberry Pi 5)
> **Catatan Kritis RP1 Kernel 6.12+:** RPi 5 menggunakan chip I/O RP1 dengan `gpiochip15` (bukan `gpiochip0`). Selalu gunakan wrapper/fallback `lgpio.gpiochip_open([15, 4, 0])`.

### Pemetaan Aktuator & Sensor (BCM)
- **Relay Solenoid (Active LOW):**
  - **Loker 1 (Kurir Inbound):** BCM `10`
  - **Loker 2 (Penyimpanan Pemilik):** BCM `9`
  - **Loker 3 (Marketplace Pickup):** BCM `6`
  - **Aux Latch (Pintu Tambahan):** BCM `19`
- **Servomotor Trapdoor (MG996R Continuous):**
  - **Servo Kiri:** BCM `13`
  - **Servo Kanan:** BCM `12`
  - *Konfigurasi Kalibrasi (`servo_config.json`):* Durasi pulsa `0.60` detik.
    - Kiri Tutup: `1.0`, Kiri Buka: `-1.0`
    - Kanan Tutup: `-1.0`, Kanan Buka: `1.0`
- **Sensor Jarak & Pintu:**
  - **Ultrasonik HC-SR04:** Trigger BCM `15`, Echo BCM `17`
  - **IR Door Sensor:** BCM `26` (Active LOW = tertutup)
  - **Tombol Fisik Pemilik:** BCM `16` (Active LOW)
- **Indikator & Audio:**
  - **Buzzer:** BCM `21` (Active HIGH)
  - **LED Hijau:** BCM `27` (Active LOW)
  - **LED Merah:** BCM `18` (Active LOW)
- **Tampilan & Input:**
  - **LCD 16x2 I2C:** PCF8574 alamat `0x27` (diberi jeda pacing agar terhindar dari I2C `Errno 121`).
  - **Keypad Matriks 3x4:**
    - Kolom (BCM): `[8, 25, 11]`
    - Baris (BCM): `[5, 1, 0, 7]`
  - **Dual Input Fallback:** Mendukung keyboard USB via `evdev` (`/dev/input/by-id/*kbd*` atau event nodes) jika keypad fisik terlepas.

---

## 4. Alur Kerja & Layanan (Workflows)

1. **Inbound Kurir (Menu 1 / Resi):**
   - Kurir memasukkan 5 digit No Resi via keypad.
   - Sistem validasi resi di DB -> Solenoid Loker 1 (BCM 10) terbuka.
   - Sensor ultrasonik mendeteksi paket masuk -> Servo trapdoor bergerak (0.60s) menjatuhkan paket ke kompartemen aman.
2. **Marketplace Pickup (Menu 2 / OTP):**
   - Pembeli memasukkan 6 digit OTP.
   - Sistem validasi OTP -> Solenoid Loker 3 (BCM 6) terbuka.
3. **Owner Biometric Access (Tombol BCM 16 / Keypad '0'):**
   - Kamera USB `/dev/video0` (Logitech C270) memotret frame.
   - Deteksi wajah via **OpenCV YuNet ONNX** (`face_detection_yunet_2023mar.onnx`).
   - Scheduler Agent (`10.1.1.57:8500`) memutuskan rute inferensi (Local Edge vs Cloud GPU).
   - Cloud GPU (`10.1.1.186:9000`) mencocokkan embedding 512-d InceptionResnetV1 ke galeri user (`Akmal`, `Iqbal`, `Shafwan`, `Syauqi`).
   - Jika cocok: Solenoid Loker 2 (BCM 9) terbuka.
4. **Offline Resilience & Sync:**
   - Jika Cloud offline, keputusan disimpan lokal (`decision_syncer.py`) di SQLite/buffer lokal dan disinkronkan otomatis saat koneksi pulih.

---

## 5. Skrip & Utilitas Penting di Direktori Ini

- `edge_package/edge_mas_controller.py`: Kontroller utama MAS Edge di Raspberry Pi.
- `servo_config.json`: Konfigurasi posisi dan durasi pulsa servo continuous.
- `tweak_servo.py`: Utilitas interaktif kalibrasi sudut/durasi servo MG996R.
- `test_all_solenoids.py`: Skrip diagnostik pengujian 4 solenoid/relay + buzzer (otomatis stop daemon agar tidak bentrok GPIO).
- `check_camera.py`: Skrip uji kamera USB C270 (snapshot YuNet + live HTTP MJPEG stream di port `8088`).
- `cloud_app_main_final.py`: Layanan Cloud Agent FastAPI dengan akselerasi GPU CUDA.
- `migration_agent.py`: Dispatcher offloading & benchmark latensi edge-to-cloud.

---

## 6. Aturan Pengembangan (Development Rules)

1. **Jaga Kompatibilitas GPIO:** Jangan pernah meng-hardcode `chip 0`. Selalu dukung `gpiochip15` untuk Pi 5.
2. **Hindari GPIO Collision:** Sebelum menjalankan tes GPIO manual di Raspberry Pi, pastikan container `edge-hardware-daemon` dihentikan sementara (`docker stop edge-hardware-daemon`), lalu hidupkan kembali setelah selesai.
3. **Database & Timezone:** Pastikan timestamp transaksi dan log menggunakan zona waktu **WIB** (`Asia/Jakarta`).
4. **Deploy ke Edge Pi:** Sinkronisasi file ke Raspberry Pi 224 dilakukan melalui script `edge_package/deploy_edge.sh` atau rsync/scp ke `pi@10.1.1.224:2523:/home/pi/penlock/`.
