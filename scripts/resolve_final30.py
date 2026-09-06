#!/usr/bin/env python3
"""Final image pass for the ~30 no-image species in index.html.

Strategy per species (best real match, honesty-first):
  1. Wikipedia article lead image (en.wikipedia pageimages) -> confidence 'high'
  2. Existing Commons search cache (img_missing_cache.json) -> species='high' / genus='med'
  3. Nothing reliable -> leave null (site shows placeholder)

Every chosen URL is verified (HTTP 200 + image/*) before acceptance.
Writes final30_patch.json: {id: {sci, image, confidence, source}}
Stdlib only.
"""
import json, os, re, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "img_missing_cache.json")
UA = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
MIN_INTERVAL = 0.35

_lock = threading.Lock(); _last = [0.0]
def _throttle():
    with _lock:
        w = MIN_INTERVAL - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()

def http(url, timeout=15, cap=1_048_576):
    backoff = 1.0
    for _ in range(3):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=dict(UA), method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read(cap)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff = min(backoff * 2, 15); continue
            return e.code, "", b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(backoff); backoff = min(backoff * 2, 15); continue
    return None, "", b""

def _norm(s):
    return re.sub(r"[^a-z]", "", s.lower())

def verify(url):
    st, ct, _ = http(url)
    return st == 200 and "image" in ct.lower()

def wiki_lead(sci):
    """Return (thumb, confidence) from the species' own Wikipedia article, else (None, None)."""
    for title in (sci, sci.replace(" ", "_")):
        url = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
               "&titles=" + urllib.parse.quote(title) +
               "&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
        st, ct, body = http(url)
        if st != 200 or not body:
            continue
        try:
            j = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            continue
        pages = (j.get("query") or {}).get("pages") or {}
        for p in pages.values():
            pi = p.get("thumbnail") or {}
            if pi.get("source"):
                return pi["source"], "high"
    return None, None

def pick_from_cache(sci, cache):
    """Best candidate from the Commons cache: species(high) > genus(med)."""
    c = cache.get(sci) or {}
    cands = c.get("candidates") or []
    if c.get("image"):
        conf = c.get("confidence") or "low"
        if conf in ("high", "med"):
            return c["image"], conf, "commons"
    genus = _norm(sci.split()[0]) if sci.split() else ""
    # prefer a candidate whose filename contains the full binomial, then genus
    def score(t):
        fn = _norm(t)
        if len(sci.split()) > 1 and _norm(sci) in fn:
            return 0
        if genus and genus in fn:
            return 1
        return 9
    ranked = sorted(cands, key=lambda x: score(_norm(x.get("title", ""))))
    for cand in ranked:
        if score(cand.get("title", "")) > 1:
            break  # only accept species or genus level
        if verify(cand["thumb"]):
            conf = "high" if score(cand.get("title", "")) == 0 else "med"
            return cand["thumb"], conf, "commons"
    return None, None, None

def extract_missing():
    html = open(os.path.join(BASE, "index.html")).read()
    start = html.find("const PLANTS = [")
    end = html.find("];", start)
    block = html[start + len("const PLANTS = "):end]
    # brace matcher that ignores braces in strings
    objs = []; n = len(block); i = 0
    while i < n:
        if block[i] == "{":
            j = i; d = 0; instr = False; esc = False
            while j < n:
                ch = block[j]
                if instr:
                    if esc: esc = False
                    elif ch == "\\": esc = True
                    elif ch == '"': instr = False
                else:
                    if ch == '"': instr = True
                    elif ch == "{": d += 1
                    elif ch == "}":
                        d -= 1
                        if d == 0: break
                j += 1
            objs.append(block[i:j + 1]); i = j + 1
        else:
            i += 1
    missing = []
    for o in objs:
        mid = re.search(r'["\']?id["\']?\s*:\s*"([^"]+)"', o)
        msc = re.search(r'["\']?sci["\']?\s*:\s*"([^"]+)"', o)
        miimg = re.search(r'["\']?image["\']?\s*:\s*(null|"[^"]*")', o)
        img = None
        if miimg:
            v = miimg.group(1)
            img = v[1:-1] if v.startswith('"') else None
        if not img and mid and msc:
            missing.append({"id": mid.group(1), "sci": msc.group(1)})
    return missing

def main():
    missing = extract_missing()
    print(f"no-image species: {len(missing)}", file=sys.stderr)
    try:
        cache = json.load(open(CACHE))
    except Exception:
        cache = {}

    patch = {}; lock = threading.RLock(); done = [0]
    def work(m):
        sci, pid = m["sci"], m["id"]
        # 1) wikipedia lead (fresh)
        try:
            thumb, conf = wiki_lead(sci)
        except Exception:
            thumb, conf = None, None
        if thumb and verify(thumb):
            res = {"sci": sci, "image": thumb, "confidence": conf, "source": "wikipedia"}
        else:
            # 2) commons cache
            img, conf, src = pick_from_cache(sci, cache)
            res = {"sci": sci, "image": img, "confidence": conf, "source": src or "none"}
        with lock:
            if res["image"]:
                patch[pid] = res
            done[0] += 1
            tag = (f"{conf}/{res['source']} {res['image'][:70]}" if res["image"] else "NO IMAGE")
            print(f"{done[0]}/{len(missing)} {sci}: {tag}", file=sys.stderr, flush=True)
        return res

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(work, missing))

    json.dump(patch, open(os.path.join(BASE, "final30_patch.json"), "w"), indent=1)
    hi = sum(1 for v in patch.values() if v["confidence"] == "high")
    me = sum(1 for v in patch.values() if v["confidence"] == "med")
    none = len(missing) - len(patch)
    print(f"\nDONE: {len(patch)} images -> {hi} high / {me} med ; {none} left as placeholder", file=sys.stderr)

if __name__ == "__main__":
    main()
