# Tahap 1: Pembersihan Dependensi MQTT (Cleanup & Simplifikasi Arsitektur)

**Dokumen**: `plan/01_cleanup_mqtt.md`  
**Target Node**:
- `penlok@10.1.1.57` (K3s Edge Brain)
- `pi@10.1.1.224:2523` (Device Edge)

---

## 1. Latar Belakang & Rasionalisasi
Pada perancangan awal, protokol MQTT (Eclipse Mosquitto) direncanakan sebagai bus data telemetri dan antrean perintah relay. Namun, berdasarkan audit implementasi riil dan dokumen `Dokumentasi.pdf`:
1. **Redundansi Telemetri**: Seluruh metrik resource node (`node-exporter` port 9100 & port 31100) sudah di-scrape secara periodik oleh server Prometheus dan divisualisasikan di Grafana via HTTP.
2. **Redundansi Logging Dataset**: Perekaman dataset telemetri (`dataset_smartbox.csv`) dilakukan melalui append langsung ke file storage volume PVC K3s, bukan lewat broker MQTT.
3. **Standarisasi Kontrak API**: `Dokumentasi.pdf` secara eksplisit mewajibkan pengalihan tugas menggunakan REST API (`POST /migration`), bukan topik MQTT.
4. **Beban Pemeliharaan Jaringan**: Menghubungkan dua broker Mosquitto lintas node memerlukan bridging dua arah yang rawan delay, desinkronisasi connection socket, dan pesan drop.

Dengan menghapus MQTT, arsitektur menjadi **stateless**, berbasis HTTP REST murni, hemat sumber daya memori, dan deterministik.

---

## 2. Rincian Pekerjaan di Edge Brain (`10.1.1.57`)

### 2.1 Menghapus Komponen Mosquitto dari Klaster K3s
Eksekusi pembersihan resource K3s:
```bash
# 1. Hapus Deployment MQTT Broker
kubectl delete deployment mqtt-broker -n default

# 2. Hapus Service MQTT Broker
kubectl delete svc mqtt-broker -n default

# 3. Hapus ConfigMap konfigurasi Mosquitto
kubectl delete configmap mosquitto-config -n default
```

### 2.2 Re-faktor `edge-agent` K3s (Tanpa Publikasi MQTT)
Berkas: `/home/penlok/edge-agent/app/main.py`
- Hapus inisialisasi `EdgeMQTTClient` dan pemanggilan `mqtt_client.publish_telemetry()`.
- Pertahankan fungsi pengumpulan metrik `SystemMonitor.get_metrics()` dan logging CSV `log_to_csv()`.
- Kode simplified `main.py`:
  ```python
  import time
  import logging
  from app.config import PUBLISH_INTERVAL, CSV_FILE
  from app.monitor import SystemMonitor
  from app.main import setup_csv_logger, log_to_csv

  logger = logging.getLogger("edge_agent.main")

  def main():
      logger.info("Starting Edge Agent (Standalone Telemetry Mode)...")
      setup_csv_logger()
      try:
          while True:
              telemetry = SystemMonitor.get_metrics()
              log_to_csv(telemetry)
              time.sleep(PUBLISH_INTERVAL)
      except KeyboardInterrupt:
          logger.info("Edge Agent stopped by user.")

  if __name__ == "__main__":
      main()
  ```
- Update image pod `edge-agent` dan deploy ulang manifes.

---

## 3. Rincian Pekerjaan di Device Edge (`10.1.1.224`)

### 3.1 Menonaktifkan Service Mosquitto di Host
```bash
# Hentikan dan disable service mosquitto agar tidak memakai port 1883
sudo systemctl stop mosquitto
sudo systemctl disable mosquitto
```

### 3.2 Membersihkan Kode MQTT di Skrip Hardware
Berkas:
- `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/pan-piXarduino-fixed.py`
- `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/cobaface.py`

Tindakan modifikasi:
1. Hapus impor `import paho.mqtt.client as mqtt`.
2. Hapus callback `on_connect`, `on_message`, dan inisialisasi `client = mqtt.Client()`.
3. Hapus baris pemanggilan `client.loop_start()` dan `client.subscribe("penlok/command")`.
4. Ganti pemanggilan perintah buka loker dengan fungsi lokal atau REST listener internal.

---

## 4. Kriteria Keberhasilan (Acceptance Criteria)
1. Perintah `kubectl get pods -A` di `10.1.1.57` tidak lagi menampilkan pod `mqtt-broker`.
2. Port 1883 tidak lagi terbuka di `10.1.1.57` maupun `10.1.1.224` (`ss -tulpn | grep 1883` bernilai kosong).
3. Pod `edge-agent` tetap mencatat baris baru secara stabil ke `/edge-agent/data/dataset_smartbox.csv`.
4. Skrip hardware berjalan bersih tanpa pesan peringatan:
   `DeprecationWarning: Callback API version 1 is deprecated`.
