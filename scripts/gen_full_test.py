import json, time, urllib.request, unicodedata, re

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"
SPEC = open('/Users/henry/sacred-botany/SCHEMA_SPEC.md').read()
REQUIRED = ['id','name','sci','family','form','continent','regions','coords',
            'habitat','image','alt','parts','compounds','pharmacology',
            'id_features','lookalikes','prep','culture','legality','safety']

def slug(sci):
    s = unicodedata.normalize('NFKD', sci).encode('ascii','ignore').decode()
    s = s.lower()
    s = re.sub(r'\(.*?\)','', s)          # drop (syn. ...) etc
    s = re.sub(r'[^a-z0-9]+','_', s).strip('_')
    return s

def call(messages, max_tokens=2500, temperature=0.3):
    body = {"model": MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as r:
        return json.loads(r.read().decode())

def gen(sci, compounds, image):
    system = (SPEC +
      "\n\n## OUTPUT (follow exactly)\n"
      "Given ONE species below, output ONLY one valid JSON object matching the schema. "
      "No markdown, no code fences, no array, no trailing text. Include ALL 19 top-level fields "
      "(prep and culture nested). Copy the image URL verbatim. compounds = clean array of compound names. "
      "Accurate and evidence-honest; never invent studies, doses, citations. "
      "Do not spend long reasoning; answer directly.")
    user = json.dumps({"sci": sci, "compounds": compounds, "image": image})
    full = call([{"role":"system","content":system},{"role":"user","content":user}])
    c = full['choices'][0]
    content = (c.get('message',{}).get('content') or '').strip()
    info = {"finish": c.get('finish_reason'), "usage": full.get('usage')}
    if content.startswith("```"):
        content = content.split("```",2)[1]
        if content.lower().startswith("json"): content = content[4:]
        content = content.rstrip().rstrip("`").strip()
    obj = json.loads(content)
    obj['id'] = slug(sci)                 # deterministic id
    obj['image'] = image                  # verbatim
    if not isinstance(obj.get('compounds'), list):
        obj['compounds'] = [x.strip() for x in re.split(r',|;|&', str(obj.get('compounds',''))) if x.strip()]
    missing = [k for k in REQUIRED if k not in obj]
    return obj, missing, info

if __name__ == "__main__":
    inputs = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))
    e = inputs[0]
    t0=time.time()
    obj, missing, info = gen(e['sci'], e['compounds'], e['image'])
    print(f"TIME {time.time()-t0:.1f}s  finish={info['finish']}  usage={info['usage']}")
    print("missing:", missing)
    print("id:", obj['id'])
    print("name:", obj.get('name'), "| family:", obj.get('family'), "| form:", obj.get('form'))
    print("continent:", obj.get('continent'), "| regions:", obj.get('regions'))
    print("coords:", obj.get('coords'), "| habitat:", obj.get('habitat'))
    print("parts:", obj.get('parts'), "| compounds:", obj.get('compounds'))
    print("pharmacology:", obj.get('pharmacology'))
    print("id_features#:", len(obj.get('id_features',[])), "| lookalikes#:", len(obj.get('lookalikes',[])))
    print("prep.steps#:", len(obj.get('prep',{}).get('steps',[])))
    print("culture.cultures:", obj.get('culture',{}).get('cultures'))
    print("legality:", obj.get('legality'))
    print("safety:", obj.get('safety'))
