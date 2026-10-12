"""CMU keystroke-dynamics benchmark (Killourhy & Maxion, DSN 2009): 51 users x 400 repetitions of '.tie5Roanl'.
Scaled-Manhattan detector (per user: mean and mean-absolute-deviation of the 31 timing features from the first 200 repetitions).
Genuine = the user's repetitions 201-400; impostor = the first 5 repetitions of every other user (250 per user).
Users are split into disjoint calibration/test halves; score = -distance (higher = more similar), same CSV format as the LFW pair scores.
usage: keystroke_scores.py <DSL-StrongPasswordData.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1]); F = [c for c in d.columns if c not in ("subject", "sessionIndex", "rep")]
users = sorted(d.subject.unique()); rng = np.random.default_rng(3); rng.shuffle(users)
split = {u: ("calibration" if i < len(users) // 2 else "test") for i, u in enumerate(users)}
rows = []
for u in users:
    g = d[d.subject == u].sort_values(["sessionIndex", "rep"]); tr = g.iloc[:200][F].values; te = g.iloc[200:][F].values
    mu = tr.mean(0); mad = np.abs(tr - mu).mean(0) + 1e-6
    sc = lambda X: -(np.abs(X - mu) / mad).sum(1)
    imp = np.vstack([d[d.subject == o].sort_values(["sessionIndex", "rep"]).iloc[:5][F].values for o in users if o != u])
    for s in sc(te): rows.append((split[u], 1, s, "genuine"))
    for s in sc(imp): rows.append((split[u], 0, s, "impostor"))
o = pd.DataFrame(rows, columns=["split", "genuine", "cosine", "kind"]); o.to_csv(sys.argv[2], index=False)
from sklearn.metrics import roc_curve, roc_auc_score
for sp in ["calibration", "test"]:
    x = o[o.split == sp]; fpr, tpr, _ = roc_curve(x.genuine, x.cosine); eer = fpr[np.nanargmin(np.abs(fpr - (1 - tpr)))]
    print(sp, "AUC", round(roc_auc_score(x.genuine, x.cosine), 4), "EER", round(float(eer), 4), "n", len(x))
