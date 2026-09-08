#!/usr/bin/env python3
"""Re-check 429'd images sequentially with backoff (Wikimedia is rate-limiting).
Updates /tmp/sb_img_audit.json in place. Stdlib only.
"""
import json, time, urllib.request, urllib.error, sys

AUDIT = "/tmp/sb_img_audit.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

res = json.load(open(AUDIT))
todo = [r for r in res if r["status"] == 429]
print(f"re-checking {len(todo)} rate-limited images (slow, ~{len(todo)}s)", flush=True)

def check(url, max_attempts=5):
    last = None
    for a in range(max_attempts):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                ct = r.headers.get("Content-Type", "")
                head = r.read(256)
                return {"status": r.status, "ct": ct, "ok": True,
                        "content_length": r.headers.get("Content-Length")}
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code == 429:
                time.sleep(2 * (a + 1))   # backoff: 2,4,6,8,10
                continue
            return {"status": e.code, "ct": e.headers.get("Content-Type", ""), "ok": False}
        except Exception as e:
            last = type(e).__name__
            time.sleep(1.5 * (a + 1))
    return {"status": last if isinstance(last, int) else 0, "ct": "", "ok": False, "err": str(last)}

done = 0
for r in todo:
    out = check(r["url"])
    r.update(out)
    def cls(rr):
        if not rr["ok"]:
            return "FAIL" if rr["status"] != 200 else "FAIL"
        if rr["status"] != 200: return "BADSTATUS"
        ct = (rr.get("ct") or "").lower()
        if "image" in ct: return "OK"
        if "html" in ct or "text" in ct: return "NOT_IMAGE"
        return "OK_OTHER"
    r["class"] = cls(r)
    done += 1
    if done % 20 == 0:
        json.dump(res, open(AUDIT, "w"), indent=1)
        print(f"  {done}/{len(todo)} ...", flush=True)
    time.sleep(0.6)   # stay under Wikimedia's limit

json.dump(res, open(AUDIT, "w"), indent=1)
from collections import Counter
c = Counter(r["class"] for r in res)
print("\n=== FINAL SUMMARY ===")
for k in ["OK", "OK_OTHER", "NOT_IMAGE", "BADSTATUS", "FAIL"]:
    print(f"  {k}: {c.get(k, 0)}")
print(f"  total: {len(res)}")
print("\n=== STILL FAILING (non-OK) ===")
bad = [r for r in res if r["class"] != "OK"]
for r in bad:
    print(f"  [{r['class']}] {r['id']} status={r['status']} ct={r.get('ct','')!r} err={r.get('err','')}")
    print(f"      {r['url'][:120]}")
print(f"\n{len(bad)} problems, {len(res)-len(bad)} OK")
