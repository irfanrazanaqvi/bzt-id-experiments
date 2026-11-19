"""Aggregate the v2 end-to-end, three-organization endorsement and Indy baseline runs.
usage: python aggregate_v2.py <fabric-results worktree>   -> data/e2e2/, data/org3/, data/indy/ (raw JSON + summary CSVs)"""
import sys, os, glob, json, shutil, re
import pandas as pd, numpy as np
FR = sys.argv[1]; D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
def mmm(v): v = [x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))]; return (np.mean(v), np.min(v), np.max(v)) if v else (np.nan,) * 3
# ---- e2e v2
out = os.path.join(D, "e2e2"); os.makedirs(out, exist_ok=True); runs = []
for f in sorted(glob.glob(f"{FR}/e2e2-run-*/e2e2_*.json")):
    run = f.split("/")[-2]; dst = os.path.join(out, run); os.makedirs(dst, exist_ok=True); shutil.copy(f, dst)
    for extra in ["system.txt", "batch_config.txt"]:
        p = os.path.join(os.path.dirname(f), extra)
        if os.path.exists(p): shutil.copy(p, dst)
    j = json.load(open(f)); m = re.search(r"-(bft|raft)-rep(\d)", run); r = {"ordering": m.group(1), "rep": int(m.group(2)), "workers": j["workers"], "conc_per_worker": j["concurrency_per_worker"],
        "flows": j["flows"], "flows_per_s": j["completed_flows_per_s"], "cpu": j["host"]["cpu_model"], "failures": sum(j["failures"].values()), **{f"dec_{k}": v for k, v in j["decisions"].items()},
        **{f"rev_{k}": v for k, v in j["revocation_check"].items() if not isinstance(v, dict)}, "rev_1pct_hash_gunzip_ms": j["revocation_check"].get("list_1pct_hash_gunzip", {}).get("mean_ms")}
    for k, s in j["steps"].items():
        if s: r[f"{k}_mean"] = s["mean_ms"]; r[f"{k}_p95"] = s["p95_ms"]
    runs.append(r)
E = pd.DataFrame(runs); E.to_csv(os.path.join(out, "e2e2_runs.csv"), index=False)
num = E.select_dtypes("number").columns.drop(["rep", "workers", "conc_per_worker"])
S = E.groupby(["ordering", "workers", "conc_per_worker"])[list(num)].agg(["mean", "min", "max"]); S.columns = ["_".join(c) for c in S.columns]
S["reps"] = E.groupby(["ordering", "workers", "conc_per_worker"]).size(); S.reset_index().to_csv(os.path.join(out, "e2e2_summary.csv"), index=False)
# ---- org3 endorsement
out = os.path.join(D, "org3"); os.makedirs(out, exist_ok=True); rows = []
for d_ in sorted(glob.glob(f"{FR}/org3-run-*")):
    m = re.search(r"-(org2and|org3and|org3of2)-rep(\d)", d_); dst = os.path.join(out, os.path.basename(d_)); os.makedirs(dst, exist_ok=True)
    for f in ["endorse_seq.json", "endorse_load.json", "e2e2_w2.json", "policy.txt", "system.txt", "containers.txt", "org3_lifecycle.log"]:
        if os.path.exists(os.path.join(d_, f)): shutil.copy(os.path.join(d_, f), dst)
    try: s = json.load(open(f"{d_}/endorse_seq.json")); l = json.load(open(f"{d_}/endorse_load.json")); e = json.load(open(f"{d_}/e2e2_w2.json"))
    except Exception as ex: print("skip", d_, ex); continue
    rows.append({"policy": m.group(1), "rep": int(m.group(2)), "seq_mean_ms": s["latency"]["mean_ms"], "seq_p95_ms": s["latency"]["p95_ms"], "load_tx_per_s": l["tx_per_s"],
                 "load_mean_ms": l["latency"]["mean_ms"], "load_p95_ms": l["latency"]["p95_ms"], "load_failed": l["submitted"] - l["committed"], "e2e_w2_flows_per_s": e["completed_flows_per_s"],
                 "e2e_issue_commit_ms": e["steps"]["issue_ledger_commit"]["mean_ms"], "e2e_audit_allow_ms": e["steps"]["audit_commit_ALLOW"]["mean_ms"]})
O = pd.DataFrame(rows); O.to_csv(os.path.join(out, "org3_runs.csv"), index=False)
OS = O.groupby("policy").agg(["mean", "min", "max"]).drop(columns="rep"); OS.columns = ["_".join(c) for c in OS.columns]; OS["reps"] = O.groupby("policy").size()
OS.reset_index().to_csv(os.path.join(out, "org3_summary.csv"), index=False)
# ---- Indy
out = os.path.join(D, "indy"); os.makedirs(out, exist_ok=True); rows = []
for d_ in sorted(glob.glob(f"{FR}/indy-run-*")):
    dst = os.path.join(out, os.path.basename(d_)); os.makedirs(dst, exist_ok=True)
    for f in ["indy_bench.json", "system.txt", "von_network_commit.txt", "containers.txt", "genesis.txn"]:
        if os.path.exists(os.path.join(d_, f)): shutil.copy(os.path.join(d_, f), dst)
    if not os.path.exists(f"{d_}/indy_bench.json"): print("skip", d_); continue
    j = json.load(open(f"{d_}/indy_bench.json"))
    for kind in ["writes", "reads"]:
        for p in j[kind]: rows.append({"run": os.path.basename(d_), "op": kind, "concurrency": p["concurrency"], "submitted": p["submitted"], "ok": p["ok"], "tx_per_s": p["tx_per_s"],
                                       "mean_ms": p["latency"]["mean_ms"] if p["latency"] else np.nan, "p95_ms": p["latency"]["p95_ms"] if p["latency"] else np.nan})
if rows:
    I = pd.DataFrame(rows); I.to_csv(os.path.join(out, "indy_runs.csv"), index=False)
    IS = I.groupby(["op", "concurrency"])[["tx_per_s", "mean_ms", "p95_ms", "ok", "submitted"]].agg(["mean", "min", "max"]); IS.columns = ["_".join(c) for c in IS.columns]
    IS.reset_index().to_csv(os.path.join(out, "indy_summary.csv"), index=False); print(IS.round(1).to_string())
pd.set_option("display.width", 250); print(S.reset_index().filter(regex="ordering|workers|flows_per_s|total_|reps|fail").round(1).to_string()); print(OS.round(1).to_string())
