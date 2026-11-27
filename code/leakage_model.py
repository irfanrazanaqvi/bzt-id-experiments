"""Leakage model for Bitstring Status List revocation with only the list digest and version anchored on the ledger.

Computes, for a national deployment:
  * list geometry (number of 131,072-entry lists) for one or m credential copies per holder;
  * compressed list size versus revoked fraction (gzip level 6, as in e2e/run2.mjs);
  * the timing-correlation anonymity set of a revocation event: an observer who knows that a target was
    revoked within a window of tau seconds, and who sees the anchor history (and can diff the published
    lists), is left with the K other status flips published in the same window; K ~ Poisson(R * w / 86400)
    with w = max(tau, cadence) when anchoring is batched every `cadence` seconds and w = tau when every
    revocation is anchored immediately. We report E[K+1], P(K = 0) (target's index pinned uniquely) and the
    expected Shannon entropy of the target's index, checked by Monte Carlo;
  * the ledger load and RP download volume of fixed-cadence re-anchoring, and the issuance cost of one-time
    (batch) indices.
Outputs data/leakage/leakage_model.json and figures/fig_leakage.{pdf,png}.
"""
import gzip, json, math, os, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'leakage'); os.makedirs(OUT, exist_ok=True)
FIG = os.path.join(HERE, '..', 'figures')
LIST_BITS = 131072                 # W3C Bitstring Status List minimum length
N_HOLDERS = 223.4e6                # NADRA registrations (paper, Section 8.13)
R_PER_DAY = [548, 2000, 10000]     # revocations per day: Italian CIE observed rate (Flamini et al.) and two higher scenarios
BBS_SIGN_MS = 60.0                 # measured mean BBS+ sign time, 10 messages (data/zk/bbs_selective_disclosure.json)
ANCHOR_CEILING_TPS = 238.0         # measured write ceiling, tuned Raft / tuned SmartBFT (Section 8.2)
rng = np.random.default_rng(7); random.seed(7)

res = {'list_bits': LIST_BITS, 'holders': N_HOLDERS}

# 1. geometry
res['lists'] = {m: math.ceil(N_HOLDERS * m / LIST_BITS) for m in (1, 3, 10)}

# 2. compressed size vs revoked fraction (mean of 5 random lists)
sizes = {}
for p in (0.001, 0.005, 0.01, 0.02, 0.05):
    s = []
    for _ in range(5):
        bits = np.zeros(LIST_BITS, dtype=np.uint8)
        idx = rng.choice(LIST_BITS, size=int(round(p * LIST_BITS)), replace=False); bits[idx] = 1
        s.append(len(gzip.compress(np.packbits(bits).tobytes(), compresslevel=6)))
    sizes[p] = round(float(np.mean(s)))
res['gzip_bytes_vs_revoked_fraction'] = sizes

# 3. timing-correlation anonymity set
def anon(R, tau, cadence):
    w = tau if cadence == 0 else max(tau, cadence)
    lam = R * w / 86400.0
    p_unique = math.exp(-lam)
    # expected entropy of the target index among K+1 candidates (uniform), Poisson-weighted
    ks = np.arange(0, int(lam + 12 * math.sqrt(lam + 1) + 20))
    pk = np.exp(-lam + ks * math.log(lam) - np.array([math.lgamma(k + 1) for k in ks])) if lam > 0 else (ks == 0).astype(float)
    H = float(np.sum(pk * np.log2(ks + 1)))
    return {'R_per_day': R, 'tau_s': tau, 'cadence_s': cadence, 'window_s': w, 'expected_candidates': round(lam + 1, 2),
            'p_unique': round(p_unique, 4), 'expected_entropy_bits': round(H, 2)}

taus = [60, 3600, 86400]
cadences = [0, 3600, 86400]
grid = [anon(R, t, c) for R in R_PER_DAY for t in taus for c in cadences]
res['timing_anonymity'] = grid

