#!/usr/bin/env python3
"""
Smart Locker All-in-One Manual Diagnostic & Workflow Test Harness
Replaces physical matrix keypad with standard keyboard / terminal input.
Designed for Raspberry Pi 5 (RP1 gpiochip15).
"""

import sys
import os
import time
import threading
import psycopg2
import lgpio
from gpiozero import OutputDevice, DigitalInputDevice, Servo

# ==============================================================================
# 1. HARDWARE PIN DEFINITIONS (BCM)
# ==============================================================================
RELAY_PINS = {
    1: 6,    # Locker 3 (Marketplace Solenoid) - Active LOW
    2: 9,    # Locker 2 (Storage / Owner Solenoid) - Active LOW
    3: 10,   # Locker 1 (Inbound Courier Solenoid) - Active LOW
    4: 19    # Locker 0 / Aux Latch - Active LOW
}

SERVO_LEFT_PIN = 13   # PWM Servo Trapdoor Pair 1
SERVO_RIGHT_PIN = 12  # PWM Servo Trapdoor Pair 2

TRIG_PIN = 15         # HC-SR04 Ultrasonic Trigger
ECHO_PIN = 17         # HC-SR04 Ultrasonic Echo
IR_DOOR_PIN = 26      # Infrared Door Sensor (Active LOW = closed)
VIBRATION_PIN = 24    # SW-420 Tamper / Vibration Sensor
OWNER_BUTTON_PIN = 16 # Owner Push Button (Active LOW)

DOUT_PIN = 4          # HX711 Loadcell DOUT
SCK_PIN = 14          # HX711 Loadcell SCK
OFFSET = 8763202      # HX711 Tare Offset (111g empty tray)
SCALE = 196.584       # HX711 Calibration Factor per gram

BUZZER_PIN = 21       # Active HIGH Buzzer
LED_GREEN_PIN = 27    # Indicator Green (Active LOW)
LED_RED_PIN = 18      # Indicator Red (Active LOW)

DETECTION_THRESHOLD_CM = 23.0  # Ultrasonic parcel detection limit

# ==============================================================================
# 2. CHIP & DATABASE INITIALIZATION
# ==============================================================================
def get_gpio_chip():
    for candidate in (15, 4, 0):
        try:
            h = lgpio.gpiochip_open(candidate)
            lgpio.gpiochip_close(h)
            return candidate
        except Exception:
            continue
    return 15

GPIO_CHIP = get_gpio_chip()

DB_CONFIG = {
    "host": "localhost",
    "port": 1723,
    "user": "smartlocker_admin",
    "password": "penlokjaya",
    "dbname": "smartlocker",
    "connect_timeout": 3
}

# Optional I2C LCD init
lcd = None
try:
    from RPLCD.i2c import CharLCD
    lcd = CharLCD('PCF8574', 0x27)
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("BoxInAja Test Mode")
    print("[INIT] LCD I2C detected on 0x27")
except Exception as e:
    print(f"[INIT] LCD not available (running terminal-only): {e}")

