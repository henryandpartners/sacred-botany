#!/usr/bin/env python3
"""Full-entry generation with thinking disabled, on the IDLE :2 instance.
   If this completes in minutes with valid JSON, local authoring is viable.
"""
import json, time, re, urllib.request

API = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b:2"

def call(body, timeout=1200):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

SPEC = open("/Users/henry/sacred-botany/SCHEMA_SPEC.md").read()
E = json.load(open("/Users/henry/sacred-botany/batches/in_01.json"))[0]
SYS = (SPEC + "\n\nIMPORTANT: Output ONLY one raw JSON object for the given plant. "
       "No markdown, no code fences, no prose. All 19 top-level fields must be present "
       "(prep and culture nested). Use the provided image URL verbatim. "
       "Be accurate and measured; never invent studies or doses. Answer directly, do not deliberate.")
USR = "Plant data: " + json.dumps(E) + "\n\n/no_think"

body = {
    "model": MODEL,
    "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": USR}],
    "max_tokens": 3000, "temperature": 0.2,
    "chat_template_kwargs": {"enable_thinking": False},
}
t0 = time.time()
full = call(body)
dt = time.time() - t0
c = full["choices"][0]
raw = (c.get("message", {}).get("content") or "").strip()
reasoning = (c.get("message", {}).get("reasoning_content") or "")
u = full.get("usage", {})
print(f"TIME {dt:.0f}s finish={c.get('finish_reason')} completion={u.get('completion_tokens')} "
      f"reasoning_len={len(reasoning)} content_len={len(raw)}", flush=True)
ct = u.get("completion_tokens") or 0
if ct:
    print(f"THROUGHPUT ~{ct/dt:.2f} tok/s", flush=True)
m = re.search(r"\{.*\}", raw, re.S)
txt = m.group(0) if m else raw
try:
    obj = json.loads(txt)
    req = ['id','name','sci','family','form','continent','regions','coords','habitat',
           'image','alt','parts','compounds','pharmacology','id_features','lookalikes',
           'prep','culture','legality','safety']
    missing = [k for k in req if k not in obj]
    print(f"PARSE: OK fields={len(obj)} missing={missing} "
          f"image_verbatim={obj.get('image') == E['image']} id={obj.get('id')}", flush=True)
    print("SAMPLE name=%s family=%s prep_steps=%d" % (obj.get("name"), obj.get("family"),
          len(obj.get("prep", {}).get("steps", []))), flush=True)
except Exception as ex:
    print("PARSE: FAIL ->", ex, flush=True)
    print("RAW head:", raw[:400].replace(chr(10), " "), flush=True)
print("NOTINK ENTRY PROBE DONE", flush=True)
