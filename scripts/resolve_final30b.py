#!/usr/bin/env python3
"""Image resolution pass B for the 27 no-image species (final30 left them null).

New sources vs pass A (which only tried en-wiki exact-title lead + Commons cache):
  1. Wikidata: item search by sci -> P18 image (item-level = species-verified) -> high
  2. Wikispecies: article opensearch -> first infobox/page image -> high
  3. Commons file search (namespace 6) -> imageinfo thumburl -> med
  4. en-Wikipedia opensearch -> article -> pageimages thumbnail -> high

Honesty-first: every accepted URL is verified (HTTP 200 + image/*).
Stdlib only. Writes final30b_patch.json: {id: {sci, image, confidence, source}}
"""
import json, os, re, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
MIN_INTERVAL = 0.35
_lock = threading.Lock(); _last = [0.0]
def _throttle():
    with _lock:
        w = MIN_INTERVAL - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()

def http(url, timeout=20, cap=2_000_000):
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

def jget(url):
    st, ct, body = http(url)
    if st != 200 or not body:
        return None
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None

def verify(url):
    st, ct, _ = http(url)
    return st == 200 and "image" in ct.lower()

def _norm(s):
    return re.sub(r"[^a-z]", "", s.lower())

# ---------- 1. Wikidata ----------
def wikidata_image(sci):
    j = jget("https://www.wikidata.org/w/api.php?action=wbsearchentities"
             "&search=" + urllib.parse.quote(sci) +
             "&language=en&limit=8&type=item&format=json")
    if not j:
        return None
    cands = j.get("search") or []
    # prefer exact normalized label match
    ordered = sorted(cands, key=lambda c: 0 if _norm(c.get("label", "")) == _norm(sci) else 1)
    ids = [c.get("id") for c in ordered if c.get("id")]
    if not ids:
        return None
    j2 = jget("https://www.wikidata.org/w/api.php?action=wbgetentities"
              "&ids=" + "%7C".join(ids) + "&props=labels|claims&format=json")
    if not j2:
        return None
    ents = j2.get("entities") or {}
    # exact-label items first
    def keyf(eid):
        e = ents.get(eid) or {}
        lab = (e.get("labels") or {}).get("en", {}).get("value", "")
        return 0 if _norm(lab) == _norm(sci) else 1
    for eid in sorted(ids, key=keyf):
        e = ents.get(eid) or {}
        claims = (e.get("claims") or {}).get("P18") or []
        for cl in claims:
            v = (cl.get("mainsnak") or {}).get("datavalue", {}).get("value", {})
            fn = v.get("media-info") or v.get("normalizedname") or v.get("text")
            if fn and fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                url = ("https://upload.wikimedia.org/wikipedia/commons/" +
                       fn[0] + "/" + fn[0:2] + "/" + urllib.parse.quote(fn.replace(" ", "_")))
                return url, "high", "wikidata"
    return None

# ---------- 2. Wikispecies ----------
def wikispecies_image(sci):
    j = jget("https://species.wikimedia.org/w/api.php?action=opensearch"
             "&search=" + urllib.parse.quote(sci) + "&limit=5&namespace=0&format=json")
    if not j or len(j) < 3:
        return None
    titles = j[1]
    urls = j[2]
    exact = None
    for t, u in zip(titles, urls):
        if _norm(t) == _norm(sci):
            exact = u; break
    target = exact or urls[0]
    if not target:
        return None
    st, ct, body = http(target, cap=1_500_000)
    if st != 200 or not body:
        return None
    html = body.decode("utf-8", "replace")
    # first commons image in the page (infobox images come early)
    m = re.search(r'src="(?:https:)?//upload\.wikimedia\.org/wikipedia/commons/[^"]+\.(?:jpg|jpeg|png|webp)', html)
    if m:
        url = re.search(r'(https?://[^"]+|//[^"]+)', m.group(0)).group(1)
        if url.startswith("//"):
            url = "https:" + url
        return url, "high", "wikispecies"
    return None

# ---------- 3. Commons file search ----------
def commons_image(sci):
    j = jget("https://commons.wikimedia.org/w/api.php?action=query&list=search"
             "&srsearch=" + urllib.parse.quote(sci) + "&srnamespace=6&limit=6&format=json")
    if not j:
        return None
    titles = [r.get("title") for r in (j.get("query", {}).get("search") or [])]
    if not titles:
        return None
    j2 = jget("https://commons.wikimedia.org/w/api.php?action=query&titles="
              + urllib.parse.quote("|".join(titles[:4])) +
              "&prop=imageinfo&iiprop=url|mime&iiurlwidth=1280&format=json")
    if not j2:
        return None
    pages = (j2.get("query") or {}).get("pages") or {}
    # exact sci filename match first
    def sortkey(pid):
        p = pages.get(pid) or {}
        t = (p.get("title") or "").lower()
        return 0 if _norm(sci) in t.replace("_", " ").replace(":", "") else 1
    for pid in sorted(pages.keys(), key=sortkey):
        ii = ((pages.get(pid) or {}).get("imageinfo") or [None])[0]
        if not ii:
            continue
        if "image" not in (ii.get("mime") or ""):
            continue
        url = ii.get("thumburl") or ii.get("url")
        if url:
            conf = "high" if sortkey(pid) == 0 else "med"
            return url, conf, "commons"
    return None

# ---------- 4. en-wiki via search ----------
def enwiki_image(sci):
    j = jget("https://en.wikipedia.org/w/api.php?action=opensearch"
             "&search=" + urllib.parse.quote(sci) + "&limit=5&namespace=0&format=json")
    if not j or len(j) < 3 or not j[2]:
        return None
    titles = j[1]
    pick = None
    for t in titles:
        if _norm(t) == _norm(sci):
            pick = t; break
    pick = pick or titles[0]
    j2 = jget("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
              "&titles=" + urllib.parse.quote(pick) +
              "&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
    if not j2:
        return None
    for p in ((j2.get("query") or {}).get("pages") or {}).values():
        pi = p.get("thumbnail") or {}
        if pi.get("source"):
            return pi["source"], "high", "wikipedia"
    return None

# ---------- driver ----------
def resolve(pid, sci):
    for fn in (wikidata_image, wikispecies_image, commons_image, enwiki_image):
        try:
            r = fn(sci)
        except Exception as e:
            r = None
        if r:
            url, conf, src = r
            if verify(url):
                return {"sci": sci, "image": url, "confidence": conf, "source": src, "ok": True}
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
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(resolve, pid, pid.replace("_", " ")): pid for pid in nulls}
        for fut in cf.as_completed(futs):
            pid = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = None
            sci = pid.replace("_", " ")
            if r and r.pop("ok", False):
                results[pid] = r
                print(f"  OK   {pid}: {r['source']} [{r['confidence']}] {r['image'][:90]}")
            else:
                print(f"  MISS {pid}")
    out = os.path.join(BASE, "final30b_patch.json")
    json.dump(results, open(out, "w"), indent=1)
    print(f"\nWrote {out}: {len(results)}/{len(nulls)} resolved")

if __name__ == "__main__":
    main()
