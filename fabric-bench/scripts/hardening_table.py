"""LaTeX table for Section 8 (hardened chaincode) from data/hardening/hardening_summary.csv."""
import csv, sys
rows = {(r['op'], r['offered']): r for r in csv.DictReader(open(sys.argv[1]))}
def cell(op, rate):
    r = rows.get((op, str(rate)))
    if not r: return '--'
    return f"{float(r['tps_median']):.0f} / {int(r['lat_ms_median'])}"
lines = []
for rate in [50, 100, 150, 200, 250, 300]:
    lines.append(f"{rate} & {cell('issueS', rate)} & {cell('issueH', rate)} & {cell('auditP', rate)}\\\\")
fails = {op: (sum(int(r['failed']) for k, r in rows.items() if k[0] == op), sum(int(r['submitted']) for k, r in rows.items() if k[0] == op)) for op in ('issueS', 'issueH', 'auditP', 'anchor')}
lines.append('\\midrule')
lines.append('Failed / submitted & ' + ' & '.join(f"{fails[o][0]:,} / {fails[o][1]:,}" for o in ('issueS', 'issueH', 'auditP')) + '\\\\')
print('\n'.join(lines))
print('% anchor:', [(k[1], rows[k]['tps_median'], rows[k]['lat_ms_median']) for k in rows if k[0] == 'anchor'], fails['anchor'])
print('% inclusion:', [(k[1], rows[k]['tps_median'], rows[k]['lat_ms_median'], rows[k]['failed']) for k in rows if k[0] == 'inclusion'])
