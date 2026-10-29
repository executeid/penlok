# Jurnal Pembaruan UI/UX: Rekonstruksi Penuh SmartBox MAS Sesuai DESIGN_WEB.md (WattVision Dashboard)

**Tanggal**: 9 Oktober 2026  
**Dokumen Spesifikasi Desain**: `DESIGN_WEB.md` ("WattVision" Monitoring System)  
**Metodologi**: `ui-ux-pro-max` (Design Intelligence & Pre-Delivery Polish)  
**Node Deployment**: `penlok@10.1.1.186:30080` (Namespace: `cloud-agent`)  
**Image Container**: `smartbox-web:v3`  
**Status**: SUKSES / LIVE RUNNING  

---

## 1. Analisis Kebutuhan Desain (`DESIGN_WEB.md`)

Berdasarkan berkas spesifikasi `DESIGN_WEB.md`, antarmuka web dirancang untuk menghadirkan atmosfer **keandalan teknis (technical reliability)**, **kontrol terpusat**, dan estetika modern bergaya *"Power BI Dashboard tapi disederhanakan untuk pengguna akhir"*, bukan antarmuka hacker monospace mentah.

### Matriks Perbandingan Desain:
| Komponen | Spesifikasi `DESIGN_WEB.md` | Implementasi Lapangan pada Proyek |
|---|---|---|
| **Tema Visual** | Dark Mode teknis, profesional, kontras tinggi | Latar belakang `#121212`, kartu panel `#1E1E1E` |
| **Palet Warna** | • Primario: `#121212`<br>• Superficie: `#1E1E1E`<br>• Acento Datos: `#00E5FF` (Cian Neón)<br>• Alerta: `#FF453A` / Caja `#3A1C1C`<br>• Secundario: `#32D74B` (Verde Lima)<br>• Texto: `#FFFFFF` (Alto Contraste) & `#98989D` | Didefinisikan secara presisi dalam `tailwind.config.js` |
| **Tipografi** | • Títulos: `Inter`, Semi Bold, 24px<br>• Métricas KPIs: `JetBrains Mono`, Bold, 32px<br>• Cuerpo: `Inter`, Regular, 14px | Terpasang via `@fontsource/inter` dan `@fontsource/jetbrains-mono` |
| **Komponen Kartu** | `border-radius: 16px`, padding `20px`, borde sutil `1px solid #2C2C2E` | Kelas Tailwind `rounded-card` (16px), padding `p-5` (20px), border `#2C2C2E` |
| **Gráficos (Charts)** | Líneas grid en `#2C2C2E`, datos en `#00E5FF` con `#30D158` para gradientes de área | Area chart SVG responsif dengan kurva bezier, gradien halus `#00E5FF` ke `#30D158`, dan grid putus-putus `#2C2C2E` |
| **Tablas** | Filas con `border-bottom: 1px solid #2C2C2E`, hover cambia fondo a `#252525` | Border `#2C2C2E`, hover row `hover:bg-[#252525] transition-colors` |
| **Alertas** | Caja con fondo `#3A1C1C`, texto rojo `#FF453A`, borde izquierdo `4px solid #FF453A` | Kotak alert `bg-[#3A1C1C] border-l-4 border-l-[#FF453A]` |
| **Layout Grid** | Grid 12 columnas: 3 KPI di atas, Gráfico (8 col), Panel Alertas (4 col) | Grid CSS 12 kolom (`grid-cols-12`): 8 kolom grafik & casilleros, 4 kolom alertas |
| **Iconography** | SVG Icons (rayo, enchufe, medidor). Tanpa emoji. | Terintegrasi menggunakan `lucide-react` (Zap, Radio, Cpu, ShieldCheck, dll) |
| **Equivalencia Moneda** | Wajib menampilkan equivalensi tarif Bolivianos (`Bs.`) | Menampilkan konsumsi energi `kWh/día` dan equivalensi mata uang Bolivianos (`Bs.`) |

---

## 2. Fitur & Halaman yang Direkonstruksi

