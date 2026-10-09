import json, urllib.request
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
for rid in ["mickelbyte/SOCOFing", "ThanhQuy78/socofing"]:
    print("== HF", rid)
    try:
        info = json.loads(get("https://huggingface.co/api/datasets/" + rid))
        print("license/tags:", info.get("cardData", {}).get("license"), info.get("tags", [])[:8], "downloads", info.get("downloads"))
        files = [s["rfilename"] for s in info.get("siblings", [])]
        print(len(files), "files; first 25:", files[:25])
    except Exception as e:
        print("err", e)
print("== maven sourceafis")
try:
    print(get("https://repo1.maven.org/maven2/com/machinezoo/sourceafis/sourceafis/maven-metadata.xml").decode()[:600])
except Exception as e:
    print("err", e)
for u in ["https://csr.lanl.gov/data/auth/", "https://csr.lanl.gov/data/2017/"]:
    print("== ", u)
    try:
        t = get(u).decode(errors="ignore"); import re
        print(re.sub(r"<[^>]+>", " ", t)[:1500]); print(re.findall(r'href="([^"]+)"', t)[:30])
    except Exception as e:
        print("err", e)
