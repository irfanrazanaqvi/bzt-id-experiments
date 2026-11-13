"""Regenerates Figs 3-8 and 10 in a consistent style from the saved CSVs (Fig 9 is drawn in exp6_real_biometric.py)."""
import os, numpy as np, pandas as pd
from figstyle import *
setup()
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "..", "data"); F = os.path.join(H, "..", "figures")
def save(fig, name): fig.savefig(os.path.join(F, name)); plt.close(fig); print("wrote", name)

# Fig 3
d = pd.read_csv(os.path.join(D, "exp1_latency_vs_peers.csv"))
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.plot(d.num_peers, d.issue_latency_ms_mean, "-o", color=C["blue"], label="Issuance, mean")
ax.plot(d.num_peers, d.issue_latency_ms_p95, "--o", color=C["blue"], mfc="white", label="Issuance, p95")
ax.plot(d.num_peers, d.verify_latency_ms_mean, "-s", color=C["verm"], label="Verification, mean")
ax.plot(d.num_peers, d.verify_latency_ms_p95, "--s", color=C["verm"], mfc="white", label="Verification, p95")
ax.set_xlabel("Number of consortium peer nodes (N)"); ax.set_ylabel("Commit latency (ms)"); ax.set_xticks(d.num_peers)
ax.legend(ncol=2, loc="center right", bbox_to_anchor=(1, 0.5)); fig.tight_layout(); save(fig, "fig3_latency_vs_peers.png")

# Fig 4
d = pd.read_csv(os.path.join(D, "exp2_throughput_vs_load.csv"))
fig, ax = plt.subplots(figsize=(6.5, 3.8))
for n, c, m in [(4, C["blue"], "o"), (10, C["green"], "s"), (22, C["verm"], "^")]:
    s = d[d.num_peers == n]; ax.plot(s.offered_load_tps, s.achieved_tps, "-" + m, color=c, label=f"N = {n} peers")
mx = d.offered_load_tps.max(); ax.plot([0, mx], [0, mx], ":", color=C["grey"], label="Ideal (achieved = offered)")
ax.set_xlabel("Offered load (verification requests/s)"); ax.set_ylabel("Achieved throughput (committed tx/s)")
ax.legend(loc="upper left"); fig.tight_layout(); save(fig, "fig4_throughput_vs_load.png")

# Figs 5, 6
sc = pd.read_csv(os.path.join(D, "exp3_scores.csv"))
fig, ax = plt.subplots(figsize=(6.5, 3.9)); bins = np.linspace(0, 1, 41)
spec = [("legitimate", "Legitimate", C["green"]), ("spoof", "Spoof", C["verm"]), ("credential_stuffing", "Credential stuffing", C["orange"]),
        ("impossible_travel", "Impossible travel", C["purple"]), ("insider_replay", "Insider replay", C["blue"])]
for k, lab, c in spec:
    v = sc[sc.label == k].zte_score
    ax.hist(v, bins=bins, density=True, histtype="stepfilled", alpha=0.25, color=c); ax.hist(v, bins=bins, density=True, histtype="step", color=c, lw=1.4, label=lab)
ax.axvline(0.75, color=C["ink"], ls="--", lw=1); ax.axvline(0.5, color=C["grey"], ls=":", lw=1.2)
ax.set_ylim(0, ax.get_ylim()[1] * 1.12); ymax = ax.get_ylim()[1]; ax.text(0.755, ymax * 0.985, "ALLOW ≥ 0.75", fontsize=8, va="top"); ax.text(0.495, ymax * 0.985, "STEP-UP ≥ 0.50", fontsize=8, va="top", ha="right", color=C["grey"])
ax.set_xlabel("Zero-trust composite score $T(x)$"); ax.set_ylabel("Density"); ax.set_xlim(0, 1.02)
ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.60)); fig.tight_layout(); save(fig, "fig5_score_distributions.png")

def roc(s, atk):
    th = np.unique(np.concatenate([[-1, 2], s])); fpr = [(s[atk == 0] < t).mean() for t in th]; tpr = [(s[atk == 1] < t).mean() for t in th]
    o = np.argsort(fpr, kind="stable"); f = np.array(fpr)[o]; t = np.array(tpr)[o]; return f, t, np.trapezoid(t, f)
atk = sc.is_attack.values
fig, ax = plt.subplots(figsize=(4.6, 4.4))
for col, lab, c in [("zte_score", "BZT-ID trust engine", C["blue"]), ("biometric_only", "Biometric-only MFA", C["verm"])]:
    f, t, a = roc(sc[col].values, atk); ax.plot(f, t, color=c, label=f"{lab} (AUC = {a:.3f})")
ax.plot([0, 1], [0, 1], "--", color=C["grey"], label="Chance"); ax.set_xlabel("False-positive rate (legitimate sessions flagged)"); ax.set_ylabel("True-positive rate (attacks detected)")
ax.set_xlim(0, 1); ax.set_ylim(0, 1.02); ax.legend(loc="lower right"); fig.tight_layout(); save(fig, "fig6_roc_curve.png")

# Fig 7
def issue(df):
    x = df[df["Name"].str.startswith("issue-")].copy(); x["rate"] = x["Name"].str.extract(r"issue-(\d+)tps").astype(int); return x.sort_values("rate")
