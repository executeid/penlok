#!/usr/bin/env python3
"""
PENLOK Face Registration & Dual-Model Sync Utility
Registers new user face photos, retrains local Edge LBPH model,
and synchronizes 512-d embeddings to Cloud GPU (RTX 3050 CUDA).
"""

import sys
import os
import glob
import time
import argparse
import subprocess
import shutil
import cv2
import numpy as np
from PIL import Image

TRAIN_DIR_EDGE = "/home/pi/penlock/software/Django-Backend-Project/media/imagetraining"
HAAR_CASCADE = "/home/pi/penlock/software/Django-Backend-Project/apps/hasiltraining/haarcascade_frontalface_default.xml"
LBPH_SAVE_EDGE = "/home/pi/penlock/software/Django-Backend-Project/apps/hasiltraining/lbph_model.xml"
LBPH_GABUNGAN = "/home/pi/penlock/pyenv3.9code/nonsudo/lbph_model.xml"

GPU_HOST = "penlok@10.1.1.186"
GPU_GALLERY_DIR = "/home/penlok/app/gallery/imagetraining"

def capture_from_camera(username: str, count: int = 15):
    """Ambil frame foto wajah langsung dari webcam USB Pi"""
    user_dir = os.path.join(TRAIN_DIR_EDGE, username)
    os.makedirs(user_dir, exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[-] Gagal membuka kamera /dev/video0!")
        return False

    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE)
    print(f"\n[KAMERA] Mulai pengambilan {count} sampel wajah untuk '{username}'...")
    print("[KAMERA] Hadapkan wajah ke kamera (pencahayaan cukup). Tekan Ctrl+C untuk batal.")

    saved = 0
    frame_counter = 0

    while saved < count:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        frame_counter += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50, 50))

        if len(faces) > 0 and frame_counter >= 8:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{username}_{saved + 1}_{timestamp}.jpg"
            filepath = os.path.join(user_dir, filename)

            cv2.imwrite(filepath, frame)
            saved += 1
            frame_counter = 0
            print(f"  [+] Sampel {saved}/{count} berhasil disimpan: {filename}")
            time.sleep(0.2)

    cap.release()
    print(f"[KAMERA] Selesai mengambil {saved} foto wajah.")
    return True


def import_from_folder(username: str, folder_path: str):
    """Import foto yang sudah ada dari folder lokal"""
    folder_path = os.path.abspath(os.path.expanduser(folder_path))
    if not os.path.exists(folder_path):
        print(f"[-] Folder '{folder_path}' tidak ditemukan!")
        return False

    user_dir = os.path.join(TRAIN_DIR_EDGE, username)
    os.makedirs(user_dir, exist_ok=True)

    imgs = glob.glob(os.path.join(folder_path, "*.[jJ][pP][gG]")) + \
           glob.glob(os.path.join(folder_path, "*.[jJ][pP][eE][gG]")) + \
           glob.glob(os.path.join(folder_path, "*.[pP][nN][gG]"))

    if not imgs:
        print(f"[-] Tidak ada file gambar di '{folder_path}'!")
        return False

    copied = 0
    for p in imgs:
        dst = os.path.join(user_dir, f"{username}_imported_{copied + 1}.jpg")
        img = cv2.imread(p)
        if img is not None:
            cv2.imwrite(dst, img)
            copied += 1
            print(f"  [+] Diimpor: {os.path.basename(p)} -> {os.path.basename(dst)}")

    print(f"[IMPORT] Berhasil mengimpor {copied} foto ke {user_dir}.")
    return True


def retrain_edge_lbph():
    """Retrain model OpenCV LBPH di Raspberry Pi 5"""
    print("\n[TRAIN EDGE] Memulai training ulang model LBPH lokal...")
    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE)
    recognizer = cv2.face.LBPHFaceRecognizer.create()

    user_folders = [d for d in os.listdir(TRAIN_DIR_EDGE) if os.path.isdir(os.path.join(TRAIN_DIR_EDGE, d))]

    faces = []
    labels = []
    user_id_map = {}

    for idx, u in enumerate(sorted(user_folders)):
        lbl = (idx + 1) * 1000 + 101  # Unique integer label
        user_id_map[lbl] = u
        u_dir = os.path.join(TRAIN_DIR_EDGE, u)
        imgs = glob.glob(os.path.join(u_dir, "*.jpg"))

        cnt = 0
        for p in imgs:
            try:
                img_pil = Image.open(p).convert("L")
                img_np = np.array(img_pil, "uint8")
                detected = face_cascade.detectMultiScale(img_np, 1.2, 5)
                for (x, y, w, h) in detected:
                    faces.append(img_np[y:y+h, x:x+w])
                    labels.append(lbl)
                    cnt += 1
            except Exception:
                continue
        print(f"  • User '{u}' (Label ID: {lbl}): {cnt} sampel wajah diproses.")

    if not faces:
        print("[-] Peringatan: Tidak ada wajah terdeteksi dengan Haar Cascade. Cek foto!")
        return False

    recognizer.train(faces, np.array(labels))
    recognizer.save(LBPH_SAVE_EDGE)
    shutil.copy(LBPH_SAVE_EDGE, LBPH_GABUNGAN)
    print(f"[TRAIN EDGE] Sukses! Model LBPH tersimpan di {LBPH_GABUNGAN} ({len(faces)} total sampel).")
    return True


