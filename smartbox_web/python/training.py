import numpy as np
from sklearn.svm import SVC
import pickle

# Load embeddings
data = np.load("embeddings.npz", allow_pickle=True)
embeddings = data["embeddings"]
labels = data["labels"]
label_map = data["label_map"].item()

print("[INFO] Jumlah embeddings:", len(embeddings))
print("[INFO] Label map:", label_map)

# Model classifier SVM
print("[INFO] Melatih SVM classifier...")
model = SVC(kernel='linear', probability=True)
model.fit(embeddings, labels)

# Simpan model dan label map
with open("face_classifier.pkl", "wb") as f:
    pickle.dump((model, label_map), f)

print("\n[DONE] Training selesai!")
print("Model disimpan → face_classifier.pkl")
print("Label map disimpan dalam file embeddings.npz")
