import json, time, urllib.request, unicodedata, re

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"

SYS = (
"You are an expert botanist and ethnobotanist. For the given plant species, output ONE valid "
"JSON object ONLY (no markdown, no code fences, no array, no trailing text) with exactly these "
"fields in this order:\n"
"id: string, snake_case from the scientific name\n"
"name: string, common name\n"
"sci: string, scientific name as given\n"
"family: string, botanical family\n"
"form: string, one phrase (tree/shrub/herb/vine/fungus + key feature)\n"
"continent: string\n"
"regions: array of 2-6 native country/region strings\n"
"coords: [lat, lon] of a representative native location\n"
"habitat: string, one line\n"
"image: string, copy the provided image URL verbatim\n"
"alt: string, short image description\n"
"parts: string, the part used\n"
"compounds: array of compound NAME strings\n"
"pharmacology: string, 1-3 sentences, evidence-honest\n"
"id_features: array of 3-5 short field-identification bullets\n"
"lookalikes: array of 2-4 bullets\n"
"prep: object {summary: string, steps: array of 2-5 strings, note: string}\n"
"culture: object {cultures: array of 2-5 strings, ritual: string, context: string}\n"
"legality: string, one honest line (note status varies by jurisdiction)\n"
"safety: string, one honest line (toxicity/interactions/consult a professional where relevant)\n"
"Be accurate and measured. Describe traditional/ceremonial use honestly. If modern evidence is "
"weak, say so. NEVER invent studies, clinical trials, precise doses, or citations. "
"Answer directly; do not deliberate at length.")

def slug(sci):
    s = unicodedata.normalize('NFKD', sci).encode('ascii','ignore').decode().lower()
    s = re.sub(r'\(.*?\)','', s)
    s = re.sub(r'[^a-z0-9]+','_', s).strip('_')
    return s

def call(messages, max_tokens=3000, temperature=0.3):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as r:
        return json.loads(r.read().decode())

def gen(sci, compounds, image):
    user = json.dumps({"sci": sci, "compounds": compounds, "image": image})
    full = call([{"role":"system","content":SYS},{"role":"user","content":user}])
    c = full['choices'][0]
    content = (c.get('message',{}).get('content') or '').strip()
    if content.startswith("```"):
        content = content.split("```",2)[1]
        if content.lower().startswith("json"): content = content[4:]
        content = content.rstrip().rstrip("`").strip()
    obj = json.loads(content)
    obj['id'] = slug(sci); obj['image'] = image
    if not isinstance(obj.get('compounds'), list):
        obj['compounds'] = [x.strip() for x in re.split(r',|;|&', str(obj.get('compounds',''))) if x.strip()]
    return obj, full.get('usage'), c.get('finish_reason')

if __name__ == "__main__":
    REQUIRED = ['id','name','sci','family','form','continent','regions','coords','habitat','image','alt','parts','compounds','pharmacology','id_features','lookalikes','prep','culture','legality','safety']
    e = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
    t0=time.time()
    obj, usage, finish = gen(e['sci'], e['compounds'], e['image'])
    print(f"TIME {time.time()-t0:.1f}s  finish={finish}  usage={usage}")
    missing=[k for k in REQUIRED if k not in obj]
    print("missing:", missing)
    print("id:", obj['id'], "| name:", obj.get('name'), "| family:", obj.get('family'))
    print("regions:", obj.get('regions'), "| coords:", obj.get('coords'))
    print("compounds:", obj.get('compounds'))
    print("pharmacology:", obj.get('pharmacology'))
    print("prep.steps#", len(obj.get('prep',{}).get('steps',[])), "| cultures:", obj.get('culture',{}).get('cultures'))
    print("legality:", obj.get('legality'))
    print("safety:", obj.get('safety'))
