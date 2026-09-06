#!/usr/bin/env python3
"""Repair pass for Sacred Botany batches (one-shot).

1. Regenerates 5 missing entries via local LLM:
   - batch 01: Delosperma ecklonis / esterhuyseniae / hallii / harazianum (dropped by resync bug)
   - batch 06: Mandarin orange (failed sci-mismatch)
2. Rebuilds out_01.js / out_06.js (+jsonl+state) in input order, deduped.
   - batch 06: drops the junk entry 'Mescaline molecule' (peyote already in live atlas).
3. Batch 04: disambiguates variety ids (anadenanthera_colubrina_var, lespedeza_bicolor_var).
4. Patches 9 compounds-empty entries -> ["No psychoactive compounds documented"].
5. Sets Tetrapterys mucronata image (genus photo, input image was empty).
"""
import json, time, sys, re
BASE = "/Users/henry/sacred-botany"
sys.path.insert(0, f"{BASE}/scripts")
from author_batches import author_one, log  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

TETRA_IMG = ("https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0a/11139-Tetrapterys_discolor-Cacuri.jpg/"
             "1280px-11139-Tetrapterys_discolor-Cacuri.jpg?utm_source=commons.wikimedia.org"
             "&utm_campaign=imageinfo&utm_content=thumbnail")
NO_COMPOUNDS = "No psychoactive compounds documented"


def load_jsonl(bnum):
    objs = []
    try:
        with open(f"{BASE}/batches/out_{bnum}.jsonl") as fh:
            for line in fh:
                o = json.loads(line)
                if "__failed__" not in o:
                    objs.append(o)
    except FileNotFoundError:
        pass
    return objs


def write_batch(bnum, items, final_objs):
    """items = input list (already final order); final_objs = 1:1 aligned. Write js+jsonl+state."""
    assert len(final_objs) == len(items), f"batch {bnum}: {len(final_objs)} objs vs {len(items)} items"
    jpath = f"{BASE}/batches/out_{bnum}.jsonl"
    with open(jpath, "w") as fh:
        for o in final_objs:
            fh.write(json.dumps(o) + "\n")
    with open(f"{BASE}/batches/state_{bnum}.json", "w") as fh:
        json.dump({"done": {str(i): o.get("id") for i, o in enumerate(final_objs)}}, fh)
    with open(f"{BASE}/batches/out_{bnum}.js", "w") as fh:
        json.dump(final_objs, fh, indent=1)
    log(f"batch {bnum}: REBUILT {len(final_objs)} entries -> out_{bnum}.js")


def main():
    in01 = json.load(open(f"{BASE}/batches/in_01.json"))
    in06 = json.load(open(f"{BASE}/batches/in_06.json"))

    # ---------- 1. regenerate missing entries ----------
    targets = {
        in01[1]["sci"]: in01[1],
        in01[2]["sci"]: in01[2],
        in01[3]["sci"]: in01[3],
        in01[4]["sci"]: in01[4],
        in06[20]["sci"]: in06[20],
    }

    def work(sci):
        t0 = time.time()
        obj, ok, detail = author_one(targets[sci])
        log(f"REPAIR {sci}: {'OK' if ok else 'FAIL'} {time.time()-t0:.0f}s"
            + ("" if ok else f" ({detail[:120]})"))
        return sci, obj, ok, detail

    repaired = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        for sci, obj, ok, detail in ex.map(work, list(targets)):
            if not ok:
                log(f"FATAL: repair failed for {sci}: {detail}")
                sys.exit(1)
            repaired[sci] = obj

    # ---------- 2. rebuild batch 01 ----------
    existing = {}
    for o in load_jsonl("01"):
        existing.setdefault(o.get("sci", "").strip().lower(), o)
    final01 = []
    for item in in01:
        sci = item["sci"].strip()
        e = repaired.get(sci) or existing.get(sci.lower())
        if not e:
            log(f"FATAL: batch 01 no entry for {sci}")
            sys.exit(1)
        final01.append(e)
    write_batch("01", in01, final01)

    # ---------- 3. rebuild batch 06 (drop 'Mescaline molecule') ----------
    in06_new = [it for it in in06 if it["sci"].strip() != "Mescaline molecule"]
    with open(f"{BASE}/batches/in_06.json", "w") as fh:
        json.dump(in06_new, fh, indent=1)
    existing6 = {}
    for o in load_jsonl("06"):
        existing6.setdefault(o.get("sci", "").strip().lower(), o)
    final06 = []
    for item in in06_new:
        sci = item["sci"].strip()
        e = repaired.get(sci) or existing6.get(sci.lower())
        if not e:
            log(f"FATAL: batch 06 no entry for {sci}")
            sys.exit(1)
        final06.append(e)
    write_batch("06", in06_new, final06)

    # ---------- 4. batch 04 variety id disambiguation ----------
    path04 = f"{BASE}/batches/out_04.js"
    arr04 = eval(open(path04).read())
    idcount = {}
    for o in arr04:
        idcount[o["id"]] = idcount.get(o["id"], 0) + 1
    for i, o in enumerate(arr04):
        if idcount.get(o["id"], 0) > 1 and re.search(r"\bvar\b", o["sci"], re.I):
            newid = o["id"] + "_var"
            log(f"batch 04 [{i}] {o['sci']}: id {o['id']} -> {newid}")
            o["id"] = newid
    json.dump(arr04, open(path04, "w"), indent=1)
    # resync jsonl + state from the fixed array
    with open(f"{BASE}/batches/out_04.jsonl", "w") as fh:
        for o in arr04:
            fh.write(json.dumps(o) + "\n")
    in04 = json.load(open(f"{BASE}/batches/in_04.json"))
    json.dump({"done": {str(i): o.get("id") for i, o in enumerate(arr04)}},
              open(f"{BASE}/batches/state_04.json", "w"))
    log("batch 04: ids fixed + resynced")

    # ---------- 5. patch compounds-empty + Tetrapterys image ----------
    patches = [
        ("03", [16, 17, 18, 19, 22, 23]),
        ("04", [0, 9]),
        ("09", [2]),
    ]
    for bnum, idxs in patches:
        path = f"{BASE}/batches/out_{bnum}.js"
        arr = eval(open(path).read())
        for i in idxs:
            if not arr[i].get("compounds"):
                arr[i]["compounds"] = [NO_COMPOUNDS]
                log(f"batch {bnum} [{i}] {arr[i]['sci']}: compounds -> [{NO_COMPOUNDS}]")
        if bnum == "09":
            arr[2]["image"] = TETRA_IMG
            arr[2]["alt"] = "Tetrapterys (genus) shrub — T. discolor, 'Cacuri'"
            log("batch 09 [2] Tetrapterys mucronata: image set (genus photo)")
        json.dump(arr, open(path, "w"), indent=1)
        with open(f"{BASE}/batches/out_{bnum}.jsonl", "w") as fh:
            for o in arr:
                fh.write(json.dumps(o) + "\n")
        inb = json.load(open(f"{BASE}/batches/in_{bnum}.json"))
        json.dump({"done": {str(i): o.get("id") for i, o in enumerate(arr)}},
                  open(f"{BASE}/batches/state_{bnum}.json", "w"))
    log("REPAIR COMPLETE")


if __name__ == "__main__":
    main()
