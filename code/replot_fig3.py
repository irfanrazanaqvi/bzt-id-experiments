"""Redraw Fig. 3 from data/exp1_latency_vs_peers.csv with an accurate title (the simulator does not model BFT ordering)."""
import os, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(root, "data", "exp1_latency_vs_peers.csv"))
fig, ax1 = plt.subplots(figsize=(7, 4.5), dpi=200)
ax1.plot(df.num_peers, df.issue_latency_ms_mean, "o-", color="#1f4e79", label="Issuance (mean)")
ax1.plot(df.num_peers, df.issue_latency_ms_p95, "o--", color="#1f4e79", alpha=0.5, label="Issuance (p95)")
ax1.plot(df.num_peers, df.verify_latency_ms_mean, "s-", color="#c0392b", label="Verification (mean)")
ax1.plot(df.num_peers, df.verify_latency_ms_p95, "s--", color="#c0392b", alpha=0.5, label="Verification (p95)")
ax1.set_xlabel("Number of consortium peer nodes (N)"); ax1.set_ylabel("Commit latency (ms)")
ax1.set_title("Simulated endorsement-quorum commit latency vs. consortium size\n(model output; no ordering-protocol traffic)", fontsize=10)
ax1.grid(alpha=0.3); ax1.legend(fontsize=8); fig.tight_layout()
fig.savefig(os.path.join(root, "figures", "fig3_latency_vs_peers.png")); print("ok")
