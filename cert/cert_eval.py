"""
Evaluate the BZT-ID trust engine's behavioural / device / time factors on the CERT Insider Threat data set r4.2
(CMU SEI, KiltHub doi:10.1184/R1/12841247, CC BY 4.0). NOTE: this data set is SIMULATED by CERT (synthetic users and
events with injected insider scenarios); it is a labelled benchmark, not production data.

Unit: one user-day. Anomaly-oriented factors in [0,1] (high = suspicious), derived from the same user's earlier days only:
  time_anom  fraction of the day's logons outside 07:00-18:00                         -> time-of-day factor (nominal weight .05)
  pc_new     fraction of the day's logons on a PC the user had not used before        -> device posture    (.15)
  usb        1 if any removable-media connect today, 0.5 weight if after hours -> min(1, n_connect_after_hours + .5*n_connect) (.15, behavioural)
  file_vol   user's file-copy count today relative to own history (z-score, clipped to [0,1] via z/4)                    (.15, behavioural)
Fixed nominal weights, renormalised over the available factors, no fitting (same as the main engine).
Label: user-day contains at least one event listed in the data set's ground-truth answers for r4.2.
Supervised baselines are fitted on 80% of USERS and tested on the other 20% (no user appears on both sides).
usage: python cert_eval.py <data_dir> <out_dir>
"""
import sys, os, glob, json, zlib, re
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
D, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
R = os.path.join(D, "r4.2")
def rd(name, usecols):
    out = []
    for c in pd.read_csv(os.path.join(R, name), usecols=usecols, chunksize=2_000_000):
        out.append(c)
    return pd.concat(out, ignore_index=True)
lg = rd("logon.csv", ["date", "user", "pc", "activity"]); lg = lg[lg.activity == "Logon"].copy()
dv = rd("device.csv", ["date", "user", "activity"]); dv = dv[dv.activity == "Connect"].copy()
fl = rd("file.csv", ["date", "user"])
for t in (lg, dv, fl):
    t["ts"] = pd.to_datetime(t["date"], format="%m/%d/%Y %H:%M:%S"); t["day"] = t["ts"].dt.normalize(); t["hour"] = t["ts"].dt.hour
print("rows logon/device/file", len(lg), len(dv), len(fl), flush=True)
# ---- labels from the ground-truth answers
pos = set(); n_ans = 0
for f in glob.glob(os.path.join(D, "answers", "r4.2-*", "*.csv")) + glob.glob(os.path.join(D, "answers", "r4.2-*.csv")):
    m = re.search(r"-([A-Z]{3}\d{4})\.csv$", f); fu = m.group(1) if m else None
    for line in open(f, errors="ignore"):
        parts = line.strip().split(",")
        if len(parts) < 4: continue
        dm = re.search(r"(\d{2}/\d{2}/\d{4})", line)
        um = [p for p in parts if re.fullmatch(r"[A-Z]{3}\d{4}", p)]
        u = fu or (um[0] if um else None)
        if dm and u: pos.add((u, pd.to_datetime(dm.group(1), format="%m/%d/%Y"))); n_ans += 1
print("answer events", n_ans, "positive user-days", len(pos), flush=True)
if not pos: sys.exit("no labels parsed")
# ---- daily features
lg["after"] = ((lg.hour < 7) | (lg.hour >= 18)).astype(float)
lg = lg.sort_values(["user", "ts"]); lg["seen_pc"] = lg.groupby(["user", "pc"]).cumcount() > 0
lg["new_pc"] = (~lg["seen_pc"]).astype(float)
g = lg.groupby(["user", "day"]).agg(n_logon=("after", "size"), time_anom=("after", "mean"), pc_new=("new_pc", "mean")).reset_index()
dv["after"] = ((dv.hour < 7) | (dv.hour >= 18)).astype(float)
u = dv.groupby(["user", "day"]).agg(n_conn=("after", "size"), n_conn_after=("after", "sum")).reset_index()
fv = fl.groupby(["user", "day"]).size().rename("n_file").reset_index()
X = g.merge(u, how="left", on=["user", "day"]).merge(fv, how="left", on=["user", "day"]).fillna(0).sort_values(["user", "day"]).reset_index(drop=True)
X["usb"] = np.minimum(1.0, X.n_conn_after + 0.5 * X.n_conn)
# file volume vs the user's own earlier days (expanding mean/std, shifted)
gb = X.groupby("user")["n_file"]
mu = gb.transform(lambda s: s.expanding().mean().shift(1)); sd = gb.transform(lambda s: s.expanding().std().shift(1))
X["file_vol"] = np.clip(((X.n_file - mu) / (sd.replace(0, np.nan))).fillna(0) / 4.0, 0, 1)
X["hist_days"] = X.groupby("user").cumcount()
X = X[X.hist_days >= 30].copy()                      # need 30 earlier active days of history for the per-user baselines
X["pc_new"] = np.where(X.hist_days >= 30, X.pc_new, 0.0)
X["y"] = [int((a, b) in pos) for a, b in zip(X.user, X.day)]
print("user-days", len(X), "positives", int(X.y.sum()), "users", X.user.nunique(), "positive users", X[X.y == 1].user.nunique(), flush=True)
K = ["time_anom", "pc_new", "usb", "file_vol"]; W = {"time_anom": .05, "pc_new": .15, "usb": .15, "file_vol": .15}
def trust(df, ks):
    w = np.array([W[k] for k in ks]); w = w / w.sum(); return 1 - sum(wi * df[k].values for wi, k in zip(w, ks))