# ==============================================================================
# 3. LOW-LEVEL HARDWARE CONTROLLERS
# ==============================================================================
class HardwareController:
    def __init__(self):
        self.lg_handle = lgpio.gpiochip_open(GPIO_CHIP)

        # Relays (Active LOW)
        self.relays = {
            1: OutputDevice(RELAY_PINS[1], active_high=False, initial_value=False),
            2: OutputDevice(RELAY_PINS[2], active_high=False, initial_value=False),
            3: OutputDevice(RELAY_PINS[3], active_high=False, initial_value=False),
            4: OutputDevice(RELAY_PINS[4], active_high=False, initial_value=False),
        }

        # Indicators
        self.buzzer = OutputDevice(BUZZER_PIN, active_high=True, initial_value=False)
        self.led_green = OutputDevice(LED_GREEN_PIN, active_high=False, initial_value=False)
        self.led_red = OutputDevice(LED_RED_PIN, active_high=False, initial_value=False)

        # Sensors (Digital Inputs)
        self.ir_door = DigitalInputDevice(IR_DOOR_PIN, pull_up=False)
        self.vibration = DigitalInputDevice(VIBRATION_PIN, pull_up=False)
        self.owner_btn = DigitalInputDevice(OWNER_BUTTON_PIN, pull_up=True)

        # Ultrasonic via lgpio timing
        lgpio.gpio_claim_output(self.lg_handle, TRIG_PIN, 0)
        lgpio.gpio_claim_input(self.lg_handle, ECHO_PIN)

        # Loadcell pins via lgpio bit-bang
        lgpio.gpio_claim_input(self.lg_handle, DOUT_PIN)
        lgpio.gpio_claim_output(self.lg_handle, SCK_PIN, 0)

    def trigger_relay(self, locker_num, duration=2.0):
        if locker_num not in self.relays:
            print(f"[-] Invalid locker number: {locker_num}")
            return
        print(f"[RELAY] Unlocking Locker {locker_num} (GPIO {RELAY_PINS[locker_num]}) for {duration}s...")
        self.beep_success()
        r = self.relays[locker_num]
        r.on()
        time.sleep(duration)
        r.off()
        print(f"[RELAY] Locker {locker_num} lock engaged.")

    def run_trapdoor_servos(self, duration_open=0.45, pause=1.5, duration_close=0.5):
        print("[SERVO] Actuating dual trapdoor servos (GPIO 12 & 13)...")
        servo_left = None
        servo_right = None
        try:
            servo_left = Servo(SERVO_LEFT_PIN)
            servo_right = Servo(SERVO_RIGHT_PIN)

            # Open trapdoor
            print("  -> Opening trapdoor...")
            servo_left.value = -1
            servo_right.value = 1
            time.sleep(duration_open)
            servo_left.detach()
            servo_right.detach()

            time.sleep(pause)

            # Close trapdoor
            print("  -> Closing trapdoor...")
            servo_left.value = 1
            servo_right.value = -1
            time.sleep(duration_close)
            servo_left.detach()
            servo_right.detach()
            print("[SERVO] Trapdoor cycle completed and servos detached.")
        except Exception as e:
            print(f"[-] Servo actuation error: {e}")
        finally:
            if servo_left:
                try: servo_left.close()
                except: pass
            if servo_right:
                try: servo_right.close()
                except: pass

    def beep_success(self):
        try:
            self.led_green.on()
            self.buzzer.on()
            time.sleep(0.3)
            self.buzzer.off()
            self.led_green.off()
        except: pass

    def beep_fail(self):
        try:
            for _ in range(3):
                self.led_red.on()
                self.buzzer.on()
                time.sleep(0.15)
                self.buzzer.off()
                self.led_red.off()
                time.sleep(0.1)
        except: pass

    def read_ultrasonic(self):
        lgpio.gpio_write(self.lg_handle, TRIG_PIN, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(self.lg_handle, TRIG_PIN, 0)

        pulse_start = time.time()
        timeout = pulse_start + 0.05
        while lgpio.gpio_read(self.lg_handle, ECHO_PIN) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return -1

        pulse_end = time.time()
        timeout = pulse_end + 0.05
        while lgpio.gpio_read(self.lg_handle, ECHO_PIN) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return -1

        duration = pulse_end - pulse_start
        distance = (duration * 34300) / 2
        return round(distance, 2)

    def read_hx711_raw(self):
        count = 0
        lgpio.gpio_write(self.lg_handle, SCK_PIN, 0)
        t_start = time.time()
        while lgpio.gpio_read(self.lg_handle, DOUT_PIN) == 1:
            if time.time() - t_start > 0.1:
                return 0
        for _ in range(24):
            lgpio.gpio_write(self.lg_handle, SCK_PIN, 1)
            count = count << 1
            lgpio.gpio_write(self.lg_handle, SCK_PIN, 0)
            if lgpio.gpio_read(self.lg_handle, DOUT_PIN):
                count += 1
        lgpio.gpio_write(self.lg_handle, SCK_PIN, 1)
        count ^= 0x800000
        lgpio.gpio_write(self.lg_handle, SCK_PIN, 0)
        return count

    def get_weight_grams(self, samples=5):
        total = 0
        valid = 0
        for _ in range(samples):
            raw = self.read_hx711_raw()
            if raw > 0:
                total += raw
                valid += 1
            time.sleep(0.02)
        if valid == 0:
            return 0.0
        avg = total / valid
        return round((avg - OFFSET) / SCALE, 2)

    def close(self):
        for r in self.relays.values():
            r.off()
            r.close()
        self.buzzer.close()
        self.led_green.close()
        self.led_red.close()
        self.ir_door.close()
        self.vibration.close()
        self.owner_btn.close()
        lgpio.gpiochip_close(self.lg_handle)

# ==============================================================================
# 4. DATABASE QUERIES & VERIFICATION
# ==============================================================================
def check_tracking_number(suffix5):
    """Verify last 5 digits of courier tracking number in package_center"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tracking_number, courier_name FROM package_center_packageentry "
            "WHERE RIGHT(tracking_number, 5) = %s LIMIT 1;",
            (suffix5,)
        )
        res = cur.fetchone()
        conn.close()
        return res
    except Exception as e:
        print(f"[-] DB Error: {e}")
        return None

def check_marketplace_otp(otp6):
    """Verify 6-digit buyer pickup OTP in marketplace_transaction"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, otp, status, total_amount FROM marketplace_transaction "
            "WHERE otp = %s AND status = 'AWAITING_PICKUP' LIMIT 1;",
            (otp6,)
        )
        res = cur.fetchone()
        conn.close()
        return res
    except Exception as e:
        print(f"[-] DB Error: {e}")
        return None

