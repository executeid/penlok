#!/usr/bin/env python3
"""
PENLOK Edge Multi-Agent System (MAS) Unified Controller
Target Node: pi@10.1.1.224 (Raspberry Pi 5)
Handles:
- Dual Input System:
    1. USB Keyboard Input (hotplug auto-detect, /dev/input/by-id/*kbd* or event nodes)
    2. Physical Matrix Keypad 3x4 (Columns: BCM 8, 25, 11 / Rows: BCM 5, 1, 0, 7)
    3. Physical Push Button (BCM 16)
- I2C LCD Display (PCF8574 on 0x27) with interactive Menu Utama
- Courier Inbound Flow (5-digit Resi -> Relay 3 / BCM 10 -> Ultrasonic -> Servos)
- Marketplace Buyer Pickup (6-digit OTP -> Relay 1 / BCM 6 -> DB update)
- Owner Biometric Access (Face Capture -> MAS Scheduler -> Cloud GPU or Local Edge -> Relay 2 / BCM 9)
- Local Offline Decision Buffering & Background Cloud Syncing (decision_syncer.py)
"""

import sys
import os
import time
import glob
import struct
import select
import threading
import argparse
import requests
import psutil
import psycopg2
import numpy as np
import cv2
import lgpio
from gpiozero import OutputDevice, DigitalInputDevice, Servo, Device
from gpiozero.pins.lgpio import LGPIOFactory

# Initialize native LGPIOFactory with Pi 5 RP1 southbridge (chip 15)
for cand in (15, 4, 0):
    try:
        Device.pin_factory = LGPIOFactory(chip=cand)
        break
    except Exception:
        pass

# Ensure local imports work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from migration_agent import dispatch_migration, LATENCY_CSV
from decision_syncer import buffer_decision, start_background_syncer

# --- Hardware Pin Definitions (BCM) ---
RELAY_LOCKER_1 = 10      # Locker 1 (Courier Inbound) - Active LOW
RELAY_LOCKER_2 = 9       # Locker 2 (Owner Storage) - Active LOW
RELAY_LOCKER_3 = 6       # Locker 3 (Marketplace Pickup) - Active LOW
RELAY_AUX = 19           # Aux Latch - Active LOW

SERVO_LEFT_PIN = 13      # Trapdoor Servo Pair 1
SERVO_RIGHT_PIN = 12     # Trapdoor Servo Pair 2

TRIG_PIN = 15            # HC-SR04 Ultrasonic Trigger
ECHO_PIN = 17            # HC-SR04 Ultrasonic Echo
IR_DOOR_PIN = 26         # Infrared Door Sensor (Active LOW = closed)
OWNER_BUTTON_PIN = 16    # Physical Push Button (Active LOW)

BUZZER_PIN = 21          # Piezo Buzzer - Active HIGH
LED_GREEN_PIN = 27       # Green Indicator - Active LOW
LED_RED_PIN = 18         # Red Indicator - Active LOW

# Matrix Keypad Pins (BCM)
KEYPAD_COLUMNS = [8, 25, 11]
KEYPAD_ROWS = [5, 1, 0, 7]
KEYPAD_MATRIX = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#'],
]

# Remote Microservice Endpoints
SCHEDULER_URL = os.getenv("SCHEDULER_URL", "http://10.1.1.57:8500/api/v1/schedule")
CLOUD_GPU_URL = os.getenv("CLOUD_GPU_URL", "http://10.1.1.186:9000/api/v1/migration")

# Local Model Paths
HAAR_CASCADE_PATH = "/home/pi/penlock/pyenv3.9code/nonsudo/haarcascade_frontalface_default.xml"
LBPH_MODEL_PATH = "/home/pi/penlock/pyenv3.9code/nonsudo/lbph_model.xml"

# Database Config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": int(os.getenv("DB_PORT", "1723")),
    "user": os.getenv("DB_USER", "smartlocker_admin"),
    "password": os.getenv("DB_PASSWORD", "penlokjaya"),
    "dbname": os.getenv("DB_NAME", "smartlocker"),
    "connect_timeout": 3
}

