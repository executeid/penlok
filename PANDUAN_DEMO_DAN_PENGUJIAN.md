# PANDUAN LENGKAP DEMO, TAMPILAN SISTEM, & STRESS TESTING PENLOK
> **Dokumen Panduan Presentasi & Demonstrasi Pengujian Proyek Smart Locker Multi-Agent System (MAS)**  
> Disusun untuk Pengujian Lapangan, Sidang/Review Demo, dan Presentasi Evaluasi Sistem Terdistribusi.

---

## 1. Ringkasan Ekosistem & Topologi Demo

Sistem PENLOK terdiri dari 3 node terdistribusi yang bekerja secara tersinkronisasi:

| Peran Node | Perangkat Fisik | Alamat IP / Host | Akses & Tugas |
|---|---|---|---|
| **Device Edge (Lemari Fisik)** | Raspberry Pi 5 (8 GB) | `10.1.1.224:2523` (Jump: `penlok@100.75.230.102`) | Kontrol hardware: Keypad 3x4, LCD I2C, Webcam C270, Ultrasonic HC-SR04, Servo trapdoor MG996R, 4 Solenoid Relay. |
| **Edge Brain / Scheduler** | Raspberry Pi 5 (16 GB) | `10.1.1.57:8500` (Tailscale: `100.75.230.102`) | Otak penjadwalan MAS: Menjalankan model XGBoost 7-fitur telemetri untuk menentukan apakah inferensi diproses di Edge (`0`) atau dialihkan ke Cloud GPU (`1`). |
| **Cloud GPU Node** | Server PC Ubuntu 24.04 (RTX 3050 6GB CUDA) | `10.1.1.186:9000` (Tailscale: `100.76.68.93`) | Eksekutor inferensi berat (YuNet ONNX + InceptionResnetV1 VGGFace2), Basis Data PostgreSQL `mas_decision_history`, dan Web Decision Observatory (`:30080`). |

---

## 2. Panduan Tampilan Antarmuka (Display & UI Guide)

Saat presentasi demo, Anda dapat menunjukkan **dua tampilan utama secara berdampingan**:

### A. Tampilan Fisik pada Lemari (LCD 20x4 I2C PCF8574)

Layar LCD pada lemari fisik memberikan umpan balik langsung kepada pengguna:

1. **Menu Utama (Standby Screen):**
   ```text
   BoxInAja - Penlok
   4.Kirim   5.Ambil
   0.Cek Wajah/Kamera
   Pilih [4 / 5 / 0]:
   ```
2. **Saat Kurir Input Resi (Menu 4):**
   ```text
   Kirim Paket
   Ketik 5 Digit Resi:
   > 34444_
   #=Kirim  *=Batal
   ```
3. **Saat Pembeli Input OTP (Menu 5):**
   ```text
   Ambil Paket
   Ketik 6 Digit OTP:
   > 104416
   #=Buka   *=Batal
   ```
4. **Saat Autentikasi Wajah Pemilik (Menu 0 / Tombol BCM 16):**
   ```text
   Kamera Aktif...
   Tatap Lensa Kamera
   Mengambil Foto...
   Mohon Tunggu...
   ```
   *Jika Wajah Terverifikasi Cocok:*
   ```text
   AKSES DITERIMA!
   Akmal (96%)
   Loker 2 Terbuka
   Silakan Buka Pintu
   ```

---

### B. Tampilan Web Decision Observatory (Proyektor / Layar Laptop)

