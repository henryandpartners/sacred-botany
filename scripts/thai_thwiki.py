#!/usr/bin/env python3
"""Thai Wikipedia search for all species -> article titles (often Thai names)."""
import json, re, requests, time

UA = {"User-Agent": "SacredBotany-ThaiLookup/1.0 (ethnobotanical research; one-off search batch)"}
BASE = "/tmp/thai_lookup"
plants = json.load(open(f"{BASE}/plants.json"))
out = {}

def thwiki(q, n=5):
    for a in range(5):
        try:
            r = requests.get("https://th.wikipedia.org/w/api.php", params={
                "action":"query","format":"json","list":"search","srsearch":q,"srlimit":str(n)},
                headers=UA, timeout=20)
            if "too many" in r.text.lower():
                time.sleep(25 + 15*a); continue
            return r.json().get("query",{}).get("search",[])
        except Exception:
            time.sleep(10 + 8*a)
    return None

for i, p in enumerate(plants):
    res = thwiki(p["sci"])
    if res is None:
        res = thwiki(p["name"])
    out[p["id"]] = [{"t": h["title"], "s": h.get("snippet","")} for h in (res or [])]
    if (i+1) % 25 == 0:
        print(f"tw {i+1}/{len(plants)}", flush=True)
    with open(f"{BASE}/thwiki.json", "w") as f:
        json.dump(out, f)
    time.sleep(1.2)

with open(f"{BASE}/thwiki.json", "w") as f:
    json.dump(out, f, indent=1)
print("DONE thwiki:", len(out))
