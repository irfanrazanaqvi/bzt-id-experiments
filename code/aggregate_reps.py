"""Merge repetitions 3-5 (GitHub Actions, fabric-results branch) into data/ and recompute summaries."""
import os, re, glob, shutil, sys
import pandas as pd
src = sys.argv[1]; D = os.path.join(os.path.dirname(__file__), "..", "data")
# --- Raft vs SmartBFT (fabric3)
for p in glob.glob(f"{src}/bft-run-2-*-rep*/fabric_results.csv"):
    m = re.search(r"bft-run-2-(\w+)-(default|tuned)-rep(\d)", p)
    shutil.copy(p, f"{D}/fabric3/runs/{m[1]}-{m[2]}-rep{m[3]}.csv")
rows = []
for p in sorted(glob.glob(f"{D}/fabric3/runs/*.csv")):
    o, b, r = re.match(r"(\w+)-(\w+)-rep(\d)", os.path.basename(p)).groups()
    df = pd.read_csv(p); df["ordering"], df["batch"], df["rep"] = o, b, r; rows.append(df)
a = pd.concat(rows)
g = a.groupby(["ordering", "batch", "Name"], sort=False)
s = g.agg(n_runs=("rep", "nunique"), lat_ms_mean=("Avg Latency (s)", lambda x: round(x.mean()*1000)), lat_min=("Avg Latency (s)", lambda x: round(x.min()*1000)),
          lat_max=("Avg Latency (s)", lambda x: round(x.max()*1000)), tp_mean=("Throughput (TPS)", lambda x: round(x.mean(), 1)), tp_min=("Throughput (TPS)", "min"),
          tp_max=("Throughput (TPS)", "max"), tp_sd=("Throughput (TPS)", lambda x: round(x.std(), 1)), failed=("Fail", "sum"), succ=("Succ", "sum")).reset_index()
s.rename(columns={"Name": "name"}).to_csv(f"{D}/fabric3/fabric3_raft_vs_bft_summary.csv", index=False)
# --- WAN
w = pd.read_csv(f"{D}/wan/wan_runs.csv"); w = w[w.rep <= 2]
for p in glob.glob(f"{src}/wan-run-2-*/fabric_results.csv"):
    m = re.search(r"wan-run-2-(\w+)-d(\d+)-rep(\d)", p)
    df = pd.read_csv(p); df["ordering"], df["one_way_delay_ms"], df["rep"] = m[1], int(m[2]), int(m[3]); w = pd.concat([w, df])
w.to_csv(f"{D}/wan/wan_runs.csv", index=False)
ws = w.groupby(["ordering", "one_way_delay_ms", "Name"], sort=False).agg(n=("rep", "nunique"), lat_ms=("Avg Latency (s)", lambda x: round(x.mean()*1000)),
     lat_min=("Avg Latency (s)", lambda x: round(x.min()*1000)), lat_max=("Avg Latency (s)", lambda x: round(x.max()*1000)),
     tp=("Throughput (TPS)", lambda x: round(x.mean(), 1)), tp_sd=("Throughput (TPS)", lambda x: round(x.std(), 1)), fail=("Fail", "sum")).reset_index()
ws.to_csv(f"{D}/wan/wan_summary.csv", index=False)
# --- Faults
for p in glob.glob(f"{src}/faults-run-3-*-rep*/faults.csv"):
    m = re.search(r"faults-run-3-(\w+)-rep(\d)", p)
    df = pd.read_csv(p); df["ordering"], df["rep"] = m[1], f"rep{m[2]}"; df.to_csv(f"{D}/faults/runs_{m[1]}_rep{m[2]}.csv", index=False)
    shutil.copy(p + ".events", f"{D}/faults/events_{m[1]}_rep{m[2]}.txt")
fr = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{D}/faults/runs_*_rep*.csv"))])
fs = fr.groupby(["ordering", "scenario"], sort=False).agg(runs=("rep", "nunique"), n_tx=("rc", "size"), committed=("rc", lambda x: int((x == 0).sum())),
     median_ms=("latency_ms", "median"), p_max_ms=("latency_ms", "max")).reset_index()
fs.to_csv(f"{D}/faults/fault_injection_summary_5reps.csv", index=False)
# --- RBA multisplit
shutil.copy(f"{src}/rba2-eval-6/rba_multisplit.csv", f"{D}/rba2/rba_multisplit.csv")
print(s.query("Name in ['issue-100tps','issue-150tps','issue-300tps','verify-600tps','audit-200tps']").to_string()); print(ws.to_string()); print(fs.to_string())
