#!/usr/bin/env python3
"""Test one entry through the updated author_batches pipeline (direct server, thinking off)."""
import sys, time, json
sys.path.insert(0, '/Users/henry/sacred-botany/scripts')
import author_batches as ab

print(f"API={ab.API}")
print(f"AUTH={'yes' if ab.AUTH_HDRS else 'no'}  MAXTOK={ab.MAXTOK}  NOTINK={bool(ab.NOTINK)}")
E = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
t0 = time.time()
obj, ok, detail = ab.author_one(E)
dt = time.time() - t0
print(f"RESULT ok={ok} dt={dt:.0f}s detail={detail[:200]}")
if ok:
    print(f"id={obj['id']} sci={obj['sci']} family={obj['family']}")
    print(f"pharmacology: {obj['pharmacology'][:150]}")
    print(f"image_verbatim={obj['image'] == E['image']}")
    print(f"name={obj['name']} regions={obj['regions']}")