# --- I2C LCD Integration with Pi 5 RP1 bus pacing & auto-retry ---
lcd_lock = threading.Lock()

def safe_lcd_write(lines_list):
    """Rock-solid I2C LCD writer with character pacing to prevent Errno 121 on Pi 5 RP1"""
    lines = list(lines_list) + ["", "", "", ""]
    lines = lines[:4]
    with lcd_lock:
        for attempt in range(6):
            try:
                from RPLCD.i2c import CharLCD
                lcd = CharLCD('PCF8574', 0x27, port=1, cols=20, rows=4)
                lcd.clear()
                time.sleep(0.04)
                for r, text in enumerate(lines):
                    lcd.cursor_pos = (r, 0)
                    for ch in str(text)[:20]:
                        lcd.write_string(ch)
                        time.sleep(0.002)
                return True
            except Exception as e:
                time.sleep(0.06)
        print("[-] safe_lcd_write failed after 6 attempts")
        return False

def lcd_write_lines(line0="", line1="", line2="", line3=""):
    safe_lcd_write([line0, line1, line2, line3])

# Hardware Devices (Singletons with safe recovery)
relays = {}
indicators = {}

def get_relays():
    global relays
    if not relays:
        try:
            relays[1] = OutputDevice(RELAY_LOCKER_3, active_high=False, initial_value=False)
            relays[2] = OutputDevice(RELAY_LOCKER_2, active_high=False, initial_value=False)
            relays[3] = OutputDevice(RELAY_LOCKER_1, active_high=False, initial_value=False)
            relays[4] = OutputDevice(RELAY_AUX, active_high=False, initial_value=False)
        except Exception as e:
            if "busy" in str(e).lower():
                print("[!] GPIO busy detected. Cleaning lock...")
                os.system("pkill -9 -f smartbox_test.py 2>/dev/null")
                time.sleep(0.5)
                relays[1] = OutputDevice(RELAY_LOCKER_3, active_high=False, initial_value=False)
                relays[2] = OutputDevice(RELAY_LOCKER_2, active_high=False, initial_value=False)
                relays[3] = OutputDevice(RELAY_LOCKER_1, active_high=False, initial_value=False)
                relays[4] = OutputDevice(RELAY_AUX, active_high=False, initial_value=False)
            else:
                raise e
    return relays

def get_indicators():
    global indicators
    if not indicators:
        indicators["buzzer"] = OutputDevice(BUZZER_PIN, active_high=True, initial_value=False)
        indicators["green"] = OutputDevice(LED_GREEN_PIN, active_high=False, initial_value=False)
        indicators["red"] = OutputDevice(LED_RED_PIN, active_high=False, initial_value=False)
    return indicators

def beep_short():
    """Short 30ms beep for keypress feedback"""
    try:
        ind = get_indicators()
        ind["buzzer"].on()
        time.sleep(0.03)
        ind["buzzer"].off()
    except Exception:
        pass

def beep_success():
    try:
        ind = get_indicators()
        ind["green"].on()
        ind["buzzer"].on()
        time.sleep(0.3)
        ind["buzzer"].off()
        ind["green"].off()
    except Exception:
        pass

def beep_denied():
    try:
        ind = get_indicators()
        for _ in range(3):
            ind["red"].on()
            ind["buzzer"].on()
            time.sleep(0.15)
            ind["buzzer"].off()
            ind["red"].off()
            time.sleep(0.1)
    except Exception:
        pass

def trigger_relay_safe(relay_id, duration=2.5):
    """Safely energize solenoid relay with guaranteed auto-cutoff"""
    rls = get_relays()
    if relay_id not in rls:
        return
    r = rls[relay_id]
    print(f"[ACTUATOR] Triggering Relay {relay_id} for {duration}s...")
    try:
        beep_success()
        r.on()
        time.sleep(duration)
    finally:
        r.off()
        print(f"[ACTUATOR] Relay {relay_id} de-energized safely.")

