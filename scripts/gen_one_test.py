import json, time, urllib.request, sys

MODEL = "qwen/qwen3.8-27b"
API = "http://127.0.0.1:1234/v1/chat/completions"
SPEC = open('/Users/henry/sacred-botany/SCHEMA_SPEC.md').read()

REQUIRED = ['id','name','sci','family','form','continent','regions','coords',
            'habitat','image','alt','parts','compounds','pharmacology',
            'id_features','lookalikes','prep','culture','legality','safety']

def call(messages, max_tokens=1600, temperature=0.4):
    body = {"model": MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"]

def gen(sci, compounds, image):
    system = (SPEC +
      "\n\n## OUTPUT FORMAT (IMPORTANT)\n"
      "You will be given exactly ONE species. Respond with ONLY a single valid JSON object "
      "that matches the schema. Do NOT wrap in markdown or code fences. Do NOT return an array. "
      "All 19 top-level fields must be present (prep and culture are nested objects). "
      "Copy the provided image URL verbatim. Render compounds as a clean array of compound NAMES. "
      "Be accurate and evidence-honest; never invent studies, doses, or citations.")
    user = json.dumps({"sci": sci, "compounds": compounds, "image": image})
    t0 = time.time()
    raw = call([{"role":"system","content":system},{"role":"user","content":user}]).strip()
    if raw.startswith("```"):
        raw = raw.split("```",2)[1]
        if raw.lower().startswith("json"): raw = raw[4:]
        raw = raw.rstrip().rstrip("`").strip()
    obj = json.loads(raw)
    missing = [k for k in REQUIRED if k not in obj]
    dt = time.time()-t0
    return obj, missing, dt

if __name__ == "__main__":
    inputs = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))
    e = inputs[0]
    print("TEST SPECIES:", e['sci'])
    obj, missing, dt = gen(e['sci'], e['compounds'], e['image'])
    print(f"TIME: {dt:.1f}s  missing: {missing}")
    print("id:", obj.get('id'), "| name:", obj.get('name'), "| family:", obj.get('family'))
    print("compounds:", obj.get('compounds'))
    print("regions:", obj.get('regions'), "| coords:", obj.get('coords'))
    print("image verbatim:", obj.get('image')==e['image'])
    print("---pharmacology---")
    print(obj.get('pharmacology'))
    print("---prep.summary---")
    print(obj.get('prep',{}).get('summary'))
