#!/usr/bin/env python3
"""Second pass: retry the species that came back with no image, using a looser
search (no filetype:bitmap restriction, larger result set, lower min size).
Updates data_to_add_image.json in place. Stdlib only, polite."""
import json, os, sys, time, threading
import urllib.request, urllib.parse, urllib.error
import concurrent.futures as cf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(BASE, "data_to_add_image.json")
UA   = {"User-Agent": "sacred-botany-atlas/1.0 (ethnobotanical reference)"}
API  = "https://commons.wikimedia.org/w/api.php"
_rl = threading.Lock(); _last=[0.0]
def thrott():
    with _rl:
        w=0.4-(time.time()-_last[0])
        if w>0: time.sleep(w)
        _last[0]=time.time()

def http(url, timeout=20):
    b=1.0
    for _ in range(4):
        thrott()
        try:
            r=urllib.request.Request(url, headers=dict(UA), method="GET")
            with urllib.request.urlopen(r, timeout=timeout) as x:
                return x.status, x.read(1_048_576)
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503,504): time.sleep(b); b=min(b*2,20); continue
            return e.code, b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(b); b=min(b*2,20); continue
    return None, b""

OK_EXT = ("jpg","jpeg","png","gif","webp")
def search(query, limit=10):
    q=urllib.parse.quote(query)
    url=(API+"?action=query&format=json&generator=search&gsrnamespace=6"
         f"&gsrlimit={limit}&prop=imageinfo&iiprop=url%7Csize%7Cmime&iiurlwidth=1280&gsrsearch="+q)
    st,body=http(url)
    if st!=200 or not body: return []
    try: j=json.loads(body.decode("utf-8","replace"))
    except Exception: return []
    pages=(j.get("query") or {}).get("pages") or {}
    out=[]
    for p in sorted(pages.values(), key=lambda p:p.get("index",999)):
        ii=(p.get("imageinfo") or [None])[0]
        if not ii: continue
        if ii.get("width",0)<250 or ii.get("height",0)<250: continue
        mime=(ii.get("mime") or "")
        if mime and not any(e in mime for e in ("jpeg","png","gif","webp")): continue
        thumb=ii.get("thumburl") or ii.get("url")
        if thumb and (any(thumb.lower().split("?")[0].endswith(e) for e in OK_EXT) or "commons" in thumb):
            out.append({"thumb":thumb,"title":p.get("title")})
    return out

def find(sci):
    c=search(sci)
    if not c:
        g=sci.split()[0]
        if len(sci.split())>1: c=search(g)
    return c[:3]

def main():
    d=json.load(open(F))
    todo=[r for r in d if not r.get("image")]
    print(f"retrying {len(todo)} no-image species", file=sys.stderr)
    lock=threading.Lock(); recovered=[0]
    def work(r):
        if r.get("image"): return
        c=find(r["sci"])
        if c:
            with lock:
                r["candidates"]=c
                r["image"]=c[0]["thumb"]
                r["img_ok"]=True
                recovered[0]+=1
        return
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(work, todo))
    json.dump(d, open(F,"w"), indent=1)
    ok=sum(1 for r in d if r.get("image"))
    print(f"DONE: now {ok}/{len(d)} with images ({recovered[0]} recovered)", file=sys.stderr)

if __name__=="__main__":
    main()
