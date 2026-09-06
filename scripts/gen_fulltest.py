import json, time, re, urllib.request
API="http://127.0.0.1:1234/v1/chat/completions"
SPEC=open('/Users/henry/sacred-botany/SCHEMA_SPEC.md').read()
E=json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
SYS=(SPEC+"\n\nIMPORTANT: Output ONLY one raw JSON object for the given plant. "
     "No markdown, no code fences, no prose, no trailing commas. "
     "All 19 top-level fields must be present (prep and culture nested). "
     "Use the provided image URL verbatim. Be accurate and measured; never invent studies or doses.")
USR="Plant data: "+json.dumps(E)
body={"model":"qwen/qwen3.8-27b","messages":[
      {"role":"system","content":SYS},{"role":"user","content":USR}],
      "max_tokens":4000,"temperature":0.2}
req=urllib.request.Request(API,data=json.dumps(body).encode(),
      headers={"Content-Type":"application/json"})
t0=time.time()
with urllib.request.urlopen(req,timeout=400) as r:
    full=json.loads(r.read().decode())
dt=time.time()-t0
c=full['choices'][0]; u=full.get('usage',{})
raw=c['message']['content']
print(f"TIME {dt:.0f}s  finish={c.get('finish_reason')}  out_tok={u.get('completion_tokens')}  reasoning={u.get('completion_tokens_details',{}).get('reasoning_tokens')}")
# robust extract
m=re.search(r'\{.*\}', raw, re.S)
txt=m.group(0) if m else raw
try:
    obj=json.loads(txt)
    print("PARSE: OK")
    top=[k for k in obj.keys()]
    print("TOP_FIELDS(%d):"%len(top), ", ".join(top))
    print("id=%s name=%s sci=%s family=%s"%(obj.get('id'),obj.get('name'),obj.get('sci'),obj.get('family')))
    print("has_prep=%s has_culture=%s prep_keys=%s culture_keys=%s"%(
        'prep' in obj,'culture' in obj,
        list(obj.get('prep',{}).keys()),list(obj.get('culture',{}).keys())))
    print("image_verbatim=%s"%(obj.get('image')==E['image']))
    print("compounds=%s"%(obj.get('compounds')))
    print("RAW_LEN=%d"%len(raw))
    print("---- RAW (first 1200) ----")
    print(raw[:1200])
except Exception as ex:
    print("PARSE: FAIL ->",ex)
    print("RAW (first 1500):"); print(raw[:1500])
