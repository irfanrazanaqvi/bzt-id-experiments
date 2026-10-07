"""
Real face-verification scores on the public LFW dataset (Labeled Faces in the Wild).

Embeds every image with an open-source pretrained face-recognition network (FaceNet
InceptionResnetV1, pretrained on VGGFace2) and writes cosine-similarity scores for
genuine (same identity) and impostor (different identity) image pairs. Identities are split
into disjoint CALIBRATION and TEST halves, so any score->probability map fitted on the
calibration half is evaluated on identities it has never seen.

usage: python lfw_scores.py out_dir
"""
import sys, os, json, time, random
import numpy as np
import torch
from sklearn.datasets import fetch_lfw_people
from facenet_pytorch import InceptionResnetV1

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
SEED = 2026
torch.set_num_threads(os.cpu_count() or 2)
t0 = time.time()
lfw = fetch_lfw_people(min_faces_per_person=2, resize=1.0, color=True, funneled=True)
X, y = lfw.images, lfw.target                       # (n,h,w,3) float32 already scaled to 0..1 by sklearn
assert 0.0 <= X.min() and X.max() <= 1.0 + 1e-6, (X.min(), X.max())
print("images", X.shape, "identities", len(set(y)), flush=True)

model = InceptionResnetV1(pretrained="vggface2").eval()
embs = []
with torch.no_grad():
    for i in range(0, len(X), 64):
        b = torch.from_numpy(X[i:i+64]).permute(0, 3, 1, 2)
        b = torch.nn.functional.interpolate(b, size=(160, 160), mode="bilinear", align_corners=False)
        b = (b - 0.5) / 0.5                          # facenet fixed standardisation
        e = model(b)
        embs.append(torch.nn.functional.normalize(e, dim=1).numpy())
        if (i // 64) % 20 == 0:
            print(f"{i}/{len(X)} {time.time()-t0:.0f}s", flush=True)
E = np.concatenate(embs)

rng = random.Random(SEED)
ids = sorted(set(y.tolist())); rng.shuffle(ids)
half = len(ids) // 2
split_of = {i: ("calibration" if k < half else "test") for k, i in enumerate(ids)}
rows = []
for split in ("calibration", "test"):
    idx = [j for j in range(len(y)) if split_of[int(y[j])] == split]
    by = {}
    for j in idx: by.setdefault(int(y[j]), []).append(j)
    same = [(a, b) for v in by.values() for k, a in enumerate(v) for b in v[k+1:]]
    rng.shuffle(same); same = same[:20000]
    diff = []
    while len(diff) < 20000:
        a, b = rng.sample(idx, 2)
        if y[a] != y[b]: diff.append((a, b))
    for lab, pairs in ((1, same), (0, diff)):
        for a, b in pairs:
            rows.append((split, lab, float(E[a] @ E[b])))
from sklearn.metrics import roc_auc_score
for sp in ("calibration", "test"):
    r = [x for x in rows if x[0] == sp]
    a = roc_auc_score([x[1] for x in r], [x[2] for x in r]); print("sanity AUC", sp, a, flush=True)
    assert a > 0.9, "embeddings look broken"
with open(os.path.join(out, "lfw_pair_scores.csv"), "w") as f:
    f.write("split,genuine,cosine\n")
    for r in rows: f.write(f"{r[0]},{r[1]},{r[2]:.6f}\n")
meta = {"dataset": "LFW (sklearn fetch_lfw_people, min_faces_per_person=2, funneled)",
        "model": "facenet-pytorch InceptionResnetV1 pretrained=vggface2", "images": int(len(X)),
        "identities": len(ids), "pairs": len(rows), "seed": SEED, "seconds": round(time.time()-t0),
        "torch": torch.__version__}
json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
print(meta)
