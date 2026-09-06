#!/usr/bin/env python3
"""Apply final30_patch.json into index.html + the matching batch source files."""
import json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
patch = json.load(open(os.path.join(BASE, "final30_patch.json")))
if not patch:
    print("nothing to patch"); raise SystemExit(0)

# batch per id: find which out_XX.js contains each id
batch_of = {}
for b in range(1, 12):
    n = f"{b:02d}"
    p = os.path.join(BASE, "batches", f"out_{n}.js")
    if not os.path.exists(p): continue
    arr = eval(open(p).read())
    for e in arr:
        batch_of[e.get("id")] = (n, arr)

# 1) patch index.html: set image for each id (only where currently null/empty)
htmlp = os.path.join(BASE, "index.html")
html = open(htmlp).read()
applied = 0
for pid, info in patch.items():
    img = info["image"]
    # match the object containing this id and replace its image field
    # find `id:"<pid>"` or `"id": "<pid>"`
    m = re.search(r'(?:["\']?id["\']?\s*:\s*)"' + re.escape(pid) + '"', html)
    if not m:
        continue
    # find the next image field after this id
    seg = html[m.end():]
    im = re.search(r'["\']?image["\']?\s*:\s*(null|"[^"]*")', seg)
    if im:
        cur = im.group(1)
        curval = cur[1:-1] if cur.startswith('"') else None
        if not curval:  # only fill empty ones
            # determine key style (quoted or not) from im.group(0)
            keystyle = 'image:' if re.match(r'\s*image:', seg[im.start()]) else '"image":'
            html = (html[:m.end() + im.start()] + keystyle + '"' + img + '"'
                    + html[m.end() + im.end()])
            applied += 1
open(htmlp, "w").write(html)
print(f"index.html: applied {applied}/{len(patch)}")

# 2) patch batch sources for consistency
for pid, info in patch.items():
    if pid not in batch_of: continue
    n, arr = batch_of[pid]
    for e in arr:
        if e.get("id") == pid and not (e.get("image") or "").strip():
            e["image"] = info["image"]
    p = os.path.join(BASE, "batches", f"out_{n}.js")
    json.dump(arr, open(p, "w"), indent=1)
    jp = os.path.join(BASE, "batches", f"out_{n}.jsonl")
    if os.path.exists(jp):
        lines = open(jp).read().splitlines()
        for i, ln in enumerate(lines):
            if ln.strip():
                o = json.loads(ln)
                if o.get("id") == pid and not (o.get("image") or "").strip():
                    o["image"] = info["image"]
                    lines[i] = json.dumps(o, ensure_ascii=False)
        open(jp, "w").write("\n".join(lines) + "\n")
    print(f"batch {n}: patched {pid}")
print("DONE")
