import os
import json
import cv2
import numpy as np
import shutil
from insightface.app import FaceAnalysis

BASE_DIR = r"C:\laragon\www\smartbox_web"
DATASET_DIR = os.path.join(BASE_DIR, "public", "dataset")

OUTPUT_FILE = os.path.join(BASE_DIR, "embeddings.json")
PUBLIC_FILE = os.path.join(BASE_DIR, "public", "embeddings.json")

print("Loading model...")

app = FaceAnalysis(name="buffalo_sc", providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(320,320))

print("Model ready")

all_embeddings = {}

for person_name in os.listdir(DATASET_DIR):

    person_path = os.path.join(DATASET_DIR, person_name)

    if not os.path.isdir(person_path):
        continue

    emb_list = []

    for file in os.listdir(person_path):

        img_path = os.path.join(person_path, file)

        img = cv2.imread(img_path)

        if img is None:
            continue

        faces = app.get(img)

        if len(faces) > 0:
            emb = faces[0].embedding.tolist()
            emb_list.append(emb)

    if len(emb_list) > 0:
        all_embeddings[person_name] = emb_list
        print(f"{person_name} : {len(emb_list)} wajah")

with open(OUTPUT_FILE, "w") as f:
    json.dump(all_embeddings, f)

# copy ke public
shutil.copy(OUTPUT_FILE, PUBLIC_FILE)

print("embeddings.json berhasil dibuat")
print("embeddings.json berhasil disalin ke public")