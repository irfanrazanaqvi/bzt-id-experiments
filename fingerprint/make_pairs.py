"""Build genuine / impostor comparison lists from SOCOFing (Shehu et al. 2018, CC BY 4.0).
SOCOFing has ONE real capture per finger plus synthetically altered copies (Easy/Medium/Hard: obliteration, central rotation, z-cut).
Genuine pair = real image vs an altered copy of the SAME finger (a degraded impression, not an independent capture);
impostor pair = real image vs the real image of the same finger type of a DIFFERENT subject.
Subjects are split into disjoint calibration/test halves. usage: make_pairs.py <root> <out.csv> [per_split]"""
import sys, os, re, random, glob, collections
root, out = sys.argv[1], sys.argv[2]; per = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
random.seed(7)
real = {}
for f in glob.glob(os.path.join(root, "**", "Real", "*.BMP"), recursive=True) + glob.glob(os.path.join(root, "**", "real", "*.BMP"), recursive=True):
    m = re.match(r"(\d+)__([MF])_(Left|Right)_(\w+)_finger\.BMP", os.path.basename(f))
    if m: real[(int(m[1]), m[3] + "_" + m[4])] = f
alt = collections.defaultdict(list)
for f in glob.glob(os.path.join(root, "**", "Altered-*", "*.BMP"), recursive=True):
    m = re.match(r"(\d+)__([MF])_(Left|Right)_(\w+)_finger_(\w+)\.BMP", os.path.basename(f))
    d = re.search(r"Altered-(\w+)", f)
    if m and d: alt[(int(m[1]), m[3] + "_" + m[4])].append((d[1], m[5], f))
subs = sorted({k[0] for k in real}); print("real images", len(real), "subjects", len(subs), "altered", sum(len(v) for v in alt.values()))
random.shuffle(subs); half = len(subs) // 2; split = {s: "calibration" for s in subs[:half]}; split.update({s: "test" for s in subs[half:]})
rows = ["split,genuine,kind,imgA,imgB"]
for sp in ["calibration", "test"]:
    keys = [k for k in real if split[k[0]] == sp]
    gk = [k for k in keys if alt.get(k)]
    for _ in range(per):
        k = random.choice(gk); d, t, f = random.choice(alt[k]); rows.append(f"{sp},1,{d}-{t},{real[k]},{f}")
    for _ in range(per):
        k = random.choice(keys); others = [j for j in keys if j[1] == k[1] and j[0] != k[0]]; j = random.choice(others); rows.append(f"{sp},0,impostor,{real[k]},{real[j]}")
open(out, "w").write("\n".join(rows) + "\n"); print("pairs", len(rows) - 1)
