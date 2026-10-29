# Jurnal Perbaikan & Modifikasi Sistem Penlock

**Tanggal**: 25 September 2026  
**Target Host**: `pi@10.1.1.224:2523`  
**Direktori Kerja Remote**: `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan`  
**Environment**: Pyenv `penlok` (Python 3.9.20) / Raspberry Pi 5 Model B Rev 1.1 (Linux 6.12.109 aarch64)

---

## 1. Analisis & Perbaikan Bug GPIO (RPi 5 Kernel 6.12)

### Gejala Error
Saat menjalankan `python3 pan-piXarduino-fixed.py`:
```text
PinFactoryFallback: Falling back from lgpio: 'can not open gpiochip'
KeyError: PinInfo(number=31, name='GPIO6'...)
RuntimeError: Cannot determine SOC peripheral base address
```

### Akar Masalah
1. RPi 5 menggunakan chip RP1 (`pinctrl-rp1`) untuk 40-pin header GPIO.
2. Kernel Linux 6.12 memetakan kontroler RP1 ke `/dev/gpiochip15`. Tidak ada `/dev/gpiochip0` atau `/dev/gpiochip4`.
3. Pustaka `gpiozero` v2.0.1 hardcode pengecekan chip ke `4` untuk RPi 5 (`gpiozero/pins/lgpio.py:66`), gagal membuka chip, lalu fallback ke driver legacy `RPi.GPIO`.
4. `RPi.GPIO` tidak mendukung basis memori periferal RPi 5, melempar `RuntimeError`.
5. Kode hardware (`pan-piXarduino-fixed.py`, `cobav2.py`, `cobaface.py`) hardcode pemanggilan `lgpio.gpiochip_open(0)`.

### Tindakan & Patch
1. **Patch Driver `gpiozero`**:
   - Berkas: `/home/pi/.pyenv/versions/penlok/lib/python3.9/site-packages/gpiozero/pins/lgpio.py`
   - Logika: Menambahkan probing dinamis kandidat chip `[15, 4, 0]`. Otomatis memilih chip 15.
2. **Patch Skrip Hardware**:
   - Berkas: `pan-piXarduino-fixed.py`, `cobaface.py`, `cobav2.py`
   - Logika: Menambahkan fungsi helper `_get_gpio_chip()` untuk deteksi chip RP1 yang aktif sebelum memanggil `lgpio.gpiochip_open()`.
3. **Pin Hardware**:
   - Tidak ada pin BCM yang diubah. Seluruh pin relay (6, 9, 10, 19), sensor ultrasonik (TRIG 15, ECHO 17), loadcell (DOUT 4, SCK 14), getar (24), IR (26), dan keypad (kolom 8, 25, 11; baris 5, 1, 0, 7) tetap sama.

---

## 2. Analisis Peran Komponen Kamera & Wajah

1. **`face.py`**:
   - Modul aktif pengenalan wajah.
   - Mengambil data user langsung dari PostgreSQL (`users_user`), verifikasi Haar cascade lokal, dan upload dataset/verifikasi log ke endpoint Django `/api/v1/facerecognition/`.
   - Diimpor langsung oleh `cobaface.py`.
2. **`camowner.py`**:
   - Preview kamera GUI Tkinter biasa selama 5 detik (`AUTO_OFF = 5`).
   - Tidak memiliki fungsi deteksi wajah ataupun integrasi database.
3. **`cobametodev2.py`**:
   - Prototipe awal terminal raw berbasis menu sebelum dipecah menjadi modul `face.py`.
4. **`cobametode.py`**:
   - Eksperimen awal training LBPH lokal offline tanpa backend Django.

---

## 3. Modifikasi Navigasi Keypad & LCD (`pan-piXarduino-fixed.py`)

### A. Menu Utama (Diubah dari 1/2 ke 4/5)
- **Tampilan LCD (`def menu_utama()`)**:
  - `3. Kirim Paket` -> `4. Kirim Paket`
  - `4. Ambil Paket` -> `5. Ambil Paket`
- **Logika Keypad (`if state == 'menu_utama'`)**:
  - Tekan `4` -> Masuk ke `state = 'menu_kirim'`
  - Tekan `5` -> Masuk ke `state = 'menu_ambil'`

### B. Sub-Menu Kirim Paket (Diubah dari 1/2 ke 4/5)
- **Tampilan LCD (`def menu_kirim()`)**:
  - `1. Scan QR` -> `4. Scan QR`
  - `2. Masukkan Resi` -> `5. Masukkan Resi`
