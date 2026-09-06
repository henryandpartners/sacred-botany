#!/usr/bin/env python3
"""Author Sacred Botany batch entries via LM Studio (per-item calls, resumable).

Reads:   batches/in_XX.json   (array of {sci, compounds, image})
Writes:  batches/out_XX.jsonl (one JSON object per line, in input order)
         batches/out_XX.js    (final JS array, written when batch complete)
         batches/state_XX.json (resume state)
Log:     batches/progress.log

Usage: python3 scripts/author_batches.py [--batches 01 02 03 ...]
"""
import json, re, time, argparse, urllib.request, subprocess

BASE = "/Users/henry/sacred-botany"

def discover_server():
    """Find llama-server direct port + API key from process table (bypass LM Studio
    proxy, which drops chat_template_kwargs and thus can't disable thinking)."""
    try:
        out = subprocess.run(["ps", "ax", "-o", "command="], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return None, None
    for line in out.splitlines():
        if "llama-server" in line and "Qwen" in line:
            m = re.search(r"--port (\d+)", line)
            k = re.search(r"--api-key (\S+)", line)
            if m and k:
                return m.group(1), k.group(1)
    return None, None

def make_caller():
    port, key = discover_server()
    if not port:
        # fall back to LM Studio proxy (thinking stays ON -> slower, needs bigger budget)
        return "http://127.0.0.1:1234/v1/chat/completions", {}, 16000
    return f"http://127.0.0.1:{port}/v1/chat/completions", {"Authorization": f"Bearer {key}"}, 8000

API, AUTH_HDRS, MAXTOK = make_caller()
MODEL = "qwen/qwen3.8-27b"
def _compact_spec():
    s = open(f"{BASE}/SCHEMA_SPEC.md").read()
    hard = s.split("## Hard rules")[1].split("## Schema")[0]
    schema = s.split("## Schema")[1].split("## Reference example")[0]
    example = s.split("## Reference example")[1].split("## Self-check")[0]
    return ("## Hard rules" + hard + "\n## Schema" + schema + "\n## Reference example" + example).strip()

SPEC = _compact_spec()
REQ_FIELDS = ['id','name','sci','family','form','continent','regions','coords','habitat',
              'image','alt','parts','compounds','pharmacology','id_features','lookalikes',
              'prep','culture','legality','safety']

# --- config ---
NOTINK = {"chat_template_kwargs": {"enable_thinking": False}}
# MAXTOK set by make_caller(): 8000 direct (content-only, thinking off) / 16000 proxy fallback (thinking on)
TIMEOUT = 1800  # NEVER shorter than real gen time: abandoned calls keep generating server-side and clog the queue

def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(f"{BASE}/batches/progress.log", "a") as f:
        f.write(line + "\n")

def call(messages, timeout=TIMEOUT):
    global API, AUTH_HDRS, MAXTOK
    api, hdrs, maxtok = make_caller()  # re-discover each call: survives server restarts
    API, AUTH_HDRS, MAXTOK = api, hdrs, maxtok
    body = {"model": MODEL, "messages": messages, "max_tokens": MAXTOK, "temperature": 0.2}
    if NOTINK:
        body.update(NOTINK)
    hdrs = dict(hdrs)
    hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def extract_obj(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    txt = m.group(0) if m else raw
    return json.loads(txt)

SYS = (SPEC + "\n\nIMPORTANT: Output ONLY one raw JSON object for the given plant. "
       "No markdown, no code fences, no prose. All 19 top-level fields must be present "
       "(prep and culture nested). Use the provided image URL verbatim. "
       "Be accurate and measured; never invent studies or doses. Answer directly, do not deliberate.")

def author_one(item):
    base = "Plant data: " + json.dumps(item)
    last_err = ""
    for attempt in range(3):
        usr = base
        if last_err:
            usr += ("\n\nPrevious attempt was invalid: " + last_err +
                    "\nOutput only the corrected single JSON object.")
        try:
            full = call([{"role": "system", "content": SYS},
                         {"role": "user", "content": usr}])
        except Exception as e:
            last_err = f"request error: {e}"
            time.sleep(5)
            continue
        c = full["choices"][0]
        raw = (c.get("message", {}).get("content") or "").strip()
        if not raw:
            last_err = f"empty content (finish={c.get('finish_reason')}, usage={full.get('usage')})"
            continue
        try:
            obj = extract_obj(raw)
        except Exception as e:
            last_err = f"parse: {e}"
            continue
        problems = []
        for k in REQ_FIELDS:
            if k not in obj:
                problems.append(f"missing:{k}")
        if obj.get("image") != item["image"]:
            problems.append("image-not-verbatim")
        if obj.get("sci") != item["sci"]:
            problems.append("sci-mismatch")
        if not (isinstance(obj.get("prep"), dict) and "steps" in obj.get("prep", {})):
            problems.append("prep-bad")
        if not isinstance(obj.get("culture"), dict):
            problems.append("culture-bad")
        if problems:
            last_err = "; ".join(problems)
            continue
        return obj, True, ""
    return None, False, last_err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", nargs="*", default=None,
                    help="batch numbers, e.g. 01 02 03 (default: all)")
    args = ap.parse_args()
    import glob
    files = sorted(glob.glob(f"{BASE}/batches/in_*.json"))
    if args.batches:
        files = [f for f in files if re.search(r"in_(\d+)", f).group(1) in args.batches]
    total = sum(len(json.load(open(f))) for f in files)
    log(f"START {len(files)} batches, {total} plants, model={MODEL}, "
        f"notink={bool(NOTINK)}, maxtok={MAXTOK}")

    for f in files:
        bnum = re.search(r"in_(\d+)", f).group(1)
        items = json.load(open(f))
        jpath = f"{BASE}/batches/out_{bnum}.jsonl"
        spath = f"{BASE}/batches/state_{bnum}.json"
        done = {}
        try:
            done = json.load(open(spath)).get("done", {})
        except Exception:
            pass
        # resync state against jsonl (jsonl is content store; state is done-ness).
        # jsonl success lines carry NO input index, so match by sci name against
        # the input list (first occurrence wins) — never by line position.
        nlines = 0
        try:
            with open(jpath) as fh:
                nlines = sum(1 for _ in fh)
        except FileNotFoundError:
            pass
        if nlines != len(done):
            sci_to_idx = {}
            for i, it in enumerate(items):
                sci_to_idx.setdefault(it["sci"].strip().lower(), []).append(i)
            used = set()
            newdone = {}
            try:
                with open(jpath) as fh:
                    for line in fh:
                        o = json.loads(line)
                        if "__failed__" in o:
                            continue
                        cands = [i for i in sci_to_idx.get(o.get("sci", "").strip().lower(), [])
                                if i not in used]
                        if cands:
                            newdone[str(cands[0])] = o.get("id")
                            used.add(cands[0])
            except FileNotFoundError:
                pass
            done = newdone
            json.dump({"done": done}, open(spath, "w"))
            log(f"batch {bnum}: resynced state from jsonl by sci-match ({len(done)} done)")
        todo = [i for i in range(len(items)) if str(i) not in done]
        log(f"batch {bnum}: {len(items)} items, {len(done)} done, {len(todo)} todo")

        for i in todo:
            item = items[i]
            t0 = time.time()
            obj, ok, detail = author_one(item)
            dt = time.time() - t0
            if ok:
                with open(jpath, "a") as fh:
                    fh.write(json.dumps(obj) + "\n")
                done[str(i)] = obj.get("id")
                json.dump({"done": done}, open(spath, "w"))
                log(f"batch {bnum} [{i+1}/{len(items)}] {item['sci']}: OK {dt:.0f}s id={obj.get('id')}")
            else:
                with open(jpath, "a") as fh:
                    fh.write(json.dumps({"__failed__": item["sci"], "index": i, "err": detail}) + "\n")
                log(f"batch {bnum} [{i+1}/{len(items)}] {item['sci']}: FAILED ({detail[:120]})")
                time.sleep(2)

        objs = []
        try:
            with open(jpath) as fh:
                for line in fh:
                    o = json.loads(line)
                    if "__failed__" not in o:
                        objs.append(o)
        except FileNotFoundError:
            pass
        # integrity guard: no dup ids, sci coverage must match input exactly.
        ids = [o.get("id") for o in objs]
        scis_out = {o.get("sci", "").strip().lower() for o in objs}
        scis_in = {it["sci"].strip().lower() for it in items}
        if len(objs) == len(items) and len(ids) == len(set(ids)) and scis_out == scis_in:
            json.dump(objs, open(f"{BASE}/batches/out_{bnum}.js", "w"), indent=1)
            log(f"batch {bnum}: COMPLETE {len(objs)} -> out_{bnum}.js")
        else:
            log(f"batch {bnum}: INCOMPLETE/INCONSISTENT {len(objs)}/{len(items)} "
                f"(dup_ids={len(ids)-len(set(ids))}, sci_match={scis_out==scis_in}) — NOT writing js; re-run to fix gaps")
    log("ALL BATCHES DONE")

if __name__ == "__main__":
    main()
