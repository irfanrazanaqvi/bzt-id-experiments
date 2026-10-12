"""Keystroke-dynamics authentication on the raw keyboard logs of SU-AIS BB-MAS (IEEE DataPort, DOI 10.21227/rpaz-0h66).
Per user and device: key hold times and digraph (down-to-down) latencies from raw down/up events (direction 0 = down, 1 = up).
Template = median and median-absolute-deviation of each key hold and each digraph from the FIRST HALF of the user's events (chronological);
test windows = consecutive blocks of W keystrokes from the SECOND HALF. Score = -mean(|z|) over the template features present in the window
(scaled Manhattan distance, |z| clipped at 10). Genuine = the user's own windows; impostor = windows of other users of the SAME split scored against this template.
Users are split at random into disjoint calibration/test halves. Output: pair-score CSV in the format of the LFW pair scores.
usage: keystroke_eval.py <zip> <device: Desktop|Tablet|Phone> <out.csv>"""
import sys, zipfile, re, io, random, collections
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
Z, DEV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, MINF, MAXZ = 60, 10, 10.0
rng = random.Random(11)
z = zipfile.ZipFile(Z)
pat = {"Desktop": r"BB-MAS_Dataset/(\d+)/\1_Desktop_Keyboard\.csv$", "Tablet": r"BB-MAS_Dataset/(\d+)/\1_HandTablet_Keyboard_\(Nexus\d+\)\.csv$", "Phone": r"BB-MAS_Dataset/(\d+)/\1_HandPhone_Keyboard_\(.*\)\.csv$"}[DEV]
files = {}
for n in z.namelist():
    m = re.search(pat, n)
    if m: files[int(m.group(1))] = n
print(DEV, "users with a keyboard file:", len(files), flush=True)
def parse(name):
    d = pd.read_csv(io.BytesIO(z.read(name)), usecols=["key", "direction", "time"])
    d["t"] = pd.to_datetime(d["time"], errors="coerce", format="mixed")
    d = d.dropna(subset=["t", "key"]).sort_values("t")
    down = {}; holds = []; downs = []                    # holds: (key, hold_s, t); downs: (key, t)
    for k, dr, t in zip(d["key"].astype(str), d["direction"], d["t"].astype("int64") / 1e9):
        if dr == 0:
            down[k] = t; downs.append((k, t))
        elif dr == 1 and k in down:
            h = t - down.pop(k)
            if 0 < h < 2.0: holds.append((k, h, t - h))
    digs = []
    for (k1, t1), (k2, t2) in zip(downs[:-1], downs[1:]):
        lat = t2 - t1
        if 0 < lat < 1.5: digs.append(((k1, k2), lat, t1))
    return holds, digs, downs
users = {}
for u, n in sorted(files.items()):
    h, dg, dn = parse(n)
    if len(dn) >= 400: users[u] = (h, dg, dn)
print("users with >=400 keystrokes:", len(users), flush=True)
ids = sorted(users); rng.shuffle(ids); half = len(ids) // 2
split = {u: ("calibration" if i < half else "test") for i, u in enumerate(ids)}
def stats(vals):
    a = np.asarray(vals); med = np.median(a); mad = np.median(np.abs(a - med)); return med, max(mad * 1.4826, 0.02)
tmpl, windows = {}, {}
for u in ids:
    h, dg, dn = users[u]; tcut = dn[len(dn) // 2][1]
    th = collections.defaultdict(list); td = collections.defaultdict(list)
    for k, v, t in h:
        if t < tcut: th[k].append(v)
    for k, v, t in dg:
        if t < tcut: td[k].append(v)
    tmpl[u] = ({k: stats(v) for k, v in th.items() if len(v) >= 5}, {k: stats(v) for k, v in td.items() if len(v) >= 3})
    late = [x for x in dn if x[1] >= tcut]; wins = []
    for i in range(0, len(late) - W + 1, W):
        t0, t1 = late[i][1], late[i + W - 1][1]
        hh = [(k, v) for k, v, t in h if t0 <= t <= t1]; ddv = [(k, v) for k, v, t in dg if t0 <= t <= t1]
        wins.append((hh, ddv))
    windows[u] = wins
def score(tp, win):
    th, td = tp; zs = []
    for k, v in win[0]:
        if k in th: m, s = th[k]; zs.append(min(abs(v - m) / s, MAXZ))
    for k, v in win[1]:
        if k in td: m, s = td[k]; zs.append(min(abs(v - m) / s, MAXZ))
    return -float(np.mean(zs)) if len(zs) >= MINF else None
rows = []
for u in ids:
    sp = split[u]; others = [o for o in ids if o != u and split[o] == sp and windows[o]]
    for w in windows[u]:
        s = score(tmpl[u], w)
        if s is not None: rows.append((sp, 1, s, "genuine"))
    for o in rng.sample(others, min(30, len(others))):
        w = rng.choice(windows[o]); s = score(tmpl[u], w)
        if s is not None: rows.append((sp, 0, s, "impostor"))
df = pd.DataFrame(rows, columns=["split", "genuine", "cosine", "kind"]); df.to_csv(OUT, index=False)
info = {"device": DEV, "users": len(ids), "calibration_users": half, "test_users": len(ids) - half, "window_keystrokes": W}
for sp in ["calibration", "test"]:
    x = df[df.split == sp]; f, t, _ = roc_curve(x.genuine, x.cosine); eer = float(f[np.nanargmin(np.abs(f - (1 - t)))])
    info[sp] = {"genuine": int((x.genuine == 1).sum()), "impostor": int((x.genuine == 0).sum()), "AUC": round(float(roc_auc_score(x.genuine, x.cosine)), 4), "EER": round(eer, 4)}
print(info)
import json; json.dump(info, open(OUT.replace(".csv", "_info.json"), "w"), indent=1)
