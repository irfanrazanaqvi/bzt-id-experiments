"""
exp3_zero_trust_detection.py
--------------------------------------------------------------------
Experiment 3: Detection performance of the continuous Zero-Trust
Engine (ZTE) versus a static single-factor MFA baseline (biometric
match score thresholded at login time only), evaluated on a labelled
synthetic workload of legitimate sessions and four attack classes:
  - Presentation/deepfake biometric spoofing
  - Credential-stuffing / brute-force
  - Impossible-travel (geo-velocity) account takeover
  - Insider credential replay

Outputs:
  data/exp3_scores.csv
  data/exp3_confusion_summary.csv
  figures/fig5_score_distributions.png
  figures/fig6_roc_curve.png
--------------------------------------------------------------------
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
from bzt_id_sim import ZeroTrustEngine, synthetic_legit_context, synthetic_attack_context
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_FIG = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT_DATA, exist_ok=True)
os.makedirs(OUT_FIG, exist_ok=True)

N_PER_CLASS = 2000
ATTACK_KINDS = ["spoof", "credential_stuffing", "impossible_travel", "insider_replay"]


def build_dataset(seed=11):
    rng = random.Random(seed)
    zte = ZeroTrustEngine()
    rows = []
    for _ in range(N_PER_CLASS * 2):  # legit class weighted 2x (realistic base rate)
        ctx = synthetic_legit_context(rng)
        rows.append({"label": "legitimate", "is_attack": 0,
                      "zte_score": zte.score(ctx), "biometric_only": ctx.biometric_match_score})
    for kind in ATTACK_KINDS:
        for _ in range(N_PER_CLASS):
            ctx = synthetic_attack_context(rng, kind)
            rows.append({"label": kind, "is_attack": 1,
                         "zte_score": zte.score(ctx), "biometric_only": ctx.biometric_match_score})
    return pd.DataFrame(rows)


def roc_points(scores, is_attack, thresholds):
    """is_attack=1 is the 'positive' (malicious) class; scores are TRUST
    scores, so a request is flagged malicious when score < threshold."""
    out = []
    for th in thresholds:
        pred_attack = (scores < th).astype(int)
        tp = int(((pred_attack == 1) & (is_attack == 1)).sum())
        fp = int(((pred_attack == 1) & (is_attack == 0)).sum())
        fn = int(((pred_attack == 0) & (is_attack == 1)).sum())
        tn = int(((pred_attack == 0) & (is_attack == 0)).sum())
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        out.append((th, tpr, fpr))
    return out


def auc_trapezoid(fpr, tpr):
    order = np.argsort(fpr)
    fpr, tpr = np.array(fpr)[order], np.array(tpr)[order]
    trapz = getattr(np, "trapezoid", None) or np.trapz
    return float(trapz(tpr, fpr))


def summarize_confusion(df, zte):
    rows = []
    # ZTE policy decision thresholds
    for name, score_col, allow_th, deny_th in [
        ("BZT-ID Zero-Trust Engine (continuous, 6-factor)", "zte_score", 0.75, 0.50),
        ("Static single-factor MFA (biometric-only, login-time)", "biometric_only", 0.80, 0.50),
    ]:
        s = df[score_col].values
        atk = df["is_attack"].values
        decision = np.where(s >= allow_th, "ALLOW", np.where(s >= deny_th, "STEP_UP", "DENY"))
        flagged = decision != "ALLOW"  # STEP_UP or DENY counts as "flagged / not silently allowed"
        tp = int(((flagged) & (atk == 1)).sum())
        fn = int(((~flagged) & (atk == 1)).sum())
        fp = int(((flagged) & (atk == 0)).sum())
        tn = int(((~flagged) & (atk == 0)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        rows.append({
            "scheme": name, "TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "precision": precision, "recall_TPR": recall, "FPR": fpr, "F1": f1,
            "accuracy": (tp + tn) / len(df),
        })
    return pd.DataFrame(rows)


def plot_distributions(df):
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=200)
    bins = np.linspace(0, 1, 40)
    ax.hist(df[df.label == "legitimate"].zte_score, bins=bins, alpha=0.55,
            label="Legitimate sessions", color="#2e8b57", density=True)
    for kind, color in zip(ATTACK_KINDS, ["#c0392b", "#e67e22", "#8e44ad", "#2980b9"]):
        ax.hist(df[df.label == kind].zte_score, bins=bins, alpha=0.45,
                label=kind.replace("_", " "), density=True, histtype="stepfilled", color=color)
    ax.axvline(0.75, color="black", linestyle="--", linewidth=1, label="ALLOW threshold")
    ax.axvline(0.50, color="gray", linestyle=":", linewidth=1, label="STEP-UP threshold")
    ax.set_xlabel("Zero-Trust composite score $T(x)$")
    ax.set_ylabel("Density")
    ax.set_title("Fig. 5. Trust-score distributions: legitimate vs. attack sessions")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_FIG, "fig5_score_distributions.png"))
    plt.close(fig)


def plot_roc(df):
    thresholds = np.linspace(0, 1, 200)
    fig, ax = plt.subplots(figsize=(6, 5.4), dpi=200)

    for score_col, label, color in [
        ("zte_score", "BZT-ID Zero-Trust Engine", "#1f4e79"),
        ("biometric_only", "Static biometric-only MFA", "#c0392b"),
    ]:
        pts = roc_points(df[score_col].values, df["is_attack"].values, thresholds)
        tprs = [p[1] for p in pts]
        fprs = [p[2] for p in pts]
        auc = auc_trapezoid(fprs, tprs)
        ax.plot(fprs, tprs, "-", color=color, label=f"{label} (AUC={auc:.3f})")

    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Chance")
    ax.set_xlabel("False Positive Rate (legitimate users flagged)")
    ax.set_ylabel("True Positive Rate (attacks detected)")
    ax.set_title("Fig. 6. ROC curve: attack detection performance")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_FIG, "fig6_roc_curve.png"))
    plt.close(fig)


if __name__ == "__main__":
    df = build_dataset()
    df.to_csv(os.path.join(OUT_DATA, "exp3_scores.csv"), index=False)
    zte = ZeroTrustEngine()
    summary = summarize_confusion(df, zte)
    summary.to_csv(os.path.join(OUT_DATA, "exp3_confusion_summary.csv"), index=False)
    plot_distributions(df)
    plot_roc(df)
    print(summary.to_string(index=False))
    print("Experiment 3 complete.")
