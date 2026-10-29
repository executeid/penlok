# Laporan Pelaksanaan Tahap 1: Pembersihan Dependensi MQTT (Cleanup & Simplifikasi Arsitektur)

**Dokumen Rujukan**: `plan/01_cleanup_mqtt.md`  
**Target Node**:
- `penlok@10.1.1.57` (K3s Edge Brain)
- `pi@10.1.1.224:2523` (Device Edge)  
**Status**: SUKSES / TERVERIFIKASI

---

## 1. Ringkasan Eksekutif

Tahap 1 bertujuan menghapus seluruh dependensi MQTT (Eclipse Mosquitto dan library `paho-mqtt`) dari klaster K3s Edge Brain dan host Device Edge. Arsitektur disederhanakan menjadi berbasis HTTP REST dan append file langsung, menghilangkan overhead sinkronisasi broker, deprecation warnings, dan socket drops.

Semua target pekerjaan telah dieksekusi dan diverifikasi pada kedua node.

---

## 2. Pekerjaan pada Node K3s Edge Brain (`penlok@10.1.1.57`)

### 2.1 Penghapusan Komponen Mosquitto dari Klaster K3s
Perintah pembersihan dieksekusi:
```bash
sudo kubectl delete deployment mqtt-broker -n default
sudo kubectl delete svc mqtt-broker -n default
sudo kubectl delete configmap mosquitto-config -n default
```
Hasil:
- Deployment `mqtt-broker` berhasil dihapus.
- Service `mqtt-broker` (ClusterIP `10.43.17.173:1883`) berhasil dihapus.
- ConfigMap `mosquitto-config` berhasil dihapus.
- Pod `mqtt-broker` telah diterminasi tuntas.

### 2.2 Refaktor `edge-agent` K3s
- File diubah: `/home/penlok/edge-agent/app/main.py`
  - Inisialisasi `EdgeMQTTClient` dan pemanggilan `mqtt_client.publish_telemetry()` dihapus seluruhnya.
  - Siklus monitoring metrik resource (`SystemMonitor.get_metrics()`) dan perekaman CSV (`log_to_csv()`) dipertahankan sepenuhnya.
  - Ditambahkan penanganan pemulihan `task_id_counter` dari baris terakhir berkas CSV yang ada untuk menjaga kontinuitas data saat pod restart.
- File konfigurasi K3s diperbarui: `/home/penlok/edge-agent/k8s/edge-agent.yaml`
  - Environment variable `MQTT_BROKER` dihapus.
- Ditambahkan berkas `.dockerignore` untuk mengecualikan arsip tar dan log agar proses build container efisien.
- Container image dibangun ulang dan diimpor ke containerd K3s:
  ```bash
  sudo docker build -t edge-agent:latest -f docker/Dockerfile .
  sudo docker save edge-agent:latest > edge-agent.tar
  sudo k3s ctr images import edge-agent.tar
  sudo kubectl apply -f k8s/edge-agent.yaml
  sudo kubectl rollout restart deployment/edge-agent
  ```
- Hasil status pod:
  - Pod `edge-agent` baru berjalan stabil dalam status `Running` (0 restart).
  - Log pod bersih dari error pengiriman MQTT (`Failed to publish message. Error code: 4` hilang total).
  - Perekaman telemetri ke `/edge-agent/data/dataset_smartbox.csv` diverifikasi aktif bertambah baris setiap interval waktu.

### 2.3 Status Port 1883 pada Edge Brain
- Perintah `sudo ss -tulpn | grep 1883` menghasilkan output kosong.
- Port 1883 tertutup sepenuhnya pada `10.1.1.57`.

---

## 3. Pekerjaan pada Node Device Edge (`pi@10.1.1.224:2523`)

### 3.1 Penonaktifan Service Mosquitto di Host
Perintah dieksekusi:
```bash
sudo systemctl stop mosquitto
sudo systemctl disable mosquitto
```
Hasil:
- Unit service `mosquitto.service` dihentikan dan dinonaktifkan dari startup systemd.
- Perintah `sudo ss -tulpn | grep 1883` menghasilkan output kosong (port 1883 tertutup sepenuhnya).

### 3.2 Pembersihan Dependensi dan Kode MQTT pada Skrip Hardware
Berkas yang dimodifikasi:
1. `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/pan-piXarduino-fixed.py`
2. `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/cobaface.py`

Tindakan perbaikan:
- Hapus impor `import paho.mqtt.client as mqtt`.
- Hapus blok konfigurasi MQTT (`MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_TOPIC_COMMAND`).
- Hapus callback MQTT `on_connect`, `on_message`, dan inisialisasi `client = mqtt.Client()`.
- Hapus fungsi `setup_mqtt_client()` dan pemanggilannya pada inisialisasi skrip.
- Tambahkan fungsi mandiri `open_locker(locker_number)` yang memicu relay lokal via `trigger_relay()` dan notifikasi HTTP REST backend.
- Kompilasi sintaks Python diverifikasi sukses via `py_compile`.

### 3.3 Pencopotan Dependensi `paho-mqtt`
- Paket `paho-mqtt 2.1.0` dicopot dari virtualenv hardware `/home/pi/.pyenv/versions/3.9.20/envs/penlok/`:
  ```bash
  /home/pi/.pyenv/versions/3.9.20/envs/penlok/bin/pip uninstall -y paho-mqtt
  ```
- Peringatan `DeprecationWarning: Callback API version 1 is deprecated` telah dihilangkan seiring dihapusnya inisialisasi client MQTT.

---

## 4. Matriks Kriteria Keberhasilan (Acceptance Criteria)

| No | Kriteria Keberhasilan | Target Node | Status | Bukti / Catatan Verifikasi |
|---|---|---|---|---|
| 1 | Pod `mqtt-broker` tidak ada lagi di klaster K3s | `10.1.1.57` | **TERPENUHI** | `sudo kubectl get pods -A \| grep -i mqtt` -> kosong |
| 2 | Port 1883 tertutup di kedua host | `10.1.1.57` & `10.1.1.224` | **TERPENUHI** | `sudo ss -tulpn \| grep 1883` -> kosong di kedua host |
| 3 | Pod `edge-agent` mencatat baris baru stabil ke PVC CSV | `10.1.1.57` | **TERPENUHI** | Baris bertambah secara real-time di `/edge-agent/data/dataset_smartbox.csv` |
| 4 | Skrip hardware bersih tanpa `DeprecationWarning` | `10.1.1.224` | **TERPENUHI** | `paho-mqtt` dihapus dari kode dan virtualenv |

---

## 5. Kesimpulan
Tahap 1 pembersihan dependensi MQTT telah selesai sepenuhnya sesuai spesifikasi `plan/01_cleanup_mqtt.md`. Sistem siap melanjutkan ke Tahap 2 (`plan/02_cloud_gpu_agent.md`).