1. **Dashboard Principal (`AdminDashboard.tsx`)**:
   - **3 Top KPIs (3 Kolom)**:
     1. *Potencia de Procesamiento*: 36 W (32px Mono), estimasi kWh/día dan tarif listrik Bolivianos (`0.52 Bs.`), bar visual kapasitas.
     2. *Sensor Ultrasonido HC-SR04*: Jarak live dalam centimeter (`cm`), badge status "Ocupado" (`#32D74B`) jika $\le 23\text{ cm}$ atau "Libre", pin BCM 15/17.
     3. *Carga CPU Edge Pi 5*: Persentase utilisasi CPU, keputusan model XGBoost (`0: Edge Pi 5` / `1: Cloud GPU`), progress bar dinamis.
   - **Gráfico de Área (8 Kolom)**:
     - SVG bezier curve dinamis dengan gradien area `#00E5FF` $\rightarrow$ `#30D158` $\rightarrow$ `#121212`.
     - Garis grid putus-putus `#2C2C2E`.
     - Pelacakan latensi inferensi total dan GPU CUDA.
   - **Panel de Alertas & Auditoría (4 Kolom)**:
     - Kotak peringatan kritis gaya WattVision (`#3A1C1C` + border kiri 4px `#FF453A`).
     - Riwayat audit kejadian waktu nyata dengan indikator status `#32D74B` (Éxito) dan `#FF453A` (Falla).
   - **Casilleros Físicos (3 Casilleros)**:
     - Casillero 1 (Entrada Repartidores), Casillero 2 (Almacenamiento Seguro), Casillero 3 (Marketplace).
     - Tombol aksi apertura remota relé 2.5 detik.

2. **Dashboard Penghuni / Usuario (`PenghuniDashboard.tsx`)**:
   - Status casillero personal asignado (Casillero 2).
   - Estado de credencial biométrica facial (ID `#789123`, sincronizado con modelo local Pi 5 y Cloud GPU).
   - Tabla de paquetes en tránsito y recibidos con hover `#252525` y badges de estado.

3. **Onboarding Biométrico Facial Moderno (`FaceOnboardingView.tsx`)**:
   - Visor de cámara web en vivo con marco guía facial central redondeado.
   - Flujo de 3 tomas angulares: *Pose 1 (Frontal)*, *Pose 2 (Perfil Izquierdo 15°)*, *Pose 3 (Perfil Derecho 15°)*.
   - Opción alternativa de subida de archivos (PNG/JPG).
   - Botón de sincronización automática que envía las muestras a `http://10.1.1.186:9000/api/v1/onboard_user` (GPU CUDA) y sincroniza automáticamente al Edge Pi 5 (`:8600`).

4. **Gestión de Paquetes & Resi (`PackageTrackingView.tsx`)**:
   - Formulario de registro de resi con autogeneración de PIN de 5 dígitos para el teclado físico del casillero.
   - Tabla de envíos con búsqueda y filtrado rápido.
   - Guía paso a paso del flujo de entrega para el repartidor.

5. **Portal de Acceso (`LoginView.tsx`)**:
   - Diseño limpio y enfocado con selector de roles (`Admin` vs `Usuario`).
   - Fondos `#1E1E1E`, botones `#00E5FF` con tipografía clara y contraste verificado (7:1).

---

## 3. Deployment & Verifikasi Klaster K3s

Aplikasi berhasil dibuild ulang dengan container image **`smartbox-web:v3`** dan di-deploy ke klaster Kubernetes K3s Cloud Node:

```text
Host Node   : pengmas-tri (10.1.1.186 / Ubuntu 24.04 LTS x86_64)
Namespace   : cloud-agent
Deployment  : smartbox-web-deployment (Image: smartbox-web:v3)
Service     : smartbox-web-service (NodePort 80:30080)
Estado Pod  : Running (1/1)
```

### Hasil Uji Verifikasi HTTP:
```bash
# 1. Uji Header & Status HTTP
curl -s -I http://10.1.1.186:30080 | head -n 5
HTTP/1.1 200 OK
Server: nginx/1.31.6
Content-Type: text/html

# 2. Uji API Sensor Hardware Real-Time
curl -s http://10.1.1.186:30080/api/sensor
{"distance_cm":5.0,"node":"edge_pi5","status":"PAKET TERDETEKSI (LOKER 1)","threshold_cm":23.0}

# 3. Uji Telemetri Multi-Agente
curl -s http://10.1.1.186:30080/api/mas-status
{"status":"HEALTHY","edgeScheduler":{"reachable":true,"mode":"xgboost"},"cloudGpu":{"gpuAvailable":true,"device":"cuda:0"}}
```

---

## 4. URL Akses Langsung

Antarmuka web dapat diakses langsung melalui browser di:
- **Jaringan Lokal (LAN)**: **`http://10.1.1.186:30080`**
- **Tailscale Mesh VPN**: **`http://100.76.68.93:30080`**
