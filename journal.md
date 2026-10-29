# Smart Locker System (Penlock / BoxInAja) — Discovery & Architecture Journal

## 1. System Metadata & Host Environment

- **Host IP**: `10.1.1.224`
- **SSH Port**: `2523` (non-standard port; port 22 refused)
- **Target User**: `pi`
- **Root Directory**: `/home/pi/penlock`
- **Core Orchestrator File**: `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/pan-piXarduino-fixed.py` (and its active variant `cobaface.py`)
- **Host Hardware**: Raspberry Pi 5 (RPi 2712 aarch64, 4-core, Linux 6.12.109+rpt-rpi-2712)
- **Python Environments**:
  - System: Python 3.11.2 (`/usr/bin/python3`)
  - Pyenv `penlok`: Python 3.9.20 (`/home/pi/.pyenv/versions/3.9.20/envs/penlok`) — used for hardware control, `lgpio`, `pyzbar`, OpenCV.
  - Pyenv `backend`: Python 3.12.3 (`/home/pi/.pyenv/versions/3.12.3/envs/backend`)
- **Active Git Repositories**:
  - `/home/pi/penlock/software`: `https://github.com/PenlokN25/backend-new.git` (branch `main`)
  - `/home/pi/penlock/pyenv3.9code`: `https://github.com/PenlokN25/smartlock2.git`
  - `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan`: `https://github.com/PenlokN25/penlok10-25.git`

---

## 2. Architecture & Service Topology