def run_trapdoor_cycle():
    """Actuate dual servos for parcel transfer from Locker 1 to Locker 2"""
    print("[SERVO] Running trapdoor cycle (GPIO 12 & 13)...")
    s_left = None
    s_right = None
    try:
        s_left = Servo(SERVO_LEFT_PIN)
        s_right = Servo(SERVO_RIGHT_PIN)
        # Open
        s_left.value = -1
        s_right.value = 1
        time.sleep(0.45)
        s_left.detach()
        s_right.detach()
        time.sleep(1.5)
        # Close
        s_left.value = 1
        s_right.value = -1
        time.sleep(0.5)
        s_left.detach()
        s_right.detach()
        print("[SERVO] Trapdoor cycle completed.")
    except Exception as e:
        print(f"[-] Servo error: {e}")
    finally:
        if s_left:
            try: s_left.close()
            except: pass
        if s_right:
            try: s_right.close()
            except: pass


# --- Camera & Face Recognition Pipeline ---
def capture_camera_frame(device_idx=0, timeout=2.5):
    cap = cv2.VideoCapture(device_idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device_idx)
    if not cap.isOpened():
        print("[-] Gagal membuka kamera /dev/video0")
        return None

    frame = None
    t0 = time.time()
    while time.time() - t0 < timeout:
        ret, temp = cap.read()
        if ret and temp is not None and temp.size > 0:
            frame = temp
            break
        time.sleep(0.05)
    cap.release()

    if frame is None:
        return None
    ret, jpeg_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return jpeg_buf.tobytes() if ret else None

def get_system_telemetry(force_decision=None):
    if force_decision == 1:
        return {"CPU": 88.5, "RAM": 8500.0, "Throughput": 85.0, "Network_Bandwidth": 50.0, "Priority": 2, "Latency": 10.0, "Queue": 5, "RAM_pct": 82.0}
    elif force_decision == 0:
        return {"CPU": 24.5, "RAM": 1100.0, "Throughput": 0.5, "Network_Bandwidth": 1.0, "Priority": 1, "Latency": 25.0, "Queue": 1, "RAM_pct": 32.0}

    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    latency_ms = 10.0
    try:
        t_ping = time.time()
        base_sched = SCHEDULER_URL.split("/api")[0]
        r = requests.get(f"{base_sched}/health", timeout=0.2)
        if r.status_code == 200:
            latency_ms = round((time.time() - t_ping) * 1000, 2)
    except Exception:
        pass

    return {
        "CPU": round(cpu_pct, 1),
        "RAM": round(mem.used / (1024 * 1024), 1),
        "Throughput": 0.5,
        "Network_Bandwidth": 1.0,
        "Priority": 3,
        "Latency": latency_ms,
        "Queue": 1,
        "RAM_pct": round(mem.percent, 1)
    }

def query_scheduler_agent(telemetry):
    try:
        r = requests.post(SCHEDULER_URL, json=telemetry, timeout=0.8)
        if r.status_code == 200:
            data = r.json()
            return data.get("decision", 0), data.get("confidence", 0.9), data.get("method", "rule_based")
    except Exception as e:
        print(f"[!] Scheduler fallback ({e}) -> Edge (0)")
    return 0, 0.5, "fallback_edge"

def verify_face_locally(frame_bytes):
    t0 = time.time()
    try:
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, "INVALID_FRAME", 0.0, 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_file = HAAR_CASCADE_PATH if os.path.exists(HAAR_CASCADE_PATH) else cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_file)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30))

        if len(faces) > 0 and os.path.exists(LBPH_MODEL_PATH) and hasattr(cv2, "face"):
            recognizer = cv2.face.LBPHFaceRecognizer.create()
            recognizer.read(LBPH_MODEL_PATH)
            faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces_sorted[0]
            face_roi = gray[y:y+h, x:x+w]
            label, lbph_conf = recognizer.predict(face_roi)

            user_map = {
                789123: "Akmal",
                451699: "Iqbal",
                249731: "Shafwan",
                619292: "Syauqi"
            }
            authorized = (lbph_conf < 80.0)
            score = round(max(0.0, 100.0 - lbph_conf) / 100.0, 4)
            proc_ms = round((time.time() - t0) * 1000, 2)
            display_name = user_map.get(label, f"USER_{label}") if authorized else "UNAUTHORIZED"
            return authorized, display_name, score, proc_ms
        else:
            return False, "NO_FACE_DETECTED", 0.0, round((time.time() - t0) * 1000, 2)
    except Exception as e:
        return False, "ERROR_PROCESSING", 0.0, round((time.time() - t0) * 1000, 2)