def mark_otp_completed(tx_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE marketplace_transaction SET status = 'COMPLETED' WHERE id = %s;", (tx_id,))
        conn.commit()
        conn.close()
        print(f"[DB] Transaction #{tx_id} updated to COMPLETED.")
    except Exception as e:
        print(f"[-] DB update error: {e}")

# ==============================================================================
# 5. END-TO-END OPERATIONAL WORKFLOWS
# ==============================================================================
def workflow_courier_dropoff(hw):
    print("\n" + "="*60)
    print("  WORKFLOW: COURIER PARCEL DROP-OFF (Locker 1 -> Locker 2)")
    print("="*60)
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Kirim Paket")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Masukkan 5 digit:")

    print("Options:")
    print("  [Valid DB samples: '51818', '87654', '23456', '27272']")
    print("  [Enter 'bypass' to skip DB verification]")
    code = input("Enter 5-digit Tracking Number: ").strip()

    if not code:
        print("[-] Canceled.")
        return

    verified = False
    pkg_info = None

    if code.lower() == 'bypass':
        verified = True
        pkg_info = (999, "MANUAL-BYPASS", "Courier-Manual")
    else:
        pkg_info = check_tracking_number(code)
        if pkg_info:
            verified = True
        else:
            print(f"[-] Tracking code '{code}' NOT found in database.")
            hw.beep_fail()
            if lcd:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Resi Tidak Valid")
            return

    print(f"\n[+] Tracking Confirmed! Parcel #{pkg_info[0]} ({pkg_info[1]})")
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Resi Diterima!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Buka Loker 1...")

    # Step 1: Open Locker 1 (Relay 3 / BCM 10)
    print("\n[STEP 1] Opening Locker 1 Solenoid (Relay 3)...")
    hw.trigger_relay(3, duration=2.5)

    # Step 2: Wait for Parcel Placement via Ultrasonic
    print("\n[STEP 2] Waiting for courier to place parcel into Locker 1...")
    print(f"         Monitoring HC-SR04 ultrasonic (Threshold < {DETECTION_THRESHOLD_CM} cm).")
    if lcd:
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Masukkan Paket..")

    parcel_detected = False
    t_start = time.time()
    while time.time() - t_start < 25:
        dist = hw.read_ultrasonic()
        if 0 < dist < DETECTION_THRESHOLD_CM:
            print(f"[SENSOR] Parcel detected! Distance = {dist:.1f} cm")
            parcel_detected = True
            break
        time.sleep(0.5)

    if not parcel_detected:
        print("[WARN] No parcel detected within 25 seconds timeout. (Continuing anyway)")

    # Step 3: Wait for Door Closure via IR Sensor
    print("\n[STEP 3] Waiting for courier to CLOSE Locker 1 door...")
    print("         Monitoring IR Sensor on GPIO 26 (pull-down).")
    if lcd:
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Tutup Pintu...")

    door_closed = False
    t_start = time.time()
    while time.time() - t_start < 20:
        # DigitalInputDevice is_active: door open = True, closed = False
        is_open = hw.ir_door.is_active
        if not is_open:
            print("[SENSOR] Door closure confirmed by IR sensor!")
            door_closed = True
            break
        time.sleep(0.4)

    if not door_closed:
        print("[WARN] Door close timeout. Assuming door is shut.")

    # Step 4: Actuate Trapdoor Servos to transfer parcel to Locker 2
    time.sleep(0.5)
    print("\n[STEP 4] Actuating trapdoor mechanism...")
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Transfer Paket")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Buka Trapdoor...")

    hw.run_trapdoor_servos(duration_open=0.45, pause=1.5, duration_close=0.5)

    # Step 5: Read new weight in Locker 2 (HX711)
    weight = hw.get_weight_grams(samples=5)
    print(f"[LOADCELL] Current storage tray weight: {weight:.1f} grams")

    hw.beep_success()
    print("\n[DONE] Parcel safely transferred to secure Locker 2!")
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Sukses Disimpan!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Berat: {weight:.0f}g")
    time.sleep(2)


