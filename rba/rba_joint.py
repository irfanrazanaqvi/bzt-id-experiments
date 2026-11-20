"""
Joint real-data test of the recommended engine (paper, Section 8.12): real login context from the RBA data set
(Wiefling et al., 2022) combined with real face-verification scores from LFW (Exp. 6 test identities).
Each held-out login receives one LFW score, drawn at random (the pairing is synthetic; both inputs are real):
  legitimate login            -> a genuine LFW pair
  attack (takeover / attacker IP), three attacker models:
    S1 impostor face          -> a random impostor pair
    S2 look-alike             -> one of the hardest 10% impostor pairs (proxy for presentation attacks)
    S3 biometric defeated     -> a genuine pair (deepfake or stolen template passes the matcher)
Schemes: biometric only; fixed-weight engine (bio .30 + four context factors, renormalised); hard floor (s < 0.99)
+ fixed weights; hard floor + learned weights (non-negative logistic regression on training users).
Thresholds are set on training users so that 1% or 5% of their legitimate logins are flagged (floor included);
results are on held-out users (80/20 split by user, as in rba_eval.py).
usage: python rba_joint.py <rba-dataset.csv> <lfw_pair_scores.csv> <out_dir>
"""
import sys, os, zlib
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
CSV, LFW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rba_eval.py")).read()
head = src.split('print("history rows"')[0]
sys.argv = [sys.argv[0], CSV, OUT]; exec(compile(head, "rba_eval_head", "exec"))
sc = pd.read_csv(LFW); cal_imp = np.sort(sc[(sc.split == "calibration") & (sc.genuine == 0)].cosine.values)
to_s = lambda c: (np.searchsorted(cal_imp, c, side="left") + 0.5) / (len(cal_imp) + 1)
sg = to_s(sc[(sc.split == "test") & (sc.genuine == 1)].cosine.values); si = to_s(sc[(sc.split == "test") & (sc.genuine == 0)].cosine.values)
hard = si[si >= np.quantile(si, 0.90)]; FLOOR = 0.99
uid = h["User ID"].values; test = (pd.Series(uid).apply(lambda u: zlib.crc32(str(u).encode()) % 5 == 0)).values
K = ["geo_new", "device_new", "asn_rare", "failed"]; C = h[K].values
W0 = np.array([.30, .20, .15, .15, .15]); W0 = W0 / W0.sum()          # bio, geo, device, network, behaviour
def th_for(risk, floored, target):
    n = len(risk); budget = target * n - floored.sum()
    if budget <= 0: return np.inf
    r = np.sort(risk[~floored])[::-1]; k = int(np.floor(budget)); return r[k] if k < len(r) else -np.inf
rows = []
for lab, name in [("y_ato", "Account takeover"), ("y_ip", "Attacker IP")]:
    y = h[lab].values
    keep = (y == 1) | ((h.y_ip.values == 0) & (h.y_ato.values == 0)); yk = y[keep]; Ck = C[keep]; tk = test[keep]
    for scen, pool in [("S1 impostor face", si), ("S2 look-alike", hard), ("S3 biometric defeated", sg)]:
        rng = np.random.default_rng(7)
        b = np.where(yk == 1, rng.choice(pool, len(yk)), rng.choice(sg, len(yk)))
        R = np.column_stack([1 - b, Ck])                                   # risk form: higher = riskier
        lr = LogisticRegression(max_iter=1000, class_weight="balanced").fit(R[~tk], yk[~tk])
        w = np.clip(lr.coef_[0], 0, None); w = w / w.sum()
        risks = {"Biometric only": (1 - b, False), "Fixed weights (bio + context)": (R @ W0, False),
                 "Floor + fixed weights": (R @ W0, True), "Floor + learned weights": (R @ w, True)}
        for sch, (rk, use_floor) in risks.items():
            fl = (b < FLOOR) if use_floor else np.zeros(len(b), bool)
            leg_tr = (~tk) & (yk == 0); r = {"attack": name, "scenario": scen, "scheme": sch, "test_positives": int(yk[tk].sum()), "test_legit": int((yk[tk] == 0).sum())}
            r["AUC"] = roc_auc_score(yk[tk], np.where(fl, 10, rk)[tk])
            for t in (0.01, 0.05):
                th = th_for(rk[leg_tr], fl[leg_tr], t); f = (fl | (rk > th))[tk]
                r[f"recall@{int(t*100)}%"] = f[yk[tk] == 1].mean(); r[f"FPR@{int(t*100)}%"] = f[yk[tk] == 0].mean()
            if sch == "Floor + learned weights": r["learned_w(bio,geo,dev,net,beh)"] = "/".join(f"{x:.2f}" for x in w)
            rows.append(r); print(r, flush=True)
pd.DataFrame(rows).to_csv(os.path.join(OUT, "rba_lfw_joint.csv"), index=False)
