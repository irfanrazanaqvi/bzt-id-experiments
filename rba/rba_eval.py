"""
Evaluate the BZT-ID trust engine's non-biometric factors on the public RBA login data set
(Wiefling et al., doi:10.5281/zenodo.6782156, CC BY 4.0; ACM TOPS 2022, doi:10.1145/3546069).

NOTE: the data set is SYNTHESIZED from real login behaviour (categorical feature statistics kept, IPs, user
agents, timestamps and RTTs randomly generated). It is real-distribution, not raw production data.

Features per login (history = the same user's EARLIER successful logins; rows with no history are dropped):
  geo_new      country not seen before (1.0), else ASN not seen before (0.5), else 0   -> geo_velocity_anomaly
  device_new   device type/OS/browser-name combination not seen before (0/1)            -> 1 - device_posture_score
  asn_rare     1 - percentile of the ASN's global frequency (rare ASN = low reputation) -> 1 - network_reputation
  failed       login attempt failed (0/1)                                               -> behavioural_anomaly
Biometric and time-of-day factors do not exist in this data; the engine's weights are renormalised over the
available factors (fixed nominal weights, no fitting).
Labels: Is Attack IP (known attacker IP) and Is Account Takeover (incident-response label; very few).
usage: python rba_eval.py <rba-dataset.csv> <out_dir>
"""
import sys, os, json, zlib
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

CSV, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
USE = ["Login Timestamp", "User ID", "Country", "ASN", "OS Name and Version", "Browser Name and Version", "Device Type", "Login Successful", "Is Attack IP", "Is Account Takeover"]
def chunks(): return pd.read_csv(CSV, usecols=USE, chunksize=2_000_000, dtype={"Country": "category", "Device Type": "category", "OS Name and Version": "category", "Browser Name and Version": "category"})
MOD = 16
# ---- pass 1: ATO users, global ASN counts, totals
ato_users = set(); asn_cnt = {}; tot = 0; n_attack = 0; n_ato = 0
for c in chunks():
    tot += len(c); n_attack += int(c["Is Attack IP"].sum()); n_ato += int(c["Is Account Takeover"].sum())
    ato_users |= set(c.loc[c["Is Account Takeover"], "User ID"].tolist())
    for k, v in c["ASN"].value_counts().items(): asn_cnt[k] = asn_cnt.get(k, 0) + int(v)
print("pass1", tot, "attackIP rows", n_attack, "ATO rows", n_ato, "ATO users", len(ato_users), flush=True)
# ---- pass 2: keep ~1/16 of users (+ all ATO users)
keep = []
for c in chunks():
    m = (c["User ID"] % MOD == 0) | c["User ID"].isin(ato_users)
    keep.append(c[m])
d = pd.concat(keep, ignore_index=True); del keep
d = d.sort_values(["User ID", "Login Timestamp"], kind="stable").reset_index(drop=True)
d["pos"] = d.groupby("User ID").cumcount()
d["succ"] = d["Login Successful"].astype(bool)
d["dev_key"] = d["Device Type"].astype(str) + "|" + d["OS Name and Version"].astype(str) + "|" + d["Browser Name and Version"].astype(str).str.split(" ").str[0]
print("sample rows", len(d), "users", d["User ID"].nunique(), flush=True)
INF = 10**12
def first_success_pos(keycols):
    p = d["pos"].where(d["succ"], INF)
    return p.groupby([d[k] for k in keycols]).transform("min")
