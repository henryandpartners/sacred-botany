#!/usr/bin/env python3
"""A/B: bonsai-27b vs qwen3.8-27b on one full entry. Prints JSON summary."""
import json, time, re, urllib.request, sys

API = "http://127.0.0.1:1234/v1/chat/completions"
BASE = "/Users/henry/sacred-botany"
E = json.load(open(f"{BASE}/batches/in_01.json"))[0]
USER = json.dumps({"sci": E['sci'], "compounds": E['compounds'], "image": E['image']})
SYS = (open(f"{BASE}/SCHEMA_SPEC.md").read()
       + "\n\nIMPORTANT: Output ONLY one raw JSON object for the given plant. "
         "No markdown, no code fences, no prose. All 19 top-level fields must be present. "
         "Use the provided image URL verbatim. Be accurate and measured. Answer directly, do not deliberate.")
REQ = ['id','name','sci','family','form','continent','regions','coords','habitat','image','alt','parts','compounds','pharmacology','id_features','lookalikes','prep','culture','legality','safety']

def gen(model, maxtok):
    body = {"model": model, "messages": [
        {"role": "system", "content": SYS},
        {"role": "user", "content": USER}],
        "max_tokens": maxtok, "temperature": 0.2}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read().decode())
    dt = time.time() - t0
    c = d["choices"][0]
    msg = c.get("message", {})
    content = (msg.get("content") or "").strip()
    u = d.get("usage", {})
    det = u.get("completion_tokens_details", {})
    res = {"model": model, "dt": round(dt,1), "finish": c.get("finish_reason"),
           "completion": u.get("completion_tokens"), "reasoning": det.get("reasoning_tokens"),
           "content_len": len(content)}
    m = re.search(r"\{.*\}", content, re.S)
    txt = m.group(0) if m else content
    try:
        obj = json.loads(txt)
        missing = [k for k in REQ if k not in obj]
        res["parse"] = "OK" if not missing else f"MISSING {missing}"
    except Exception as ex:
        res["parse"] = f"FAIL {str(ex)[:80]}"
    return res

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("bonsai", "both"):
        print(json.dumps(gen("prism-ml/bonsai-27b", 6000), indent=1), flush=True)
    if which in ("qwen", "both"):
        print(json.dumps(gen("qwen/qwen3.8-27b", 16000), indent=1), flush=True)