def verify_owner_access(hw=None, lcd=None, force_decision=None, test_image_bytes=None, cloud_url=None):
    print("\n" + "="*60)
    print("  [MAS] MEMULAI PROSES AUTENTIKASI PEMILIK (LOCKER 2)")
    print("="*60)

    lcd_write_lines("Autentikasi Wajah", "Tatap Kamera...", "Evaluasi AI MAS...", "Mohon Tunggu...")

    frame_bytes = test_image_bytes or capture_camera_frame()
    if not frame_bytes:
        print("[-] Gagal mengambil gambar dari kamera.")
        lcd_write_lines("AKSES DITOLAK!", "Kamera Bermasalah", "Coba Lagi")
        beep_denied()
        return False

    telemetry = get_system_telemetry(force_decision=force_decision)
    decision, sched_conf, method = query_scheduler_agent(telemetry)
    print(f"[MAS] Keputusan Scheduler: {'1 (CLOUD)' if decision == 1 else '0 (EDGE)'}")

    authorized = False
    user_id = None
    proc_ms = 0.0
    confidence = 0.0
    task_id = f"TASK_{int(time.time() * 1000)}"

    if decision == 1:
        target_cloud = cloud_url or CLOUD_GPU_URL
        mig_res = dispatch_migration(task_id, "SB01", frame_bytes, decision=1, cloud_url=target_cloud)
        if mig_res["status"] == "Success":
            authorized = True
            user_id = mig_res.get("user_id")
            confidence = mig_res.get("confidence", 0.95)
            proc_ms = mig_res.get("processing_time_ms", 25.0)
        else:
            decision = 0

    if decision == 0:
        authorized, user_id, confidence, proc_ms = verify_face_locally(frame_bytes)

    # Buffer decision into SQLite to guarantee zero-loss and sync to Cloud
    buffer_decision(
        task_id=task_id,
        decision=decision,
        decision_label="MIGRASI_KE_CLOUD" if decision == 1 else "PROSES_DI_EDGE",
        execution_node="Cloud GPU (RTX 3050)" if decision == 1 else "Device Edge (Pi 5)",
        cpu_pct=telemetry["CPU"],
        ram_pct=telemetry["RAM_pct"],
        latency_ms=telemetry["Latency"],
        execution_time_ms=proc_ms,
        user_id=user_id or "UNKNOWN",
        confidence=confidence,
        status="SUCCESS" if authorized else "REJECTED",
        notes=f"Owner auth via MAS ({method})"
    )

    if authorized:
        print(f"[+] AKSES DITERIMA: {user_id}")
        lcd_write_lines("AKSES DITERIMA!", f"Halo, {user_id}"[:20], "Membuka Loker 2", "Silakan Buka Pintu")
        trigger_relay_safe(2, duration=2.5)
        return True
    else:
        print(f"[-] AKSES DITOLAK: {user_id}")
        lcd_write_lines("AKSES DITOLAK!", "Wajah Tdk Cocok", "Bukan Pemilik", "Coba Lagi")
        beep_denied()
        return False


# --- Database Query Helpers for Keyboard Operations ---
def check_db_resi(suffix5):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, tracking_number, package_name FROM package_center_packageentry WHERE RIGHT(tracking_number, 5) = %s LIMIT 1;", (suffix5,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        print("[-] DB resi check error:", e)
        return None

