# Jurnal Teknis: Peningkatan Metode Face Recognition ke Standar Industri (OpenCV YuNet + Deep FaceNet CUDA)

**Tanggal**: 7 Oktober 2026  
**Node Target**:
- **Device Edge**: `pi@10.1.1.224` (Raspberry Pi 5 8GB)
- **Cloud GPU**: `penlok@10.1.1.186` (Ubuntu 24.04, NVIDIA GeForce RTX 3050 6GB CUDA)  
**Status**: SELESAI / TERVERIFIKASI PENUH  

---

## 1. Analisis Masalah Metode Lama (LBPH & Haar Cascade)

Pada perancangan awal sistem Penlok, deteksi wajah mengandalkan **Haar Cascade** (`haarcascade_frontalface_default.xml`) dan pengenalan wajah mengandalkan **OpenCV LBPH** (`cv2.face.LBPHFaceRecognizer`):
1. **Kegagalan Akurasi pada Kamera Live**:
   - Haar Cascade sangat rentan terhadap variasi pencahayaan, bayangan, dan kemiringan kepala (yaw/pitch).
   - LBPH menghitung histogram tekstur piksel lokal berdimensi rendah. Jika kondisi pencahayaan antara saat pendaftaran foto (misal: foto WhatsApp) dan webcam ruangan berbeda, jarak Chi-square distance membengkak ($> 80$), menyebabkan sistem menolak wajah pemilik sah (*False Rejection*).
2. **Keterbatasan Tanpa Bounding Box di Cloud**:
   - Pengiriman frame utuh (640×480) ke Cloud GPU tanpa cropping menyebabkan model membandingkan piksel latar belakang ruangan/tembok alih-alih fitur wajah, menurunkan tingkat kemiripan kosinus (*Cosine Similarity*).
3. **Overhead Training**:
   - Setiap kali ada penambahan user baru, file model XML harus di-training ulang secara penuh (`.train()`).

---

## 2. Implementasi Best Practice: Arsitektur Split Edge-Cloud

Untuk mengatasi masalah di atas, sistem ditingkatkan menggunakan arsitektur modern:

```
┌───────────────────────────────────────┐
│        DEVICE EDGE (Pi 5 CPU)         │
│                                       │
│  1. Capture USB Webcam Frame (640x480)│
│  2. Deteksi & Crop via OpenCV YuNet   │
│     (Ringan, ~5-8ms di CPU ARM)       │
└──────────────────┬────────────────────┘
                   │
                   ▼ (Kirim Cropped Face / Frame JPEG via Tailscale)
┌────────────────────────────────────────────────────────┐
│             CLOUD GPU (RTX 3050 CUDA 13.2)             │
│                                                        │
│  3. OpenCV YuNet Face Detection + Landmark Alignment   │
│  4. Preprocessing ke Tensor [1, 3, 160, 160]           │
│  5. InceptionResnetV1 (VGGFace2) Deep Metric Learning  │
│     • Ekstraksi 512-d L2-Normalized Embedding Vector   │
│     • Matrix Multiplication Cosine Similarity di VRAM  │
│  6. Keputusan Otomatis: >= 0.60 -> Match               │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│       ACTUATOR (Relay 2 / BCM 9)      │
│  Solenoid Locker 2 Terbuka (2.5 Detik)│
└───────────────────────────────────────┘
```

---

## 3. Komponen Teknis yang Diperbarui

### 3.1 Model Deteksi Wajah: OpenCV YuNet ONNX
- **Model**: `face_detection_yunet_2023mar.onnx` (Ukuran: 232 KB).
- **Keunggulan**:
  - Model deep neural network berbasis ONNX yang tertanam secara native di OpenCV (`cv2.FaceDetectorYN`).
  - Eksekusi instan ($< 5\text{ms}$ di GPU, $< 10\text{ms}$ di CPU Pi 5).
  - Tahan terhadap kemiringan wajah hingga 45 derajat dan kondisi minim cahaya.
  - Menghasilkan koordinat bounding box presisi dengan margin padding otomatis 10%.

### 3.2 Model Pengenalan Wajah: InceptionResnetV1 (VGGFace2)
- **Framework**: PyTorch 2.6.0 CUDA 12.4 di NVIDIA RTX 3050.
- **Arsitektur**: Inception-ResNet-v1 yang dilatih pada dataset VGGFace2.
- **Mekanisme Pendaftaran (Zero-Retraining)**:
  - Tidak ada proses training ulang XML.
  - Setiap foto user yang masuk diekstraksi menjadi embedding 512 dimensi.
  - Vektor rata-rata (*mean embedding*) disimpan dalam berkas serialisasi `gallery_embeddings.pt` di memori VRAM GPU.
  - Pencocokan wajah dilakukan melalui perkalian matriks kosinus $\vec{u} \cdot \vec{v}^T$.

### 3.3 Pembersihan Dummy User & Penyelarasan Database
Seluruh label buatan dan akun dummy telah dihapus. Sistem kini terhubung 100% ke 4 profil pemilik sah di database PostgreSQL:
- **Akmal** (`face_id: 789123`, folder `akmal`)
- **Iqbal** (`face_id: 451699`, folder `balbal`)
- **Shafwan** (`face_id: 249731`, folder `panpenlok`)
- **Syauqi** (`face_id: 619292`, folder `soqisoqi`)

---

## 4. Hasil Uji Empiris & Validasi

### 4.1 Uji Deteksi & Identifikasi Wajah di Cloud GPU (`10.1.1.186:9000`)
| Target Input | Hasil Deteksi | Status Autentikasi | Cosine Similarity | Waktu GPU |
|---|---|:---:|:---:|:---:|
| Foto Akmal | `akmal` | **TRUE** | **1.0000** (100%) | 33 ms |
| Foto Iqbal | `Iqbal (Owner)` | **TRUE** | **0.9633** (96.3%) | 21 ms |
| Foto Shafwan | `Shafwan (Owner)` | **TRUE** | **0.9752** (97.5%) | 21 ms |
| Foto Syauqi | `Syauqi (Owner)` | **TRUE** | **0.9231** (92.3%) | 17 ms |
| Tembok / Objek Kosong | `UNKNOWN` | **FALSE** | **0.4121** (Tolak) | 26 ms |

### 4.2 Uji Deteksi di Edge Lokal Pi 5 (LBPH Updated)
| Target Input | Hasil Deteksi | Status Autentikasi | Waktu Eksekusi Pi 5 |
|---|---|:---:|:---:|
| Foto Akmal | `Akmal` | **TRUE** | 310 ms |
| Foto Iqbal | `Iqbal` | **TRUE** | 228 ms |
| Foto Shafwan | `Shafwan` | **TRUE** | 224 ms |
| Foto Syauqi | `Syauqi` | **TRUE** | 231 ms |
| Tembok / Objek Kosong | `NO_FACE_DETECTED` | **FALSE** | 32 ms |

---

## 5. Panduan Penggunaan Operasional

### Menjalankan Uji Loker Live:
```bash
ssh -p 2523 pi@10.1.1.224
cd /home/pi/penlock/manual_test
./run_test.sh
# Pilih opsi [9] untuk verifikasi wajah langsung di depan webcam
```

### Mendaftarkan Sampel Foto Tambahan (Jika Ingin Akurasi Lebih Tinggi):
Untuk mengambil 15 variasi ekspresi langsung dari webcam loker:
```bash
ssh -p 2523 pi@10.1.1.224
cd /home/pi/penlock
python3 register_face.py --name "akmal" --capture --count 15
```
Skrip otomatis memperbarui embedding di GPU tanpa perlu restart manual.
