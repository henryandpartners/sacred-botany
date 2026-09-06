#!/usr/bin/env python3
"""Probe LM Studio: model list, thinking-disable test, full single-item generation."""
import json, time, re, urllib.request

API = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"

def call(body, timeout=540):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

print("== models ==")
try:
    ms = json.loads(urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=10).read().decode())
    for m in ms.get("data", []):
        print(" -", m.get("id"))
except Exception as e:
    print("model list err:", e)
    raise SystemExit("server not reachable")

print("== phase A: no-think micro probe (chat_template_kwargs) ==")
body = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Reply with exactly: TEST_OK"}],
    "max_tokens": 200, "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": False},
}
t0 = time.time()
full = call(body, timeout=120)
dt = time.time() - t0
c = full["choices"][0]
content = (c.get("message", {}).get("content") or "").strip()
reasoning = (c.get("message", {}).get("reasoning_content") or "")
print(f"TIME {dt:.1f}s finish={c.get('finish_reason')} content={content[:80]!r} "
      f"reasoning_len={len(reasoning)} usage={full.get('usage')}")
notink_ok = "TEST_OK" in content and len(reasoning) == 0
print("NOTINK_OK =", notink_ok)

print("== phase B: full single-item generation ==")
SPEC = open("/Users/henry/sacred-botany/SCHEMA_SPEC.md").read()
E = json.load(open("/Users/henry/sacred-botany/batches/in_01.json"))[0]
SYS = (SPEC + "\n\nIMPORTANT: Output ONLY one raw JSON object for the given plant. "
       "No markdown, no code fences, no prose. All 19 top-level fields must be present "
       "(prep and culture nested). Use the provided image URL verbatim. "
       "Be accurate and measured; never invent studies or doses. Answer directly, do not deliberate.")
USR = "Plant data: " + json.dumps(E)
body = {
    "model": MODEL,
    "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": USR}],
    "max_tokens": 3000 if notink_ok else 4000,
    "temperature": 0.2,
}
if notink_ok:
    body["chat_template_kwargs"] = {"enable_thinking": False}
t0 = time.time()
full = call(body, timeout=540)
dt = time.time() - t0
c = full["choices"][0]
raw = (c.get("message", {}).get("content") or "").strip()
reasoning = (c.get("message", {}).get("reasoning_content") or "")
u = full.get("usage", {})
print(f"TIME {dt:.0f}s finish={c.get('finish_reason')} completion_tokens={u.get('completion_tokens')} "
      f"reasoning_len={len(reasoning)} content_len={len(raw)}")
m = re.search(r"\{.*\}", raw, re.S)
txt = m.group(0) if m else raw
try:
    obj = json.loads(txt)
    req = ['id','name','sci','family','form','continent','regions','coords','habitat',
           'image','alt','parts','compounds','pharmacology','id_features','lookalikes',
           'prep','culture','legality','safety']
    missing = [k for k in req if k not in obj]
    print(f"PARSE: OK fields={len(obj)} missing={missing} "
          f"image_verbatim={obj.get('image') == E['image']} id={obj.get('id')}")
except Exception as ex:
    print("PARSE: FAIL ->", ex)
    print("RAW head:", raw[:400].replace(chr(10), " "))
print("PROBE DONE")