def workflow_buyer_pickup(hw):
    print("\n" + "="*60)
    print("  WORKFLOW: MARKETPLACE BUYER PICKUP (Locker 3)")
    print("="*60)
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Ambil Paket")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Masukkan 6-OTP:")

    print("Options:")
    print("  [Valid DB samples: '749674', '832505', '263312', '104416', '421803']")
    print("  [Enter 'bypass' to skip DB verification]")
    otp = input("Enter 6-digit OTP: ").strip()

    if not otp:
        print("[-] Canceled.")
        return

    verified = False
    tx_info = None

    if otp.lower() == 'bypass':
        verified = True
        tx_info = (999, "MANUAL-OTP", "AWAITING_PICKUP", 0)
    else:
        tx_info = check_marketplace_otp(otp)
        if tx_info:
            verified = True
        else:
            print(f"[-] OTP '{otp}' is INVALID or already completed.")
            hw.beep_fail()
            if lcd:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("OTP Salah!")
            return

    print(f"\n[+] OTP Verified! Transaction #{tx_info[0]} Status={tx_info[2]}")
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("OTP Sesuai!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Buka Loker 3...")

    # Open Locker 3 (Relay 1 / BCM 6)
    print("[RELAY] Unlocking Locker 3 Solenoid (Relay 1)...")
    hw.trigger_relay(1, duration=3.0)

    if tx_info[0] != 999:
        mark_otp_completed(tx_info[0])

    print("[DONE] Buyer collected item. Locker 3 closed.")
    if lcd:
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Silakan Ambil!")
    time.sleep(2)


def workflow_owner_unlock(hw):
    print("\n" + "="*60)
    print("  WORKFLOW: OWNER ACCESS (Locker 2 / Relay 2 - GPIO 9)")
    print("="*60)
    print("Select verification mode:")
    print("  [1] Multi-Agent Face Authentication (Camera -> Scheduler -> Migration/Edge)")
    print("  [2] Direct Solenoid Unlock (Bypass / Hardware Test)")
    sub = input("Selection [1/2, default=1]: ").strip()

    if sub == '2':
        print("[RELAY] Direct Solenoid Bypass triggered. Opening Locker 2...")
        if lcd:
            try:
                lcd.clear()
                lcd.cursor_pos = (0, 0)
                lcd.write_string("Akses Pemilik")
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Buka Loker 2...")
            except: pass
        hw.trigger_relay(2, duration=2.5)
        print("[DONE] Owner compartment unlocked.")
        if lcd:
            try:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Loker 2 Terbuka")
            except: pass
        time.sleep(2)
        return

    # Multi-Agent Face Authentication flow
    try:
        # Dynamically import edge_mas_controller from parent or current directory
        penlock_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if penlock_root not in sys.path:
            sys.path.insert(0, penlock_root)
        from edge_mas_controller import verify_owner_access
        success = verify_owner_access(hw=hw, lcd=lcd)
        if success:
            print("[DONE] Owner authentication successful. Locker 2 cycle completed.")
        else:
            print("[FAIL] Owner authentication rejected.")
    except Exception as e:
        print(f"[!] Error executing MAS Face Authentication: {e}")
        print("[!] Falling back to direct diagnostic solenoid trigger...")
        hw.trigger_relay(2, duration=2.5)


