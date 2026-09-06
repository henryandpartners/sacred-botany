#!/usr/bin/env python3
"""Pass 2: resolve remaining no-image entries via Wikipedia page lead images.

For each species, query en.wikipedia API (titles=<sci>, prop=pageimages).
The lead image of the species' own Wikipedia article is a strong match.
Stdlib only.
Writes missing_images_wiki.json: [{batch, id, sci, image, title}]
"""
import json, os, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
MIN_INTERVAL = 0.4

_rl_lock = threading.Lock(); _rl_last = [0.0]
def _throttle():
    with _rl_lock:
        w = MIN_INTERVAL - (time.time() - _rl_last[0])
        if w > 0: time.sleep(w)
        _rl_last[0] = time.time()

def http(url, timeout=20):
    backoff = 1.0
    for _ in range(4):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=dict(UA), method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read(500_000)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff = min(backoff*2, 20); continue
            return e.code, "", b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(backoff); backoff = min(backoff*2, 20); continue
    return None, "", b""

def wiki_image(sci):
    """Return (thumb_url, article_title) or (None, None)."""
    # exact-article first
    for title in (sci, sci.replace(" ", "_")):
        url = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
               "&titles=" + urllib.parse.quote(title) +
               "&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
        st, ct, body = http(url)
        if st != 200 or not body: continue
        try:
            j = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            continue
        pages = (j.get("query") or {}).get("pages") or {}
        for p in pages.values():
            if p.get("title") and "not found" not in str(p.get("title", "")).lower():
                pi = p.get("thumbnail") or {}
                if pi.get("source"):
                    return pi["source"], p["title"]
    return None, None

def main():
    prev = json.load(open(os.path.join(BASE, "missing_images_resolved.json")))
    todo = [x for x in prev if not x["image"]]
    print(f"todo={len(todo)}", file=sys.stderr)
    out = []
    lock = threading.RLock()
    done = [0]

    def work(x):
        thumb, title = wiki_image(x["sci"])
        with lock:
            done[0] += 1
            print(f"{done[0]}/{len(todo)} {x['sci']}: " +
                  (f"OK {thumb[:80]} (art: {title})" if thumb else "none"), file=sys.stderr, flush=True)
            return {"batch": x["batch"], "id": x["id"], "sci": x["sci"],
                    "image": thumb, "title": title}

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        out = list(ex.map(work, todo))

    ok = sum(1 for o in out if o["image"])
    print(f"DONE: {ok}/{len(out)} resolved via Wikipedia", file=sys.stderr)
    json.dump(out, open(os.path.join(BASE, "missing_images_wiki.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
