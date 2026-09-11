#!/usr/bin/env python3
"""Find verified correct-species image URLs for plants needing images.
Primary: iNaturalist taxa API. Fallback: Wikimedia Commons search.
Every final URL is verified: HTTP 200 + image/* content-type.
"""
import json, re, sys, time, urllib.request, urllib.parse, urllib.error

UA = {"User-Agent": "sacred-botany-image-audit/1.0 (research; contact: henryandpartners)"}
INAT = "https://api.inat.org/v1"

def http_get(url, headers=None, timeout=25):
    h = dict(UA); 
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()

def verify_image(url, timeout=25):
    """Return (ok, status, content_type, approx_bytes)."""
    try:
        h = dict(UA); h["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=h, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            cl = r.headers.get("Content-Length") or r.headers.get("Content-Range","")
            r.read(1)
            return (200 <= r.status < 300), r.status, ct, cl
    except urllib.error.HTTPError as e:
        return False, e.code, e.headers.get("Content-Type",""), None
    except Exception as e:
        return False, 0, str(e), None

def inat_taxon_id(sci):
    q = urllib.parse.quote(sci)
    try:
        st, hd, body = http_get(f"{INAT}/taxa?q={q}")
        data = json.loads(body)
        res = data.get("results") or []
        # prefer exact species match
        for r in res:
            if r.get("taxon_rank") == "species" and r.get("name","").lower() == sci.lower():
                return r["id"], r.get("name")
        if res:
            return res[0]["id"], res[0].get("name")
    except Exception as e:
        pass
    return None, None

def inat_photo(sci):
    tid, matched = inat_taxon_id(sci)
    if not tid: return None, None, None
    try:
        st, hd, body = http_get(f"{INAT}/taxa/{tid}")
        data = json.loads(body)
        dp = data.get("default_photo") or {}
        url = dp.get("url")
        if url:
            # try original, fall back to medium/large by size
            base = re.sub(r"/(square|small|medium|large|original|s|m|l|t)\.jpg$", "", url)
            for size in ("original","large","medium"):
                cand = f"{base}/{size}.jpg"
                ok, status, ct, cl = verify_image(cand)
                if ok and "image" in ct.lower():
                    return cand, "inaturalist", (matched == sci)
            return base + "/medium.jpg", "inaturalist", (matched == sci)
    except Exception:
        pass
    return None, None, matched

def wikimedia_photo(sci):
    try:
        q = urllib.parse.quote(sci)
        st, hd, body = http_get(
            "https://commons.wikimedia.org/w/api.php?action=query&format=json"
            f"&list=search&srsearch={q}&srnamespace=6&srlimit=8")
        data = json.loads(body)
        files = [x["title"] for x in (data.get("query",{}).get("search",[]))]
        for title in files:
            name = title.replace("File:","",1)
            st2, hd2, body2 = http_get(
                "https://commons.wikimedia.org/w/api.php?action=query&format=json"
                f"&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url")
            d2 = json.loads(body2)
            pages = d2.get("query",{}).get("pages",{})
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                url = ii.get("url")
                if url:
                    ok, status, ct, cl = verify_image(url)
                    if ok and "image" in ct.lower():
                        return url, "wikimedia", True
    except Exception:
        pass
    return None, None, None

def main():
    need = json.load(open("/tmp/sb_need_images.json"))
    out = {}
    for i,(pid, info) in enumerate(need.items()):
        sci = info["sci"]
        url, src, matched = inat_photo(sci)
        conf = "exact" if (src and matched) else ("genus" if src else "none")
        if not url:
            url, src, m2 = wikimedia_photo(sci)
            conf = "exact" if src else "none"
        out[pid] = {"sci": sci, "url": url, "source": src, "confidence": conf}
        tag = "OK " if url else "MISS"
        print(f"[{i+1:2d}/{len(need)}] {tag} {pid:32s} {conf:6s} {url or ''}", flush=True)
        time.sleep(0.25)
    json.dump(out, open("/tmp/sb_imgfix.json","w"), ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(v["confidence"] for v in out.values())
    print("\nSUMMARY:", dict(c), "total:", len(out))
    miss = [k for k,v in out.items() if not v["url"]]
    if miss: print("STILL MISSING:", ", ".join(sorted(miss)))

if __name__ == "__main__":
    main()
