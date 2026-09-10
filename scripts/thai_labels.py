#!/usr/bin/env python3
import json, re, requests, time

UA = {"User-Agent": "SacredBotany-ThaiLookup/1.0 (ethnobotanical research; one-off bulk label fetch)"}
BASE = "/tmp/thai_lookup"
qids = json.load(open(f"{BASE}/qids.json"))

# map qid -> list of species ids
byq = {}
for pid, info in qids.items():
    if info.get("qid"):
        byq.setdefault(info["qid"], []).append(pid)
qids_list = list(byq.keys())
print(f"{len(qids_list)} unique QIDs for {sum(len(v) for v in byq.values())} species")

def get(url, params=None, tries=6):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=25)
            t = r.text
            if "too many" in t.lower():
                time.sleep(20 + 15*i); continue
            return r.json()
        except Exception:
            time.sleep(8 + 8*i)
    raise RuntimeError("exhausted")

labels = {}
for i in range(0, len(qids_list), 50):
    chunk = qids_list[i:i+50]
    data = get("https://www.wikidata.org/w/api.php", {"action":"wbgetentities","ids":"|".join(chunk),"props":"labels","languages":"th","format":"json"})
    for q, e in data.get("entities", {}).items():
        if q == "-1": continue
        th = (e.get("labels", {}).get("th") or {}).get("value")
        for pid in byq.get(q, []):
            labels[pid] = th
    print(f"batch {i//50+1}: done ({i+len(chunk)}/{len(qids_list)})", flush=True)
    time.sleep(2)

with open(f"{BASE}/labels.json", "w") as f:
    json.dump(labels, f, indent=1)
withthai = {k:v for k,v in labels.items() if v}
print(f"labels fetched: {len(labels)}, with Thai: {len(withthai)}")
for pid in sorted(withthai, key=lambda x: (not withthai[x]))[:20]:
    print(f"  {pid} => {withthai[pid]}")
