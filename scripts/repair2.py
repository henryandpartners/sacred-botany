#!/usr/bin/env python3
"""Repair pass v2 (resume-safe): regen 5 entries with per-item disk checkpointing,
then rebuild batch 01/06, fix batch 04 variety ids, patch 9 compounds-empty entries,
set Tetrapterys image.

Checkpoint store: batches/repair_store.json  {sci: entry}
Safe to re-run: already-stored items are skipped.
"""
import json, time, sys, re
from concurrent.futures import ThreadPoolExecutor
BASE = "/Users/henry/sacred-botany"
sys.path.insert(0, f"{BASE}/scripts")
from author_batches import call, extract_obj, SYS, REQ_FIELDS, log  # noqa: E402

STORE = f"{BASE}/batches/repair_store.json"
TETRA_IMG = ("https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0a/11139-Tetrapterys_discolor-Cacuri.jpg/"
             "1280px-11139-Tetrapterys_discolor-Cacuri.jpg?utm_source=commons.wikimedia.org"
             "&utm_campaign=imageinfo&utm_content=thumbnail")
NO_COMPOUNDS = "No psychoactive compounds documented"


def store_load():
    try:
        return json.load(open(STORE))
    except Exception:
        return {}


def store_put(sci, obj):
    st = store_load()
    st[sci] = obj
    json.dump(st, open(STORE, "w"), indent=1)


def base_valid(o, item):
    probs = [k for k in REQ_FIELDS if k not in o]
    if o.get("image") != item["image"]:
        probs.append("image-not-verbatim")
    if not (isinstance(o.get("prep"), dict) and "steps" in o.get("prep", {})):
        probs.append("prep-bad")
    if not isinstance(o.get("culture"), dict):
        probs.append("culture-bad")
    return probs


def regen(item, allow_sci_norm=False):
    """Generate entry for item with retries; checkpoint to store on success."""
    sci = item["sci"].strip()
    store = store_load()
    if sci in store:
        log(f"REGEN {sci}: already in store, skipping")
        return store[sci]
    hint = ""
    if allow_sci_norm:
        hint = ("\n\nCRITICAL: the 'sci' field must be EXACTLY the string \"" + sci + "\" "
                "(verbatim from the input). Do NOT substitute a Latin binomial. "
                "Output only the single JSON object.")
    last = ""
    for attempt in range(4):
        usr = "Plant data: " + json.dumps(item) + hint
        if last:
            usr += f"\n\nPrevious attempt was invalid: {last}. Output only the corrected single JSON object."
        try:
            full = call([{"role": "system", "content": SYS}, {"role": "user", "content": usr}])
            raw = (full["choices"][0].get("message", {}).get("content") or "").strip()
            if not raw:
                last = f"empty content (finish={full['choices'][0].get('finish_reason')})"
                continue
            o = extract_obj(raw)
            probs = base_valid(o, item)
            if not probs and o.get("sci") == sci:
                store_put(sci, o)
                return o
            if probs == [] and allow_sci_norm and o.get("sci") != sci:
                o["sci"] = sci
                log(f"REGEN {sci}: accepted, sci post-normalized to input value")
                store_put(sci, o)
                return o
            last = "; ".join(probs) or "sci-mismatch"
        except Exception as e:
            last = f"request error: {e}"
        time.sleep(5)
    raise RuntimeError(f"regen failed for {sci}: {last}")