fig, ax = plt.subplots(1, 2, figsize=(6.5, 3.3))
for key, lab, c, m in [("default", "Default batching (2 s, 10 tx/block)", C["blue"], "o"), ("tuned", "Tuned batching (200 ms, 100 tx/block)", C["verm"], "s")]:
    x = issue(pd.read_csv(os.path.join(D, "fabric", f"fabric_{key}.csv")))
    ax[0].plot(x["rate"], x["Avg Latency (s)"] * 1000, "-" + m, color=c, label=lab); ax[1].plot(x["rate"], x["Throughput (TPS)"], "-" + m, color=c, label=lab)
ax[1].plot([0, 310], [0, 310], ":", color=C["grey"]); ax[1].text(212, 236, "ideal", color=C["grey"], fontsize=8, rotation=34)
ax[0].set_ylim(bottom=0); ax[1].set_xlim(0, 310); ax[1].set_ylim(0, 310)
ax[0].set_ylabel("Mean commit latency (ms)"); ax[1].set_ylabel("Committed throughput (tx/s)")
for a in ax: a.set_xlabel("Offered send rate (tx/s)")
panel(ax[0], "(a) Write latency"); panel(ax[1], "(b) Write throughput")
h, l = ax[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.08, 1, 1)); save(fig, "fig7_fabric_real_benchmark.png")

# Fig 8
w = pd.read_csv(os.path.join(D, "exp5_weight_sensitivity.csv")); dd = pd.read_csv(os.path.join(D, "exp5_difficulty_sweep.csv"))
rnd = w[w.weights != "nominal"]; nom = float(w[w.weights == "nominal"].auc.iloc[0])
fig, ax = plt.subplots(1, 2, figsize=(6.5, 3.2))
ax[0].hist(rnd.auc, bins=25, color=C["sky"], edgecolor="white"); ax[0].axvline(nom, color=C["ink"], ls="--", lw=1.2)
ax[0].text(nom - 0.0003, ax[0].get_ylim()[1] * 0.97, "nominal ", fontsize=8, va="top", ha="right"); ax[0].set_xlabel("ROC-AUC (500 random weight vectors)"); ax[0].set_ylabel("Count")
ax[1].plot(dd.difficulty_d, dd.zte_auc, "-o", color=C["blue"], label="Trust engine"); ax[1].plot(dd.difficulty_d, dd.bio_only_auc, "-s", color=C["verm"], label="Biometric only")
ax[1].set_xlabel("Attack difficulty $d$ (0 = Exp. 3, 1 = indistinguishable)"); ax[1].set_ylabel("ROC-AUC"); ax[1].legend(loc="lower left")
panel(ax[0], "(a) Sensitivity to feature weights"); panel(ax[1], "(b) Sensitivity to attack difficulty"); fig.tight_layout(); save(fig, "fig8_sensitivity.png")

# Fig 10
f3 = pd.read_csv(os.path.join(D, "fabric3", "fabric3_raft_vs_bft_summary.csv")); bl = pd.read_csv(os.path.join(D, "baselines", "baselines_summary.csv"))
fab = lambda o, b, n, c: float(f3[(f3.ordering == o) & (f3.batch == b) & (f3.name == n)][c].iloc[0])
base = lambda m, op, off, c: float(bl[(bl["mode"] == m) & (bl.op == op) & (bl.offered == off)][c].iloc[0])
labels = ["Centralized DB", "JWT service", "Fabric Raft, default", "Fabric Raft, tuned", "Fabric SmartBFT, default", "Fabric SmartBFT, tuned"]
cols = [C["grey"], C["lgrey"], C["blue"], C["sky"], C["verm"], C["orange"]]
lat = [base("central", "issue", 100, "lat_mean_ms"), base("jwt", "issue", 100, "lat_mean_ms")] + [fab(o, b, "issue-100tps", "lat_ms_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
wtp = [base("central", "issue", 300, "tp_mean"), base("jwt", "issue", 300, "tp_mean")] + [fab(o, b, "issue-300tps", "tp_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
rtp = [base("central", "verify", 600, "tp_mean"), base("jwt", "verify", 600, "tp_mean")] + [fab(o, b, "verify-600tps", "tp_mean") for o in ("raft", "bft") for b in ("default", "tuned")]
fig, ax = plt.subplots(1, 3, figsize=(6.5, 3.3))
for a, v, t, yl in zip(ax, [lat, wtp, rtp], ["(a) Write latency\nat 100 tx/s", "(b) Write throughput\nat 300 tx/s", "(c) Read throughput\nat 600 tx/s"], ["Mean latency (ms)", "Committed tx/s", "Committed tx/s"]):
    a.bar(range(6), v, color=cols, edgecolor="#333", linewidth=0.4)
    for i, x in enumerate(v): a.text(i, x, f"{x:.0f}", ha="center", va="bottom", fontsize=7.5)
    a.set_xticks([]); a.set_ylabel(yl); panel(a, t); a.set_ylim(0, max(v) * 1.15); a.grid(axis="x", visible=False)
from matplotlib.patches import Patch
fig.legend([Patch(fc=c, ec="#333", lw=0.4) for c in cols], labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.01), fontsize=8)
fig.tight_layout(rect=(0, 0.14, 1, 1)); save(fig, "fig10_baselines_bft.png")
