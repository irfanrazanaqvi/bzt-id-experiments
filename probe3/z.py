import sys, json, urllib.parse, urllib.request
for q in ["socofing", "sokoto coventry fingerprint", "keystroke dynamics", "fingerprint"]:
    print("== zenodo", q)
    try:
        u = "https://zenodo.org/api/records?q=" + urllib.parse.quote(q) + "&size=6"
        d = json.load(urllib.request.urlopen(u, timeout=40))
        for h in d["hits"]["hits"]:
            print(h["id"], h["metadata"].get("license", {}).get("id"), h["metadata"]["title"][:90], sum(f["size"] for f in h.get("files", [])) // 1000000, "MB")
    except Exception as e:
        print("err", e)
for q in ["socofing", "fingerprint", "keystroke"]:
    print("== hf", q)
    try:
        d = json.load(urllib.request.urlopen("https://huggingface.co/api/datasets?search=" + q + "&limit=8", timeout=40))
        print([x["id"] for x in d])
    except Exception as e:
        print("err", e)
