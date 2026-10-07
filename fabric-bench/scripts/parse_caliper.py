#!/usr/bin/env python3
"""Parse the Caliper summary table(s) from a log into a tidy CSV.
usage: parse_caliper.py caliper.log out.csv
Columns follow Caliper's header names (Name, Succ, Fail, Send Rate (TPS), latencies, Throughput (TPS))."""
import csv, re, sys

def parse(text):
    rows, header = [], None
    for line in text.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)          # strip ANSI colours
        m = re.search(r"(\|.*\|)\s*$", line)                 # drop log-prefix noise
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).strip("|").split("|")]
        if len(cells) < 6 or set("".join(cells)) <= set("-: "):
            continue
        if cells[0].lower() == "name":
            header = cells
            continue
        if header and len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return header, rows

if __name__ == "__main__":
    text = open(sys.argv[1], errors="replace").read()
    header, rows = parse(text)
    if not rows:
        sys.exit("no Caliper result rows found in log")
    seen, uniq = set(), []
    for r in rows:                                           # same table can be printed twice
        k = tuple(r.values())
        if k not in seen:
            seen.add(k); uniq.append(r)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader(); w.writerows(uniq)
    print(f"parsed {len(uniq)} rounds -> {sys.argv[2]}")
