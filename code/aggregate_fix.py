"""Correct the SmartBFT batch labels and add the corrected tuned runs and the end-to-end flow.
The first SmartBFT 'tuned' runs edited configtx/configtx.yaml, but the BFT network reads bft-config/configtx.yaml,
so those runs used the default SmartBFT configuration; they are relabelled default (reps 6-10).
usage: python3 aggregate_fix.py <fabric-results checkout>"""
import os, re, glob, shutil, sys, json, subprocess
import pandas as pd
src = sys.argv[1]; H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "..", "data"); R = os.path.join(D, "fabric3", "runs")
for r in range(1, 6):
    a, b = f"{R}/bft-tuned-rep{r}.csv", f"{R}/bft-default-rep{r + 5}.csv"
    if os.path.exists(a) and not os.path.exists(b): subprocess.run(["git", "mv", a, b], check=True)
for p in glob.glob(f"{src}/bft-run-*-bft-tunedfix-rep*/fabric_results.csv"):
    rep = re.search(r"rep(\d+)", p)[1]; shutil.copy(p, f"{R}/bft-tuned-rep{rep}.csv")
    shutil.copy(os.path.join(os.path.dirname(p), "batch_config.txt"), f"{D}/fabric3/batch_config_bft_tuned_rep{rep}.txt")
with open(f"{D}/fabric3/BATCH_NOTE.txt", "w") as f:
    f.write(__doc__.split("usage:")[0].strip() + "\nbft-tuned-rep1..5 are the corrected runs (BatchTimeout 200ms, MaxMessageCount 100 in bft-config/configtx.yaml).\n")
rows = []
for p in sorted(glob.glob(f"{R}/*.csv")):
    o, b, r = re.match(r"(\w+)-(\w+)-rep(\d+)", os.path.basename(p)).groups()
    df = pd.read_csv(p); df["ordering"], df["batch"], df["rep"] = o, b, r; rows.append(df)
a = pd.concat(rows)
s = a.groupby(["ordering", "batch", "Name"], sort=False).agg(n_runs=("rep", "nunique"), lat_ms_mean=("Avg Latency (s)", lambda x: round(x.mean()*1000)),
    lat_min=("Avg Latency (s)", lambda x: round(x.min()*1000)), lat_max=("Avg Latency (s)", lambda x: round(x.max()*1000)),
    tp_mean=("Throughput (TPS)", lambda x: round(x.mean(), 1)), tp_min=("Throughput (TPS)", "min"), tp_max=("Throughput (TPS)", "max"),
    tp_sd=("Throughput (TPS)", lambda x: round(x.std(), 1)), failed=("Fail", "sum"), succ=("Succ", "sum")).reset_index().rename(columns={"Name": "name"})
s.to_csv(f"{D}/fabric3/fabric3_raft_vs_bft_summary.csv", index=False)
tot = a.groupby(["ordering", "batch"]).agg(failed=("Fail", "sum"), succ=("Succ", "sum"), runs=("rep", "nunique")).reset_index()
tot["submitted"] = tot.failed + tot.succ; tot.to_csv(f"{D}/fabric3/fabric3_failures.csv", index=False)
print(s[s.name.isin(["issue-10tps", "issue-100tps", "issue-150tps", "issue-300tps", "verify-600tps"])].to_string()); print(tot.to_string())
# ---- end-to-end flow
E2 = f"{D}/e2e"; os.makedirs(E2, exist_ok=True); recs = []
for p in glob.glob(f"{src}/e2e-run-*-*-rep*/e2e_*.json"):
    m = re.search(r"e2e-run-\d+-(\w+)-rep(\d+)/e2e_(\w+)\.json", p); o, rep, mode = m[1], int(m[2]), m[3]
    shutil.copy(p, f"{E2}/{o}_rep{rep}_{mode}.json"); j = json.load(open(p))
    base = dict(ordering=o, rep=rep, mode=mode, flows=j["flows"], concurrency=j["concurrency"], wall_s=j["wall_s"], flows_per_s=j["completed_flows_per_s"],
                failures=sum(j["failures"].values()), revoke_ok=json.dumps(j.get("revocation_check", {})))
    for k, v in j["steps"].items():
        if v: recs.append({**base, "step": k, "mean_ms": v["mean_ms"], "p50_ms": v["p50_ms"], "p95_ms": v["p95_ms"], "n": v["n"]})
e = pd.DataFrame(recs); e.to_csv(f"{E2}/e2e_runs.csv", index=False)
es = e.groupby(["ordering", "mode", "step"]).agg(reps=("rep", "nunique"), mean_ms=("mean_ms", "mean"), mean_min=("mean_ms", "min"), mean_max=("mean_ms", "max"),
     p95_ms=("p95_ms", "mean"), flows_per_s=("flows_per_s", "mean"), fps_min=("flows_per_s", "min"), fps_max=("flows_per_s", "max"), failures=("failures", "sum")).round(2).reset_index()
es.to_csv(f"{E2}/e2e_summary.csv", index=False); print(es.to_string()); print(e[["ordering", "rep", "mode", "revoke_ok"]].drop_duplicates().to_string())