def check_db_otp(otp6):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, otp, status FROM marketplace_transaction WHERE otp = %s AND status = 'AWAITING_PICKUP' LIMIT 1;", (otp6,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        print("[-] DB OTP check error:", e)
        return None

def mark_db_otp_completed(tx_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE marketplace_transaction SET status = 'COMPLETED' WHERE id = %s;", (tx_id,))
        conn.commit()
        conn.close()
        print(f"[DB] Transaction #{tx_id} completed.")
    except Exception as e:
        print("[-] DB update error:", e)


# --- State Machine & Interactive Input Logic ---
STATE_STANDBY = "STANDBY"
STATE_INPUT_RESI = "INPUT_RESI"
STATE_INPUT_OTP = "INPUT_OTP"
current_state = STATE_STANDBY
typed_buffer = ""
last_action_time = time.time()

def show_standby_screen():
    global current_state, typed_buffer, last_action_time
    current_state = STATE_STANDBY
    typed_buffer = ""
    last_action_time = time.time()
    print("[MENU] Returning to STANDBY screen.")
    lcd_write_lines(
        "BoxInAja - Penlok",
        "4.Kirim  5.Ambil",
        "Tombol: Buka Wajah",
        "Pilih [4] / [5]:"
    )

def handle_key_event(key_char):
    global current_state, typed_buffer, last_action_time
    last_action_time = time.time()
    print(f"\n[KEY_EVENT] Key: '{key_char}' | Current State: {current_state} | Current Buffer: '{typed_buffer}'")

    if key_char in ('ESC', 'C', 'c'):
        show_standby_screen()
        return

    # ============================================================
    # 1. STATE: STANDBY (Menu Utama)
    # ============================================================
    if current_state == STATE_STANDBY:
        if key_char == '4':
            # Option 4: Kirim Paket -> DIRECT to 5-digit resi entry!
            current_state = STATE_INPUT_RESI
            typed_buffer = ""
            print("[STATE] Entered STATE_INPUT_RESI")
            lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", "> _____ ", "#=Kirim  *=Batal")

        elif key_char == '5':
            # Option 5: Ambil Paket -> DIRECT to 6-digit OTP entry!
            current_state = STATE_INPUT_OTP
            typed_buffer = ""
            print("[STATE] Entered STATE_INPUT_OTP")
            lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", "> ______", "#=Buka   *=Batal")

        elif key_char in ('O', 'o'):
            # Keyboard letter 'O' triggers Owner Face Auth
            verify_owner_access()
            time.sleep(1.5)
            show_standby_screen()

        elif key_char in '0123456789':
            # Helpful feedback if user presses other number at standby
            print(f"[STANDBY] Unmapped number '{key_char}' at standby.")
            beep_short()
            lcd_write_lines("Pilihan Menu:", "Tekan [4] utk Kirim", "Tekan [5] utk Ambil", "Tombol utk Wajah")
            time.sleep(1.5)
            show_standby_screen()

    # ============================================================
    # 2. STATE: INPUT_RESI (5-Digit Tracking Number)
    # ============================================================
    elif current_state == STATE_INPUT_RESI:
        if key_char in ('BACKSPACE', '*'):
            if len(typed_buffer) > 0:
                typed_buffer = typed_buffer[:-1]
                lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", f"> {typed_buffer.ljust(5, '_')}", "#=Kirim  *=Hapus")
            else:
                show_standby_screen()

        elif key_char in '0123456789':
            if len(typed_buffer) < 5:
                typed_buffer += key_char
                print(f"[RESI_BUFFER] Updated: '{typed_buffer}'")
                lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", f"> {typed_buffer.ljust(5, '_')}", "#=Kirim  *=Hapus")
                
                # Auto-validate once 5 digits are entered!
                if len(typed_buffer) == 5:
                    time.sleep(0.3)
                    validate_resi_and_open(typed_buffer)

        elif key_char in ('ENTER', '#') and len(typed_buffer) >= 5:
            validate_resi_and_open(typed_buffer)

    # ============================================================
    # 3. STATE: INPUT_OTP (6-Digit Marketplace OTP)
    # ============================================================
    elif current_state == STATE_INPUT_OTP:
        if key_char in ('BACKSPACE', '*'):
            if len(typed_buffer) > 0:
                typed_buffer = typed_buffer[:-1]
                lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", f"> {typed_buffer.ljust(6, '_')}", "#=Buka   *=Hapus")
            else:
                show_standby_screen()

        elif key_char in '0123456789':
            if len(typed_buffer) < 6:
                typed_buffer += key_char
                print(f"[OTP_BUFFER] Updated: '{typed_buffer}'")
                lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", f"> {typed_buffer.ljust(6, '_')}", "#=Buka   *=Hapus")
                
                # Auto-validate once 6 digits are entered!
                if len(typed_buffer) == 6:
                    time.sleep(0.3)
                    validate_otp_and_open(typed_buffer)

        elif key_char in ('ENTER', '#') and len(typed_buffer) >= 6:
            validate_otp_and_open(typed_buffer)


def validate_resi_and_open(resi_code):
    print(f"\n[VALIDASI_RESI] Validating 5-digit resi: '{resi_code}'...")
    lcd_write_lines("Kirim Paket", "Memvalidasi Resi...", f"Resi: {resi_code}", "Mohon Tunggu...")
    pkg = check_db_resi(resi_code)
    if pkg:
        print(f"[RESI] Valid package found: #{pkg[0]} ({pkg[1]} - {pkg[2]})")
        lcd_write_lines("RESI DITERIMA!", f"Resi: {resi_code}", "Membuka Loker 1", "Silakan Masukkan")
        trigger_relay_safe(3, duration=2.5) # Relay 3 = Locker 1
        time.sleep(1.5)
        # Servos trapdoor handoff
        lcd_write_lines("Transfer Paket", "Membuka Trapdoor...", "Pindah ke Loker 2", "Mohon Tunggu...")
        run_trapdoor_cycle()
        lcd_write_lines("Sukses Disimpan!", "Paket di Loker 2", "Pintu Terkunci", "Terima Kasih!")
        time.sleep(2.0)
    else:
        print(f"[RESI] Invalid resi code: {resi_code}")
        lcd_write_lines("RESI TIDAK COCOK!", f"Resi: {resi_code}", "Data Tdk Ditemukan", "Akses Ditolak")
        beep_denied()
        time.sleep(2.0)
    show_standby_screen()


def validate_otp_and_open(otp_code):
    print(f"\n[VALIDASI_OTP] Validating 6-digit OTP: '{otp_code}'...")
    lcd_write_lines("Ambil Paket", "Memvalidasi OTP...", f"OTP: {otp_code}", "Mohon Tunggu...")
    tx = check_db_otp(otp_code)
    if tx:
        print(f"[OTP] Valid marketplace transaction #{tx[0]}")
        lcd_write_lines("OTP COCOK!", "Transaksi Selesai", "Membuka Loker 3", "Silakan Ambil")
        trigger_relay_safe(1, duration=3.0) # Relay 1 = Locker 3
        mark_db_otp_completed(tx[0])
        time.sleep(2.0)
    else:
        print(f"[OTP] Invalid OTP: {otp_code}")
        lcd_write_lines("OTP TIDAK VALID!", f"OTP: {otp_code}", "Kode Salah / Habis", "Akses Ditolak")
        beep_denied()
        time.sleep(2.0)
    show_standby_screen()


# --- Worker 1: USB Keyboard Listener (Non-blocking & Dynamic Hotplug) ---
def find_real_usb_keyboards():
    """Find real USB keyboard nodes while ignoring HDMI audio jack and power buttons"""
    candidates = []
    # 1. By-id or by-path matching kbd
    for p in glob.glob("/dev/input/by-id/*kbd*") + glob.glob("/dev/input/by-path/*kbd*"):
        r = os.path.realpath(p)
        if r not in candidates:
            candidates.append(r)
    if candidates:
        return candidates

    # 2. Parse /proc/bus/input/devices
    if os.path.exists("/proc/bus/input/devices"):
        try:
            with open("/proc/bus/input/devices") as f:
                content = f.read()
            for sec in content.split("\n\n"):
                if "hdmi" in sec.lower() or "pwr_button" in sec.lower():
                    continue
                if "kbd" in sec:
                    for line in sec.splitlines():
                        if line.startswith("H: Handlers="):
                            for part in line.split():
                                if part.startswith("event"):
                                    node = f"/dev/input/{part}"
                                    if os.path.exists(node) and node not in candidates:
                                        candidates.append(node)
        except Exception:
            pass
    return candidates

def usb_keyboard_listener_thread():
    print("[DAEMON] Memulai USB Keyboard listener thread (Hotplug-ready)...")
    EV_KEY_MAP = {
        2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 9: '8', 10: '9', 11: '0',
        79: '1', 80: '2', 81: '3', 75: '4', 76: '5', 77: '6', 71: '7', 72: '8', 73: '9', 82: '0',
        28: '#', 96: '#',          # Enter / Keypad Enter -> # (Confirm)
        14: '*',                    # Backspace -> * (Delete/Back)
        1: 'ESC',
        24: 'O',                    # 'O' key for Owner
        55: '*', 43: '#', 98: '/'
    }

    struct_fmt = "qqHHi"
    event_size = struct.calcsize(struct_fmt)

    while True:
        keyboards = find_real_usb_keyboards()
        if not keyboards:
            time.sleep(1.5)
            continue

        active_fds = []
        for dev_path in keyboards:
            try:
                fd = os.open(dev_path, os.O_RDONLY | os.O_NONBLOCK)
                active_fds.append(fd)
                print(f"[KEYBOARD] Connected to input node: {dev_path}")
            except Exception:
                continue

        if not active_fds:
            time.sleep(1.5)
            continue

        try:
            while True:
                rlist, _, _ = select.select(active_fds, [], [], 1.0)
                if not rlist:
                    all_exist = all(os.path.exists(d) for d in keyboards)
                    if not all_exist:
                        break
                    continue

                for fd in rlist:
                    data = os.read(fd, event_size)
                    if len(data) >= event_size:
                        sec, usec, ev_type, ev_code, ev_val = struct.unpack(struct_fmt, data)
                        # EV_KEY = 1, ev_val == 1 is key-down
                        if ev_type == 1 and ev_val == 1:
                            if ev_code in EV_KEY_MAP:
                                key_char = EV_KEY_MAP[ev_code]
                                beep_short()
                                handle_key_event(key_char)
        except Exception as e:
            print(f"[-] Keyboard select error: {e}")
        finally:
            for fd in active_fds:
                try: os.close(fd)
                except: pass
            time.sleep(1.0)


# --- Worker 2: Physical GPIO Matrix Keypad Scanner ---
def gpio_matrix_keypad_thread():
    print("[DAEMON] Memulai GPIO Matrix Keypad scanner thread (BCM 8,25,11 & 5,1,0,7)...")
    h = None
    for cand in (15, 4, 0):
        try:
            h = lgpio.gpiochip_open(cand)
            break
        except Exception:
            pass

    if h is None:
        print("[-] Gagal membuka gpiochip untuk keypad matrix.")
        return

    try:
        for col_pin in KEYPAD_COLUMNS:
            lgpio.gpio_claim_output(h, col_pin, 0)
        for row_pin in KEYPAD_ROWS:
            lgpio.gpio_claim_input(h, row_pin, lgpio.SET_PULL_DOWN)

        while True:
            pressed_key = None
            found_col_pin = None
            found_row_pin = None

            for col_idx, col_pin in enumerate(KEYPAD_COLUMNS):
                lgpio.gpio_write(h, col_pin, 1)
                for row_idx, row_pin in enumerate(KEYPAD_ROWS):
                    if lgpio.gpio_read(h, row_pin) == 1:
                        pressed_key = KEYPAD_MATRIX[row_idx][col_idx]
                        found_col_pin = col_pin
                        found_row_pin = row_pin
                        break
                lgpio.gpio_write(h, col_pin, 0)
                if pressed_key:
                    break

            if pressed_key is not None:
                print(f"[KEYPAD_HARDWARE] Key: '{pressed_key}' detected (Col Pin {found_col_pin}, Row Pin {found_row_pin})")
                beep_short()
                handle_key_event(pressed_key)

                # Wait for release cleanly to prevent bounce/repeat races
                t_rel = time.time()
                while time.time() - t_rel < 2.0:
                    still_pressed = False
                    for col_pin in KEYPAD_COLUMNS:
                        lgpio.gpio_write(h, col_pin, 1)
                        for row_pin in KEYPAD_ROWS:
                            if lgpio.gpio_read(h, row_pin) == 1:
                                still_pressed = True
                                break
                        lgpio.gpio_write(h, col_pin, 0)
                        if still_pressed:
                            break
                    if not still_pressed:
                        break
                    time.sleep(0.03)

            time.sleep(0.04)
    except Exception as e:
        print(f"[-] GPIO Keypad scanner error: {e}")
    finally:
        if h is not None:
            try: lgpio.gpiochip_close(h)
            except: pass


# --- Worker 3: Physical Push Button (BCM 16) ---
def physical_button_listener_thread():
    print(f"[DAEMON] Memulai monitoring tombol fisik BCM {OWNER_BUTTON_PIN}...")
    btn = None
    try:
        btn = DigitalInputDevice(OWNER_BUTTON_PIN, pull_up=True)
    except Exception as e:
        print(f"[-] Button device error: {e}")
        return

    try:
        while True:
            if btn.is_active:
                print(f"\n[TRIGGER] Tombol fisik BCM {OWNER_BUTTON_PIN} DITEKAN!")
                beep_short()
                verify_owner_access(lcd=global_lcd)
                time.sleep(1.0)
                show_standby_screen()
            time.sleep(0.1)
    except Exception as e:
        print(f"[-] Button listener error: {e}")
    finally:
        if btn:
            try: btn.close()
            except: pass


# --- Worker 4: Inactivity Timeout Guard ---
def inactivity_timeout_thread():
    global current_state, last_action_time
    while True:
        time.sleep(2.0)
        if current_state != STATE_STANDBY:
            if time.time() - last_action_time > 30.0:
                print("[TIMEOUT] 30 seconds inactivity. Auto-returning to STANDBY.")
                show_standby_screen()


def run_daemon():
    print("="*60)
    print("  PENLOK SMART LOCKER UNIFIED DAEMON (DUAL KEYPAD + BUTTON)")
    print("="*60)
    show_standby_screen()

    start_background_syncer()

    t_kbd = threading.Thread(target=usb_keyboard_listener_thread, daemon=True, name="USBKbdThread")
    t_kbd.start()

    t_mat = threading.Thread(target=gpio_matrix_keypad_thread, daemon=True, name="GPIOMatrixKeypadThread")
    t_mat.start()

    t_btn = threading.Thread(target=physical_button_listener_thread, daemon=True, name="PhysicalButtonThread")
    t_btn.start()

    t_tout = threading.Thread(target=inactivity_timeout_thread, daemon=True, name="TimeoutThread")
    t_tout.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[DAEMON] Terminated by user.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PENLOK Edge MAS Controller")
    parser.add_argument("--listen", action="store_true", help="Run background dual keypad & button daemon")
    parser.add_argument("--once", action="store_true", help="Run face verification once and exit")
    parser.add_argument("--force-cloud", action="store_true", help="Force cloud migration decision (1)")
    parser.add_argument("--force-edge", action="store_true", help="Force edge local decision (0)")

    args = parser.parse_args()

    if args.listen:
        run_daemon()
    elif args.force_cloud:
        verify_owner_access(force_decision=1)
    elif args.force_edge:
        verify_owner_access(force_decision=0)
    elif args.once:
        verify_owner_access()
    else:
        run_daemon()