def monitor_sensors_live(hw):
    print("\n" + "="*60)
    print("  LIVE SENSOR STREAM (Press Ctrl+C to stop)")
    print("="*60)
    try:
        while True:
            dist = hw.read_ultrasonic()
            ir_state = "OPEN (Clear)" if hw.ir_door.is_active else "CLOSED (Obstacle)"
            vibe_state = "SHAKE DETECTED" if hw.vibration.is_active else "Quiet"
            btn_state = "PRESSED" if hw.owner_btn.is_active else "Released"
            weight = hw.get_weight_grams(samples=3)

            sys.stdout.write(
                f"\r[SENSORS] Ultra: {dist:5.1f}cm | IR: {ir_state:17s} | "
                f"Vibe: {vibe_state:14s} | Btn: {btn_state:8s} | Weight: {weight:6.1f}g  "
            )
            sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n[LIVE] Exited sensor monitor.")


# ==============================================================================
# 6. MAIN INTERACTIVE CLI
# ==============================================================================
def print_main_menu():
    print("\n" + "#"*60)
    print("  SMART LOCKER ALL-IN-ONE MANUAL TEST HARNESS (Pi 5)")
    print("  (Standard Keyboard Input Mode)")
    print("#"*60)
    print("  [1] Actuate Locker 1 Solenoid (Courier / Relay 3 - GPIO 10)")
    print("  [2] Actuate Locker 2 Solenoid (Owner / Relay 2 - GPIO 9)")
    print("  [3] Actuate Locker 3 Solenoid (Marketplace / Relay 1 - GPIO 6)")
    print("  [4] Actuate Aux Latch Solenoid (Locker 0 / Relay 4 - GPIO 19)")
    print("  [5] Test Dual Trapdoor Servos (Open -> Hold -> Close)")
    print("  [6] Stream Live Sensors (Ultra, IR Door, Vibe, Weight)")
    print("  ------------------------------------------------------------")
    print("  [7] RUN COURIER DROP-OFF FLOW (Resi -> L1 -> Ultra -> IR -> Servos)")
    print("  [8] RUN BUYER PICKUP FLOW (6-digit OTP -> L3 Unlock)")
    print("  [9] RUN OWNER ACCESS FLOW (Face MAS Authn + Locker 2 Solenoid)")
    print("  [T] Run Quick Self-Diagnostic of All Relays & Buzzer")
    print("  [0] Exit")
    print("#"*60)

def main():
    hw = HardwareController()
    print("[READY] All hardware devices initialized cleanly.")
    try:
        while True:
            print_main_menu()
            choice = input("Enter selection [0-9, T]: ").strip().upper()

            if choice == '1':
                hw.trigger_relay(3, 2.0)
            elif choice == '2':
                hw.trigger_relay(2, 2.0)
            elif choice == '3':
                hw.trigger_relay(1, 2.0)
            elif choice == '4':
                hw.trigger_relay(4, 2.0)
            elif choice == '5':
                hw.run_trapdoor_servos()
            elif choice == '6':
                monitor_sensors_live(hw)
            elif choice == '7':
                workflow_courier_dropoff(hw)
            elif choice == '8':
                workflow_buyer_pickup(hw)
            elif choice == '9':
                workflow_owner_unlock(hw)
            elif choice == 'T':
                print("[TEST] Running sequential relay test...")
                for i in (3, 2, 1, 4):
                    hw.trigger_relay(i, 1.0)
                    time.sleep(0.5)
                hw.beep_success()
                print("[TEST] Hardware diagnostic complete.")
            elif choice == '0':
                print("[EXIT] Shutting down...")
                break
            else:
                print("[-] Unknown option. Try again.")
    finally:
        hw.close()
        if lcd:
            try:
                lcd.clear()
                lcd.write_string("System Standby")
            except: pass
        print("[CLEANUP] All GPIO pins closed and returned safely.")

if __name__ == '__main__':
    main()
