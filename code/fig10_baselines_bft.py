"""Figure 10: BZT-ID chaincode on real Fabric 3.0 (Raft vs SmartBFT ordering) versus centralized-DB and JWT baselines."""
import os, pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(__file__); D = os.path.join(H, "..", "data")
f3 = pd.read_csv(os.path.join(D, "fabric3", "fabric3_raft_vs_bft_summary.csv")); bl = pd.read_csv(os.path.join(D, "baselines", "baselines_summary.csv"))
def fab(o, b, name, col): return float(f3[(f3.ordering == o) & (f3.batch == b) & (f3.name == name)][col].iloc[0])
def base(m, op, off, col): return float(bl[(bl["mode"] == m) & (bl.op == op) & (bl.offered == off)][col].iloc[0])
labels = ["Centralized\nDB", "JWT\nservice", "Fabric Raft\n(default)", "Fabric Raft\n(tuned)", "Fabric BFT\n(default)", "Fabric BFT\n(tuned)"]
cols = ["#8a8f98", "#b7bbc2", "#2a78d6", "#7fb0ea", "#eb6834", "#f3a583"]
lat = [base("central", "issue", 100, "lat_mean_ms"), base("jwt", "issue", 100, "lat_mean_ms")] + [fab(o, b, "issue-100tps", "lat_ms_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
wtp = [base("central", "issue", 300, "tp_mean"), base("jwt", "issue", 300, "tp_mean")] + [fab(o, b, "issue-300tps", "tp_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
rtp = [base("central", "verify", 600, "tp_mean"), base("jwt", "verify", 600, "tp_mean")] + [fab(o, b, "verify-600tps", "tp_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
# order Raft/BFT lists correctly (loop order raft default, raft tuned, bft default, bft tuned)
fig, ax = plt.subplots(1, 3, figsize=(12.5, 4.2), dpi=200)
for a, v, t, yl in zip(ax, [lat, wtp, rtp], ["(a) Write latency at 100 tx/s offered", "(b) Committed write throughput at 300 tx/s offered", "(c) Committed read throughput at 600 tx/s offered"], ["mean latency (ms)", "tx/s", "tx/s"]):
    b = a.bar(range(6), v, color=cols)
    for i, x in enumerate(v): a.text(i, x, f"{x:.0f}", ha="center", va="bottom", fontsize=8)
    a.set_xticks(range(6)); a.set_xticklabels(labels, fontsize=7); a.set_title(t, fontsize=9); a.set_ylabel(yl); a.grid(axis="y", alpha=.25); a.set_axisbelow(True)
    a.set_ylim(0, max(v) * 1.15)
fig.tight_layout(); fig.savefig(os.path.join(H, "..", "figures", "fig10_baselines_bft.png"))
print(lat, wtp, rtp)
