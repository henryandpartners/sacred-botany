#!/usr/bin/env python3
"""Audit every plant image URL: HTTP status + content-type + byte size.
Browser UA (Wikimedia / iNat block default python UA). Stdlib only.
Writes JSON report to /tmp/sb_img_audit.json and prints a summary.
"""
import json, re, sys, concurrent.futures as cf, urllib.request, urllib.error, time

HTML = "/Users/henry/sacred-botany/index.html"
OUT  = "/tmp/sb_img_audit.json"
UA   = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

html = open(HTML, encoding="utf-8").read()
i = html.find("const PLANTS")
start = html.find("[", i)
depth=0; end=None; instr=False; esc=False
for k in range(start, len(html)):
    ch=html[k]
    if instr:
        if esc: esc=False
        elif ch=="\\": esc=True
        elif ch=='"': instr=False
        continue
    if ch=='"': instr=True
    elif ch=="[": depth+=1
    elif ch=="]":
        depth-=1
        if depth==0: end=k; break
arr=html[start+1:end]
objs=[]; depth=0; cur=0; instr=False; esc=False
for k,ch in enumerate(arr):
    if instr:
        if esc: esc=False
        elif ch=="\\": esc=True
        elif ch=='"': instr=False
        continue
    if ch=='"': instr=True
    elif ch=="{": depth+=1
    elif ch=="}":
        depth-=1
        if depth==0: objs.append(arr[cur:k+1]); cur=k+1

def get(o,key):
    m=re.search(r'["\']?'+key+r'["\']?\s*:\s*"((?:[^"\\]|\\.)*)"',o)
    return m.group(1) if m else None

plants=[(get(o,"id"), get(o,"image")) for o in objs]
targets=[(pid,url) for pid,url in plants if url]
print(f"auditing {len(targets)} images of {len(plants)} plants", flush=True)

def check(item):
    pid,url=item
    req=urllib.request.Request(url, headers={"User-Agent":UA, "Accept":"image/avif,image/webp,image/*,*/*"})
    t0=time.time()
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            ct=r.headers.get("Content-Type","")
            # read first chunk only to confirm bytes flow
            head=r.read(256)
            size_hdr=r.headers.get("Content-Length")
            return {"id":pid,"url":url,"status":r.status,"ct":ct,
                    "bytes_head":len(head),"content_length":size_hdr,"ms":int((time.time()-t0)*1000),"ok":True}
    except urllib.error.HTTPError as e:
        return {"id":pid,"url":url,"status":e.code,"ct":e.headers.get("Content-Type",""),"ok":False,"err":str(e.code)}
    except Exception as e:
        return {"id":pid,"url":url,"status":0,"ct":"","ok":False,"err":type(e).__name__+": "+str(e)[:120]}

results=[]
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for res in ex.map(check, targets):
        results.append(res)

# classify
def cls(r):
    if not r["ok"]: return "FAIL"
    if r["status"]!=200: return "BADSTATUS"
    ct=(r.get("ct") or "").lower()
    if "image" in ct: return "OK"
    if "html" in ct or "text" in ct: return "NOT_IMAGE"
    return "OK_OTHER"
for r in results: r["class"]=cls(r)

results.sort(key=lambda r:(r["class"], r["id"]))
json.dump(results, open(OUT,"w"), indent=1)
from collections import Counter
c=Counter(r["class"] for r in results)
print("\n=== SUMMARY ===")
for k in ["OK","OK_OTHER","NOT_IMAGE","BADSTATUS","FAIL"]:
    print(f"  {k}: {c.get(k,0)}")
print(f"  total: {len(results)}")
print("\n=== PROBLEMS (non-OK) ===")
for r in results:
    if r["class"]!="OK":
        print(f"  [{r['class']}] {r['id']} status={r['status']} ct={r.get('ct','')!r} err={r.get('err','')}")
        print(f"      {r['url'][:110]}")
print("\nwrote", OUT)