# Monte Carlo check for the headline cell (R=548/day, tau=60 s, immediate anchoring)
def mc(R, tau, cadence, trials=20000, days=30):
    hits, ent = 0, 0.0
    for _ in range(trials):
        n = rng.poisson(R * days)
        times = rng.uniform(0, days * 86400, n)
        t0 = rng.uniform(days * 86400 * 0.25, days * 86400 * 0.75)        # target's revocation time
        if cadence:
            pub = np.ceil(times / cadence) * cadence; tp = math.ceil(t0 / cadence) * cadence
        else:
            pub = times; tp = t0
        lo = t0 - tau / 2; hi = t0 + tau / 2                                 # attacker's knowledge window
        if cadence:   # attacker can only use publication epochs: any epoch overlapping the window
            elo = math.ceil(lo / cadence) * cadence; ehi = math.ceil(hi / cadence) * cadence
            k = int(np.sum((pub >= elo) & (pub <= ehi)))
        else:
            k = int(np.sum((pub >= lo) & (pub <= hi)))
        hits += (k == 0); ent += math.log2(k + 1)
    return {'R_per_day': R, 'tau_s': tau, 'cadence_s': cadence, 'p_unique_mc': round(hits / trials, 4), 'entropy_bits_mc': round(ent / trials, 2)}
res['monte_carlo'] = [mc(548, 60, 0), mc(548, 3600, 0), mc(548, 60, 86400), mc(548, 3600, 3600)]

# 4. mitigation cost
mit = []
for m in (1, 10):
    L = res['lists'][m]
    for cad in (3600, 86400):
        writes_day = L * 86400 / cad
        mit.append({'copies_per_holder': m, 'lists': L, 'cadence_s': cad, 'anchor_writes_per_day': int(writes_day),
                    'anchor_tps': round(writes_day / 86400, 3), 'share_of_write_ceiling_pct': round(100 * writes_day / 86400 / ANCHOR_CEILING_TPS, 3),
                    'all_lists_gzip_MB_at_1pct': round(L * sizes[0.01] / 1e6, 1),
                    'issuance_cpu_core_hours': round(N_HOLDERS * m * BBS_SIGN_MS / 1000 / 3600)})
res['mitigation_cost'] = mit
json.dump(res, open(os.path.join(OUT, 'leakage_model.json'), 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('lists', 'gzip_bytes_vs_revoked_fraction')}, indent=0))
for g in grid:
    if g['R_per_day'] == 548: print(g)
print(res['monte_carlo']); print(mit)

# figure: P(target index pinned) vs attacker knowledge window, immediate vs batched anchoring
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    try:
        import figstyle; C = figstyle.C
    except Exception:
        C = {'blue': '#0072B2', 'verm': '#D55E00', 'green': '#009E73', 'grey': '#7f7f7f'}
    tau = np.logspace(1, 5, 200)
    fig, ax = plt.subplots(figsize=(7, 2.9))
    for cad, lab, col, ls in [(0, 'anchor each revocation', C['verm'], '-'), (3600, 'hourly epoch', C['blue'], '--'), (86400, 'daily epoch', C['green'], ':')]:
        for R, lw in [(548, 2.2)]:
            w = tau if cad == 0 else np.maximum(tau, cad)
            ax.plot(tau / 60, np.exp(-R * w / 86400), color=col, ls=ls, lw=lw, label=lab)
    ax.set_xscale('log'); ax.set_xlabel("Attacker's knowledge of revocation time (minutes)"); ax.set_ylabel('P(target index pinned)')
    ax.set_ylim(-0.02, 1.02); ax.grid(alpha=.3); ax.legend(frameon=False, loc='upper right')
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_leakage.pdf')); fig.savefig(os.path.join(FIG, 'fig_leakage.png'), dpi=600)
    print('figure written')
except Exception as e:
    print('figure skipped', e)