first_user = first_success_pos(["User ID"])
d["has_hist"] = d["pos"] > first_user
f_country = first_success_pos(["User ID", "Country"]); f_asn = first_success_pos(["User ID", "ASN"]); f_dev = first_success_pos(["User ID", "dev_key"])
new_country = d["pos"] <= f_country; new_asn = d["pos"] <= f_asn; new_dev = d["pos"] <= f_dev
d["geo_new"] = np.where(new_country, 1.0, np.where(new_asn, 0.5, 0.0))
d["device_new"] = new_dev.astype(float)
tot_asn = np.array(sorted(asn_cnt.values())); 
d["asn_rare"] = 1.0 - np.searchsorted(tot_asn, d["ASN"].map(asn_cnt).values) / len(tot_asn)
d["failed"] = (~d["succ"]).astype(float)
h = d[d["has_hist"]].copy()
h["y_ip"] = h["Is Attack IP"].astype(int); h["y_ato"] = h["Is Account Takeover"].astype(int)
print("history rows", len(h), "attackIP", int(h.y_ip.sum()), "ATO", int(h.y_ato.sum()), flush=True)
# ---- scores. nominal weights of bzt_id_sim.ZeroTrustEngine: geo .20, device .15, network .15, behavioural .15 (bio .30 and time .05 unavailable)
W = {"geo_new": .20, "device_new": .15, "asn_rare": .15, "failed": .15}
def trust(df, keys):
    w = np.array([W[k] for k in keys]); w = w / w.sum()
    return 1.0 - sum(wi * df[k].values for wi, k in zip(w, keys))     # all four are anomaly-oriented: trust = 1 - weighted anomaly
rows = []
def boot_ci(score, y, B=100, n=200_000, seed=1):
    r = np.random.default_rng(seed); out = []
    idx_all = np.arange(len(y))
    for _ in range(B):
        i = r.choice(idx_all, size=min(n, len(y)), replace=True)
        if y[i].min() == y[i].max(): continue
        out.append(roc_auc_score(y[i], -score[i]))
    return np.percentile(out, [2.5, 97.5]) if out else (np.nan, np.nan)
def rec_at_fpr(score, y, fpr):
    th = np.quantile(score[y == 0], fpr); return float((score[y == 1] <= th).mean())
def evaluate(name, score, label_col, mask=None):
    y = h[label_col].values; s = score
    if mask is not None: y, s = y[mask], s[mask]
    if y.sum() == 0: return
    a = roc_auc_score(y, -s); lo, hi = boot_ci(s, y) if y.sum() > 5 else (np.nan, np.nan)
    rows.append({"label": label_col, "scheme": name, "n": len(y), "positives": int(y.sum()), "AUC": a, "AUC_lo": lo, "AUC_hi": hi,
                 "recall@FPR=1%": rec_at_fpr(s, y, .01), "recall@FPR=5%": rec_at_fpr(s, y, .05), "recall@ALLOW<0.75": float((s[y == 1] < .75).mean()), "FPR@ALLOW<0.75": float((s[y == 0] < .75).mean())})
feat_sets = {"Engine (geo, device, ASN reputation)": ["geo_new", "device_new", "asn_rare"], "Engine (+ failed-login factor)": ["geo_new", "device_new", "asn_rare", "failed"]}
for lab in ["y_ip", "y_ato"]:
    for nm, ks in feat_sets.items(): evaluate(nm, trust(h, ks), lab)
    evaluate("Single rule: new country", 1 - h["geo_new"].clip(upper=1).where(h["geo_new"] == 1, 0).values, lab)
    evaluate("Single rule: new device", 1 - h["device_new"].values, lab)
    evaluate("Single rule: failed login", 1 - h["failed"].values, lab)
# supervised baselines, split by user (80/20), same four features
uid = h["User ID"].values; test = (pd.Series(uid).apply(lambda u: zlib.crc32(str(u).encode()) % 5 == 0)).values
X = h[["geo_new", "device_new", "asn_rare", "failed"]].values
for lab in ["y_ip", "y_ato"]:
    y = h[lab].values
    if y[~test].sum() < 5 or y[test].sum() == 0: continue
    for nm, mk in [("Logistic regression (supervised, user-split)", lambda: LogisticRegression(max_iter=500, class_weight="balanced")), ("Gradient boosting (supervised, user-split)", lambda: HistGradientBoostingClassifier(random_state=0))]:
        m = mk().fit(X[~test], y[~test]); p = m.predict_proba(X[test])[:, 1]; yt = y[test]
        rows.append({"label": lab, "scheme": nm, "n": len(yt), "positives": int(yt.sum()), "AUC": roc_auc_score(yt, p), "AUC_lo": np.nan, "AUC_hi": np.nan,
                     "recall@FPR=1%": float((p[yt == 1] >= np.quantile(p[yt == 0], .99)).mean()), "recall@FPR=5%": float((p[yt == 1] >= np.quantile(p[yt == 0], .95)).mean()), "recall@ALLOW<0.75": np.nan, "FPR@ALLOW<0.75": np.nan})
