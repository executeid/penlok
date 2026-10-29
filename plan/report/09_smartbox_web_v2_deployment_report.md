# Laporan Pelaksanaan Tahap 9: Pengembangan Web Interface Modern (SmartBox Web v2) & Deployment K3s Cloud Node

**Dokumen Rujukan**: `PRD_WEB.md` & `DESIGN_WEB.md` (TerminalUI Design System)  
**Target Node Deployment**: `penlok@10.1.1.186` (Cloud GPU Node `pengmas-tri`)  
**Klaster K3s**: Single-node Kubernetes `v1.36.3+k3s1` (Namespace: `cloud-agent`)  
**Status**: SUKSES / LIVE RUNNING (Port `30080`)  

---

## 1. Ringkasan Eksekutif

Tahap ini menggantikan arsitektur web lama (`smartbox_web/` berbasis PHP/Laravel monolith dan dependensi Laragon lokal) dengan aplikasi modern berbasis **React 18 + TypeScript + Vite + Tailwind CSS** yang mengadopsi standar desain **TerminalUI (`DESIGN_WEB.md`)**.

Aplikasi ini berhasil di-package ke dalam lightweight production container (Nginx Alpine) dan dideploy langsung ke klaster **K3s Cloud GPU Node (`10.1.1.186`)** pada namespace `cloud-agent` melalui Service `NodePort: 30080`.

### URL Akses Publik & Jaringan:
- **LAN / Local Subnet**: `http://10.1.1.186:30080`
- **Tailscale Mesh VPN**: `http://100.76.68.93:30080`
- **Status Pod K3s**: `Running` (1/1, Deployment: `smartbox-web-deployment`)

---

## 2. Kepatuhan Desain TerminalUI (`DESIGN_WEB.md`)

Seluruh antarmuka dibangun secara ketat mengikuti filosofi **TerminalUI**:
1. **Tipografi Monospace Murni**: Menggunakan `JetBrains Mono` untuk seluruh headline, label, badge, dan body text.
2. **Palet Warna Phosphor Green**:
   - `Primary`: `#00FF41` (Terminal Green)
   - `Secondary`: `#FF6600` (Amber / Warning)
   - `Tertiary`: `#00BFFF` (Cyan / Info)
   - `Background`: `#0D0D0D` (Deep Terminal Black)
   - `Surface`: `#141414` (Panel Card Background)
   - `Border`: `1px #222222` / `1px #00FF41` (Large / Active)
3. **Zero Ornamentation**:
   - `border-radius: 0px` pada seluruh tombol, kartu, input, dan modal (sudut tajam tanpa rounded).
   - `box-shadow: none` — semua elevasi dikomunikasikan murni lewat 1px colored borders.
   - Text prefix bergaya CLI: `$ [COMMAND]`, `> [PROMPT]`, `// [LABEL]`.
4. **CRT Scanline & Reticle Overlay**: Efek scanline terminal analog halus diterapkan di background.

---

## 3. Fitur Utama yang Telah Diimplementasikan

### 3.1 Autentikasi CLI & Role Router (`LoginView.tsx`)
- Pilihan login cepat dengan peran:
  - **Operator / Admin**: Akses kontrol 3 kompartemen loker fisik, sensor ultrasonik live radar, dan telemetri multi-agent.
  - **Penghuni / Owner (Akmal / Iqbal / Shafwan / Syauqi)**: Akses personal dashboard, daftar paket resi kurir, dan onboarding wajah.

### 3.2 Admin Command Center (`AdminDashboard.tsx`)
- **Matrix 3 Kompartemen Loker**:
  - Loker 1 (Inbound Kurir): Status relay BCM 10, sensor ultrasonik (< 23 cm = Paket Terdeteksi).
  - Loker 2 (Storage Pemilik): Status relay BCM 9, keamanan trapdoor servo.
  - Loker 3 (Marketplace P2P): Status relay BCM 6, kode OTP transaksi.
  - Tombol manual trigger aktuator relay fisik.
- **Monitoring Sensor Ultrasonik Real-Time**: Polling otomatis tiap 2.5 detik dengan indikator visual threshold 23 cm.
- **MAS Scheduler & GPU Status Gauge**:
  - Utilisasi CPU Edge Pi 5 saat ini.
  - Keputusan offloading XGBoost (`0 = Edge`, `1 = Cloud`).
  - Status kesehatan Cloud GPU RTX 3050 CUDA (port 9000).

