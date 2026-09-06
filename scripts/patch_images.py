#!/usr/bin/env python3
"""Patch 24 accepted images into batch files (js + jsonl + state)."""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOIMG_ACCEPT = {"Ailanthus malabarica", "Banisteriopsis inebrians"}

def main():
    # build {batch: {id: image}}
    patch = {}
    for x in json.load(open(f"{BASE}/missing_images_resolved.json")):
        if x.get("image") and (x.get("confidence") == "high" or x["sci"] in NOIMG_ACCEPT):
            patch.setdefault(x["batch"], {})[x["id"]] = x["image"]
    for x in json.load(open(f"{BASE}/missing_images_wiki.json")):
        if x.get("image") and x["sci"] in NOIMG_ACCEPT:
            patch.setdefault(x["batch"], {})[x["id"]] = x["image"]

    total = 0
    for b, m in sorted(patch.items()):
        p = f"{BASE}/batches/out_{b}.js"
        arr = eval(open(p).read())
        n = 0
        for e in arr:
            if e.get("id") in m and not (e.get("image") or "").strip():
                e["image"] = m[e["id"]]; n += 1
        json.dump(arr, open(p, "w"), indent=1)
        # jsonl
        jp = f"{BASE}/batches/out_{b}.jsonl"
        if os.path.exists(jp):
            lines = open(jp).read().splitlines()
            for i, ln in enumerate(lines):
                if ln.strip():
                    o = json.loads(ln)
                    if o.get("id") in m and not (o.get("image") or "").strip():
                        o["image"] = m[o["id"]]
                        lines[i] = json.dumps(o, ensure_ascii=False)
            open(jp, "w").write("\n".join(lines) + "\n")
        # state
        sp = f"{BASE}/batches/state_{b}.json"
        if os.path.exists(sp):
            st = json.load(open(sp))
            ids = [x["id"] for x in arr]
            st["done"] = ids
            json.dump(st, open(sp, "w"), indent=1)
        print(f"batch {b}: patched {n}/{len(m)}")
        total += n
    print(f"TOTAL: {total} images patched")

if __name__ == "__main__":
    main()
