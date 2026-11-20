"""Statistical treatment of the headline performance comparisons (paper, Sections 7-8).
Per configuration: mean with a 95% t-interval over independent runs; between configurations:
two-sided Welch t-test and Mann-Whitney U test. Output: data/stats_tests.csv"""
import os, glob, pandas as pd, numpy as np
from scipy import stats
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
def runs(cfg, name, col="Throughput (TPS)"):
    v = []
    for f in sorted(glob.glob(f"{D}/fabric3/runs/{cfg}-rep*.csv")):
        r = pd.read_csv(f); r = r[r.Name == name]
        if len(r): v.append(float(r[col].iloc[0]) * (1000 if "Latency" in col else 1))
    return np.array(v)
def ci(v): m = v.mean(); h = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v)); return m, m - h, m + h
rows = []
def cmp(label, a, b, la, lb, unit):
    ma, la_, ua = ci(a); mb, lb_, ub = ci(b)
    t = stats.ttest_ind(a, b, equal_var=False); u = stats.mannwhitneyu(a, b, alternative="two-sided")
    rows.append(dict(comparison=label, a=la, n_a=len(a), mean_a=ma, ci_a=f"{la_:.1f}-{ua:.1f}", b=lb, n_b=len(b), mean_b=mb, ci_b=f"{lb_:.1f}-{ub:.1f}", unit=unit,
                     welch_p=t.pvalue, mannwhitney_p=u.pvalue))
cmp("Write throughput at 300 tx/s offered", runs("bft-tuned", "issue-300tps"), runs("raft-tuned", "issue-300tps"), "SmartBFT tuned", "Raft tuned", "tx/s")
cmp("Write throughput at 300 tx/s offered", runs("bft-default", "issue-300tps"), runs("raft-default", "issue-300tps"), "SmartBFT default", "Raft default", "tx/s")
cmp("Write throughput at 300 tx/s offered", runs("bft-tuned", "issue-300tps"), runs("bft-default", "issue-300tps"), "SmartBFT tuned", "SmartBFT default", "tx/s")
cmp("Write latency at 100 tx/s", runs("bft-tuned", "issue-100tps", "Avg Latency (s)"), runs("raft-tuned", "issue-100tps", "Avg Latency (s)"), "SmartBFT tuned", "Raft tuned", "ms")
o = pd.read_csv(f"{D}/org3/org3_runs.csv")
g = lambda p, c: o[o.policy == p][c].values.astype(float)
cmp("Closed-loop write throughput", g("org3and", "load_tx_per_s"), g("org2and", "load_tx_per_s"), "AND of 3 orgs", "AND of 2 orgs", "tx/s")
cmp("Closed-loop write throughput", g("org3of2", "load_tx_per_s"), g("org2and", "load_tx_per_s"), "2 of 3 orgs", "AND of 2 orgs", "tx/s")
cmp("Loaded write latency", g("org3and", "load_mean_ms"), g("org2and", "load_mean_ms"), "AND of 3 orgs", "AND of 2 orgs", "ms")
w = pd.read_csv(f"{D}/wan/wan_runs.csv")
print(w.columns.tolist()[:20])
R = pd.DataFrame(rows); R.to_csv(f"{D}/stats_tests.csv", index=False)
pd.set_option("display.width", 250); print(R.round(4).to_string())