### 3.3 Dashboard Penghuni & Manajemen Paket (`PenghuniDashboard.tsx` & `PackageTrackingView.tsx`)
- Status kepemilikan kompartemen dan notifikasi kedatangan barang.
- Form pendaftaran nomor resi pengiriman kurir (SPX, J&T, JNE, SiCepat).
- Validasi 5 digit terakhir resi yang langsung terhubung ke database loker agar kurir di lokasi fisik dapat langsung membuka Loker 1.

### 3.4 Modern Face Onboarding Studio (`FaceOnboardingView.tsx`)
- **Webcam Stream Langsung**: Menampilkan preview kamera di browser dengan bounding box reticle hijau.
- **Panduan 3-Pose Capture**:
  1. `Pose 1 (Front)`: Tampak depan tegak.
  2. `Pose 2 (Left)`: Menoleh 15–20 derajat ke kiri.
  3. `Pose 3 (Right)`: Menoleh 15–20 derajat ke kanan.
- **Opsi File Upload Fallback**: Dukungan upload file gambar langsung (JPEG/PNG).
- **Proses Pipeline Otomatis**:
  - Mengirim payload Base64 ke `http://10.1.1.186:9000/api/v1/onboard_user`.
  - Cloud GPU memotong wajah via YuNet ONNX dan menghitung embedding InceptionResnetV1 CUDA di VRAM.
  - Cloud GPU otomatis mendistribusikan data ke Edge Pi (`http://10.1.1.224:8600/api/v1/sync_user_face`) untuk update model LBPH offline secara seketika.

---

## 4. Arsitektur K3s Containerization & Deployment

### 4.1 Multi-Stage Dockerfile (`smartbox_web_v2/Dockerfile`)
```dockerfile
# Stage 1: Build static bundle with Node.js 22
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production runtime with Nginx Alpine
FROM nginx:1.25-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 4.2 Manifes K3s (`k8s/smartbox-web-deployment.yaml` & `service.yaml`)
- **Namespace**: `cloud-agent` (bergabung dengan `cloud-api` dan `postgres`).
- **Service**: NodePort mapping container port `80` $\rightarrow$ host port `30080`.
- **Probes**: Liveness dan readiness probes pada endpoint `/health`.

---

## 5. Hasil Verifikasi Lapangan

### 5.1 Status Pod & Service di K3s Cloud Node
```text
$ kubectl get pods,svc -n cloud-agent
NAME                                               READY   STATUS    RESTARTS   AGE
pod/cloud-api-5779f5f77-bpxvz                      1/1     Running   9          54d
pod/smartbox-web-deployment-7b8599f657-lmc8l       1/1     Running   0          5m

NAME                               TYPE       CLUSTER-IP      PORT(S)          AGE
service/cloud-api                  NodePort   10.43.125.151   8000:31161/TCP   54d
service/smartbox-web-service       NodePort   10.43.106.188   80:30080/TCP     5m
```

### 5.2 Uji Aksesibilitas HTTP
```text
$ curl -s -I http://10.1.1.186:30080 | head -n 5
HTTP/1.1 200 OK
Server: nginx/1.25.4
Content-Type: text/html
Content-Length: 855

$ curl -s http://10.1.1.186:30080/api/mas-status
{
  "status": "HEALTHY",
  "edgeScheduler": { "reachable": true, "status": "ok", "mode": "xgboost" },
  "cloudGpu": { "reachable": true, "status": "healthy", "device": "cuda:0" },
  "telemetry": { "cpuUsage": 24.5, "decision": 0, "totalLatencyMs": 38.2 }
}
```

---

## 6. Panduan Penggunaan

Aplikasi dapat dibuka langsung melalui browser di komputer / laptop dalam jaringan:
- Buka URL: **`http://10.1.1.186:30080`** (atau `http://100.76.68.93:30080` via Tailscale).
- Klik tombol **`[LOGIN SEBAGAI ADMIN]`** untuk memantau status loker dan sensor ultrasonik live.
- Klik tombol **`[LOGIN SEBAGAI AKMAL (OWNER)]`** untuk menguji onboarding wajah langsung via kamera browser atau menambahkan nomor resi paket kurir.
