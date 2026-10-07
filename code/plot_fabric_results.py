"""Figure 7: real Hyperledger Fabric 2.5.9 benchmark (Caliper) - write latency and throughput.
Reads data/fabric/fabric_{default,tuned}.csv, writes figures/fig7_fabric_real_benchmark.png"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
D = os.path.join(HERE, "..", "data", "fabric")
OUT = os.path.join(HERE, "..", "figures", "fig7_fabric_real_benchmark.png")
SERIES = [("default", "Default batching (2 s timeout, 10 tx/block)", "#2a78d6", "o"),
          ("tuned", "Tuned batching (200 ms timeout, 100 tx/block)", "#eb6834", "s")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

def issue(df):
    d = df[df["Name"].str.startswith("issue-")].copy()
    d["rate"] = d["Name"].str.extract(r"issue-(\d+)tps").astype(int)
    return d.sort_values("rate")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), facecolor="#fcfcfb")
for ax in axes:
    ax.set_facecolor("#fcfcfb")
    ax.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#bdbcb7")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_xlabel("Offered send rate (tx/s)", color=INK, fontsize=10)

for key, label, color, marker in SERIES:
    d = issue(pd.read_csv(os.path.join(D, f"fabric_{key}.csv")))
    axes[0].plot(d["rate"], d["Avg Latency (s)"] * 1000, color=color, lw=2, marker=marker, ms=7,
                 mec="#fcfcfb", mew=1.5, label=label)
    axes[1].plot(d["rate"], d["Throughput (TPS)"], color=color, lw=2, marker=marker, ms=7,
                 mec="#fcfcfb", mew=1.5, label=label)

lim = [0, 310]
axes[1].plot(lim, lim, color="#9a9994", lw=1, ls=(0, (4, 3)))
axes[1].text(214, 232, "ideal (y = x)", color=MUTED, fontsize=8, rotation=32)
axes[0].set_ylabel("Mean commit latency (ms)", color=INK, fontsize=10)
axes[1].set_ylabel("Committed throughput (tx/s)", color=INK, fontsize=10)
axes[0].set_title("(a) Write latency (IssueCredential)", color=INK, fontsize=11, loc="left")
axes[1].set_title("(b) Write throughput (IssueCredential)", color=INK, fontsize=11, loc="left")
axes[0].set_ylim(bottom=0); axes[1].set_xlim(lim); axes[1].set_ylim(lim)
axes[0].legend(frameon=False, fontsize=8.5, labelcolor=INK, loc="upper right")
fig.suptitle("BZT-ID chaincode on real Hyperledger Fabric 2.5.9 (2 orgs, Raft, one 4-vCPU runner), Caliper 0.7.1",
             color=MUTED, fontsize=9, x=0.012, ha="left", y=0.035)
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.savefig(OUT, dpi=200, facecolor=fig.get_facecolor())
print("wrote", OUT)
