"""
exp6_real_biometric.py
Experiment 6: replace the SYNTHETIC biometric match score by REAL face-verification scores
computed on the public LFW dataset (see biometric/lfw_scores.py), and compare the trust engine
with (i) a static biometric-only gate and (ii) supervised ML detectors on the same six features.

Calibration (no tuning on the evaluation data): the raw cosine similarity is mapped to
s = F_imp(cosine) = fraction of CALIBRATION-split impostor pairs scoring lower (i.e. 1 - FAR).
Evaluation scores come from the disjoint-identity TEST split.

Biometric source per session class (the other five features remain synthetic, as in Exp. 3):
  legitimate           -> real genuine pairs
  credential_stuffing  -> real impostor pairs
  insider_replay       -> real impostor pairs
  impossible_travel    -> real genuine pairs (valid biometric, account taken over)
  spoof                -> hardest 10 % of real impostor pairs (PROXY for presentation attacks;
                          LFW contains no spoof samples)

usage: python exp6_real_biometric.py <lfw_pair_scores.csv>
Outputs: data/exp6_summary.csv, data/exp6_ml_baselines.csv, data/exp6_weight_sensitivity.csv,
         data/exp6_biometric_calibration.csv, figures/fig9_real_biometric.png
"""
import sys, os, random
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import asdict
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.dirname(__file__))
from bzt_id_sim import ZeroTrustEngine, synthetic_legit_context, synthetic_attack_context

HERE = os.path.dirname(__file__); OUT_DATA = os.path.join(HERE, "..", "data"); OUT_FIG = os.path.join(HERE, "..", "figures")
KINDS = ["spoof", "credential_stuffing", "impossible_travel", "insider_replay"]
FEATS = list(ZeroTrustEngine.WEIGHTS.keys()); ANOM = ZeroTrustEngine.ANOMALY_FEATURES
N = 2000
sc = pd.read_csv(sys.argv[1])
cal_imp = np.sort(sc[(sc.split == "calibration") & (sc.genuine == 0)].cosine.values)
tg = sc[(sc.split == "test") & (sc.genuine == 1)].cosine.values
ti = sc[(sc.split == "test") & (sc.genuine == 0)].cosine.values
def to_s(c):  # 1 - FAR on calibration impostors, kept strictly inside (0,1)
    return (np.searchsorted(cal_imp, c, side="left") + 0.5) / (len(cal_imp) + 1)
sg, si = to_s(tg), to_s(ti)
hard = si[si >= np.quantile(si, 0.90)]

# real-biometric standalone quality on the TEST split
def auc_g(g, i): return roc_auc_score(np.r_[np.ones(len(g)), np.zeros(len(i))], np.r_[g, i])
def far_frr(th): return float((si >= th).mean()), float((sg < th).mean())
cal_rows = [{"operating_point": f"FAR~{far}", "threshold_s": th, "FAR": far_frr(th)[0], "FRR": far_frr(th)[1]}
            for far, th in [("10%", 0.90), ("1%", 0.99), ("0.1%", 0.999)]]
pd.DataFrame(cal_rows).to_csv(os.path.join(OUT_DATA, "exp6_biometric_calibration.csv"), index=False)
print("biometric-only on LFW test: AUC=%.4f" % auc_g(sg, si), cal_rows)

def build(seed=11):
    rng = random.Random(seed); nr = np.random.default_rng(seed)
    rows = []
    for _ in range(2 * N):
        d = asdict(synthetic_legit_context(rng)); d["biometric_match_score"] = float(nr.choice(sg)); d["label"] = "legitimate"; d["atk"] = 0; rows.append(d)
    for k in KINDS:
        for _ in range(N):
            d = asdict(synthetic_attack_context(rng, k)); d["label"] = k; d["atk"] = 1
            d["biometric_match_score"] = float(nr.choice({"credential_stuffing": si, "insider_replay": si, "impossible_travel": sg, "spoof": hard}[k])); rows.append(d)
    return pd.DataFrame(rows)

def trust(df, w):
    t = np.zeros(len(df))
    for f, wf in zip(FEATS, w):
        v = df[f].values; t += wf * ((1 - v) if f in ANOM else v)
    return np.clip(t, 0, 1)

def auc_attack_low(score, atk):  # AUC for 'attack has lower score'
    return roc_auc_score(atk, -score)

def op(score, atk, th):  # flag if score < th
    f = score < th; tp = (f & (atk == 1)).sum(); fn = (~f & (atk == 1)).sum(); fp = (f & (atk == 0)).sum(); tn = (~f & (atk == 0)).sum()
    return tp / (tp + fn), fp / (fp + tn)

def recall_at_fpr(score, atk, target):
    th = np.quantile(score[atk == 0], target); return float((score[atk == 1] <= th).mean())  # flag score<=th; FPR~target

def boot(score, atk, B=300, seed=1):
    r = np.random.default_rng(seed); n = len(atk); out = []
    for _ in range(B):
        i = r.integers(0, n, n); 
        if atk[i].min() == atk[i].max(): continue
        out.append(auc_attack_low(score[i], atk[i]))
    return np.percentile(out, [2.5, 97.5])

