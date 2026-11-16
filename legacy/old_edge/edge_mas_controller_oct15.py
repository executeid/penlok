#!/usr/bin/env python3
"""
PENLOK Edge Multi-Agent System (MAS) Unified Controller
Target Node: pi@10.1.1.224 (Raspberry Pi 5)
Handles:
- USB Keyboard Input Listener (/dev/input/event* or /dev/input/by-id/*kbd*)
- Physical Push Button (BCM 16)
- I2C LCD Display (0x27) with interactive Menu Utama
- Courier Inbound Flow (5-digit Resi -> Relay 3 / BCM 10 -> Ultrasonic -> Servos)
- Marketplace Buyer Pickup (6-digit OTP -> Relay 1 / BCM 6 -> DB update)
- Owner Biometric Access (Face Capture -> MAS Scheduler -> Relay 2 / BCM 9)
"""

import sys
import os
import time
import glob
import struct
import threading
import argparse
import requests
import psutil
import psycopg2
import numpy as np
import cv2
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

# --- I2C LCD Integration ---
global_lcd = None
try:
    from RPLCD.i2c import CharLCD
    global_lcd = CharLCD('PCF8574', 0x27)
    print("[INIT] I2C LCD (0x27) initialized successfully.")
except Exception as e:
    print(f"[INIT] I2C LCD not available: {e}")

lcd_lock = threading.Lock()

def lcd_write_lines(line0="", line1="", line2="", line3=""):
    """Thread-safe LCD display updater"""
    if not global_lcd:
        return
    with lcd_lock:
        try:
            global_lcd.clear()
            lines = [line0, line1, line2, line3]
            for idx, text in enumerate(lines):
                if text:
                    global_lcd.cursor_pos = (idx, 0)
                    global_lcd.write_string(str(text)[:20])
        except Exception as e:
            print(f"[-] LCD write error: {e}")

# Hardware Devices (Singletons with safe recovery)
relays = {}
indicators = {}
sensors = {}

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
    if lcd is None:
        lcd = global_lcd
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

    if decision == 1:
        task_id = f"TASK_{int(time.time() * 1000)}"
        target_cloud = cloud_url or CLOUD_GPU_URL
        mig_res = dispatch_migration(task_id, "SB01", frame_bytes, decision=1, cloud_url=target_cloud)
        if mig_res["status"] == "Success":
            authorized = True
            user_id = mig_res.get("user_id")
        else:
            decision = 0

    if decision == 0:
        authorized, user_id, conf, proc_ms = verify_face_locally(frame_bytes)

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


# --- Keyboard & State Machine Listener ---
STATE_STANDBY = "STANDBY"
STATE_KIRIM_MENU = "KIRIM_MENU"
STATE_INPUT_RESI = "INPUT_RESI"
STATE_INPUT_OTP = "INPUT_OTP"
current_state = STATE_STANDBY
typed_buffer = ""

def show_standby_screen():
    global current_state, typed_buffer
    current_state = STATE_STANDBY
    typed_buffer = ""
    lcd_write_lines(
        "BoxInAja - Penlok",
        "4.Kirim  5.Ambil",
        "Tombol/O: Buka Wajah",
        "Ketik [4/5/O]:"
    )

