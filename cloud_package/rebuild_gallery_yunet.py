import os
import glob
import cv2
import torch
import numpy as np
from facenet_pytorch import InceptionResnetV1

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("Using compute device:", device)
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

yunet_path = "/home/penlok/app/face_detection_yunet_2023mar.onnx"
detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320), 0.5, 0.3, 500)

gallery_dir = "/home/penlok/app/gallery/imagetraining"
users = sorted([d for d in os.listdir(gallery_dir) if os.path.isdir(os.path.join(gallery_dir, d))])

embeddings = {}

for u in users:
    imgs = sorted(glob.glob(os.path.join(gallery_dir, u, "*.*")))
    user_embs = []
    print(f"Processing user: {u} ({len(imgs)} images)...")
    for p in imgs:
        img = cv2.imread(p)
        if img is None:
            continue
        h, w, _ = img.shape
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)

        face_crop = None
        if faces is not None and len(faces) > 0:
            box = faces[0][:4].astype(int)
            x, y, bw, bh = box
            pad_x = int(bw * 0.1)
            pad_y = int(bh * 0.1)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w, x + bw + pad_x)
            y2 = min(h, y + bh + pad_y)
            face_crop = img[y1:y2, x1:x2]
        else:
            face_crop = img

        if face_crop is None or face_crop.size == 0:
            continue

        rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (160, 160))
        t = torch.from_numpy(resized).permute(2, 0, 1).float()
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
        print(f"  [+] User {u}: Computed mean embedding from {len(user_embs)} detected faces")

torch.save(embeddings, "/home/penlok/app/gallery_embeddings.pt")
print("Re-generated YuNet-cropped gallery_embeddings.pt successfully!")