```
+-----------------------------------------------------------------------------------+
|                              RASPBERRY PI 5 (HOST)                                |
|                                                                                   |
|  +--------------------+         +------------------+         +-----------------+  |
|  |  Mosquitto MQTT    |         | pan-piXarduino   |         | Arduino Nano/   |  |
|  |  Broker (:1883)    | <-----> | Daemon (Py 3.9)  | <=====> | Uno via USB     |  |
|  +--------------------+         +--------+---------+ (Serial | /dev/ttyACM0    |  |
|            ^                             |           9600)   | (RFID RC522, IR)|  |
|            |                             |                   +-----------------+  |
|            |                 +-----------+-----------+                            |
|            |                 | Hardware Actuators &  |                            |
|            |                 | Sensors (GPIO / I2C)  |                            |
|            |                 +-----------------------+                            |
|            |                             |                                        |
|            v                             v                                        |
|  +-----------------------------------------------------------------------------+  |
|  |                           DOCKER CONTAINERS                                 |  |
|  |                                                                             |  |
|  |  +------------------------+      +------------------+      +-------------+  |  |
|  |  | smartlocker-backend    | <--> | smartlocker-db   | <--> | smartlocker-|  |  |
|  |  | Django 5.2 / Gunicorn  |      | PostgreSQL 15    |      | redis       |  |  |
|  |  | (:8000)                |      | (Port :1723 host)|      | Redis 7     |  |  |
|  |  +-----------+------------+      +------------------+      +------+------+  |  |
|  |              |                                                    |         |  |
|  |              +-------------------+                                |         |  |
|  |                                  v                                v         |  |
|  |                      +------------------------+      +-------------------+  |  |
|  |                      | smartlocker-celery     | <--- | smartlocker-      |  |  |
|  |                      | Worker                 |      | celery-beat       |  |  |
|  |                      +------------------------+      +-------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Active Docker Containers on Host
1. `smartlocker-backend`: Gunicorn HTTP server running Django REST backend on `0.0.0.0:8000`.
2. `smartlocker-db`: PostgreSQL 15 mapped to `0.0.0.0:1723` on host (internal 5432).
3. `smartlocker-redis`: Redis 7 mapped to `0.0.0.0:6379`.
4. `smartlocker-celery`: Asynchronous task execution worker.
5. `smartlocker-celery-beat`: Periodic scheduler (beat).
6. Host service: `mosquitto.service` running MQTT broker on port 1883.

---

## 3. Hardware Pinout & Wiring Specifications

All pin numbers reference Raspberry Pi **BCM (Broadcom) GPIO**:

| Component | BCM Pin / Interface | Wiring / Protocol | Function |
|---|---|---|---|
| **Relay 1 (Locker 3)** | GPIO 6 | Active LOW | Actuates Solenoid Lock 3 (Marketplace locker) |
| **Relay 2 (Locker 2)** | GPIO 9 | Active LOW | Actuates Solenoid Lock 2 (Internal secure storage) |
| **Relay 3 (Locker 1)** | GPIO 10 | Active LOW | Actuates Solenoid Lock 1 (Inbound drop-off locker) |
| **Relay 4 (Inbound / Aux)** | GPIO 19 | Active LOW | Actuates Solenoid Lock Inbound/RFID latch |
| **Servo Left** | GPIO 13 | PWM (`gpiozero.Servo`) | Trapdoor actuation mechanism (L1 -> L2 transfer) |
| **Servo Right** | GPIO 12 | PWM (`gpiozero.Servo`) | Trapdoor actuation mechanism (counter-direction) |
| **LCD Display** | I2C (SDA/SCL) | I2C Addr `0x27`, chip `PCF8574` | User UI prompts ("BoxInAja" menu) |
| **Keypad 3x4 (Columns)** | GPIO 8, 25, 11 | Digital Output (strobe) | Matrix keypad column scan |
| **Keypad 3x4 (Rows)** | GPIO 5, 1, 0, 7 | Digital Input (pull-down) | Matrix keypad row read |
| **Ultrasonic HC-SR04 (L1)** | TRIG: GPIO 15, ECHO: GPIO 17 | `lgpio` timing | Parcel presence detection in Locker 1 |
| **IR Sensor (Locker 1)** | GPIO 26 | Digital Input (pull-down) | Detects Locker 1 door closed state |
| **Load Cell (HX711)** | DOUT: GPIO 4, SCK: GPIO 14 | Bit-bang SPI | Continuous weight monitoring (calibrated tare) |
| **Vibration Sensor** | GPIO 24 | Digital Input | SW-420 tamper detection |
| **Push Button (Owner)** | GPIO 16 | Digital Input (pull-up) | Triggers camera owner verification |
| **Push Button (QR trigger)** | GPIO 20 | Digital Input (pull-up) | Activates QR camera in `cobav2.py` |
| **Buzzer** | GPIO 21 | Digital Output | Audio feedback for accepted / denied input |
| **LED Indicators** | Red: GPIO 23, 18; Green: GPIO 22, 27 | Digital Output | Status visual signals |
| **Arduino MCU** | `/dev/ttyACM0` | Serial USB (9600 baud) | RFID-RC522 and auxiliary sensor integration |
| **Webcam** | `/dev/video0` | USB V4L2 | Face recognition capture & QR / Barcode scanning |

---

## 4. Software Subsystems & Directory Map

```
/home/pi/penlock/
├── coba/                  # Isolated hardware test scripts
├── penlock/               # Standalone Python 3.11 virtualenv
├── pyenv3.9code/          # Hardware orchestration codebase
│   └── nonsudo/
│       ├── blynk/         # Alternative/legacy Blynk IoT controls
│       ├── gabungan/      # Main production hardware integration scripts
│       ├── kalibrasi/     # HX711 calibration utilities
│       ├── masterslave-arduino/ # Arduino serial protocol scripts
│       └── metodeface/    # Standalone LBPH face recognition experiments
├── qr/                    # QR & barcode testing tools
├── servo/                 # Standalone servo movement test scripts
└── software/              # Django Backend Application
    ├── db2/               # Standalone DB docker-compose definition
    └── Django-Backend-Project/
        ├── apps/
        │   ├── facerecognition/ # OpenCV LBPH face training & access logs
        │   ├── iot/             # Ingestion API & notification signals
        │   ├── lockers/         # Locker inventory, logs, open requests
        │   ├── marketplace/     # Escrow, transactions, OTP generation
        │   ├── notifications/   # Push notification tasks (Celery)
        │   ├── package_center/  # Parcel registry & tracking
        │   └── users/           # Custom User with roles & Face IDs
        └── smartlocker/         # Django settings, WSGI, Celery config