def handle_key_event(key_char):
    global current_state, typed_buffer
    print(f"[KEYBOARD] Key: '{key_char}' | State: {current_state} | Buffer: '{typed_buffer}'")

    if key_char == 'ESC':
        show_standby_screen()
        return

    # --- STATE: STANDBY ---
    if current_state == STATE_STANDBY:
        if key_char == '4':
            current_state = STATE_KIRIM_MENU
            lcd_write_lines("Kirim Paket", "5.Ketik 5 Digit Resi", "O.Buka Wajah", "Pilih [5] ESC=Btl")
        elif key_char == '5':
            current_state = STATE_INPUT_OTP
            typed_buffer = ""
            lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", "> ______", "ENTER=Buka ESC=Btl")
        elif key_char in ('O', 'o', '9'):
            verify_owner_access(lcd=global_lcd)
            time.sleep(1.5)
            show_standby_screen()

    # --- STATE: KIRIM MENU ---
    elif current_state == STATE_KIRIM_MENU:
        if key_char in ('5', '4', 'ENTER'):
            current_state = STATE_INPUT_RESI
            typed_buffer = ""
            lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", "> _____ ", "ENTER=Kirim ESC=Btl")

    # --- STATE: INPUT RESI ---
    elif current_state == STATE_INPUT_RESI:
        if key_char == 'BACKSPACE':
            typed_buffer = typed_buffer[:-1]
            lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", f"> {typed_buffer.ljust(5, '_')}", "ENTER=Kirim ESC=Btl")
        elif key_char in '0123456789' and len(typed_buffer) < 5:
            typed_buffer += key_char
            lcd_write_lines("Kirim Paket", "Ketik 5 Digit Resi:", f"> {typed_buffer.ljust(5, '_')}", "ENTER=Kirim ESC=Btl")
            if len(typed_buffer) == 5:
                # Auto submit on 5 digits
                handle_key_event('ENTER')
        elif key_char == 'ENTER' and len(typed_buffer) >= 5:
            resi_code = typed_buffer
            lcd_write_lines("Kirim Paket", "Memvalidasi Resi...", f"Resi: {resi_code}", "Mohon Tunggu...")
            pkg = check_db_resi(resi_code)
            if pkg:
                print(f"[RESI] Valid package found: #{pkg[0]} ({pkg[1]})")
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

    # --- STATE: INPUT OTP ---
    elif current_state == STATE_INPUT_OTP:
        if key_char == 'BACKSPACE':
            typed_buffer = typed_buffer[:-1]
            lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", f"> {typed_buffer.ljust(6, '_')}", "ENTER=Buka ESC=Btl")
        elif key_char in '0123456789' and len(typed_buffer) < 6:
            typed_buffer += key_char
            lcd_write_lines("Ambil Paket", "Ketik 6 Digit OTP:", f"> {typed_buffer.ljust(6, '_')}", "ENTER=Buka ESC=Btl")
            if len(typed_buffer) == 6:
                handle_key_event('ENTER')
        elif key_char == 'ENTER' and len(typed_buffer) >= 6:
            otp_code = typed_buffer
            lcd_write_lines("Ambil Paket", "Memvalidasi OTP...", f"OTP: {otp_code}", "Mohon Tunggu...")
            tx = check_db_otp(otp_code)
            if tx:
                print(f"[OTP] Valid marketplace transaction #{tx[0]}")
                lcd_write_lines("OTP COCOK!", "Transaksi Selesai", "Membuka Loker 3", "Silakan Ambil")
                trigger_relay_safe(1, duration=3.0) # Relay 1 = Locker 3
                mark_db_otp_completed(tx[0])
                time.sleep(1.5)
            else:
                print(f"[OTP] Invalid OTP: {otp_code}")
                lcd_write_lines("OTP TIDAK VALID!", f"OTP: {otp_code}", "Kode Salah / Habis", "Akses Ditolak")
                beep_denied()
                time.sleep(2.0)
            show_standby_screen()


def usb_keyboard_listener_thread():
    """Reads Linux evdev events from plugged-in USB keyboard"""
    print("[DAEMON] Memulai USB Keyboard listener thread...")
    EV_KEY_MAP = {
        2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 9: '8', 10: '9', 11: '0',
        79: '1', 80: '2', 81: '3', 75: '4', 76: '5', 77: '6', 71: '7', 72: '8', 73: '9', 82: '0',
        28: 'ENTER', 96: 'ENTER',
        14: 'BACKSPACE',
        1: 'ESC',
        24: 'O', # 'O' key for Owner
        55: '*', 43: '#', 98: '/'
    }

    struct_fmt = "qqHHi"
    event_size = struct.calcsize(struct_fmt)

    while True:
        # Search for connected keyboard
        kbd_devices = glob.glob("/dev/input/by-id/*kbd*") or glob.glob("/dev/input/event*")
        active_fd = None
        for dev_path in kbd_devices:
            try:
                fd = os.open(dev_path, os.O_RDONLY)
                active_fd = fd
                print(f"[KEYBOARD] Connected to keyboard device: {dev_path}")
                break
            except Exception:
                continue

        if active_fd is None:
            time.sleep(2.0)
            continue

        try:
            while True:
                data = os.read(active_fd, event_size)
                if not data or len(data) < event_size:
                    break
                sec, usec, ev_type, ev_code, ev_val = struct.unpack(struct_fmt, data)
                # EV_KEY = 1, ev_val == 1 is key-down
                if ev_type == 1 and ev_val == 1:
                    if ev_code in EV_KEY_MAP:
                        key_char = EV_KEY_MAP[ev_code]
                        handle_key_event(key_char)
        except Exception as e:
            print(f"[-] Keyboard read exception: {e}")
        finally:
            try: os.close(active_fd)
            except: pass
            time.sleep(1.0)


def physical_button_listener_thread():
    """Monitors physical push button BCM 16"""
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
                verify_owner_access(lcd=global_lcd)
                time.sleep(1.0) # Debounce
                show_standby_screen()
            time.sleep(0.1)
    except Exception as e:
        print(f"[-] Button listener error: {e}")
    finally:
        if btn:
            try: btn.close()
            except: pass


def run_daemon():
    print("="*60)
    print("  PENLOK SMART LOCKER HARDWARE DAEMON (KEYBOARD + BUTTON)")
    print("="*60)
    show_standby_screen()

    # Start USB keyboard reader thread
    t_kbd = threading.Thread(target=usb_keyboard_listener_thread, daemon=True)
    t_kbd.start()

    # Start physical button thread
    t_btn = threading.Thread(target=physical_button_listener_thread, daemon=True)
    t_btn.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[DAEMON] Terminated by user.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PENLOK Edge MAS Controller")
    parser.add_argument("--listen", action="store_true", help="Run background keyboard & button listener daemon")
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
