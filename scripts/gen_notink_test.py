import json, time, urllib.request

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"
SPEC = open('/Users/henry/sacred-botany/SCHEMA_SPEC.md').read()
E = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
SYS = (SPEC + "\n\nOutput ONLY one valid JSON object for the given species, all 19 fields, no markdown.")
USR = json.dumps({"sci": E['sci'], "compounds": E['compounds'], "image": E['image']})

def call(messages, max_tokens=2500, temperature=0.3, extra=None):
    body = {"model": MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    if extra: body.update(extra)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=400) as r:
            return json.loads(r.read().decode())
    except Exception as ex:
        return {"error": str(ex)}

def report(tag, full):
    if "error" in full:
        print(f"[{tag}] ERROR {full['error'][:120]}"); return
    c = full['choices'][0]
    content = (c.get('message',{}).get('content') or '').strip()
    print(f"[{tag}] finish={c.get('finish_reason')} len={len(content)} usage={full.get('usage')}")
    print("   head:", content[:160].replace("\n"," "))

# Variant A: disable thinking via chat_template_kwargs
t0=time.time()
report("A chat_template_kwargs", call([{"role":"system","content":SYS},{"role":"user","content":USR}],
        extra={"chat_template_kwargs":{"enable_thinking":False}}))
print("  A time", f"{time.time()-t0:.1f}s")