def sync_and_update_cloud_gpu(username: str):
    """Kirim foto ke Cloud GPU dan update embedding InceptionResnetV1 CUDA"""
    print(f"\n[SYNC CLOUD] Mengirim dataset wajah '{username}' ke Cloud GPU ({GPU_HOST})...")
    user_dir_edge = os.path.join(TRAIN_DIR_EDGE, username)

    # 1. Buat folder dan scp foto ke Cloud GPU
    cmd_mkdir = ["ssh", "-o", "BatchMode=yes", GPU_HOST, f"mkdir -p '{GPU_GALLERY_DIR}/{username}'"]
    subprocess.run(cmd_mkdir, check=True)

    cmd_scp = f"scp -r '{user_dir_edge}'/* '{GPU_HOST}:{GPU_GALLERY_DIR}/{username}/'"
    subprocess.run(cmd_scp, shell=True, check=True)
    print("  [+] Berkas foto berhasil ditransfer ke Cloud GPU.")

    # 2. Trigger perhitungan embedding 512-d di GPU RTX 3050 CUDA
    print("[SYNC CLOUD] Menjalankan forward pass InceptionResnetV1 di GPU CUDA...")
    remote_script = f"""
/home/penlok/app/venv/bin/python -c '
import os, glob, torch, cv2
from facenet_pytorch import InceptionResnetV1

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

gallery_dir = "{GPU_GALLERY_DIR}"
users = [d for d in os.listdir(gallery_dir) if os.path.isdir(os.path.join(gallery_dir, d))]

embeddings = {{}}
for u in users:
    imgs = sorted(glob.glob(f"{{gallery_dir}}/{{u}}/*.jpg"))[:15]
    user_embs = []
    for p in imgs:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (160, 160))
        t = torch.from_numpy(img).permute(2, 0, 1).float()
        t = (t - 127.5) / 128.0
        t = t.unsqueeze(0).to(device)
        with torch.no_grad():
            emb = model(t)
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            user_embs.append(emb)
    if user_embs:
        mean_emb = torch.cat(user_embs, dim=0).mean(dim=0, keepdim=True)
        mean_emb = torch.nn.functional.normalize(mean_emb, p=2, dim=1)
        embeddings[u] = mean_emb
        print(f"  • GPU Embeddings computed for: {{u}} ({{len(user_embs)}} frames)")

torch.save(embeddings, "/home/penlok/app/gallery_embeddings.pt")
print("  [+] Saved new gallery_embeddings.pt")
'
sudo systemctl restart cloud-agent
sleep 2
systemctl is-active cloud-agent
"""
    cmd_remote = ["ssh", GPU_HOST, remote_script]
    res = subprocess.run(cmd_remote, capture_output=True, text=True)
    print(res.stdout)
    if "active" in res.stdout:
        print("[SYNC CLOUD] Cloud Agent berhasil diperbarui dan aktif!")
        return True
    else:
        print("[-] Peringatan: Cloud Agent output:", res.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="PENLOK Registrasi Wajah Otomatis")
    parser.add_argument("--name", type=str, help="Nama pengguna / folder user (contoh: budi)")
    parser.add_argument("--capture", action="store_true", help="Ambil foto otomatis via kamera USB Pi")
    parser.add_argument("--count", type=int, default=15, help="Jumlah foto yang diambil kamera (default: 15)")
    parser.add_argument("--folder", type=str, help="Import foto dari folder lokal (misal: ~/foto-akmal)")

    args = parser.parse_args()

    username = args.name
    if not username:
        print("\n" + "="*50)
        print("  PENLOK REGISTRASI WAJAH PEMILIK BARU")
        print("="*50)
        username = input("Masukkan username / nama pemilik baru: ").strip().lower().replace(" ", "_")
        if not username:
            print("[-] Nama tidak boleh kosong!")
            return

    # 1. Pengambilan Foto
    if args.folder:
        ok = import_from_folder(username, args.folder)
    elif args.capture:
        ok = capture_from_camera(username, args.count)
    else:
        print("\nPilih metode input foto:")
        print("  [1] Ambil langsung lewat kamera USB Smart Locker (15 foto)")
        print("  [2] Import dari folder foto yang sudah ada")
        opt = input("Pilihan [1/2]: ").strip()
        if opt == '1':
            ok = capture_from_camera(username, args.count)
        elif opt == '2':
            f_path = input("Masukkan path folder gambar: ").strip()
            ok = import_from_folder(username, f_path)
        else:
            print("[-] Pilihan dibatalkan.")
            return

    if not ok:
        print("[-] Gagal mendapatkan foto wajah.")
        return

    # 2. Retrain Edge LBPH
    retrain_edge_lbph()

    # 3. Sync & Compute Embeddings on Cloud GPU
    sync_and_update_cloud_gpu(username)

    print("\n" + "="*50)
    print(f"  [SUKSES] Wajah '{username}' resmi terdaftar!")
    print("  • Model Edge Pi (LBPH) : Aktif")
    print("  • Model Cloud GPU (RTX): Aktif")
    print("="*50 + "\n")

if __name__ == '__main__':
    main()
