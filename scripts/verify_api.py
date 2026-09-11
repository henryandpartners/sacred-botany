#!/usr/bin/env python3
"""Verify the 56 flagged plants' image URLs via the Commons API (definitive
file-existence check, not subject to image-file rate limiting).
  ALIVE -> file exists in Commons (keep; also record canonical URL)
  DEAD  -> API reports missing (needs replacement)
  OTHER -> non-wikimedia host (fall back to direct HTTP check)
"""
import re, json, time, urllib.request, urllib.parse, urllib.error

HTML = "/Users/henry/sacred-botany/index.html"
UA = {"User-Agent": "sacred-botany-audit/1.0 (research; henryandpartners)"}
API = "https://commons.wikimedia.org/w/api.php"

def extract_plants():
    html = open(HTML).read()
    start = html.find("const PLANTS = [")
    end = html.find("const markers", start)
    region = html[start:end]
    ID_RE = re.compile(r'\bid["\']?\s*:\s*["\']([^"\']+)["\']')
    IMG_RE = re.compile(r'\bimage["\']?\s*:\s*["\']([^"\']+)["\']')
    ids = [(m.start(), m.group(1)) for m in ID_RE.finditer(region)]
    out = {}
    for k,(pos,pid) in enumerate(ids):
        nxt = ids[k+1][0] if k+1 < len(ids) else len(region)
        m = IMG_RE.search(region[pos:nxt])
        out[pid] = m.group(1) if m else None
    return out

def derive_filetitle(url):
    """Return 'File:<name>' for an upload.wikimedia.org URL, else None."""
    p = urllib.parse.urlparse(url)
    if "wikimedia.org" not in p.netloc:
        return None
    path = p.path
    if "/thumb/" in path:
        # .../commons/thumb/<h1>/<h2>/NNNpx-RealName.ext
        tail = path.split("/thumb/",1)[1]
        fname = tail.split("/")[-1]
        fname = re.sub(r'^\d+px-','',fname)
    else:
        fname = path.split("/")[-1]
    fname = urllib.parse.unquote(fname)
    return f"File:{fname}"

def api_check(filetitle, tries=3):
    """Return (exists, canonical_url, mime)."""
    q = urllib.parse.quote(filetitle)
    url = f"{API}?action=query&format=json&titles={q}&prop=imageinfo&iiprop=url|mime|size"
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            pages = d.get("query",{}).get("pages",{})
            for p in pages.values():
                if "missing" in p:
                    return False, None, None
                ii = (p.get("imageinfo") or [{}])[0]
                return True, ii.get("url"), ii.get("mime")
            return False, None, None
        except urllib.error.HTTPError as e:
            if e.code in (429,503):
                time.sleep(1.5*(a+1)); continue
            if e.code in (404,):
                return False, None, None
        except Exception:
            time.sleep(1.0*(a+1))
    return None, None, None  # None = inconclusive (transient)

def http_alive(url, tries=3):
    for a in range(tries):
        try:
            h=dict(UA); h["Range"]="bytes=0-0"
            req=urllib.request.Request(url,headers=h,method="GET")
            with urllib.request.urlopen(req,timeout=15) as r:
                ct=r.headers.get("Content-Type",""); r.read(1)
                if 200<=r.status<300 and "image" in ct.lower(): return True
        except urllib.error.HTTPError as e:
            if e.code in (404,410): return False
        except Exception: pass
        time.sleep(0.8*(a+1))
    return None

def main():
    plants = extract_plants()
    need = json.load(open("/tmp/sb_need_images.json"))
    res = {}
    for k,(pid,info) in enumerate(need.items()):
        url = plants.get(pid)
        if not url:
            res[pid]={"verdict":"NO_IMAGE","sci":info["sci"],"url":None}; print(f"[{k+1:2d}] NO_IMAGE {pid}"); continue
        ft = derive_filetitle(url)
        if ft:
            exists, canon, mime = api_check(ft)
            if exists is True:
                res[pid]={"verdict":"ALIVE","sci":info["sci"],"url":url,"canonical":canon,"mime":mime,"file":ft}
                print(f"[{k+1:2d}] ALIVE    {pid:30s} {ft[:55]}")
            elif exists is False:
                res[pid]={"verdict":"DEAD","sci":info["sci"],"url":url,"file":ft}
                print(f"[{k+1:2d}] DEAD     {pid:30s} {ft[:55]}")
            else:
                res[pid]={"verdict":"UNCLEAR","sci":info["sci"],"url":url,"file":ft}
                print(f"[{k+1:2d}] UNCLEAR  {pid:30s} {ft[:55]} (transient)")
        else:
            ok = http_alive(url)
            v = "ALIVE" if ok is True else ("DEAD" if ok is False else "UNCLEAR")
            res[pid]={"verdict":v,"sci":info["sci"],"url":url,"host":"other"}
            print(f"[{k+1:2d}] {v:8s} {pid:30s} (non-wikimedia: {url[:50]})")
        time.sleep(0.35)
    json.dump(res, open("/tmp/sb_verify2.json","w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print("\nSUMMARY:", dict(Counter(v["verdict"] for v in res.values())))

if __name__ == "__main__":
    main()
