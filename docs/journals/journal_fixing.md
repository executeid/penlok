# Comprehensive System & GPIO Fixing Journal

**Date**: 26 September 2026  
**Target Host**: `pi@10.1.1.224:2523`  
**Jump Host**: `tcc@100.76.68.93`  
**Routing**: `ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224`  
**Remote Working Directory**: `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan`  
**Hardware / OS**: Raspberry Pi 5 Model B Rev 1.1 (Linux 6.12.109+rpt-rpi-2712 aarch64)  
**Primary Python Environment**: Pyenv `penlok` (Python 3.9.20)  

---

## 1. Network Topology & Access Architecture

All administrative and runtime actions targeting the Smart Locker hardware controller (`10.1.1.224:2523`) must route through the intermediate jump host `tcc@100.76.68.93`.

```
[Local / Agent Harness]
         │
         ▼ (SSH Port 22)
[Jump Host: tcc@100.76.68.93]
         │
         ▼ (SSH ProxyJump Port 2523)
[Smart Locker Pi 5: pi@10.1.1.224]
```

### SSH Connection Syntax
```bash
ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224
```

---

## 2. Root Cause Analysis & Problem Breakdown

### Issue A: `lgpio.error: 'can not open gpiochip'`
- **Symptom**: Legacy hardware scripts (`pan-piXarduino.py`, `kalibrasi/tarescalefactor.py`, `calibrate_auto.py`, `buzzer1.py`, etc.) crashed upon startup:
  ```text
  File ".../lgpio.py", line 645, in gpiochip_open
      return _u2i(handle)
  lgpio.error: 'can not open gpiochip'
  ```
- **Root Cause**:
  1. Raspberry Pi 5 uses the RP1 southbridge chip (`pinctrl-rp1`) to control the 40-pin GPIO header.
  2. Under Linux kernel 6.12+, RP1 is allocated as `/dev/gpiochip15`. Character devices `/dev/gpiochip0` and `/dev/gpiochip4` do not exist.
  3. Legacy scripts explicitly invoke `lgpio.gpiochip_open(0)`.
  4. C library `_lgpio._gpiochip_open(0)` returns error code `-78`, which raises `lgpio.error`.

### Issue B: `lgpio.error: 'GPIO busy'` / `KeyError: PinInfo(number=31, name='GPIO6'...)`
- **Symptom**: Running `pan-piXarduino-fixed.py` or `cobaface.py` failed during relay initialization:
  ```text
  KeyError: PinInfo(number=31, name='GPIO6'...)
  lgpio.error: 'GPIO busy'
  ```
- **Root Cause**:
  1. Orphaned background Python processes (PIDs `162098`, `213992`) were left running from aborted shell sessions.
  2. These processes retained open file descriptors on `/dev/gpiochip15` and held exclusive kernel line claims on GPIO pins (Relay 1: GPIO 6, Relay 2: GPIO 9, Relay 3: GPIO 10, Relay 4: GPIO 19, Loadcell: 4/14, HC-SR04: 15/17, Keypad matrix, etc.).
  3. Subsequent runs attempting to claim input/output on the same lines were rejected by the kernel.

### Issue C: `ModuleNotFoundError: No module named 'RPLCD'` in Non-Interactive Shells
- **Symptom**: Running commands via SSH without interactive login (e.g. `ssh ... "python3 script.py"`) failed immediately:
  ```text
  ModuleNotFoundError: No module named 'RPLCD'
  ```
- **Root Cause**:
  1. `/home/pi/.bashrc` contained an early return for non-interactive shells:
     ```bash
     case $- in
         *i*) ;;
           *) return;;
     esac
     ```
  2. Pyenv exports (`PATH="$HOME/.pyenv/bin:$PATH"` and `eval "$(pyenv init -)"`) were located at lines 115–117, *after* the non-interactive check.
  3. `/home/pi/.profile` lacked Pyenv initialization.
  4. As a result, non-interactive SSH sessions resolved `python3` to system Python 3.11 (`/usr/bin/python3`), which lacks the application libraries (`RPLCD`, `gpiozero`, `opencv`, `ultralytics`, `psycopg2-binary`).

### Issue D: Hanging / Unbounded CPU Consumption on `loadcellfinal.py` Import
- **Symptom**: Scripts importing `loadcellfinal.py` hung indefinitely, consuming 18% CPU.
- **Root Cause**: `loadcellfinal.py` executed an infinite `while True:` calibration loop at the top level without an `if __name__ == '__main__':` boundary.

### Issue E: Subprocess Interpreter Desynchronization & Missing GUI Display
- **Symptom**: `cobaface.py` and `pan-piXarduino.py` called `subprocess.run(["python3", ...])`, bypassing the active virtual environment. `camowner.py` and `camtimer.py` crashed with `_tkinter.TclError: no display name` when executed without an active `$DISPLAY`.

