#!/usr/bin/env python3
"""Thai-name lookup for sacred-botany (rate-limit robust, resumable).

Phase 1: wbsearchentities per species -> QID          (state: qids.json)
Phase 2: wbgetentities bulk (50/call) -> Thai labels  (state: entities.json)
Phase 3: th.wikipedia search for missing             (state: wikith.json)
Final:   lookup_results.json
"""
import json, re, time, sys
import requests

UA = {"User-Agent": "SacredBotany-ThaiLookup/1.0 (ethnobotanical research script; one-off lookup)"}
BASE = "/tmp/thai_lookup"
S = requests.Session()
S.headers.update(UA)

def jget(url, params=None, backoff=90):
    """GET JSON with rate-limit backoff. Returns (data, err)."""
    for attempt in range(6):
        try:
            r = S.get(url, params=params, timeout=25)
            txt = r.text[:200]
            if "too many requests" in r.text.lower():
                time.sleep(backoff)
                continue
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            if attempt == 5:
                return None, f"{type(e).__name__}: {e}"
            time.sleep(5 * (attempt + 1))
    return None, "rate-limited after retries"

plants = json.load(open(f"{BASE}/plants.json"))

OVERRIDE = {
    "ayahuasca": "Banisteriopsis caapi",
    "jurema": "Anadenanthera peregrina",
    "psilocybe": "Psilocybe cubensis",
    "mandarin_orange": "Citrus reticulata",
    "petalostylis_labicheoides_var": "Petalostylis labicheoides",
    "hippophae_rhamnoides": "Hippophae rhamnoides",
}

def clean_sci(sci):
    sci = re.sub(r"\s*\(syn\..*\)$", "", sci)
    sci = re.sub(r"\s*\(and related species\)$", "", sci)
    sci = re.sub(r"\s*/\s*A\..*$", "", sci)
    sci = re.sub(r"\s*\+\s*\S+$", "", sci)
    return sci.strip()

def thai_ok(s):
    return bool(s) and bool(re.search(r"[\u0E00-\u0E7F]", s))

# ---------- Phase 1: QID search ----------
qids = {}
try:
    qids = json.load(open(f"{BASE}/qids.json"))
except FileNotFoundError:
    pass
pending = [p for p in plants if p["id"] not in qids]
for i, p in enumerate(pending):
    sci = OVERRIDE.get(p["id"], clean_sci(p["sci"]))
    d, err = jget("https://www.wikidata.org/w/api.php", params={
        "action": "wbsearchentities", "search": sci,
        "language": "en", "format": "json", "limit": "5", "type": "item"})
    rec = {"search_sci": sci}
    if d and not err:
        hits = d.get("search", [])
        for hit in hits:
            if (hit.get("label") or "").strip().lower() == sci.lower():
                rec["qid"] = hit["id"]; break
        if "qid" not in rec and hits:
            for hit in hits:
                if sci.lower().split()[0] in (hit.get("label") or "").lower():
                    rec["qid"] = hit["id"]; rec["approx"] = True; break
    rec["err"] = err
    qids[p["id"]] = rec
    time.sleep(1.2)
    if (i + 1) % 20 == 0 or i == len(pending) - 1:
        print(f"  P1 {i+1}/{len(pending)}", flush=True)
        json.dump(qids, open(f"{BASE}/qids.json", "w"), ensure_ascii=False)

json.dump(qids, open(f"{BASE}/qids.json", "w"), ensure_ascii=False)
found = sum(1 for v in qids.values() if "qid" in v)
print(f"P1 done: {found}/{len(plants)} with QID", flush=True)

# ---------- Phase 2: bulk entity labels ----------
qids_list = []
for v in qids.values():
    if "qid" in v and v["qid"]:
        qids_list.append(v["qid"])
qids_list = sorted(set(qids_list))
entities = {}
try:
    entities = json.load(open(f"{BASE}/entities.json"))
except FileNotFoundError:
    pass
todo = [q for q in qids_list if q not in entities]
for i in range(0, len(todo), 50):
    chunk = todo[i:i+50]
    d, err = jget("https://www.wikidata.org/w/api.php", params={
        "action": "wbgetentities", "ids": "|".join(chunk),
        "props": "labels", "languages": "en|th", "format": "json"})
    if d and not err:
        for qid, ent in d.get("entities", {}).items():
            if qid == "missing":
                continue
            entities[qid] = {
                "en": ent.get("labels", {}).get("en", {}).get("value", ""),
                "th": ent.get("labels", {}).get("th", {}).get("value", "")}
    else:
        print("  P2 chunk err:", err, flush=True)
    time.sleep(2)
    print(f"  P2 {min(i+50, len(todo))}/{len(todo)}", flush=True)

json.dump(entities, open(f"{BASE}/entities.json", "w"), ensure_ascii=False)
print(f"P2 done: {len(entities)} entities", flush=True)

# ---------- Phase 3: thai wikipedia for missing ----------
need = []
for p in plants:
    v = qids.get(p["id"], {})
    qid = v.get("qid")
    th = entities.get(qid, {}).get("th", "") if qid else ""
    if not thai_ok(th):
        need.append(p["id"])
wikith = {}
try:
    wikith = json.load(open(f"{BASE}/wikith.json"))
except FileNotFoundError:
    pass
todo3 = [i for i in need if i not in wikith]
for i, pid in enumerate(todo3):
    sci = OVERRIDE.get(pid, clean_sci(next(p["sci"] for p in plants if p["id"] == pid)))
    d, err = jget("https://th.wikipedia.org/w/api.php", params={
        "action": "query", "format": "json", "list": "search",
        "srsearch": sci, "srlimit": "4"})
    if d and not err:
        wikith[pid] = [h["title"] for h in d.get("query", {}).get("search", [])]
    else:
        wikith[pid] = []
        wikith[pid + "__err"] = err
    time.sleep(1.0)
    if (i + 1) % 25 == 0 or i == len(todo3) - 1:
        print(f"  P3 {i+1}/{len(todo3)}", flush=True)
        json.dump(wikith, open(f"{BASE}/wikith.json", "w"), ensure_ascii=False)

json.dump(wikith, open(f"{BASE}/wikith.json", "w"), ensure_ascii=False)

# ---------- Merge ----------
results = []
for p in plants:
    v = qids.get(p["id"], {})
    qid = v.get("qid")
    ent = entities.get(qid, {}) if qid else {}
    results.append({
        "id": p["id"], "name": p["name"], "sci": p["sci"],
        "thai_current": p["thai_current"],
        "qid": qid, "approx": v.get("approx", False),
        "wd_en": ent.get("en", ""), "wd_th": ent.get("th", ""),
        "wiki_th_hits": wikith.get(p["id"], []),
    })
json.dump(results, open(f"{BASE}/lookup_results.json", "w"), ensure_ascii=False, indent=1)
filled = sum(1 for r in results if thai_ok(r["wd_th"]) or
             any(thai_ok(t) for t in r["wiki_th_hits"]))
print(f"DONE: {len(results)} species, {filled} with Thai candidate")
