# Laporan Pelaksanaan Tahap 12: Rekonstruksi Web Interface Khusus Log Keputusan Multi-Agen (MAS Decision Observatory)

**Dokumen Rujukan**: `DESIGN_WEB.md` & `PRD_WEB.md`  
**Sasaran Rekonstruksi**: Mengeliminasi seluruh modul sampingan (kurir, nomor resi, marketplace, login majemuk) dan memfokuskan antarmuka web 100% pada **Pemantauan Keputusan Komputasi Multi-Agen (Lokal di Edge vs. Migrasi ke Cloud GPU)**.  
**Target Node Deployment**: `penlok@10.1.1.186:30080` (Namespace: `cloud-agent`)  
**Image Container**: `smartbox-web:v8`  
**Status**: SUKSES / LIVE RUNNING  

---

## 1. Ringkasan Perubahan & Eliminasi Slop

Sesuai instruksi dan evaluasi antislop:
1. **Modul yang Dihapus Total**:
   - Form pendaftaran kurir & pelacakan resi belanja online.
   - Pintu masuk login ganda / simulasi role switcher.
   - Panel loker marketplace 3 kompartemen.
   - Sisa-sisa perhitungan kelistrikan/WattVision.
2. **Fokus Baru Tunggal (Single-Purpose Dashboard)**:
   - Antarmuka dirancang sebagai **"PENLOK MAS // DECISION & OFFLOAD OBSERVATORY"**.
   - Menampilkan metrik ilmiah dan catatan riil: apakah setiap tugas verifikasi wajah dijalankan **LOKAL DI EDGE (Pi 5)** atau **DIMIGRASIKAN KE CLOUD GPU (RTX 3050)**.
   - Menampilkan 7 variabel fitur telemetri yang mendasari keputusan model XGBoost secara transparan.

---

## 2. Struktur Antarmuka Baru Sesuai `DESIGN_WEB.md`

### 2.1 Header & Status Koneksi Node
- Menampilkan status langsung 3 node infrastruktur:
  - **Edge Pi 5** (`10.1.1.224`)
  - **Scheduler Brain** (`10.1.1.57:8500`, Model: `XGBoost v2.0`)
  - **Cloud GPU** (`10.1.1.186:9000`, Akselerator: `NVIDIA RTX 3050 CUDA`)
- Tombol sakelar **Auto-Refresh (3 detik)** dan tombol segarkan manual.

### 2.2 4 Kartu Metrik Utama (KPIs)
- **Total Tugas Dievaluasi**: Jumlah seluruh permintaan verifikasi wajah.
- **Diproses Lokal di Edge (0)**: Jumlah dan persentase tugas yang dieksekusi di CPU Pi 5 saat beban normal ($\le 75\%$ CPU), dilengkapi indikator visual hijau (`#32D74B`).
- **Dimigrasikan ke Cloud GPU (1)**: Jumlah dan persentase tugas yang dialihkan ke GPU RTX 3050 saat beban tinggi ($> 75\%$ CPU), dilengkapi indikator visual sian (`#00E5FF`).
- **Rata-rata Waktu Tanggap**: Membandingkan waktu eksekusi GPU (misal: 148.9 ms / rata-rata inferensi murni 15–35 ms) dengan CPU Edge (272.4 ms).

### 2.3 Grafik Garis Waktu Keputusan Riil (12-Grid System)
- **Kurva Area SVG 8 Kolom**:
  - Memetakan titik data kronologis beban prosesor Pi 5 (%) dengan kurva bezier gradien `#00E5FF` $\rightarrow$ `#32D74B` $\rightarrow$ `#121212`.
  - Garis putus-putus merah menandai ambang batas beban kritis CPU ($75\%$).
  - Titik lingkaran membedakan tugas yang dialihkan (lingkaran sian) vs diproses lokal (lingkaran hijau).
- **Panduan Logika Model 4 Kolom**:
  - Rincian aturan model XGBoost dan pencegahan thermal throttling pada perangkat tepi.

### 2.4 Tabel Log Keputusan Real-Time (Core Component)
- **Filter Cepat**: `Semua (300)`, `Lokal di Edge (150)`, `Migrasi ke Cloud (150)`.
- **Kolom Tabel**:
  1. *No*
  2. *Waktu*
  3. *Task ID*
  4. *Keputusan Alur*: Badge `LOKAL EDGE (0)` vs `MIGRASI CLOUD (1)`
  5. *Node Pelaksana*: `Perangkat Tepi (Pi 5)` vs `Cloud GPU (RTX 3050)`
  6. *Beban CPU & RAM*
  7. *Waktu Proses (ms)*
  8. *Identitas Hasil*: Akmal, Iqbal, Shafwan, Syauqi, atau Ditolak
  9. *Aksi*: Tombol inspeksi `[Detail Vektor]`
- **Modal Inspeksi Vektor 7 Fitur**:
  - Membuka modal interaktif saat tombol mata diklik.
  - Membedah vektor masukan lengkap: CPU%, RAM%, Latensi ms, Prioritas, Antrean, Throughput, Bandwidth, Skor Keyakinan Model, dan Catatan Alur.

---

## 3. Integrasi Backend Riil (Zero-Mock Data)

1. **Endpoint Log Keputusan (`/api/decision-logs`)**:
   - Dihubungkan langsung ke basis data PostgreSQL `penlok_cloud` pada tabel `mas_decision_history`.
   - Mengembalikan ringkasan KPI dan 50 catatan keputusan terbaru secara dinamis.
2. **Koneksi Node Sensor & Telemetri**:
   - Nginx proxy meneruskan data ke Cloud GPU (`:9000`), Scheduler (`:8500`), dan Edge Pi 5 (`:8600`).

---

## 4. Status Deployment K3s Cloud Node

- **Klaster**: `pengmas-tri` (`10.1.1.186`)
- **Namespace**: `cloud-agent`
- **Pod Deployment**: `smartbox-web-deployment` (Image: `smartbox-web:v8`, Status: `Running 1/1`)
- **Service**: `smartbox-web-service` (`NodePort: 30080`)
- **Akses Langsung Browser**:
  - Jaringan Lokal / LAN: **`http://10.1.1.186:30080`**
  - Tailscale VPN: **`http://100.76.68.93:30080`**
