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
"Be accurate and measured. If modern evidence is weak, say so. NEVER invent studies, trials, "
"precise doses, or citations. Answer directly, do not deliberate.")

def call(messages, max_tokens=3000, temperature=0.3, extra=None):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if extra: body.update(extra)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=400) as r:
            return json.loads(r.read().decode())
    except Exception as ex:
        return {"error": str(ex)}

E = json.load(open('/Users/henry/sacred-botany/batches/in_01.json'))[0]
base_user = json.dumps({"sci": E['sci'], "compounds": E['compounds'], "image": E['image']})

# Variant: /no_think appended to user message
t0=time.time()
full = call([{"role":"system","content":SYS},{"role":"user","content":base_user + "\n/no_think"}])
dt=time.time()-t0
if "error" in full:
    print("ERR", full['error'][:150])
else:
    c=full['choices'][0]
    content=(c.get('message',{}).get('content') or '').strip()
    print(f"TIME {dt:.1f}s finish={c.get('finish_reason')} usage={full.get('usage')}")
    print("head:", content[:200].replace(chr(10),' '))
