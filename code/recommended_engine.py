"""
recommended_engine.py
Evaluates the engine configuration the paper recommends (Section 6.2): a hard biometric floor
(DENY if the calibrated face score is below the 1% false-accept point, s < 0.99) combined with factor
weights learned from labelled traffic and a flag threshold recalibrated on legitimate training traffic.

Workload: the real-biometric (LFW) session workload of Exp. 6 (same generator, seed 11). 5-fold stratified
cross-validation; the weights (non-negative logistic regression in the engine's own form) and the threshold
are fitted on the training folds only, and every number is measured on the held-out fold.
Operating points: overall false-positive rate (legitimate sessions flagged, floor included) of 1% and 5%,
set on the training folds.

usage: python recommended_engine.py data/biometric/lfw_pair_scores.csv
Output: data/recommended_engine_lfw.csv, data/recommended_engine_lfw_perclass.csv
"""
import sys, os, runpy
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
sys.path.insert(0, HERE)
import matplotlib; matplotlib.use("Agg")
# reuse the Exp. 6 workload builder without re-running its outputs
src = open(os.path.join(HERE, "exp6_real_biometric.py")).read().split("df = build(); atk = df.atk.values")[0]
ns = {"__file__": os.path.join(HERE, "exp6_real_biometric.py")}; sys.argv = [sys.argv[0], sys.argv[1]]; exec(compile(src, "exp6_head", "exec"), ns)
df = ns["build"](); FEATS, ANOM, KINDS = ns["FEATS"], ns["ANOM"], ns["KINDS"]
from bzt_id_sim import ZeroTrustEngine
atk = df.atk.values; bio = df.biometric_match_score.values; lab = df.label.values
R = np.column_stack([(df[f].values if f in ANOM else 1 - df[f].values) for f in FEATS])  # risk form: higher = riskier
w0 = np.array([ZeroTrustEngine.WEIGHTS[f] for f in FEATS]); FLOOR = 0.99
fixed_risk = R @ w0

def th_for(risk_tr, floored_tr, target):
    """threshold on risk so that (floored or risk > th) flags `target` of legitimate training sessions."""
    n = len(risk_tr); budget = target * n - floored_tr.sum()
    if budget <= 0: return np.inf
    r = np.sort(risk_tr[~floored_tr])[::-1]; k = int(np.floor(budget))
    return r[k] if k < len(r) else -np.inf

schemes = ["Biometric only", "Fixed-weight engine", "Fixed-weight engine + floor", "Learned weights", "Recommended: floor + learned weights", "Gradient boosting (supervised)"]
flags = {(s, t): np.zeros(len(df), bool) for s in schemes for t in (0.01, 0.05)}; score = {s: np.zeros(len(df)) for s in schemes}; W = []
for tr, te in StratifiedKFold(5, shuffle=True, random_state=3).split(R, atk):
    lr = LogisticRegression(max_iter=2000, class_weight="balanced").fit(R[tr], atk[tr])
    w = np.clip(lr.coef_[0], 0, None); w = w / w.sum(); W.append(w); lrisk = R @ w
    gb = HistGradientBoostingClassifier(random_state=0).fit(np.c_[R, bio][tr], atk[tr]); grisk = gb.predict_proba(np.c_[R, bio])[:, 1]
    risks = {"Biometric only": -bio, "Fixed-weight engine": fixed_risk, "Fixed-weight engine + floor": fixed_risk, "Learned weights": lrisk,
             "Recommended: floor + learned weights": lrisk, "Gradient boosting (supervised)": grisk}
    for s, rk in risks.items():
        fl = (bio < FLOOR) if "floor" in s else np.zeros(len(df), bool)
        score[s][te] = np.where(fl, 10, rk)[te]   # floored sessions rank as maximally risky
        leg = tr[atk[tr] == 0]
        for t in (0.01, 0.05):
            th = th_for(rk[leg], fl[leg], t); flags[(s, t)][te] = (fl | (rk > th))[te]
rows = []
for s in schemes:
    r = {"scheme": s, "AUC": roc_auc_score(atk, score[s])}
    for t in (0.01, 0.05):
        f = flags[(s, t)]; r[f"recall@FPR{int(t*100)}%"] = f[atk == 1].mean(); r[f"measured_FPR@{int(t*100)}%"] = f[atk == 0].mean()
    rows.append(r)
res = pd.DataFrame(rows); res.to_csv(os.path.join(OUT, "recommended_engine_lfw.csv"), index=False)
pc = pd.DataFrame([{"scheme": s, **{k: flags[(s, 0.05)][lab == k].mean() for k in KINDS}} for s in schemes])
pc.to_csv(os.path.join(OUT, "recommended_engine_lfw_perclass.csv"), index=False)
wm = np.mean(W, 0)
print(res.round(4).to_string()); print(pc.round(3).to_string()); print("learned weights (mean over folds):", dict(zip(FEATS, wm.round(3))),
      "floor FRR on legit:", (bio[atk == 0] < FLOOR).mean())