def main():
    in01 = json.load(open(f"{BASE}/batches/in_01.json"))
    in06 = json.load(open(f"{BASE}/batches/in_06.json"))
    targets = [in01[1], in01[2], in01[3], in01[4]]
    mandarin = in06[20]
    assert mandarin["sci"] == "Mandarin orange", mandarin

    # ---- phase 1: regenerate (2 parallel workers, checkpointed) ----
    def work(it):
        t0 = time.time()
        o = regen(it, allow_sci_norm=(it["sci"].strip() == "Mandarin orange"))
        log(f"REGEN {it['sci'].strip()}: OK {time.time()-t0:.0f}s id={o.get('id')}")
        return o

    all_items = targets + [mandarin]
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(work, all_items))
    log("PHASE 1 DONE: all 5 entries in store")

    # ---- phase 2: rebuild batch 01 ----
    existing = {}
    with open(f"{BASE}/batches/out_01.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            if "__failed__" not in o:
                existing.setdefault(o.get("sci", "").strip().lower(), o)
    store = store_load()
    final01 = []
    for it in in01:
        sci = it["sci"].strip()
        e = store.get(sci) or existing.get(sci.lower())
        if not e:
            raise RuntimeError(f"batch 01 no entry for {sci}")
        final01.append(e)
    assert len(final01) == 24
    with open(f"{BASE}/batches/out_01.jsonl", "w") as fh:
        for o in final01:
            fh.write(json.dumps(o) + "\n")
    json.dump({"done": {str(i): o["id"] for i, o in enumerate(final01)}},
              open(f"{BASE}/batches/state_01.json", "w"))
    json.dump(final01, open(f"{BASE}/batches/out_01.js", "w"), indent=1)
    log("PHASE 2 DONE: batch 01 rebuilt (24 entries)")

    # ---- phase 3: rebuild batch 06 (drop Mescaline molecule) ----
    in06_new = [it for it in in06 if it["sci"].strip() != "Mescaline molecule"]
    assert len(in06_new) == 23, len(in06_new)
    json.dump(in06_new, open(f"{BASE}/batches/in_06.json", "w"), indent=1)
    existing6 = {}
    with open(f"{BASE}/batches/out_06.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            if "__failed__" not in o:
                existing6.setdefault(o.get("sci", "").strip().lower(), o)
    store = store_load()
    final06 = []
    for it in in06_new:
        sci = it["sci"].strip()
        e = store.get(sci) or existing6.get(sci.lower())
        if not e:
            raise RuntimeError(f"batch 06 no entry for {sci}")
        final06.append(e)
    ids6 = [o["id"] for o in final06]
    assert len(ids6) == len(set(ids6)), "dup ids batch 06"
    with open(f"{BASE}/batches/out_06.jsonl", "w") as fh:
        for o in final06:
            fh.write(json.dumps(o) + "\n")
    json.dump({"done": {str(i): o["id"] for i, o in enumerate(final06)}},
              open(f"{BASE}/batches/state_06.json", "w"))
    json.dump(final06, open(f"{BASE}/batches/out_06.js", "w"), indent=1)
    log("PHASE 3 DONE: batch 06 rebuilt (23 entries, Mescaline molecule dropped)")

    # ---- phase 4: batch 04 variety ids ----
    p04 = f"{BASE}/batches/out_04.js"
    arr04 = eval(open(p04).read())
    idcount = {}
    for o in arr04:
        idcount[o["id"]] = idcount.get(o["id"], 0) + 1
    fixed = 0
    for o in arr04:
        if idcount.get(o["id"], 0) > 1 and re.search(r"\bvar\b", o["sci"], re.I):
            log(f"batch 04 {o['sci']}: id {o['id']} -> {o['id']}_var")
            o["id"] = o["id"] + "_var"
            fixed += 1
    if fixed:
        json.dump(arr04, open(p04, "w"), indent=1)
        with open(f"{BASE}/batches/out_04.jsonl", "w") as fh:
            for o in arr04:
                fh.write(json.dumps(o) + "\n")
        json.dump({"done": {str(i): o["id"] for i, o in enumerate(arr04)}},
                  open(f"{BASE}/batches/state_04.json", "w"))
    log(f"PHASE 4 DONE: batch 04 ids fixed ({fixed})")

    # ---- phase 5: compounds patches + Tetrapterys image ----
    for bnum, idxs in [("03", [16, 17, 18, 19, 22, 23]), ("04", [0, 9])]:
        p = f"{BASE}/batches/out_{bnum}.js"
        arr = eval(open(p).read())
        n = 0
        for i in idxs:
            if not arr[i].get("compounds"):
                arr[i]["compounds"] = [NO_COMPOUNDS]
                n += 1
        if n:
            json.dump(arr, open(p, "w"), indent=1)
            with open(f"{BASE}/batches/out_{bnum}.jsonl", "w") as fh:
                for o in arr:
                    fh.write(json.dumps(o) + "\n")
            json.dump({"done": {str(i): o["id"] for i, o in enumerate(arr)}},
                      open(f"{BASE}/batches/state_{bnum}.json", "w"))
        log(f"PHASE 5: batch {bnum} compounds patched ({n})")

    p09 = f"{BASE}/batches/out_09.js"
    arr09 = eval(open(p09).read())
    if not arr09[2].get("compounds"):
        arr09[2]["compounds"] = [NO_COMPOUNDS]
    if not arr09[2].get("image"):
        arr09[2]["image"] = TETRA_IMG
        arr09[2]["alt"] = "Tetrapterys (genus) shrub — T. discolor, 'Cacuri'"
        log("PHASE 5: batch 09 Tetrapterys image set (genus photo)")
    else:
        log(f"PHASE 5: batch 09 Tetrapterys already has image: {arr09[2]['image'][:60]}")
    json.dump(arr09, open(p09, "w"), indent=1)
    with open(f"{BASE}/batches/out_09.jsonl", "w") as fh:
        for o in arr09:
            fh.write(json.dumps(o) + "\n")
    json.dump({"done": {str(i): o["id"] for i, o in enumerate(arr09)}},
              open(f"{BASE}/batches/state_09.json", "w"))
    log("ALL REPAIR PHASES COMPLETE")


if __name__ == "__main__":
    main()