# ---- learned weights in the engine's own form (trust = 1 - weighted anomaly), fitted on training users only, threshold recalibrated on training users at 5% FPR
from scipy.optimize import nnls
K = ["geo_new", "device_new", "asn_rare", "failed"]
for lab in ["y_ip", "y_ato"]:
    y = h[lab].values
    if y[~test].sum() < 5 or y[test].sum() == 0: continue
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0, positive=True).fit(X[~test], y[~test])
    w = lr.coef_[0]; w = w / w.sum() if w.sum() > 0 else np.ones(4) / 4
    anom_tr = X[~test] @ w; anom_te = X[test] @ w
    th = np.quantile(anom_tr[y[~test] == 0], .95)     # flag if anomaly above the 95th percentile of legitimate training logins
    yt = y[test]
    rows.append({"label": lab, "scheme": "Engine, learned weights + recalibrated threshold (user-split) w=" + "/".join(f"{x:.2f}" for x in w), "n": len(yt), "positives": int(yt.sum()),
                 "AUC": roc_auc_score(yt, anom_te), "AUC_lo": np.nan, "AUC_hi": np.nan, "recall@FPR=1%": float((anom_te[yt == 1] >= np.quantile(anom_tr[y[~test] == 0], .99)).mean()),
                 "recall@FPR=5%": float((anom_te[yt == 1] > th).mean()), "recall@ALLOW<0.75": float((anom_te[yt == 1] > th).mean()), "FPR@ALLOW<0.75": float((anom_te[yt == 0] > th).mean())})
    # fixed-weight engine on the same test users, for a like-for-like comparison, and leave-one-factor-out ablation (fixed weights)
    for nm, ks in [("Engine fixed weights, test users only", K)] + [("Ablation: engine without " + d_, [k for k in K if k != d_]) for d_ in K]:
        sc = trust(h, ks)[test]
        rows.append({"label": lab, "scheme": nm, "n": len(yt), "positives": int(yt.sum()), "AUC": roc_auc_score(yt, -sc), "AUC_lo": np.nan, "AUC_hi": np.nan,
                     "recall@FPR=1%": rec_at_fpr(sc, yt, .01), "recall@FPR=5%": rec_at_fpr(sc, yt, .05), "recall@ALLOW<0.75": float((sc[yt == 1] < .75).mean()), "FPR@ALLOW<0.75": float((sc[yt == 0] < .75).mean())})
res = pd.DataFrame(rows); res.to_csv(os.path.join(OUT, "rba_summary.csv"), index=False); print(res.round(4).to_string())
info = {"rows_total": tot, "attack_ip_rows_total": n_attack, "ato_rows_total": n_ato, "sample_rows": int(len(d)), "sample_users": int(d["User ID"].nunique()), "history_rows": int(len(h)),
        "history_attack_ip": int(h.y_ip.sum()), "history_ato": int(h.y_ato.sum()), "feature_means_attack_vs_legit": {k: [float(h.loc[h.y_ip == 1, k].mean()), float(h.loc[h.y_ip == 0, k].mean())] for k in ["geo_new", "device_new", "asn_rare", "failed"]}}
json.dump(info, open(os.path.join(OUT, "rba_info.json"), "w"), indent=1); print(json.dumps(info, indent=1))