test = X.user.apply(lambda s: zlib.crc32(s.encode()) % 5 == 0).values
rows = []
def rec_at_fpr(sc, y, fpr): th = np.quantile(sc[y == 0], fpr); return float((sc[y == 1] <= th).mean())
def boot(sc, y, B=200, seed=1):
    r = np.random.default_rng(seed); o = []
    for _ in range(B):
        i = r.integers(0, len(y), len(y))
        if y[i].min() != y[i].max(): o.append(roc_auc_score(y[i], -sc[i]))
    return np.percentile(o, [2.5, 97.5])
def add(name, sc, y, lower_is_bad=True, ci=False):
    s = sc if lower_is_bad else -sc
    lo, hi = boot(s, y) if ci else (np.nan, np.nan)
    rows.append({"scheme": name, "n": len(y), "positives": int(y.sum()), "AUC": roc_auc_score(y, -s), "AUC_lo": lo, "AUC_hi": hi,
                 "recall@FPR=1%": rec_at_fpr(s, y, .01), "recall@FPR=5%": rec_at_fpr(s, y, .05), "recall@ALLOW<0.75": float((s[y == 1] < .75).mean()), "FPR@ALLOW<0.75": float((s[y == 0] < .75).mean())})
Xt = X[test]; yt = Xt.y.values
add("Engine, fixed weights (all four factors), test users", trust(Xt, K), yt, ci=True)
for k in K: add("Ablation: engine without " + k, trust(Xt, [x for x in K if x != k]), yt)
for k in K: add("Single factor: " + k, 1 - Xt[k].values, yt)
Xtr = X[~test]; ytr = Xtr.y.values
lr = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xtr[K].values, ytr)
add("Logistic regression (supervised, user-split)", -lr.decision_function(Xt[K].values), yt, ci=True)
gbm = HistGradientBoostingClassifier(random_state=0).fit(Xtr[K].values, ytr)
add("Gradient boosting (supervised, user-split)", -gbm.predict_proba(Xt[K].values)[:, 1], yt, ci=True)
# learned weights in the engine's own form
w = np.clip(lr.coef_[0], 0, None); w = w / w.sum() if w.sum() > 0 else np.ones(4) / 4
an_tr = Xtr[K].values @ w; an_te = Xt[K].values @ w; th = np.quantile(an_tr[ytr == 0], .95)
rows.append({"scheme": "Engine, learned weights + recalibrated threshold w=" + "/".join(f"{x:.2f}" for x in w), "n": len(yt), "positives": int(yt.sum()), "AUC": roc_auc_score(yt, an_te), "AUC_lo": np.nan, "AUC_hi": np.nan,
             "recall@FPR=1%": float((an_te[yt == 1] >= np.quantile(an_tr[ytr == 0], .99)).mean()), "recall@FPR=5%": float((an_te[yt == 1] > th).mean()), "recall@ALLOW<0.75": float((an_te[yt == 1] > th).mean()), "FPR@ALLOW<0.75": float((an_te[yt == 0] > th).mean())})
res = pd.DataFrame(rows); res.to_csv(os.path.join(OUT, "cert_summary.csv"), index=False); print(res.round(3).to_string())
json.dump({"logon_rows": len(lg), "device_connects": len(dv), "file_rows": len(fl), "answer_events": n_ans, "user_days": int(len(X)), "positive_user_days": int(X.y.sum()), "users": int(X.user.nunique()),
           "positive_users": int(X[X.y == 1].user.nunique()), "test_user_days": int(len(Xt)), "test_positives": int(yt.sum()), "test_users": int(Xt.user.nunique())}, open(os.path.join(OUT, "cert_info.json"), "w"), indent=1)
