"""List the BB-MAS zip structure (folder -> file counts and sizes) and print the first lines of one small file per kind. Publishes no data rows beyond column headers + 2 rows."""
import sys, zipfile, collections, re
z = zipfile.ZipFile(sys.argv[1]); out = sys.argv[2]
info = z.infolist(); print("entries", len(info))
agg = collections.defaultdict(lambda: [0, 0])
for i in info:
    if i.is_dir(): continue
    parts = i.filename.split("/")
    key = "/".join(re.sub(r"\d+", "N", p) for p in parts[:-1]) + "/" + re.sub(r"\d+", "N", parts[-1])
    agg[key][0] += 1; agg[key][1] += i.file_size
with open(out + "/pattern_summary.txt", "w") as f:
    for k, (n, s) in sorted(agg.items(), key=lambda x: -x[1][1]):
        f.write(f"{n:6d} files {s/1e6:10.1f} MB  {k}\n")
print(open(out + "/pattern_summary.txt").read()[:5000])
seen = set()
with open(out + "/schema_samples.txt", "w") as f:
    for i in info:
        if i.is_dir(): continue
        key = re.sub(r"\d+", "N", i.filename)
        if key in seen or i.file_size > 50_000_000 and not i.filename.lower().endswith((".csv", ".txt")): continue
        seen.add(key)
        if len(seen) > 40: break
        if i.filename.lower().endswith((".csv", ".txt", ".md")):
            with z.open(i) as fh:
                lines = [fh.readline().decode(errors="ignore").rstrip()[:300] for _ in range(3)]
            f.write("== " + i.filename + f" ({i.file_size/1e6:.1f} MB)\n" + "\n".join(lines) + "\n")
for i in info:
    if "readme" in i.filename.lower() and i.filename.lower().endswith((".txt", ".md")):
        open(out + "/readme_" + i.filename.split("/")[-1], "wb").write(z.read(i))
