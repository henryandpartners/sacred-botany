#!/usr/bin/env python3
"""Check image existence via the Wikimedia Commons API (imageinfo).
Lighter + officially sanctioned; avoids direct-download 429s.
Usage: python3 api_check.py <json-file-of-records>  (records have id+url)
Prints a summary; writes api_check_results.json
"""
import json, sys, time, urllib.request, urllib.parse, urllib.error

UA = ("sacred-botany-image-audit/1.0 (research; contact: henryandpartners) "
      "python-urllib/3")

def api_check(url):
    # url like https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Foo.jpg/1280px-Foo.jpg
    # or https://upload.wikimedia.org/wikipedia/commons/7/71/Foo.jpg
    host_path = url.split("wikipedia/", 1)
    if len(host_path) < 2:
        return {"ok": False, "err": "unparseable-url"}
    rest = host_path[1]            # commons/thumb/0/04/Foo.jpg/1280px-Foo.jpg
    # strip query
    rest = rest.split("?", 1)[0]
    if "/thumb/" in rest:
        base = rest.split("/thumb/", 1)[1]     # 0/04/Foo.jpg/1280px-Foo.jpg
        filepart = base.split("/", 2)[2] if base.count("/") >= 2 else base
    else:
        filepart = rest.split("/")[2] if rest.count("/") >= 2 else rest
    filepart = filepart.split("/", 1)[0]        # drop thumbnail suffix
    filename = urllib.parse.unquote(filepart)
    if not filename.lower().startswith("file:"):
        filename = "File:" + filename
    q = urllib.parse.urlencode({
        "action": "query", "titles": filename, "prop": "imageinfo",
        "iiprop": "url|mime|size", "format": "json", "redirects": 1,
    })
    apiurl = "https://commons.wikimedia.org/w/api.php?" + q
    for a in range(4):
        req = urllib.request.Request(apiurl, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            pages = data.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) == -1:
                    return {"ok": False, "err": "not-found", "file": filename}
                ii = p.get("imageinfo", [{}])[0]
                mime = ii.get("mime", "")
                return {"ok": mime.startswith("image/"), "file": filename,
                        "mime": mime, "width": ii.get("width"), "height": ii.get("height")}
            return {"ok": False, "err": "no-pages", "file": filename}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 * (a + 1)); continue
            return {"ok": False, "err": f"http-{e.code}", "file": filename}
        except Exception as e:
            return {"ok": False, "err": type(e).__name__, "file": filename}
    return {"ok": False, "err": "429-exhausted", "file": filename}

if __name__ == "__main__":
    recs = json.load(open(sys.argv[1]))
    out = {}
    for n, r in enumerate(recs):
        out[r["id"]] = api_check(r["url"])
        time.sleep(0.4)
        if (n + 1) % 25 == 0:
            print(f"  {n+1}/{len(recs)} ...", flush=True)
    json.dump(out, open("api_check_results.json", "w"), indent=1)
    ok = sum(1 for v in out.values() if v["ok"])
    print(f"\nAPI check: {ok} OK / {len(out)-ok} problems (of {len(out)})")
    print("=== PROBLEMS ===")
    for k, v in out.items():
        if not v["ok"]:
            print(f"  {k}: {v.get('err','?')} file={v.get('file','?')}")
