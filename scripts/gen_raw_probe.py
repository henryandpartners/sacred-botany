import json, time, urllib.request

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"

def call(messages, max_tokens=1600, temperature=0.4):
    body = {"model": MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        full = json.loads(r.read().decode())
    return full

if __name__ == "__main__":
    inputs = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))
    e = inputs[0]
    system = "You are a botanist. Reply with a single valid JSON object for this plant with fields id, name, sci. No markdown."
    user = json.dumps({"sci": e['sci']})
    t0=time.time()
    full = call([{"role":"system","content":system},{"role":"user","content":user}], max_tokens=200)
    dt=time.time()-t0
    print(f"TIME {dt:.1f}s")
    print("CHOICES len:", len(full.get('choices',[])))
    c = full['choices'][0]
    print("finish_reason:", c.get('finish_reason'))
    print("content repr:", repr(c.get('message',{}).get('content'))[:500])
    print("usage:", full.get('usage'))