df = build(); atk = df.atk.values
w0 = [ZeroTrustEngine.WEIGHTS[f] for f in FEATS]
eng = trust(df, w0); bio = df.biometric_match_score.values
rows = []
for name, s, ths in [("BZT-ID trust engine (6 factors; ALLOW<0.75)", eng, [0.75]),
                     ("Biometric-only, FAR 1% gate (s>=0.99)", bio, [0.99]),
                     ("Biometric-only, FAR 0.1% gate (s>=0.999)", bio, [0.999])]:
    rc, fp = op(s, atk, ths[0]); lo, hi = boot(s, atk)
    rows.append({"scheme": name, "AUC": auc_attack_low(s, atk), "AUC_CI_lo": lo, "AUC_CI_hi": hi, "recall": rc, "FPR": fp,
                 "recall@FPR=1%": recall_at_fpr(s, atk, 0.01), "recall@FPR=5%": recall_at_fpr(s, atk, 0.05)})
# post-hoc ablation (NOT tuned on this data; 1 % FAR is the conventional operating point):
# hybrid policy = flag if the engine does not ALLOW OR the biometric score is below the 1 % FAR gate
hyb = (eng < 0.75) | (bio < 0.99)
hy_rc = float(hyb[atk == 1].mean()); hy_fp = float(hyb[atk == 0].mean())
hy_pc = {k: float(hyb[(df.label == k).values].mean()) for k in KINDS}
rows.append({"scheme": "Hybrid: engine ALLOW and biometric s>=0.99 (post-hoc ablation)", "AUC": float("nan"), "AUC_CI_lo": float("nan"), "AUC_CI_hi": float("nan"),
             "recall": hy_rc, "FPR": hy_fp, "recall@FPR=1%": float("nan"), "recall@FPR=5%": float("nan")})
# per-class recall of engine at its threshold
pcr = {k: float((eng[(df.label == k).values] < 0.75).mean()) for k in KINDS}
pcb = {k: float((bio[(df.label == k).values] < 0.99).mean()) for k in KINDS}
summ = pd.DataFrame(rows); summ.to_csv(os.path.join(OUT_DATA, "exp6_summary.csv"), index=False)
pd.DataFrame({"class": KINDS, "engine_recall": [pcr[k] for k in KINDS], "bio_only_FAR1%_recall": [pcb[k] for k in KINDS], "hybrid_recall": [hy_pc[k] for k in KINDS]}).to_csv(os.path.join(OUT_DATA, "exp6_per_class_recall.csv"), index=False)
print(summ.round(4).to_string()); print("per-class engine", pcr, "bio", pcb)

# supervised ML baselines (5-fold CV, same features) -- in-distribution reference, trained on the labels
X = df[FEATS].values; ml = []
for name, mk in [("Logistic regression (supervised)", lambda: LogisticRegression(max_iter=1000)),
                 ("Gradient boosting (supervised)", lambda: HistGradientBoostingClassifier(random_state=0))]:
    p = np.zeros(len(df)); 
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=3).split(X, atk):
        m = mk().fit(X[tr], atk[tr]); p[te] = m.predict_proba(X[te])[:, 1]
    sc_ = 1 - p; lo, hi = boot(sc_, atk)
    ml.append({"scheme": name, "AUC": auc_attack_low(sc_, atk), "AUC_CI_lo": lo, "AUC_CI_hi": hi,
               "recall@FPR=1%": recall_at_fpr(sc_, atk, 0.01), "recall@FPR=5%": recall_at_fpr(sc_, atk, 0.05)})
ml.append({"scheme": "BZT-ID engine (fixed weights, no training)", "AUC": summ.AUC[0], "AUC_CI_lo": summ.AUC_CI_lo[0], "AUC_CI_hi": summ.AUC_CI_hi[0],
           "recall@FPR=1%": summ["recall@FPR=1%"][0], "recall@FPR=5%": summ["recall@FPR=5%"][0]})
mlf = pd.DataFrame(ml); mlf.to_csv(os.path.join(OUT_DATA, "exp6_ml_baselines.csv"), index=False); print(mlf.round(4).to_string())

# weight sensitivity on the real-biometric workload
rg = np.random.default_rng(5); aucs = []
for _ in range(300):
    w = rg.dirichlet(50 * np.array(w0)); aucs.append(auc_attack_low(trust(df, w), atk))
pd.DataFrame({"auc": aucs}).to_csv(os.path.join(OUT_DATA, "exp6_weight_sensitivity.csv"), index=False)
print("weight AUC min/med/max", np.min(aucs), np.median(aucs), np.max(aucs), "nominal", summ.AUC[0], "equal", auc_attack_low(trust(df, [1/6]*6), atk))

# figure
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.3), dpi=200)
b = np.linspace(-0.2, 1, 49)
ax[0].hist(tg, bins=b, alpha=.6, color="#2a78d6", label="genuine pairs", density=True); ax[0].hist(ti, bins=b, alpha=.6, color="#eb6834", label="impostor pairs", density=True)
ax[0].set_xlabel("raw cosine similarity (FaceNet embeddings)"); ax[0].set_ylabel("density"); ax[0].set_title("(a) Real LFW biometric scores (test identities)", fontsize=10); ax[0].legend(fontsize=8)
for nm, s, c in [("Trust engine", eng, "#2a78d6"), ("Biometric only", bio, "#eb6834")]:
    fp = np.linspace(0, 1, 400); th = np.quantile(s[atk == 0], fp); tp = [(s[atk == 1] <= t).mean() for t in th]
    ax[1].plot(fp, tp, color=c, label=f"{nm} (AUC {auc_attack_low(s, atk):.3f})")
ax[1].set_xlabel("false-positive rate (legitimate flagged)"); ax[1].set_ylabel("recall"); ax[1].set_xlim(0, .3); ax[1].set_title("(b) ROC on the real-biometric workload", fontsize=10); ax[1].legend(fontsize=8)
for a in ax: a.grid(alpha=.25)
fig.tight_layout(); fig.savefig(os.path.join(OUT_FIG, "fig9_real_biometric.png"))
