"""Extensions of the timing-correlation leakage model (Section 5.2), answering three questions the Poisson model leaves open.

1. Bursty revocations. The Poisson model assumes revocations arrive evenly. We simulate four processes with the same
   long-run mean R (548/day): homogeneous Poisson; office hours only (09-17 on weekdays); day-to-day overdispersion
   (gamma-distributed daily rate, CV = 1); and clustered arrivals (Neyman-Scott: clusters of mean size 4 spread over
   ~5 min). The target is drawn uniformly among revocation events (Palm sampling), so a target inside a burst gets the
   burst's companions. We also condition on a target revoked at 02:00-05:00 under the office-hours process, the case an
   adversary that chooses when to revoke (or knows the target was revoked at night) can exploit.
2. Multi-flip intersection. A position whose status changes more than once (suspension, then reinstatement) is seen in
   two candidate sets. The other candidates survive the intersection only if they too flip in the second epoch.
3. Privacy versus revocation latency. Longer epochs give more cover and a longer window in which a revoked credential is
   still accepted. We also evaluate a k-floor epoch: publish when k real flips have accumulated or after T_max, padding
   with decoy flips of unassigned positions, which guarantees log2(k) bits at bounded latency.
Also runs the Monte Carlo check for every row of Table 3 (the 2,000/day row previously had only the closed form).
Outputs data/leakage/leakage_ext.json and figures/fig_leakage_ext.{pdf,png}.
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'leakage'); os.makedirs(OUT, exist_ok=True)
FIG = os.path.join(HERE, '..', 'figures')
DAY = 86400.0
R0 = 548.0
N_POS = 223.4e6            # one position per holder (lists x 131,072, assigned)
rng = np.random.default_rng(11)
DAYS = 120                 # simulated timeline
res = {'R_mean_per_day': R0, 'days_simulated': DAYS}


def proc_poisson(R, days):
    n = rng.poisson(R * days)
    return np.sort(rng.uniform(0, days * DAY, n))


def proc_office(R, days):
    # all revocations Mon-Fri 09:00-17:00; same long-run mean
    t = []
    for d in range(days):
        if d % 7 in (5, 6):
            continue
        n = rng.poisson(R * 7 / 5)
        t.append(d * DAY + 9 * 3600 + rng.uniform(0, 8 * 3600, n))
    return np.sort(np.concatenate(t))


def proc_overdispersed(R, days, cv=1.0):
    k = 1 / cv ** 2
    t = []
    for d in range(days):
        n = rng.poisson(rng.gamma(k, R / k))
        t.append(d * DAY + rng.uniform(0, DAY, n))
    return np.sort(np.concatenate(t))


def proc_clustered(R, days, mean_size=4.0, spread=300.0):
    nc = rng.poisson(R / mean_size * days)
    centres = rng.uniform(0, days * DAY, nc)
    sizes = rng.geometric(1 / mean_size, nc)
    t = np.repeat(centres, sizes) + rng.exponential(spread, sizes.sum())
    return np.sort(t[t < days * DAY])


def anonymity(times, tau, cadence, targets=20000, target_filter=None):
    """P(pinned) and E[log2(K+1)] for targets drawn among events in the middle of the timeline."""
    T = times[-1]
    mid = np.where((times > 0.2 * T) & (times < 0.8 * T))[0]
    if target_filter is not None:
        mid = mid[target_filter(times[mid])]
    idx = rng.choice(mid, size=min(targets, len(mid)), replace=len(mid) < targets)
    t0 = times[idx]
    if cadence == 0:
        lo, hi = t0 - tau / 2, t0 + tau / 2
    else:                                   # epochs overlapping the observer's window
        lo = np.floor((t0 - tau / 2) / cadence) * cadence
        hi = np.ceil((t0 + tau / 2) / cadence) * cadence
        hi = np.maximum(hi, lo + cadence)
    k = np.searchsorted(times, hi, 'right') - np.searchsorted(times, lo, 'left') - 1
    return {'p_pin': round(float(np.mean(k == 0)), 4), 'H_bits': round(float(np.mean(np.log2(k + 1))), 2),
            'median_candidates': int(np.median(k + 1))}


# 1. burstiness
procs = {'poisson': proc_poisson, 'office_hours': proc_office, 'overdispersed_cv1': proc_overdispersed, 'clustered_m4': proc_clustered}
sims = {name: f(R0, DAYS) for name, f in procs.items()}
night = lambda t: ((t % DAY) >= 2 * 3600) & ((t % DAY) < 5 * 3600)
burst = []
for name, times in sims.items():
    for tau, cad in [(60, 0), (60, 3600), (60, 86400), (3600, 0)]:
        burst.append({'process': name, 'tau_s': tau, 'cadence_s': cad, **anonymity(times, tau, cad)})
# night-time target: office-hours process has no night revocations, so model a night revocation as an extra event
off = sims['office_hours']
for tau, cad in [(60, 0), (60, 3600), (60, 86400)]:
    T = off[-1]; days = np.arange(int(0.2 * T / DAY), int(0.8 * T / DAY))
    days = days[days % 7 < 5]
    t0 = days * DAY + 3 * 3600 + rng.uniform(0, 3600, len(days))
    if cad == 0:
        lo, hi = t0 - tau / 2, t0 + tau / 2
    else:
        lo = np.floor((t0 - tau / 2) / cad) * cad; hi = np.maximum(np.ceil((t0 + tau / 2) / cad) * cad, lo + cad)
    k = np.searchsorted(off, hi, 'right') - np.searchsorted(off, lo, 'left')
    burst.append({'process': 'office_hours_night_target', 'tau_s': tau, 'cadence_s': cad,
                  'p_pin': round(float(np.mean(k == 0)), 4), 'H_bits': round(float(np.mean(np.log2(k + 1))), 2),
                  'median_candidates': int(np.median(k + 1))})
res['burstiness'] = burst

# 2. multi-flip intersection (suspension then reinstatement of the same position)
multi = []
for R in (548, 2000, 10000):
    for cad in (3600, 86400):
        lam = R * cad / DAY                         # other flips in the target's epoch
        p_again = lam / N_POS                       # chance a given other candidate also flips in the second epoch
        exp_others = lam * p_again
        multi.append({'R_per_day': R, 'cadence_s': cad, 'candidates_after_first_flip': round(lam + 1, 1),
                      'expected_other_candidates_after_second_flip': float('%.3g' % exp_others),
                      'p_pin_after_second_flip': round(math.exp(-exp_others), 4)})
res['multi_flip'] = multi

# 3. privacy vs revocation latency
cads = np.unique(np.round(np.logspace(np.log10(60), np.log10(DAY), 25)))
pl = []
for R in (548, 2000, 10000):
    for c in cads:
        lam = R * max(60, c) / DAY
        ks = np.arange(0, int(lam + 12 * math.sqrt(lam + 1) + 20))
        pk = np.exp(-lam + ks * math.log(lam) - np.array([math.lgamma(k + 1) for k in ks]))
        pl.append({'R_per_day': R, 'cadence_s': float(c), 'mean_latency_s': float(c / 2), 'max_latency_s': float(c),
                   'H_bits_tau60': round(float(np.sum(pk * np.log2(ks + 1))), 3),
                   'exposure_credential_hours_per_day': round(R * c / 2 / 3600, 1)})
res['privacy_latency'] = pl
# k-floor epochs with decoys: latency for the target = time until k flips accumulate (capped by T_max)
kf = []
for name in ('poisson', 'office_hours'):
    times = sims[name]
    for k in (16, 32, 128):
        for tmax in (3600, 4 * 3600, DAY):
            # epoch boundaries: walk the timeline
            bounds, last, cnt = [], 0.0, 0
            i = 0
            n = len(times)
            while i < n:
                j = min(i + k - 1, n - 1)
                end = times[j] if (j - i + 1) == k else None
                if end is not None and end - last <= tmax:
                    bounds.append(end); last = end; i = j + 1
                else:
                    last = last + tmax; bounds.append(last); i = np.searchsorted(times, last, 'right')
            bounds = np.array(bounds)
            real = np.diff(np.concatenate([[0], np.searchsorted(times, bounds, 'right')]))
            decoys = np.maximum(0, k - real)
            e = np.searchsorted(bounds, times, 'left'); e = e[e < len(bounds)]
            lat = bounds[e] - times[:len(e)]
            kf.append({'process': name, 'k': k, 'T_max_s': tmax, 'guaranteed_bits': round(math.log2(k), 1),
                       'mean_latency_min': round(float(np.mean(lat)) / 60, 1), 'p95_latency_min': round(float(np.percentile(lat, 95)) / 60, 1),
                       'epochs_per_day': round(float(len(bounds) / (times[-1] / DAY)), 1),
                       'decoy_epochs_pct': round(float(100 * np.mean(decoys > 0)), 1),
                       'decoys_per_day': round(float(decoys.sum() / (times[-1] / DAY)), 1)})
res['k_floor'] = kf

# 4. Monte Carlo for every Table 3 row (homogeneous Poisson)
t3 = []
for R, tau, cad in [(548, 60, 0), (548, 60, 3600), (548, 60, 86400), (2000, 60, 0), (10000, 60, 0), (10000, 60, 86400),
                    (548, 3600, 0), (548, 3600, 3600), (548, 3600, 86400)]:
    times = proc_poisson(R, 40 if R > 2000 else DAYS)
    t3.append({'R_per_day': R, 'tau_s': tau, 'cadence_s': cad, **anonymity(times, tau, cad)})
res['table3_monte_carlo'] = t3

json.dump(res, open(os.path.join(OUT, 'leakage_ext.json'), 'w'), indent=1)
for b in burst: print(b)
for m in multi: print(m)
for r in t3: print(r)
for r in kf: print(r)

# figure: (a) P(pin) by arrival process; (b) entropy vs mean latency
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    import sys; sys.path.insert(0, HERE)
    try:
        import figstyle; figstyle.setup(); C = figstyle.C
    except Exception:
        C = {'blue': '#0072B2', 'verm': '#D55E00', 'green': '#009E73', 'grey': '#7f7f7f'}
    plt.rcParams['pdf.fonttype'] = 42
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 3.0))
    labels = {'poisson': 'Poisson', 'office_hours': 'Office\nhours', 'overdispersed_cv1': 'Over-\ndispersed', 'clustered_m4': 'Clustered', 'office_hours_night_target': 'Night\ntarget'}
    cells = [(60, 0, 'per revocation'), (60, 3600, 'hourly'), (60, 86400, 'daily')]
    x = np.arange(len(labels)); wdt = 0.26
    cols = [C['verm'], C['blue'], C['green']]
    for j, (tau, cad, lab) in enumerate(cells):
        ys = [next(r['H_bits'] for r in burst if r['process'] == p and r['tau_s'] == tau and r['cadence_s'] == cad) for p in labels]
        a.bar(x + (j - 1) * wdt, ys, wdt, color=cols[j], label=lab)
    a.set_xticks(x); a.set_xticklabels(labels.values()); a.set_ylabel('Residual entropy H (bits)')
    figstyle.panel(a, '(a) Arrival process'); a.set_ylim(0, 12.5); a.legend(frameon=False, ncol=3, loc='upper left', fontsize=9, handlelength=1.2, columnspacing=0.8); a.grid(axis='y', alpha=.3)
    for R, ls in [(548, '-'), (2000, '--'), (10000, ':')]:
        rows = [r for r in pl if r['R_per_day'] == R]
        b.plot([r['mean_latency_s'] / 60 for r in rows], [r['H_bits_tau60'] for r in rows], ls=ls, color=C['blue'], label=f'R = {R:,}/day')
    b.set_xscale('log'); b.set_xticks([1, 10, 100, 1000]); b.set_xticklabels(['1', '10', '100', '1,000']); b.set_xlabel('Mean revocation latency (min)'); b.set_ylabel('Residual entropy H (bits)')
    figstyle.panel(b, '(b) Privacy against latency'); b.legend(frameon=False); b.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_leakage_ext.pdf')); fig.savefig(os.path.join(FIG, 'fig_leakage_ext.png'), dpi=600)
    print('figure written')
except Exception as e:
    print('figure skipped', e)
