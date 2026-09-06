import json, time, urllib.request
MODEL="qwen/qwen3.8-27b"; API="http://127.0.0.1:1234/v1/chat/completions"
E=json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
SYS="You are a botanist. Output ONE valid JSON object with fields id,name,sci,family for the given plant. No markdown, answer directly."
USR=json.dumps({"sci":E['sci']})
def t(tag, extra):
    body={"model":MODEL,"messages":[{"role":"system","content":SYS},{"role":"user","content":USR}],"max_tokens":2000,"temperature":0.3}
    body.update(extra)
    req=urllib.request.Request(API,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    t0=time.time()
    try:
        with urllib.request.urlopen(req,timeout=400) as r: full=json.loads(r.read().decode())
    except Exception as ex:
        print(f"[{tag}] ERR {str(ex)[:100]}"); return
    c=full['choices'][0]; u=full.get('usage',{})
    print(f"[{tag}] {time.time()-t0:.0f}s finish={c.get('finish_reason')} reasoning={u.get('completion_tokens_details',{}).get('reasoning_tokens')} out={u.get('completion_tokens')}")
t("baseline {}", {})
t("thinking:false", {"thinking": False})
t("enable_thinking:false", {"enable_thinking": False})
