#!/usr/bin/env python3
"""
PENLOK Camera Diagnostic & Live Preview Tool
1. Test Snapshot: captures frame, runs YuNet + FaceNet, reports status.
2. Live Web Stream: runs local HTTP stream at http://0.0.0.0:8088 so you can see live camera in browser.
"""

import sys
import os
import time
import argparse
import cv2
import numpy as np

# Ensure penlock imports
sys.path.insert(0, "/home/pi/penlock")

YUNET_MODEL = "/home/pi/penlock/face_detection_yunet_2023mar.onnx"
OUTPUT_SNAP = "/home/pi/penlock/test_camera.jpg"

def take_snapshot():
    print("\n[KAMERA] Membuka kamera /dev/video0...")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[-] GAGAL: /dev/video0 tidak dapat dibuka.")
        print("    Pastikan kabel USB kamera Logitech C270 tercolok kencang.")
        return False

    print("[+] Kamera berhasil terbuka. Menstabilkan sensor cahaya (5 frame)...")
    for _ in range(5):
        cap.read()
        time.sleep(0.05)

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[-] GAGAL: Tidak dapat membaca frame dari kamera.")
        return False

    h, w, _ = frame.shape
    print(f"[+] Frame terbaca: {w}x{h} piksel.")

    # Detect face using YuNet ONNX
    num_faces = 0
    if os.path.exists(YUNET_MODEL):
        detector = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (w, h), 0.5, 0.3, 500)
        _, faces = detector.detect(frame)
        if faces is not None and len(faces) > 0:
            num_faces = len(faces)
            for f in faces:
                b = f[:4].astype(int)
                conf = f[-1]
                cv2.rectangle(frame, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), (0, 255, 0), 2)
                cv2.putText(frame, f"Face: {conf:.2f}", (b[0], max(20, b[1] - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imwrite(OUTPUT_SNAP, frame)
    print(f"[+] Foto disimpan ke: {OUTPUT_SNAP}")
    print(f"[+] Jumlah wajah terdeteksi: {num_faces}")

    # Test verification against Cloud GPU
    try:
        from migration_agent import dispatch_migration
        _, buf = cv2.imencode(".jpg", frame)
        print("\n[AI] Menguji pencocokan ke Cloud GPU (RTX 3050 CUDA)...")
        cloud_url = os.getenv("CLOUD_GPU_URL", "http://100.76.68.93:9000/api/v1/migration")
        res = dispatch_migration("CHECK_CAM", "SB01", buf.tobytes(), decision=1, cloud_url=cloud_url)
        print(f"     Hasil Cloud GPU : User = {res.get('user_id')}")
        print(f"     Status          : {'TERVERIFIKASI (Cocok)' if res.get('authorized') else 'DITOLAK (Bukan Pemilik / Wajah Belum Jelas)'}")
        print(f"     Skor Kemiripan  : {res.get('confidence')} (Ambang batas: >= 0.60)")
    except Exception as e:
        print(f"[-] Cloud test notice: {e}")

    return True


def run_live_web_stream(port=8088):
    """Serve live MJPEG video stream over HTTP so user can view in browser"""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    print("\n" + "="*60)
    print(f"  PENLOK LIVE CAMERA STREAMER (PORT {port})")
    print("="*60)
    print(f"Buka di browser: http://100.66.41.38:{port}/ (atau via LAN lemari)")
    print("Tekan Ctrl+C di terminal ini untuk berhenti.\n")

    class CamHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                html = f"""<html>
<head><title>Penlok Live Camera Stream</title></head>
<body style="background:#121212; color:#00E5FF; font-family:monospace; text-align:center; padding:20px;">
  <h2>PENLOK SMART LOCKER // LIVE WEBCAM PREVIEW</h2>
  <div style="margin:20px auto; max-width:640px; border:2px solid #00E5FF;">
    <img src="/mjpeg" style="width:100%; display:block;" />
  </div>
  <p style="color:#98989D;">Resolusi: 640x480 | Port: {port} | Format: MJPEG Stream</p>
</body></html>"""
                self.wfile.write(html.encode('utf-8'))

            elif self.path == '/mjpeg':
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()

                cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)

                try:
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        self.wfile.write(b"--frame\r\n")
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(jpeg)))
                        self.end_headers()
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b"\r\n")
                        time.sleep(0.04)
                except Exception:
                    pass
                finally:
                    cap.release()

    server = HTTPServer(('0.0.0.0', port), CamHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STREAM] Streaming dihentikan.")
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PENLOK Camera Check")
    parser.add_argument("--stream", action="store_true", help="Jalankan web streaming live di port 8088")
    parser.add_argument("--port", type=int, default=8088, help="Port untuk web stream (default: 8088)")
    args = parser.parse_args()

    if args.stream:
        run_live_web_stream(port=args.port)
    else:
        take_snapshot()
