#!/usr/bin/env python3
"""
PENLOK Solenoid & Relay Hardware Diagnostic Utility
Tests all 4 locker relays (Solenoid locks) individually or in sequence.
Automatically pauses edge-hardware-daemon during test to prevent GPIO busy locks.
"""

import sys
import os
import time
import subprocess
import lgpio

RELAY_MAP = {
    1: {"name": "Loker 1 (Pintu Masuk Kurir)", "pin": 10},
    2: {"name": "Loker 2 (Penyimpanan Aman Pemilik)", "pin": 9},
    3: {"name": "Loker 3 (Marketplace / Pengambilan)", "pin": 6},
    4: {"name": "Loker 4 (Aux Latch / Pintu Tambahan)", "pin": 19},
}

BUZZER_PIN = 21

def pause_daemon():
    try:
        subprocess.run("docker stop edge-hardware-daemon >/dev/null 2>&1", shell=True)
    except Exception:
        pass

def resume_daemon():
    try:
        print("\n[DAEMON] Mengaktifkan kembali edge-hardware-daemon...")
        subprocess.run("docker start edge-hardware-daemon >/dev/null 2>&1", shell=True)
        print("[DAEMON] Daemon aktif kembali di latar belakang.")
    except Exception:
        pass

def open_chip():
    for c in (15, 4, 0):
        try:
            return lgpio.gpiochip_open(c)
        except Exception:
            pass
    raise RuntimeError("Tidak dapat membuka gpiochip!")

def beep(h, duration=0.15):
    try:
        lgpio.gpio_claim_output(h, BUZZER_PIN, 0)
        lgpio.gpio_write(h, BUZZER_PIN, 1)
        time.sleep(duration)
        lgpio.gpio_write(h, BUZZER_PIN, 0)
    except Exception:
        pass

def trigger_relay(h, relay_id, duration=2.5, active_low=True):
    if relay_id not in RELAY_MAP:
        print(f"[-] ID Relai {relay_id} tidak valid!")
        return

    info = RELAY_MAP[relay_id]
    pin = info["pin"]
    name = info["name"]

    on_val = 0 if active_low else 1
    off_val = 1 if active_low else 0

    mode_str = "Active-LOW (0 = ON, 1 = OFF)" if active_low else "Active-HIGH (1 = ON, 0 = OFF)"
    print(f"\n[TEST] Menguji {name} pada Pin BCM {pin}...")
    print(f"       Mode: {mode_str} | Durasi: {duration}s")

    try:
        beep(h, 0.1)
        lgpio.gpio_claim_output(h, pin, off_val)
        time.sleep(0.1)

        print(f"  >>> RELAI ON (Nilai: {on_val}) - DENGARKAN SUARA KLIK / PERIKSA LAMPU LED MODUL RELAI <<<")
        lgpio.gpio_write(h, pin, on_val)
        time.sleep(duration)

        print(f"  <<< RELAI OFF (Nilai: {off_val}) - TERKUNCI KEMBALI RAPAT >>>")
        lgpio.gpio_write(h, pin, off_val)
        time.sleep(0.3)
    except Exception as e:
        print(f"[-] Gagal menguji relai {pin}: {e}")

def test_all_sequential(h, duration=2.0, active_low=True):
    print("\n" + "="*60)
    print("  MEMULAI UJI SEMUA RELAI BERGANTIAN (1 s/d 4)")
    print("="*60)
    for r_id in (1, 2, 3, 4):
        trigger_relay(h, r_id, duration=duration, active_low=active_low)
        time.sleep(1.0)
    beep(h, 0.3)
    print("\n[SELESAI] Uji semua relai selesai.")

def main():
    print("="*60)
    print("  PENLOK SMART LOCKER - PENGUJIAN FISIK RELAI & SOLENOID")
    print("="*60)

    # Pause daemon temporarily
    pause_daemon()
    time.sleep(0.5)

    h = open_chip()
    print(f"[CHIP] Terhubung ke GPIO Chip RP1 (Handle: {h})")

    active_low = True

    try:
        # Check command line args
        if len(sys.argv) > 1:
            arg = sys.argv[1].upper()
            if arg in ('A', '--ALL'):
                test_all_sequential(h, 2.0, active_low)
                return
            elif arg in ('1', '2', '3', '4'):
                trigger_relay(h, int(arg), 2.5, active_low)
                return

        while True:
            mode_desc = "Active-LOW (Standar Modul Relai)" if active_low else "Active-HIGH"
            print("\n" + "-"*50)
            print(f"Mode Pemicuan: [{mode_desc}]")
            print("  [1] Uji Solenoid Loker 1 (BCM 10) - Pintu Masuk Kurir")
            print("  [2] Uji Solenoid Loker 2 (BCM 9)  - Pintu Pemilik")
            print("  [3] Uji Solenoid Loker 3 (BCM 6)  - Pintu Marketplace")
            print("  [4] Uji Solenoid Loker 4 (BCM 19) - Pintu Aux / Tambahan")
            print("  [A] Uji SEMUA Solenoid Bergantian (1 -> 2 -> 3 -> 4)")
            print("  [M] Tukar Mode Pemicuan (Active-LOW / Active-HIGH)")
            print("  [0] Keluar & Nyalakan Kembali Daemon Otomatis")
            print("-"*50)

            choice = input("Pilih menu [1/2/3/4/A/M/0]: ").strip().upper()

            if choice == '1':
                trigger_relay(h, 1, 2.5, active_low)
            elif choice == '2':
                trigger_relay(h, 2, 2.5, active_low)
            elif choice == '3':
                trigger_relay(h, 3, 2.5, active_low)
            elif choice == '4':
                trigger_relay(h, 4, 2.5, active_low)
            elif choice == 'A':
                test_all_sequential(h, 2.0, active_low)
            elif choice == 'M':
                active_low = not active_low
                print(f"[MODE] Mode pemicuan diubah menjadi: {'Active-LOW' if active_low else 'Active-HIGH'}")
            elif choice == '0':
                break
            else:
                print("[-] Pilihan tidak valid.")
    finally:
        lgpio.gpiochip_close(h)
        print("[CLEANUP] GPIO handle ditutup.")
        resume_daemon()

if __name__ == '__main__':
    main()
