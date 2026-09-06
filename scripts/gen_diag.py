import json, time, urllib.request

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"
SPEC = open('/Users/henry/sacred-botany/SCHEMA_SPEC.md').read()

def call(messages, max_tokens=2500, temperature=0.3):
    body = {"model": MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as r:
        return json.loads(r.read().decode())

if __name__ == "__main__":
    e = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
    system = (SPEC + "\n\nOutput ONLY one valid JSON object for the given species, all 19 fields, no markdown.")
    user = json.dumps({"sci": e['sci'], "compounds": e['compounds'], "image": e['image']})
    t0=time.time()
    full = call([{"role":"system","content":system},{"role":"user","content":user}])
    c = full['choices'][0]
    print("TIME", f"{time.time()-t0:.1f}s")
    print("finish_reason:", c.get('finish_reason'))
    print("content repr:", repr((c.get('message',{}).get('content') or '')[:300]))
    print("usage:", full.get('usage'))
