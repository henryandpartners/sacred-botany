#!/usr/bin/env python3
"""Image resolution pass C for remaining no-image species, via Openverse + iNaturalist.

Openverse aggregates CC-licensed images (herbaria, web, wikis) — strong for obscure species.
iNaturalist: photos tied to species-level observations.

Honesty-first:
  - accept only candidates whose title/taxon matches the full scientific name (high)
    or genus (med); skip weak matches entirely.
  - every accepted URL verified (HTTP 200 + image/*).
Writes final30c_patch.json: {id: {sci, image, confidence, source}}
Stdlib only.
"""
import json, os, re, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
# Openverse anonymous: ~20 req/min -> allow 18/min with slack
OV_INTERVAL = 3.4
_lock = threading.Lock(); _last = [0.0]
def _throttle(sec):
    with _lock:
        w = sec - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()

def http(url, timeout=20, cap=3_000_000, interval=0.4):
    backoff = 1.0
    for _ in range(3):
        _throttle(interval)
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

def jget(url, interval=0.4):
    st, ct, body = http(url, interval=interval)
    if st != 200 or not body:
        return None
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None

def verify(url):
    st, ct, _ = http(url, cap=1_000_000, interval=0.4)
    return st == 200 and "image" in ct.lower()

def _norm(s):
    return re.sub(r"[^a-z]", "", s.lower())

# ---------- Openverse ----------
def openverse_image(sci):
    j = jget("https://api.openverse.org/v1/images/?q=" + urllib.parse.quote(sci)
             + "&page_size=12", interval=OV_INTERVAL)
    if not j:
        return None
    res = j.get("results") or []
    nsci, ngen = _norm(sci), _norm(sci.split()[0])
    high, med = [], []
    for r in res:
        title = (r.get("title") or "")
        t = _norm(title)
        url = r.get("url")
        if not url:
            continue
        if nsci and nsci in t:
            high.append((title, url))
        elif ngen and t.startswith(ngen) and len(t) > len(ngen) - 1:
            med.append((title, url))
    for title, url in high:
        return url, "high", "openverse", title
    for title, url in med:
        return url, "med", "openverse", title
    return None

# ---------- iNaturalist ----------
def inat_image(sci):
    j = jget("https://api.inaturalist.org/v1/photos?taxon_name="
             + urllib.parse.quote(sci) + "&per_page=8&order_by=quality")
    if not j:
        return None
    results = j.get("results") or []
    for r in results:
        url = r.get("original_flash_photo_url") or r.get("square_flash_photo_url")
        if url:
            return url, "high", "inaturalist", sci
    return None

def resolve(pid, sci):
    for fn in (openverse_image, inat_image):
        try:
            r = fn(sci)
        except Exception:
            r = None
        if r:
            url, conf, src, title = r
            if verify(url):
                return {"sci": sci, "image": url, "confidence": conf,
                        "source": src, "candidate_title": title[:120], "ok": True}
    return None

def main():
    html = open(os.path.join(BASE, "index.html")).read()
    nulls = []
    for m in re.finditer(r'"id":\s*"([^"]+)"', html):
        seg = html[m.end():m.end() + 800]
        if re.search(r'"image":\s*(null|"")', seg):
            nulls.append(m.group(1))
    print(f"null-image plants: {len(nulls)}")
    results = {}
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(resolve, pid, pid.replace("_", " ")): pid for pid in nulls}
        for fut in cf.as_completed(futs):
            pid = futs[fut]
            try:
                r = fut.result()
            except Exception:
                r = None
            if r and r.pop("ok", False):
                results[pid] = r
                print(f"  OK   {pid}: {r['source']} [{r['confidence']}] {r['candidate_title'][:70]}")
            else:
                print(f"  MISS {pid}")
    out = os.path.join(BASE, "final30c_patch.json")
    json.dump(results, open(out, "w"), indent=1)
    print(f"\nWrote {out}: {len(results)}/{len(nulls)} resolved")

if __name__ == "__main__":
    main()
