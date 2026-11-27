"""Batch-cut latency model for Fabric Raft ordering, calibrated on one batching configuration and
validated on another (data/fabric3/fabric3_raft_vs_bft_summary.csv, Caliper fixed-rate load).

Model: a transaction's commit latency = batching wait w + endorsement/commit constant c0 + v * (b + 1) / 2,
where blocks are cut after B transactions or T after the first transaction of the block (Raft BatchTimeout),
b is the mean block size, and v is the per-transaction validation/commit time inside a block (transactions
of a block are validated in sequence). w and b are computed exactly for fixed-rate arrivals.
c0 and v are fitted by least squares on the default configuration (B=10, T=2 s); the fitted model then
predicts the tuned configuration (B=100, T=200 ms) without refitting. Points at or above the measured
saturation (300 tx/s offered) are excluded.
Writes data/capacity/capacity_model.json.
"""
import json, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'data')
OUT = os.path.join(D, 'capacity'); os.makedirs(OUT, exist_ok=True)
df = pd.read_csv(os.path.join(D, 'fabric3', 'fabric3_raft_vs_bft_summary.csv'))
CFG = {'default': (10, 2.0), 'tuned': (100, 0.2)}

def batch_stats(lam, B, T, n=20000):
    t = np.arange(n) / lam; waits = np.empty(n); sizes = []; i = 0
    while i < n:
        t0 = t[i]; cut = t0 + T
        j = i
        while j < n and j - i < B and t[j] <= cut: j += 1
        cut_time = t[j - 1] if j - i == B else cut
        waits[i:j] = cut_time - t[i:j]; sizes.append(j - i); i = j
    return waits[n // 10:].mean() * 1000, float(np.mean(sizes[len(sizes) // 10:]))

rows = []
for cfg, (B, T) in CFG.items():
    for wl in ('issue', 'audit'):
        sub = df[(df.ordering == 'raft') & (df.batch == cfg) & df.name.str.startswith(wl + '-')]
        for _, r in sub.iterrows():
            lam = float(r['name'].split('-')[1].replace('tps', ''))
            if lam >= 300: continue
            w, b = batch_stats(lam, B, T)
            rows.append({'cfg': cfg, 'workload': wl, 'offered_tps': lam, 'measured_ms': float(r.lat_ms_mean), 'wait_ms': w, 'block_size': b})
R = pd.DataFrame(rows)
tr = R[R.cfg == 'default']
A = np.c_[np.ones(len(tr)), (tr.block_size + 1) / 2]
(c0, v), *_ = np.linalg.lstsq(A, tr.measured_ms - tr.wait_ms, rcond=None)
R['predicted_ms'] = R.wait_ms + c0 + v * (R.block_size + 1) / 2
R['abs_err_pct'] = 100 * (R.predicted_ms - R.measured_ms).abs() / R.measured_ms
summ = {'c0_ms': round(float(c0), 1), 'v_ms_per_tx': round(float(v), 2),
        'fit_mape_pct_default': round(float(R[R.cfg == 'default'].abs_err_pct.mean()), 1),
        'validation_mape_pct_tuned': round(float(R[R.cfg == 'tuned'].abs_err_pct.mean()), 1),
        'validation_max_err_pct_tuned': round(float(R[R.cfg == 'tuned'].abs_err_pct.max()), 1)}

# national-scale write load (Section 8.13 assumptions) and the effect of batching audit records
peak_checks = 710.0; issuance_peak = 18.0; ceiling = 238.0
scen = []
for name, audit_tps in [('audit record per verification', peak_checks),
                        ('Merkle root per RP gateway every 1 s (100 gateways)', 100.0),
                        ('Merkle root per RP gateway every 10 s (100 gateways)', 10.0)]:
    lam = issuance_peak + audit_tps
    ok = lam < 0.85 * ceiling
    if ok:
        w, b = batch_stats(lam, *CFG['tuned']); pred = w + c0 + v * (b + 1) / 2
    else:
        pred = None
    scen.append({'scenario': name, 'write_tps': lam, 'utilisation_of_measured_ceiling': round(lam / ceiling, 2),
                 'predicted_latency_ms_tuned': None if pred is None else round(pred)})
out = {'model': summ, 'points': R.round(1).to_dict('records'), 'national_scenarios': scen}
json.dump(out, open(os.path.join(OUT, 'capacity_model.json'), 'w'), indent=1)
print(summ); print(R.round(1).to_string()); print(scen)
