import json, time, urllib.request, sys
sys.path.insert(0,'/Users/henry/sacred-botany/scripts')
from gen_compact_test import SYS

MODEL = "prism-ml/bonsai-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"

def call(messages, max_tokens=6000, temperature=0.3):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=500) as r:
        return json.loads(r.read().decode())

E = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
user = json.dumps({"sci": E['sci'], "compounds": E['compounds'], "image": E['image']})
t0=time.time()
full = call([{"role":"system","content":SYS},{"role":"user","content":user}])
dt=time.time()-t0
c=full['choices'][0]
content=(c.get('message',{}).get('content') or '').strip()
print(f"MODEL bonsai  TIME {dt:.1f}s finish={c.get('finish_reason')} usage={full.get('usage')}")
print("content len:", len(content))
print("head:", content[:220].replace(chr(10),' '))
# try parse
try:
    if content.startswith("```"):
        content=content.split("```",2)[1]
        if content.lower().startswith("json"): content=content[4:]
        content=content.rstrip().rstrip("`").strip()
    obj=json.loads(content)
    print("PARSE OK, keys:", len(obj))
except Exception as ex:
    print("PARSE FAIL:", str(ex)[:120])
