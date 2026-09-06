#!/usr/bin/env python3
"""One-off: author 'Mandarin orange' (batch 06) with sci post-normalization.

The model keeps 'correcting' sci to Citrus reticulata; the hard rule is sci
verbatim from input ('Mandarin orange'). So: accept a valid entry even when
sci differs, then force sci back to the input value. Rebuilds out_06.js.
"""
import json, sys, time
BASE = "/Users/henry/sacred-botany"
sys.path.insert(0, f"{BASE}/scripts")
from author_batches import call, extract_obj, SYS, REQ_FIELDS, log  # noqa: E402

item = json.load(open(f"{BASE}/batches/in_06.json"))[20]
assert item["sci"] == "Mandarin orange", item
HINT = ("\n\nCRITICAL: the 'sci' field must be EXACTLY the string \"Mandarin orange\" "
        "(verbatim from the input above). Do NOT substitute a Latin binomial such as "
        "Citrus reticulata — the family field already carries the genus context. "
        "Output only the corrected single JSON object.")

def valid(o, strict_sci):
    probs = [k for k in REQ_FIELDS if k not in o]
    if o.get("image") != item["image"]:
        probs.append("image-not-verbatim")
    if strict_sci and o.get("sci") != item["sci"]:
        probs.append("sci-mismatch")
    if not (isinstance(o.get("prep"), dict) and "steps" in o.get("prep", {})):
        probs.append("prep-bad")
    if not isinstance(o.get("culture"), dict):
        probs.append("culture-bad")
    return probs

last = ""
obj = None
for attempt in range(4):
    usr = "Plant data: " + json.dumps(item) + HINT
    if last:
        usr += f"\n\nPrevious attempt was invalid: {last}. Output only the corrected single JSON object."
    try:
        full = call([{"role": "system", "content": SYS}, {"role": "user", "content": usr}])
        raw = (full["choices"][0].get("message", {}).get("content") or "").strip()
        if not raw:
            last = f"empty content (finish={full['choices'][0].get('finish_reason')})"
            continue
        o = extract_obj(raw)
        probs = valid(o, strict_sci=True)
        if not probs:
            obj = o
            break
        if probs == ["sci-mismatch"]:
            # accept, then normalize sci back to input (hard rule: verbatim)
            o["sci"] = item["sci"]
            obj = o
            log("Mandarin orange: accepted with sci post-normalized to input value")
            break
        last = "; ".join(probs)
    except Exception as e:
        last = f"request error: {e}"
    time.sleep(5)

if obj is None:
    log(f"FATAL: Mandarin orange failed: {last}")
    sys.exit(1)
log(f"Mandarin orange: OK id={obj.get('id')} family={obj.get('family')}")

# ---------- rebuild batch 06 (same logic as repair.py) ----------
in06 = json.load(open(f"{BASE}/batches/in_06.json"))
in06_new = [it for it in in06 if it["sci"].strip() != "Mescaline molecule"]
json.dump(in06_new, open(f"{BASE}/batches/in_06.json", "w"), indent=1)

objs = []
try:
    with open(f"{BASE}/batches/out_06.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            if "__failed__" not in o:
                objs.append(o)
except FileNotFoundError:
    pass
existing = {o.get("sci", "").strip().lower(): o for o in objs}
final = []
for it in in06_new:
    sci = it["sci"].strip()
    e = obj if sci == "Mandarin orange" else existing.get(sci.lower())
    if not e:
        log(f"FATAL: batch 06 no entry for {sci}")
        sys.exit(1)
    final.append(e)
assert len(final) == len(in06_new) == 23, (len(final), len(in06_new))
ids = [o["id"] for o in final]
assert len(ids) == len(set(ids)), "dup ids in batch 06"

with open(f"{BASE}/batches/out_06.jsonl", "w") as fh:
    for o in final:
        fh.write(json.dumps(o) + "\n")
json.dump({"done": {str(i): o["id"] for i, o in enumerate(final)}},
          open(f"{BASE}/batches/state_06.json", "w"))
json.dump(final, open(f"{BASE}/batches/out_06.js", "w"), indent=1)
log("batch 06: REBUILT 23 entries -> out_06.js")
log("MANDARIN REPAIR COMPLETE")
