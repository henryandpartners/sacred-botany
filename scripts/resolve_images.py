#!/usr/bin/env python3
"""Resolve candidate Wikimedia Commons images (1280px thumb) for each species in data_to_add.json.

Search-only (no per-image verify): stores up to 3 candidate thumbnails per species
(binomial first, then genus fallback). Verification happens in a later QA pass, where
a failing candidate can simply be swapped for the next one.

Polite: global rate limiter + light retry/backoff. Resumable via img_cache.json.
Stdlib only.
Writes data_to_add_image.json: {sci, compounds, candidates:[{thumb,title}...], image, img_ok}
"""
import json, os, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC   = os.path.join(BASE, "data_to_add.json")
OUT   = os.path.join(BASE, "data_to_add_image.json")
CACHE = os.path.join(BASE, "img_cache.json")
UA    = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
API   = "https://commons.wikimedia.org/w/api.php"
MIN_INTERVAL = 0.35
MAX_WORKERS  = 3

# ---- global rate limiter ----
_rl_lock = threading.Lock(); _rl_last = [0.0]
def _throttle():
    with _rl_lock:
        w = MIN_INTERVAL - (time.time() - _rl_last[0])
        if w > 0:
            time.sleep(w)
        _rl_last[0] = time.time()

def http(url, timeout=20):
    backoff = 1.0
    for _ in range(4):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=dict(UA), method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(1_048_576)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff = min(backoff * 2, 20); continue
            return e.code, b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(backoff); backoff = min(backoff * 2, 20); continue
    return None, b""

def _search(query, limit=5):
    q = urllib.parse.quote('filetype:bitmap ' + query)
    url = (API + "?action=query&format=json&generator=search&gsrnamespace=6"
           f"&gsrlimit={limit}&prop=imageinfo&iiprop=url%7Csize&iiurlwidth=1280&gsrsearch=" + q)
    status, body = http(url)
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
        if not ii:
            continue
        if ii.get("width", 0) < 300 or ii.get("height", 0) < 300:
            continue
        thumb = ii.get("thumburl") or ii.get("url")
        if thumb:
            out.append({"thumb": thumb, "title": p.get("title")})
    return out

def find_candidates(sci):
    c = _search(sci)
    if not c:
        genus = sci.split()[0]
        if len(sci.split()) > 1:
            c = _search(genus)
    return c[:3]

def main():
    data = json.load(open(SRC))
    cache = {}
    if os.path.exists(CACHE):
        try: cache = json.load(open(CACHE))
        except Exception: cache = {}
    lock = threading.RLock()
    todo = [d for d in data if not (cache.get(d["sci"]) or {}).get("candidates")]
    print(f"total={len(data)} cached={len(data)-len(todo)} todo={len(todo)}", file=sys.stderr)

    done = [0]
    def save():
        with lock:
            json.dump(cache, open(CACHE, "w"), indent=1)

    def work(d):
        sci = d["sci"]
        if (cache.get(sci) or {}).get("candidates"):
            return
        cands = find_candidates(sci)
        with lock:
            cache[sci] = {"sci": sci, "candidates": cands,
                          "image": (cands[0]["thumb"] if cands else None)}
            done[0] += 1
            if done[0] % 25 == 0:
                save()
                ok = sum(1 for v in cache.values() if v.get("image"))
                print(f"{done[0]}/{len(todo)} resolved (with-image {ok})", file=sys.stderr)

    if todo:
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            list(ex.map(work, todo))
    with lock:
        save()

    results = []
    for d in data:
        c = cache.get(d["sci"]) or {}
        results.append({"sci": d["sci"], "compounds": d.get("compounds", ""),
                        "candidates": c.get("candidates", []),
                        "image": c.get("image"), "img_ok": bool(c.get("image"))})
    json.dump(results, open(OUT, "w"), indent=1)
    okc = sum(1 for r in results if r["image"])
    print(f"DONE: {okc}/{len(results)} have candidate images -> {os.path.basename(OUT)}", file=sys.stderr)

if __name__ == "__main__":
    main()