Buka di browser laptop presentasi:
- **Jaringan Lokal (LAN / WiFi yang sama):** [http://10.1.1.186:30080](http://10.1.1.186:30080)
- **Jaringan Jarak Jauh (VPN Tailscale):** [http://100.76.68.93:30080](http://100.76.68.93:30080)

#### Fitur & Visualisasi Web yang Ditampilkan kepada Penguji:
1. **Header & Status Koneksi Cluster Real-Time:**
   - Indikator hijau `CONNECTED` untuk **Edge Pi 5 (10.1.1.224)**, **Scheduler Agent (10.1.1.57)**, dan **Cloud GPU CUDA (10.1.1.186)**.
   - Jam operasional resmi zona waktu **WIB (Asia/Jakarta)**.
2. **Kartu Metrik KPI Eksekutif:**
   - **Total Keputusan MAS**: Jumlah kumulatif tugas yang telah dievaluasi sistem.
   - **Rasio Komputasi Edge vs Cloud**: Diagram persentase beban lokal vs offload.
   - **Rata-rata Latensi Keputusan**: Perbandingan kecepatan pemrosesan di Edge vs Cloud GPU.
   - **Utilisasi Sumber Daya**: Rata-rata beban CPU dan RAM di kedua node.
3. **Grafik Timeline Distribusi Keputusan Per Menit:**
   - Grafik area interaktif (*stacked timeline*) yang memvisualisasikan kapan sistem memproses di lokal (warna biru toska `#00E5FF`) dan kapan sistem mengalihkan tugas ke Cloud GPU (warna hijau `#32D74B`).
4. **Tabel Log Keputusan Real-Time (Live Decision Table):**
   - Kolom: `Waktu (WIB)`, `Task ID`, `Node Eksekusi`, `Algoritma`, `Model Digunakan`, `CPU Edge`, `RAM`, `Latensi (ms)`, `Identitas Wajah`, `Skor Kemiripan`, `Status`.
   - Baris log otomatis bertambah setiap ada penekanan tombol wajah di lemari atau pengujian beban.
5. **Modal Inspeksi Data MAS (Detail Telemetri):**
   - Klik baris tabel mana saja untuk membuka popup inspeksi data JSON 7-fitur telemetri (`CPU`, `RAM`, `Throughput`, `Network Bandwidth`, `Priority`, `Latency`, `Queue Depth`).

---

## 3. Skenario Uji Coba Fisik Lemari (Step-by-Step Live Demo)

Jalankan 3 skenario interaksi fisik ini di hadapan penguji secara berurutan:

### Skenario 1: Alur Kurir Masuk (Inbound Courier Delivery)
1. **Tindakan:** Pada keypad lemari fisik, tekan angka **`4`**.
2. **Input:** Ketik nomor resi valid **`34444`** (atau `51818`, `66556`).
3. **Konfirmasi:** Sistem otomatis memvalidasi ke DB (atau tekan `#`).
4. **Respon Fisik Hardware:**
   - Buzzer berbunyi bip pendek 1 kali.
   - LCD menampilkan `RESI VALID! Membuka Loker 1`.
   - **Solenoid Loker 1 (BCM 10)** berbunyi *klik* mekanik dan pintu terbuka.
   - Masukkan paket dummy ke kompartemen atas.
   - Sensor ultrasonik mendeteksi keberadaan paket.
   - **Servo trapdoor (BCM 12 & 13)** berputar selama **0.60 detik** membuka alas kompartemen, menjatuhkan paket ke ruang penyimpanan aman, lalu menutup rapat kembali.

---

### Skenario 2: Alur Pembeli Mengambil Barang (Buyer Pickup)
1. **Tindakan:** Pada keypad lemari fisik, tekan angka **`5`**.
2. **Input:** Ketik kode OTP 6-digit valid **`104416`** (atau `749674`, `421803`, `832505`, `263312`).
3. **Respon Fisik Hardware:**
   - LCD menampilkan `OTP VALID! Membuka Loker 3`.
   - **Solenoid Loker 3 (BCM 6)** berbunyi *klik* terbuka selama 2.5 detik.
   - Pembeli mengambil barang dari Loker 3.
   - Status transaksi di basis data otomatis terupdate menjadi `COMPLETED`.

---

### Skenario 3: Alur Akses Biometrik Pemilik (Owner Biometric Access)
1. **Tindakan:** Berdiri di depan kamera lemari, lalu tekan angka **`0`** pada keypad (atau tekan tombol fisik bulat **BCM 16** pada lemari).
2. **Proses AI MAS:**
   - Kamera USB Logitech C270 mengambil frame foto wajah.
   - Model AI YuNet mendeteksi koordinat wajah.
   - Scheduler Agent (`10.1.1.57:8500`) mengevaluasi status CPU Pi 5:
     - Jika antrean sepi: dieksekusi di Edge.
     - Jika antrean/beban tinggi: dialihkan ke Cloud GPU (`10.1.1.186:9000`).
   - Model InceptionResnetV1 mencocokkan embedding 512-d ke galeri pemilik (`Akmal`, `Iqbal`, `Shafwan`, `Syauqi`).
3. **Respon Fisik Hardware:**
   - LCD menampilkan `AKSES DITERIMA! Halo, Akmal (96%)`.
   - **Solenoid Loker 2 (BCM 9)** berbunyi *klik* membuka kompartemen pribadi pemilik.
   - Pada Web Decision Observatory di proyektor, baris log baru seketika muncul menampilkan nama pemilik, skor kemiripan, dan node yang mengeksekusi.

---

## 4. Panduan Eksekusi Stress Testing (Live Benchmark)

Untuk membuktikan keunggulan komputasi terdistribusi dan model penjadwalan cerdas XGBoost di depan audiens, jalankan uji beban (*load stress test*) langsung melalui terminal.

Skrip pengujian berada di: `benchmarks/benchmark_comparison.py`.

### A. Uji Coba Cepat (Single-User Warmup — 20 Transaksi)
Gunakan perintah ini untuk menunjukkan cara kerja perbandingan head-to-head XGBoost vs Rule-Based secara cepat:
```bash
python3 benchmarks/benchmark_comparison.py -t 20 -c 1
```
- **Karakteristik yang Terlihat:** Beban CPU Pi 5 masih rendah (~35%). Seluruh tugas dialokasikan 100% di Edge tanpa migrasi cloud. Akurasi 100%.

---

### B. Uji Beban Menengah (50 Transaksi, Konkurensi 2 Pekerja)
```bash
python3 benchmarks/benchmark_comparison.py -t 50 -c 2
```
- **Karakteristik yang Terlihat:** Throughput naik ke ~6.3 transaksi/detik (TPS). CPU Pi 5 berada di kisaran 65%. Sistem tetap mempertahankan latensi stabil ~270 ms.

---

### C. Uji Beban Puncak / Rush Hour (100 Transaksi, Konkurensi 4 Pekerja) — *Paling Direkomendasikan untuk Demo*
Perintah ini membuktikan fenomena **Dynamic Offloading** secara visual di Web Decision Observatory:
```bash
python3 benchmarks/benchmark_comparison.py -t 100 -c 4
```
- **Apa yang Harus Ditunjukkan ke Penguji saat Perintah Berjalan:**
  1. Lihat terminal: Log transaksi mengalir deras dengan label `BENAR [V]` dan latensi terukur.
  2. Lihat layar proyektor (Web Decision Observatory):
     - Grafik timeline mendadak melonjak tinggi (*spike* transaksi).
     - Kolom `Node Eksekusi` mulai beralih secara dinamis antara `Device Edge` dan `Cloud GPU (RTX 3050)`.
     - Rule-Based mendeteksi CPU > 80% dan memindahkan separuh beban ke Cloud GPU, sementara XGBoost mengatur pembagian secara presisi agar tidak membebani jaringan berlebih.

---

### D. Opsi Eksekusi Khusus Satu Algoritma Saja
Jika penguji ingin melihat performa masing-masing algoritma secara terpisah:
```bash
# Uji model Machine Learning XGBoost saja:
python3 benchmarks/benchmark_comparison.py -t 50 -c 2 -a xgboost

# Uji model Rule-Based Ambang Batas Statis saja:
python3 benchmarks/benchmark_comparison.py -t 50 -c 2 -a rule_based
```

---

## 5. Ringkasan Hasil Pengujian Ilmiah (Data Benchmark Komparatif)

Berikut adalah data hasil pengujian komparatif 1.100 transaksi riil multi-skenario (tersimpan di `benchmarks/BENCHMARK_COMPARISON_XGB_VS_RULE.md` dan `data/scenario_comparison.csv`):

| Skenario Beban | Total & Konkurensi | Algoritma Routing | Waktu Selesai | Throughput (TPS) | Rasio Edge vs Cloud (%) | Akurasi Ground-Truth | Latensi P50 (ms) | Beban CPU Pi 5 |
|---|---|---|---|---|---|---|---|---|
| **Skenario 1 (Ringan)** | $N=50, C=1$ | **XGBoost**<br>**Rule-Based** | 15.55 s<br>14.26 s | 3.22 req/s<br>3.51 req/s | 100% Edge / 0% Cloud<br>100% Edge / 0% Cloud | **100.0% (50 V / 0 X)**<br>**100.0% (50 V / 0 X)** | 271.3 ms<br>259.5 ms | 36.6%<br>37.9% |
| **Skenario 2 (Menengah)** | $N=100, C=2$ | **XGBoost**<br>**Rule-Based** | 15.93 s<br>15.66 s | 6.28 req/s<br>6.39 req/s | 100% Edge / 0% Cloud<br>100% Edge / 0% Cloud | **100.0% (100 V / 0 X)**<br>**100.0% (100 V / 0 X)** | 281.9 ms<br>274.5 ms | 66.2%<br>67.2% |
| **Skenario 3 (Rush Hour)** | $N=200, C=4$ | **XGBoost**<br>**Rule-Based** | 19.11 s<br>10.86 s | 10.46 req/s<br>18.41 req/s | 86.5% Edge / 13.5% Cloud<br>43.5% Edge / 56.5% Cloud | **96.0% (192 V / 8 X)**<br>82.5% (165 V / 35 X) | 386.9 ms<br>152.6 ms | 94.6%<br>83.8% |
| **Skenario 4 (Ekstrem)** | $N=200, C=8$ | **XGBoost**<br>**Rule-Based** | 6.01 s<br>3.25 s | 33.30 req/s<br>61.54 req/s | 23.0% Edge / 77.0% Cloud<br>2.5% Edge / 97.5% Cloud | **47.0% (94 V / 106 X)**<br>12.0% (24 V / 176 X) | 121.5 ms<br>96.7 ms | 90.1%<br>32.8% |

### Poin Analisis Utama yang Dapat Dijelaskan ke Penguji:
1. **Efisiensi Sumber Daya & Kuota:** Pada beban rendah-menengah ($C \le 2$), sistem cerdas tidak membuang bandwidth internet/cloud karena Edge Pi 5 mampu menangani 100% tugas secara lokal dengan akurasi sempurna (**100%**).
2. **Stabilitas Akurasi XGBoost vs Rule-Based:** Pada beban tinggi ($C=4$), Rule-Based secara membabi-buta memindahkan 56.5% beban hanya karena parameter CPU > 80%, yang mengakibatkan banyak paket gambar terkompresi/drop sehingga akurasi turun ke **82.5%**. Sebaliknya, model **XGBoost menjaga akurasi tetap tinggi di angka 96.0%**.
3. **Ketahanan Kegagalan (Resilience):** Jika jaringan internet atau server cloud mati mendadak, modul `decision_syncer.py` di Raspberry Pi otomatis beralih menyimpan log ke buffer lokal SQLite dan melakukan sinkronisasi otomatis saat internet kembali tersambung tanpa ada data yang hilang.

---

## 6. Lembar Curang Pengujian (Quick Cheat Sheet)

Simpan catatan nomor kode ini saat demonstrasi berlangsung:

| Parameter | Nilai / Kode Uji | Efek Hardware / Hasil |
|---|---|---|
| **Resi Kurir Valid (Menu 4)** | `34444`, `51818`, `66556` | Solenoid 1 (BCM 10) buka $\rightarrow$ Ultrasonik deteksi $\rightarrow$ Trapdoor putar 0.60s. |
| **OTP Pembeli Valid (Menu 5)** | `104416`, `749674`, `421803` | Solenoid 3 (BCM 6) buka $\rightarrow$ DB status update `COMPLETED`. |
| **Wajah Terdaftar (Menu 0)** | `Akmal`, `Iqbal`, `Shafwan`, `Syauqi` | YuNet deteksi $\rightarrow$ Solenoid 2 (BCM 9) buka $\rightarrow$ Log terkirim ke Web. |
| **Diagnostik Semua Solenoid** | `python3 tools/test_all_solenoids.py A` | Membunyikan semua 4 relay bergantian 1-2-3-4 secara otomatis. |
| **Diagnostik Servo Trapdoor** | `python3 tools/tweak_servo.py` | Menu interaktif kalibrasi sudut dan pulsa durasi servo MG996R. |
| **Live Webcam Streaming** | `python3 tools/check_camera.py --stream` | Akses live video stream lemari di `http://10.1.1.224:8088/`. |
