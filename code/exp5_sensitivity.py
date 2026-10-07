"""
exp5_sensitivity.py
Experiment 5: sensitivity of the Zero-Trust engine to (a) its feature weights and
(b) the difficulty of the attacks.  Uses the same synthetic generators as Experiment 3.

(a) Weight sensitivity: 500 weight vectors drawn from Dirichlet(50 * nominal) plus the equal-weight
    vector, evaluated on the Exp. 3 workload.
(b) Attack difficulty: every attack feature is blended toward a legitimate sample,
    x' = (1 - d) * x_attack + d * x_legit, d in {0, .25, .5, .75}.  d = 0 is Exp. 3.

Outputs: data/exp5_weight_sensitivity.csv, data/exp5_difficulty_sweep.csv,
         figures/fig8_sensitivity.png
"""
import os, random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import asdict
from bzt_id_sim import ZeroTrustEngine, synthetic_legit_context, synthetic_attack_context, RequestContext

HERE = os.path.dirname(__file__)
OUT_DATA = os.path.join(HERE, "..", "data"); OUT_FIG = os.path.join(HERE, "..", "figures")
KINDS = ["spoof", "credential_stuffing", "impossible_travel", "insider_replay"]
N = 2000
FEATS = list(ZeroTrustEngine.WEIGHTS.keys())
ANOM = ZeroTrustEngine.ANOMALY_FEATURES


def auc(neg, pos):
    """AUC for 'attack has LOWER trust score': P(score_attack < score_legit) + 0.5 ties."""
    s = np.concatenate([neg, pos]); r = pd.Series(s).rank().values
    n_neg, n_pos = len(neg), len(pos)
    u = r[:n_neg].sum() - n_neg * (n_neg + 1) / 2          # U = #pairs with legit score > attack score
    return u / (n_neg * n_pos)


def build(d, seed=11):
    rng = random.Random(seed)
    legit = [asdict(synthetic_legit_context(rng)) for _ in range(2 * N)]
    atk = []
    for k in KINDS:
        for _ in range(N):
            a = asdict(synthetic_attack_context(rng, k))
            if d > 0:
                l = asdict(synthetic_legit_context(rng))
                a = {f: (1 - d) * a[f] + d * l[f] for f in a}
            atk.append(a)
    return pd.DataFrame(legit)[FEATS], pd.DataFrame(atk)[FEATS]


def trust(df, w):
    t = np.zeros(len(df))
    for f, wf in zip(FEATS, w):
        v = df[f].values
        t += wf * ((1 - v) if f in ANOM else v)
    return np.clip(t, 0, 1)


def metrics(legit, atk, w, thr=0.75):
    sl, sa = trust(legit, w), trust(atk, w)
    return {"auc": auc(sl, sa), "recall": float((sa < thr).mean()), "fpr": float((sl < thr).mean())}


nominal = np.array([ZeroTrustEngine.WEIGHTS[f] for f in FEATS])
legit, atk = build(0.0)
rows = [{"weights": "nominal", **metrics(legit, atk, nominal)},
        {"weights": "equal", **metrics(legit, atk, np.full(6, 1 / 6))}]
rs = np.random.RandomState(2026)
for i in range(500):
    w = rs.dirichlet(50 * nominal)
    rows.append({"weights": f"dirichlet_{i}", **metrics(legit, atk, w)})
wdf = pd.DataFrame(rows); wdf.to_csv(os.path.join(OUT_DATA, "exp5_weight_sensitivity.csv"), index=False)
dd = wdf[wdf.weights.str.startswith("dirichlet")]
print("weights: nominal", wdf.iloc[0][["auc", "recall", "fpr"]].round(4).to_dict())
print("weights: equal  ", wdf.iloc[1][["auc", "recall", "fpr"]].round(4).to_dict())
print("500 random weight vectors: AUC min/median/max = %.4f / %.4f / %.4f ; recall min/median/max = %.3f / %.3f / %.3f"
      % (dd.auc.min(), dd.auc.median(), dd.auc.max(), dd.recall.min(), dd.recall.median(), dd.recall.max()))

rows = []
for d in [0.0, 0.25, 0.5, 0.75]:
    lg, at = build(d)
    m = metrics(lg, at, nominal)
    base_l, base_a = lg["biometric_match_score"].values, at["biometric_match_score"].values
    rows.append({"difficulty_d": d, "zte_auc": m["auc"], "zte_recall": m["recall"], "zte_fpr": m["fpr"],
                 "bio_only_auc": auc(base_l, base_a), "bio_only_recall": float((base_a < 0.80).mean()),
                 "bio_only_fpr": float((base_l < 0.80).mean())})
ddf = pd.DataFrame(rows); ddf.to_csv(os.path.join(OUT_DATA, "exp5_difficulty_sweep.csv"), index=False)
print(ddf.round(4).to_string(index=False))

fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.4), facecolor="#fcfcfb")
for a in ax:
    a.set_facecolor("#fcfcfb"); a.grid(True, color="#e6e5e1"); a.set_axisbelow(True)
    for s in ("top", "right"): a.spines[s].set_visible(False)
ax[0].hist(dd.auc, bins=25, color="#2a78d6", edgecolor="#fcfcfb")
ax[0].axvline(wdf.iloc[0].auc, color="#0b0b0b", lw=1.5, ls="--"); ax[0].text(wdf.iloc[0].auc, ax[0].get_ylim()[1] * 0.92, " nominal", fontsize=8.5)
ax[0].set_xlabel("ROC-AUC (500 random weight vectors)"); ax[0].set_ylabel("Count")
ax[0].set_title("(a) Sensitivity to feature weights", loc="left", fontsize=11)
ax[1].plot(ddf.difficulty_d, ddf.zte_auc, color="#2a78d6", marker="o", lw=2, mec="#fcfcfb", mew=1.5, label="Zero-Trust engine")
ax[1].plot(ddf.difficulty_d, ddf.bio_only_auc, color="#eb6834", marker="s", lw=2, mec="#fcfcfb", mew=1.5, label="Biometric-only baseline")
ax[1].set_xlabel("Attack difficulty d (0 = Exp. 3, 1 = indistinguishable)"); ax[1].set_ylabel("ROC-AUC")
ax[1].set_title("(b) Sensitivity to attack difficulty", loc="left", fontsize=11); ax[1].legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(OUT_FIG, "fig8_sensitivity.png"), dpi=200, facecolor=fig.get_facecolor())
