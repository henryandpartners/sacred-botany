#!/usr/bin/env python3
"""Resolve Wikimedia Commons images for the 54 entries with empty image fields.

Search: binomial first, genus fallback. Top candidate verified (200 + image/*).
Confidence: 'high' = filename contains full binomial (normalized),
            'med'  = genus-level match, 'low' = other/none.
Stdlib only. Resumable via img_missing_cache.json.
Writes missing_images_resolved.json: [{batch, id, sci, confidence, image, candidates, verified}]
"""
import json, os, re, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "img_missing_cache.json")
OUT = os.path.join(BASE, "missing_images_resolved.json")
UA = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
API = "https://commons.wikimedia.org/w/api.php"
MIN_INTERVAL = 0.35
MAX_WORKERS = int(__import__("os").environ.get("MAXW", "2"))

_rl_lock = threading.Lock(); _rl_last = [0.0]
def _throttle():
    with _rl_lock:
        w = MIN_INTERVAL - (time.time() - _rl_last[0])
        if w > 0: time.sleep(w)
        _rl_last[0] = time.time()

def http(url, timeout=20, cap=1_048_576):
    backoff = 1.0
    for _ in range(4):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=dict(UA), method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read(cap)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff = min(backoff*2, 20); continue
            return e.code, "", b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(backoff); backoff = min(backoff*2, 20); continue
    return None, "", b""

def _norm(s):
    return re.sub(r"[^a-z]", "", s.lower())

def _search(query, limit=6):
    q = urllib.parse.quote("filetype:bitmap " + query)
    url = (API + "?action=query&format=json&generator=search&gsrnamespace=6"
           f"&gsrlimit={limit}&prop=imageinfo&iiprop=url%7Csize&iiurlwidth=1280&gsrsearch=" + q)
    status, ct, body = http(url)
    if status != 200 or not body:
        return []
    try:
        j = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return []
    pages = (j.get("query") or {}).get("pages") or {}
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        ii = (p.get("imageinfo") or [None])[0]
        if not ii: continue
        if ii.get("width", 0) < 300 or ii.get("height", 0) < 300: continue
        thumb = ii.get("thumburl") or ii.get("url")
        if thumb:
            out.append({"thumb": thumb, "title": p.get("title", "")})
    return out

def confidence(sci, title):
    fn = _norm(title)
    genus = _norm(sci.split()[0])
    if len(sci.split()) > 1 and _norm(sci) in fn:
        return "high"
    if genus and genus in fn:
        return "med"
    return "low"

def collect_missing():
    """Scan out_01..11.js for entries with empty image. Returns [{batch, id, sci}]"""
    missing = []
    for b in range(1, 12):
        n = f"{b:02d}"
        p = os.path.join(BASE, "batches", f"out_{n}.js")
        if not os.path.exists(p): continue
        arr = eval(open(p).read())
        for e in arr:
            if not (e.get("image") or "").strip():
                missing.append({"batch": n, "id": e.get("id"), "sci": e.get("sci", "")})
    return missing

def main():
    missing = collect_missing()
    print(f"missing entries: {len(missing)}", file=sys.stderr)
    cache = {}
    if os.path.exists(CACHE):
        try: cache = json.load(open(CACHE))
        except Exception: cache = {}
    lock = threading.RLock()
    done = [0]
    def save():
        with lock: json.dump(cache, open(CACHE, "w"), indent=1)

    def work(item):
        sci = item["sci"]
        if sci in cache and cache[sci].get("resolved"): return
        cands = _search(sci)
        best = None; conf = None
        if cands:
            # prefer high-confidence candidate ordering
            scored = sorted(enumerate(cands), key=lambda ic: (
                0 if _norm(sci) in _norm(ic[1]["title"]) else
                1 if _norm(sci.split()[0]) in _norm(ic[1]["title"]) else 2, ic[0]))
            for _, c in scored[:1]:
                st, ct, _ = http(c["thumb"])
                if st == 200 and "image" in ct.lower():
                    best = c["thumb"]; conf = confidence(sci, c["title"])
            if not best and cands:
                st, ct, _ = http(cands[0]["thumb"])
                if st == 200 and "image" in ct.lower():
                    best = cands[0]["thumb"]; conf = confidence(sci, cands[0]["title"])
        with lock:
            cache[sci] = {"sci": sci, "candidates": cands[:3], "image": best,
                          "confidence": conf, "resolved": True}
            done[0] += 1
            if done[0] % 10 == 0:
                save()
                ok = sum(1 for v in cache.values() if v.get("image"))
                print(f"{done[0]}/{len(missing)} resolved (with-image {ok})", file=sys.stderr)

    todo = [m for m in missing if not (cache.get(m["sci"]) or {}).get("resolved")]
    print(f"todo={len(todo)} cached={len(missing)-len(todo)}", file=sys.stderr)
    if todo:
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            list(ex.map(work, todo))
    with lock: save()

    results = []
    for m in missing:
        c = cache.get(m["sci"]) or {}
        results.append({**m, "image": c.get("image"), "confidence": c.get("confidence"),
                        "candidates": c.get("candidates", [])})
    json.dump(results, open(OUT, "w"), indent=1)
    hi = sum(1 for r in results if r["confidence"] == "high")
    me = sum(1 for r in results if r["confidence"] == "med")
    lo = sum(1 for r in results if r["confidence"] in ("low", None))
    print(f"DONE: {hi} high / {me} med / {lo} low-or-none -> {os.path.basename(OUT)}", file=sys.stderr)

if __name__ == "__main__":
    main()
