"""Summarise the H1/H4 native-network Caliper runs: per operation and offered rate, median (min-max) over repetitions."""
import re, sys, glob, json, statistics as st, os, csv
src = sys.argv[1]; out = sys.argv[2]
rows = {}
for f in sorted(glob.glob(os.path.join(src, 'rep*.log')) + glob.glob(os.path.join(src, 'incl_rep*.log'))):
    seen = set()
    for line in open(f):
        m = re.match(r'^\| (\S+)\s*\| (\d+)\s*\| (\d+)\s*\| ([\d.]+)\s*\| ([\d.]+)\s*\| ([\d.]+)\s*\| ([\d.]+)\s*\| ([\d.]+)\s*\|', line)
        if not m or m.group(1) in seen: continue
        seen.add(m.group(1))
        rows.setdefault(m.group(1), []).append(dict(file=os.path.basename(f), succ=int(m.group(2)), fail=int(m.group(3)), send=float(m.group(4)),
                                                    max_s=float(m.group(5)), avg_s=float(m.group(7)), tps=float(m.group(8))))
summ = []
for k, v in rows.items():
    op, _, rate = k.rpartition('-')
    summ.append(dict(op=op, offered=int(rate) if rate.isdigit() else rate, reps=len(v),
                     tps_median=st.median(r['tps'] for r in v), tps_min=min(r['tps'] for r in v), tps_max=max(r['tps'] for r in v),
                     lat_ms_median=round(1000 * st.median(r['avg_s'] for r in v)), lat_ms_min=round(1000 * min(r['avg_s'] for r in v)), lat_ms_max=round(1000 * max(r['avg_s'] for r in v)),
                     failed=sum(r['fail'] for r in v), submitted=sum(r['succ'] + r['fail'] for r in v)))
summ.sort(key=lambda r: (r['op'], r['offered'] if isinstance(r['offered'], int) else 0))
with open(out, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
for r in summ: print(r)
