#!/usr/bin/env python3
"""Measure real tok/s + test /no_think full-entry generation."""
import json, time, re, urllib.request

API = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"

def call(body, timeout=1500):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

print("== phase 1: forced-length speed test (thinking ON) ==", flush=True)
body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write exactly 600 words of plain prose on the history of Pacific island navigation. No headings, no lists."},
    ],
    "max_tokens": 1500, "temperature": 0.7,
}
t0 = time.time()
full = call(body)
dt = time.time() - t0
c = full["choices"][0]
raw = (c.get("message", {}).get("content") or "")
reasoning = (c.get("message", {}).get("reasoning_content") or "")
u = full.get("usage", {})
ct = u.get("completion_tokens", 0)
print(f"TIME {dt:.0f}s finish={c.get('finish_reason')} completion={ct} "
      f"content_words={len(raw.split())} reasoning_len={len(reasoning)}", flush=True)
if ct:
    print(f"THROUGHPUT ~{ct/dt:.1f} tok/s (all completion tokens incl. reasoning)", flush=True)

print("== phase 2: full entry with /no_think suffix ==", flush=True)
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
    "max_tokens": 4000, "temperature": 0.2,
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
except Exception as ex:
    print("PARSE: FAIL ->", ex)
    print("RAW head:", raw[:300].replace(chr(10), " "), flush=True)
print("SPEED PROBE DONE", flush=True)
