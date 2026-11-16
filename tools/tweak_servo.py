#!/usr/bin/env python3
"""
PENLOK Servo Calibration & Position Tweaking Utility
Allows precise adjustment of dual trapdoor servos (BCM 12 & BCM 13).
Records and updates baseline closed/open positions in servo_config.json.
"""

import sys
import os
import json
import time
import subprocess
from gpiozero import Servo, Device
from gpiozero.pins.lgpio import LGPIOFactory

# Initialize native LGPIOFactory on Pi 5 RP1 southbridge (chip 15)
for cand in (15, 4, 0):
    try:
        Device.pin_factory = LGPIOFactory(chip=cand)
        break
    except Exception:
        pass

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servo_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "servo_left_pin": 13,
        "servo_right_pin": 12,
        "closed_position": {
            "description": "Posisi tertutup (Baseline tercatat)",
            "servo_left_value": 1.0,
            "servo_right_value": -1.0,
            "duration_sec": 0.5
        },
        "open_position": {
            "description": "Posisi terbuka",
            "servo_left_value": -1.0,
            "servo_right_value": 1.0,
            "duration_sec": 0.45
        }
    }

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"[CONFIG] Konfigurasi posisi tersimpan ke {CONFIG_PATH}")
    except Exception as e:
        print(f"[-] Gagal menyimpan konfigurasi: {e}")

def pause_daemon():
    try:
        subprocess.run("docker stop edge-hardware-daemon >/dev/null 2>&1", shell=True)
    except Exception:
        pass

def resume_daemon():
    try:
        subprocess.run("docker start edge-hardware-daemon >/dev/null 2>&1", shell=True)
        print("[DAEMON] edge-hardware-daemon diaktifkan kembali.")
    except Exception:
        pass

def move_servos(val_left, val_right, duration=0.45):
    """Move both servos and safely detach PWM to prevent jitter/burnout"""
    s_left = None
    s_right = None
    try:
        s_left = Servo(13)
        s_right = Servo(12)
        print(f"[SERVO] Menggerakkan: Left(GPIO 13)={val_left}, Right(GPIO 12)={val_right} selama {duration}s...")
        s_left.value = val_left
        s_right.value = val_right
        time.sleep(duration)
    finally:
        if s_left:
            s_left.detach()
            s_left.close()
        if s_right:
            s_right.detach()
            s_right.close()
        print("[SERVO] Detach selesai. Sinyal PWM dimatikan aman.")

def move_single_servo(pin, val, duration=0.45):
    """Move a single servo on specified pin"""
    s = None
    try:
        s = Servo(pin)
        print(f"[SERVO] Menggerakkan Pin BCM {pin} ke nilai {val} selama {duration}s...")
        s.value = val
        time.sleep(duration)
    finally:
        if s:
            s.detach()
            s.close()
        print(f"[SERVO] Pin {pin} detach selesai.")

def main():
    pause_daemon()
    cfg = load_config()

    print("="*60)
    print("  PENLOK DUAL SERVO CALIBRATION & TWEAKING UTILITY")
    print("="*60)
    print("PIN: Servo Kiri = BCM 13 | Servo Kanan = BCM 12")
    print(f"\n[CATATAN POSISI TERTUTUP SAAT INI (BASELINE)]:")
    print(f"  • Servo Kiri  (BCM 13): {cfg['closed_position']['servo_left_value']}")
    print(f"  • Servo Kanan (BCM 12): {cfg['closed_position']['servo_right_value']}")
    print(f"  • Durasi Sinyal       : {cfg['closed_position']['duration_sec']} detik")

    try:
        while True:
            print("\n" + "-"*50)
            print("PILIHAN MENU KALIBRASI:")
            print("  [1] Terapkan Posisi TERTUTUP (Kiri=1.0, Kanan=-1.0)")
            print("  [2] Uji Posisi TERBUKA Saat Ini (Kiri=-1.0, Kanan=1.0)")
            print("  [3] Set Nilai Manual Kiri & Kanan (-1.0 s/d 1.0)")
            print("  [4] Uji Servo Kiri Saja (BCM 13)")
            print("  [5] Uji Servo Kanan Saja (BCM 12)")
            print("  [6] Uji Siklus Penuh: Buka -> Jeda -> Tutup")
            print("  [S] Simpan Pengaturan Posisi Terbuka Baru")
            print("  [0] Keluar")
            print("-"*50)

            choice = input("Pilih menu [1-6, S, 0]: ").strip().upper()

            if choice == '1':
                c = cfg["closed_position"]
                move_servos(c["servo_left_value"], c["servo_right_value"], c["duration_sec"])

            elif choice == '2':
                o = cfg["open_position"]
                move_servos(o["servo_left_value"], o["servo_right_value"], o["duration_sec"])

            elif choice == '3':
                try:
                    vl = float(input("Masukkan nilai Servo Kiri  BCM 13 (-1.0 s/d 1.0): "))
                    vr = float(input("Masukkan nilai Servo Kanan BCM 12 (-1.0 s/d 1.0): "))
                    dur = float(input("Masukkan durasi pergerakan detik (misal: 0.45): ") or 0.45)
                    move_servos(vl, vr, dur)
                except ValueError:
                    print("[-] Input harus berupa angka float!")

            elif choice == '4':
                try:
                    vl = float(input("Masukkan nilai Servo Kiri BCM 13 (-1.0 s/d 1.0): "))
                    dur = float(input("Masukkan durasi detik (default 0.45): ") or 0.45)
                    move_single_servo(13, vl, dur)
                except ValueError:
                    print("[-] Input tidak valid!")

            elif choice == '5':
                try:
                    vr = float(input("Masukkan nilai Servo Kanan BCM 12 (-1.0 s/d 1.0): "))
                    dur = float(input("Masukkan durasi detik (default 0.45): ") or 0.45)
                    move_single_servo(12, vr, dur)
                except ValueError:
                    print("[-] Input tidak valid!")

            elif choice == '6':
                o = cfg["open_position"]
                c = cfg["closed_position"]
                print("\n[SIKLUS] 1. Membuka trapdoor...")
                move_servos(o["servo_left_value"], o["servo_right_value"], o["duration_sec"])
                print("[SIKLUS] 2. Menahan posisi terbuka selama 2.0 detik...")
                time.sleep(2.0)
                print("[SIKLUS] 3. Menutup kembali trapdoor...")
                move_servos(c["servo_left_value"], c["servo_right_value"], c["duration_sec"])
                print("[SIKLUS] Siklus selesai.")

            elif choice == 'S':
                try:
                    print("\nSimpan Nilai Posisi TERBUKA Baru:")
                    new_l = float(input("Nilai Servo Kiri  BCM 13 (misal: -0.8): "))
                    new_r = float(input("Nilai Servo Kanan BCM 12 (misal: 0.8): "))
                    new_dur = float(input("Durasi detik (misal: 0.45): ") or 0.45)

                    cfg["open_position"]["servo_left_value"] = new_l
                    cfg["open_position"]["servo_right_value"] = new_r
                    cfg["open_position"]["duration_sec"] = new_dur
                    save_config(cfg)
                except ValueError:
                    print("[-] Input tidak valid!")

            elif choice == '0':
                break
            else:
                print("[-] Pilihan tidak valid.")

    finally:
        resume_daemon()

if __name__ == '__main__':
    main()
