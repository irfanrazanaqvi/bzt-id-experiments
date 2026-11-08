"""Recall at matched false-positive rates for Experiment 3 (engine vs biometric-only baseline).
Reads data/exp3_scores.csv (12,000 sessions); writes data/exp3_matched_fpr.csv."""
import os, numpy as np, pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.read_csv(os.path.join(root, "data", "exp3_scores.csv"))
rows = []
for name, col in [("BZT-ID engine", "zte_score"), ("Biometric-only", "biometric_only")]:
    leg = d[d.is_attack == 0][col].values; att = d[d.is_attack == 1][col].values
    for fpr in (0.01, 0.05):
        thr = np.quantile(leg, fpr)  # flag sessions scoring below thr
        rows.append({"scheme": name, "target_FPR": fpr, "recall": float((att < thr).mean())})
out = pd.DataFrame(rows); out.to_csv(os.path.join(root, "data", "exp3_matched_fpr.csv"), index=False); print(out)