---

## 3. Systematic Fixes & Code Modifications

### 3.1 Global `lgpio` Dynamic Chip Detection Patch
Patched `gpiochip_open()` across all Python environments on the host:
- `/home/pi/.pyenv/versions/3.9.20/envs/penlok/lib/python3.9/site-packages/lgpio.py`
- `/usr/lib/python3/dist-packages/lgpio.py`
- `/home/pi/penlock/penlock/lib/python3.11/site-packages/lgpio.py`

**Implementation Diff**:
```python
def gpiochip_open(gpiochip):
   """
   This returns a handle to a gpiochip device.
   """
   handle = u2i(_lgpio._gpiochip_open(gpiochip))
   if handle < 0:
      for _alt in (15, 4, 0):
         if _alt == gpiochip:
            continue
         _alt_h = u2i(_lgpio._gpiochip_open(_alt))
         if _alt_h >= 0:
            gpiochip = _alt
            handle = _alt_h
            break
   if handle >= 0:
      handle = handle | (gpiochip << 16)
   return _u2i(handle)
```
*Result*: Any script calling `lgpio.gpiochip_open(0)` automatically probes and binds to `/dev/gpiochip15` on Raspberry Pi 5 without code modifications.

---

### 3.2 Shell Environment & Pyenv PATH Restructuring
Moved Pyenv initializations to the very top of `/home/pi/.bashrc` (prior to `case $- in`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
fi
```

*Result*: Both interactive and non-interactive SSH commands (`ssh -J ... "python3 ..."`) automatically use Pyenv `penlok` (Python 3.9.20) as defined by `/home/pi/penlock/.python-version`.

---

### 3.3 Elimination of Orphaned Background Processes
Executed process audit and termination:
```bash
kill -9 162098 213992
```
Verified GPIO line liberation via kernel interface:
```bash
sudo lsof /dev/gpiochip*
sudo gpioinfo 15
```
*Result*: All lines on `gpiochip15` returned to clean, unreserved status.

---

### 3.4 `loadcellfinal.py` Safe Import Guard
Added entry point protection to:
- `/home/pi/penlock/pyenv3.9code/nonsudo/gabungan/loadcellfinal.py`
- `/home/pi/penlock/pyenv3.9code/nonsudo/loadcellfinal.py`

```python
if __name__ == '__main__':
    try:
        print("Timbangan siap...\nTekan Ctrl+C untuk berhenti.\n")
        while True:
            raw = get_average()
            berat = (raw - OFFSET) / SCALE
            print(f"Berat: {berat:.2f} gram")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Dihentikan oleh pengguna.")
    finally:
        lgpio.gpiochip_close(h)
```

---

### 3.5 Subprocess Invocation & Tkinter Headless Safeguards
1. **Interpreter Binding**: Replaced `"python3"` subprocess invocations in `cobaface.py` and `pan-piXarduino.py` with `[sys.executable, os.path.join(base_dir, ...)]` and `cwd=base_dir`.
2. **Display Fallback**: Added display defaults to `camowner.py` and `camtimer.py`:
   ```python
   import os
   os.environ.setdefault("DISPLAY", ":0")
   ```

---

## 4. Verification & Operational Testing

All tests executed via jump host: `ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224`

| Test Target | Command Executed | Result | Status |
|---|---|---|---|
| Master Orchestrator | `python3 pan-piXarduino-fixed.py` | LCD, Arduino, Loadcell, MQTT broker connected cleanly. No GPIO errors. | PASS |
| Face Recognition Master | `python3 cobaface.py` | MQTT, Relays, Loadcell, Arduino serial initialized cleanly. | PASS |
| Legacy Master Script | `python3 pan-piXarduino.py` | Arduino connected, GPIO fallback to chip 15 verified. | PASS |
| Loadcell Calibration | `python3 tarescalefactor.py` | Opened chip 0 -> redirected to chip 15 without crash. | PASS |
| Subprocess Execution | `servo2.py` via `ir_single_read.py` | Dual servos (GPIO 12/13) actuated and detached cleanly. | PASS |
| GPIO Release Check | `sudo lsof /dev/gpiochip*` | No orphaned handles or leaked lines. | PASS |

---

## 5. Standard Operational Runbook

### To Start the Main Smart Locker Program
```bash
ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224
cd /home/pi/penlock/pyenv3.9code/nonsudo/gabungan
python3 pan-piXarduino-fixed.py
```

### To Check for Conflicting Hardware Processes
```bash
ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224 "ps aux | grep -E 'python.*(pan|coba|infra|loadcell)'"
```

### To Force Release All GPIO Lines
```bash
ssh -J tcc@100.76.68.93 -p 2523 pi@10.1.1.224 "sudo pkill -f 'python.*(pan|coba|infra|loadcell)'; sudo lsof /dev/gpiochip*"
```