```

### Detailed Subsystem Breakdown

### 4.1 Backend: Django REST Framework (`software/Django-Backend-Project`)
1. **`users` App**:
   - Model `User` extends `AbstractUser` with custom roles: `OWNER`, `COURIER`, `SELLER`, `BUYER`, `ADMIN`.
   - `OWNER` users automatically receive a unique 6-digit numeric `face_id` (generated via `generate_uid2()`).
2. **`lockers` App**:
   - `Locker`: Tracks locker slot number (`0`, `1`, `2`, `3`), type (`INBOUND`, `STORAGE`, `MARKETPLACE`), status (`AVAILABLE`, `OCCUPIED`), and assigned `gpio_pin`.
   - `LockerRequest`: Queue table for physical unlock commands initiated from mobile apps. Contains `locker_number`, `requested_by`, `fulfilled`, `fulfilled_at`.
   - `LockerLog`: Audit log of all open/close/deposit/retrieve actions.
3. **`facerecognition` App**:
   - `Datawajahnew`: Stores face image datasets uploaded for OWNER users (`imagetraining/<user>/`).
   - `Logsmartaccess2`: Audit logs for camera-based access attempts (`AUTHORIZED` vs `UNAUTHORIZED`).
   - Training Engine: Uses OpenCV's `cv2.face.LBPHFaceRecognizer_create()` to generate `/app/hasiltraining/lbph_model.xml`.
4. **`package_center` App**:
   - `PackageEntry`: Stores parcels with tracking numbers, courier name, locker slot assignment, and delivery statuses (`REGISTERED`, `IN_TRANSIT`, `DELIVERED`).
5. **`marketplace` App**:
   - P2P marketplace with escrow workflow:
     `PENDING` -> `PAID` -> `ESCROW` -> `AWAITING_PICKUP` -> `RELEASED` -> `COMPLETED`.
   - Generates random 6-digit `otp` for buyers to collect packages from physical lockers.
6. **`iot` App**:
   - `IoTEvent`: Ingestion point for device telemetry (`/api/v1/iot/events/`).
   - `signals.py`: Listens to `IoTEvent` post-save. Automatically triggers Celery notifications.
   - Detects vibration anomaly: If 7 consecutive events are `TAMPER_DETECTED` without an intervening `TAMPER_RESET`, fires alert: `"WARNING!! SENSOR MENDETEKSI ANOMALI GETARAN"`.
7. **`notifications` App**:
   - Asynchronous worker dispatch via Celery (`push_notification_task`) with batch notification records.

---

### 4.2 Hardware Orchestration (`pyenv3.9code/nonsudo/gabungan/`)

#### A. Master Control Loop: `pan-piXarduino-fixed.py`
The master background script combining all hardware elements:
- **I2C LCD & 3x4 Matrix Keypad UI**:
  - `1. Kirim Paket` -> `1. Scan QR` (runs `cobav2.py`) OR `2. Masukkan Resi` (inputs last 5 digits of tracking ID; validates against `package_center_packageentry` in DB; triggers Relay 3).
  - `2. Ambil Paket` -> Inputs 6-digit OTP; validates against `marketplace_transaction` in DB; triggers Relay 1.
- **Push Button Owner Access**:
  - Pressing GPIO 16 launches `camowner.py` (webcam preview / face recognition) and triggers Relay 2.
- **Parcel Handoff Mechanism (Locker 1 -> Locker 2)**:
  - Ultrasonic sensor (HC-SR04) continuously measures distance in Locker 1.
  - When distance < 23 cm (parcel detected), it triggers `ir_single_read.py`.
  - Once the courier closes the door (IR sensor GPIO 26 goes low), `servo2.py` triggers dual servos (GPIO 12 & 13) to drop the parcel via trapdoor into storage Locker 2.
- **Database Unlock Polling**:
  - Background thread queries `lockers_lockerrequest` table where `fulfilled = false` every 2 seconds.
  - When mobile app requests an unlock, it immediately fires the mapped relay (`LOCKER_RELAY_MAP`) and updates `fulfilled = true, fulfilled_at = NOW()`.
- **MQTT Command Ingestion**:
  - Subscribes to `penlok/command` on `localhost:1883`.
  - Receives `{"action": "open", "locker_number": "1"}` and triggers relays directly.
- **Load Cell Monitoring**:
  - Continuous reading of HX711 loadcell (offset `8763202`, scale factor `196.584`).
  - Reports weight changes exceeding 5-gram delta.
- **Arduino Serial Interface**:
  - Reads line events from `/dev/ttyACM0`:
    - `RFID:ACCEPTED:<uid>` -> Unlocks Relay 4, plays green LED/buzzer melody.
    - `RFID:DENIED:<uid>` -> Plays red error beep.
    - `ULTRA:DETECTED` / `IR:DETECTED` -> Secondary locker alerts.

#### B. Camera & Face Authentication: `face.py`
- Direct interactive CLI application for face registration and verification.
- Uses Haar Cascade (`haarcascade_frontalface_default.xml`) for face localization with real-time video overlay.
- Automatically captures multi-angle face images, uploads to backend endpoint `/api/v1/facerecognition/createimagetrainingusernew/`.
- Verifies live face by sending capture to `/api/v1/facerecognition/createlogusersmartnew/`, retrieving confidence score and authorization status.

#### C. Barcode & QR Scanner: `cobav2.py`
- Headless scanning loop using OpenCV and `pyzbar`.
- Activated by physical push button on GPIO 20.
- Decodes QR / Barcode data, queries PostgreSQL table `package_center_packageentry` to check tracking number existence.
- Automatically exits with success status after 3 consecutive valid detections or 7-second timeout.

---

## 5. End-to-End Operational Workflows

### 5.1 Courier Drop-Off Flow
1. Courier approaches locker terminal, views LCD prompt: `"1. Kirim Paket"`.
2. Courier selects option `1` (Scan QR) or `2` (Manual 5-digit resi via Keypad).
3. If scanning QR, webcam scans barcode; if valid in database, Relay 3 triggers (BCM 10) to open Locker 1.
4. Courier places parcel inside Locker 1; HC-SR04 ultrasonic detects distance < 23 cm.
5. Courier closes door; IR sensor (GPIO 26) confirms door is closed.
6. `servo2.py` activates dual servos on GPIO 12 and 13, opening the trapdoor for 2 seconds.
7. Parcel slides into lower secure Locker 2; trapdoor closes.
8. Status is recorded in DB and push notification sent to package owner.

### 5.2 Marketplace Buyer Retrieval Flow
1. Buyer completes purchase on marketplace; backend generates 6-digit OTP upon escrow release.
2. Buyer approaches terminal, chooses `"2. Ambil Paket"`.
3. Buyer enters 6-digit OTP on matrix keypad.
4. System queries `marketplace_transaction` table for matching OTP.
5. If valid, buzzer confirms, green LED lights, and Relay 1 triggers (BCM 6) to unlock Locker 3.
6. Transaction status is updated and push notification notifies seller that item was collected.

### 5.3 Owner Pushbutton & Face Retrieval Flow
1. Locker owner presses physical button (GPIO 16).
2. Raspberry Pi triggers camera face recognition routine (`camowner.py` / `face.py`).
3. Haar cascade locates face; LBPH model matches against registered owner face dataset.
4. If confidence passes threshold, Relay 2 (BCM 9) activates to open storage Locker 2.

### 5.4 Remote App Unlock Flow
1. Mobile user taps "Open Locker" in application.
2. API endpoint `POST /api/v1/lockers/storage/open/<slot>/` validates user JWT token and creates a `LockerRequest` row (`fulfilled=False`).
3. Background polling thread in `pan-piXarduino-fixed.py` picks up record within 2 seconds.
4. GPIO relay triggers; row is marked `fulfilled=True`.
5. An `IoTEvent` (`LOCKER_OPENED`) is recorded and logged in `LockerLog`.

---

## 6. Observations & Engineering Recommendations

1. **Database Direct Coupling vs API Gateway**:
   - Hardware scripts (`pan-piXarduino-fixed.py`, `cobav2.py`, `face.py`) connect directly to PostgreSQL on port 1723 with hardcoded credentials (`smartlocker_admin:penlokjaya`), bypassing Django's ORM validation and business logic.
   - *Recommendation*: Migrate hardware scripts to communicate solely through REST endpoints (`/api/v1/iot/...`) or MQTT topics to maintain centralized access control and audit logging.
2. **Keypad Matrix Polling in Main Thread**:
   - In `pan-piXarduino-fixed.py`, `read_key()` and `wait_key()` utilize blocking `time.sleep()`. During external script execution (e.g. `subprocess.run(["python3", "cobav2.py"])`), the keypad loop is completely paused.
   - *Recommendation*: Encapsulate keypad monitoring into an event-driven queue or async worker.
3. **Relay Pin Mapping Consistency**:
   - In `pan-piXarduino-fixed.py`:
     - Locker 0 (Inbound) -> Relay 4 (GPIO 19)
     - Locker 1 -> Relay 3 (GPIO 10)
     - Locker 2 -> Relay 2 (GPIO 9)
     - Locker 3 -> Relay 1 (GPIO 6)
   - In Django DB `Locker` table, `gpio_pin` values are currently configured as `[('3', 6), ('1', 19), ('2', 10)]`. Ensure pin assignments in database match hardware script dictionary mappings.
4. **Environment Variables**:
   - Database credentials and device tokens (`IoT@event2025`) are present in code defaults. Centralize configuration into systemd `.env` files.

---

## 7. Patch History: Raspberry Pi 5 Kernel 6.12 GPIO Compatibility (Sep 2026)

- **Issue**: `gpiozero` threw `PinFactoryFallback: Falling back from lgpio: 'can not open gpiochip'` and crashed with `RuntimeError: Cannot determine SOC peripheral base address`.
- **Root Cause**: RPi 5 uses RP1 southbridge for GPIO. In Linux kernel 6.12+, RP1 was assigned to `/dev/gpiochip15` instead of `gpiochip4` or `gpiochip0`. `gpiozero` 2.0.1 hardcoded `chip=4` on Pi 5 and failed back to unsupported `RPi.GPIO`.
- **Backups Created**:
  - `gpiozero/pins/lgpio.py.bak`
  - `pan-piXarduino-fixed.py.bak`
  - `cobaface.py.bak_pre_gpiofix`
  - `cobav2.py.bak`
- **Fix Applied**:
  1. Patched `gpiozero.pins.lgpio.LGPIOFactory` in `penlok` pyenv site-packages to probe candidate chips `[15, 4, 0]`.
  2. Patched `pan-piXarduino-fixed.py`, `cobaface.py`, and `cobav2.py` with dynamic `_get_gpio_chip()` routine to open the valid gpiochip (`15`).