- **Logika Keypad (`elif state == 'menu_kirim'`)**:
  - Tekan `4` -> Masuk ke `state = 'menu_scan_qr'` (menjalankan `cobav2.py`)
  - Tekan `5` -> Masuk ke `state = 'menu_input_id_kirim'` (input 5 digit resi manual)

---

## 4. Referensi Kode Verifikasi Database PostgreSQL

### Pengambilan Paket ("5. Ambil Paket")
- **Tabel**: `marketplace_transaction` (kolom `otp`)
- **Format**: 6 Digit Numerik
- **Contoh OTP Siap Ambil (`AWAITING_PICKUP`)**:
  - `104416` (Transaksi ID 13 - nasi box)
  - `575082` (Transaksi ID 12 - Router)
  - `421803` (Transaksi ID 11 - tes produk 2)
  - `301976` (Transaksi ID 10 - Tes Produk 1)
  - `117632` (Transaksi ID 9 - tes produk 2)
  - `082346` (Transaksi ID 8 - coba)
  - `357962` (Transaksi ID 7 - Tes Produk 1)

### Pengiriman Paket ("4. Kirim Paket" -> "5. Masukkan Resi")
- **Tabel**: `package_center_packageentry` (kolom `tracking_number`)
- **Format**: 5 Digit Terakhir Resi (`RIGHT(tracking_number, 5)`)
- **Contoh Kode 5 Digit Valid**:
  - `66556` (Resi: `SPX566556` - Kacamata)
  - `87766` (Resi: `SPX99887766` - Jaket)
  - `27272` (Resi: `SPX152527272` - paketyt)
  - `51818` (Resi: `SPX029282727151818` - hahahaba)
  - `34444` (Resi: `123334444` - balbox1)

---

## 5. Berkas Cadangan (Backup Files)

Jika ingin melakukan rollback ke kondisi awal:
1. `pan-piXarduino-fixed.py.bak` (sebelum patch GPIO)
2. `pan-piXarduino-fixed.py.bak_menu12` (sebelum modifikasi menu keypad 1/2)
3. `cobaface.py.bak_pre_gpiofix` (sebelum patch GPIO pada skrip face)
4. `cobav2.py.bak` (sebelum patch GPIO pada QR scanner)
5. `gpiozero/pins/lgpio.py.bak` (cadangan driver asli gpiozero)

---

## 6. Sesi Perbaikan Lanjutan (26 September 2026) via Jump Host `tcc@100.76.68.93`

### Akses Jaringan
- Koneksi ke target dialihkan melalui jump host:
  `ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224`

### Masalah Teridentifikasi & Solusi
1. **Fallback Global `lgpio.gpiochip_open`**:
   - Gejala: Skrip warisan (`pan-piXarduino.py`, `kalibrasi/tarescalefactor.py`, dsb.) memanggil `lgpio.gpiochip_open(0)` dan melempar `lgpio.error: 'can not open gpiochip'` karena RP1 pada RPi 5 berada di `gpiochip15`.
   - Solusi: Patch langsung pada `lgpio.gpiochip_open()` di pyenv `penlok`, venv `penlock`, dan sistem python `/usr/lib/python3/dist-packages/lgpio.py`. Jika membuka chip gagal, otomatis mencoba kandidat `[15, 4, 0]`.
2. **Environment & PATH Non-Interaktif**:
   - Gejala: Pemanggilan SSH non-interaktif atau skrip menjalankan `/usr/bin/python3` (Python 3.11 Debian tanpa modul `RPLCD`), menyebabkan `ModuleNotFoundError: No module named 'RPLCD'`.
   - Solusi: Pindahkan inisialisasi Pyenv (`PYENV_ROOT`, `shims`, `eval "$(pyenv init -)"`) ke bagian paling atas `~/.bashrc` (sebelum pengecekan interaktif `case $- in`) dan tambahkan ke `~/.profile`.
3. **Orphaned Background Process Mengunci GPIO (`lgpio.error: 'GPIO busy'`)**:
   - Gejala: Proses python latar belakang lama masih menahan handle `/dev/gpiochip15`, menyebabkan `OutputDevice(6)` melempar `GPIO busy`.
   - Solusi: Matikan proses orphaned (PID 162098, 213992). Semua pin GPIO kembali bersih.
4. **Subprocess Interpreter & Import Hang**:
   - `loadcellfinal.py`: Tambahkan pembungkus `if __name__ == '__main__':` agar tidak hang saat diimpor skrip lain.
   - `cobaface.py`, `camowner.py`, `camtimer.py`: Gunakan `sys.executable` dan fallback default `DISPLAY=:0`.

