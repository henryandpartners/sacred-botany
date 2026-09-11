#!/usr/bin/env python3
"""Search Wikimedia Commons for extra images per plant:
  - kind 'part': the plant part that contains the psychoactive substance
  - kind 'use' : how people consume / process the plant
Writes incremental results to more_images_progress.json (resumable).
"""
import json, re, time, urllib.parse, urllib.request, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
PROG = os.path.join(ROOT, "more_images_progress.json")
UA = {"User-Agent": "sacred-botany-research/1.0 (botanical reference site; contact: henryandpartners) python-urllib"}

# ---------- parse PLANTS ----------
def parse_plants(html):
    m = re.search(r'const PLANTS\s*=\s*\[', html)
    i = html.index('[', m.start()); depth = 0; in_str = None; esc = False
    while i < len(html):
        c = html[i]
        if in_str:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == in_str: in_str = None
        else:
            if c in '"\'': in_str = c
            elif c == '[': depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0: break
        i += 1
    arr = html[html.index('[', m.start()):i+1]
    out = []
    # split entries: top-level objects start at '{' with depth 1
    depth = 0; start = None; in_str = None; esc = False
    for i, c in enumerate(arr):
        if in_str:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == in_str: in_str = None
            continue
        if c in '"\'': in_str = c; continue
        if c == '{':
            if depth == 0: start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = arr[start:i+1]
                d = {}
                for key in ("id","name","sci","parts","prep","image","alt"):
                    mm = re.search(r'(?:"%s"\s*:\s*|(?<!\w)%s:)' % (key, key), chunk)
                    if not mm: continue
                    j = mm.end()
                    if chunk[j] == '"':
                        j2 = j+1; buf=[]; esc=False
                        while j2 < len(chunk):
                            ch = chunk[j2]
                            if esc: buf.append(ch); esc=False
                            elif ch == '\\': esc=True
                            elif ch == '"': break
                            else: buf.append(ch)
                            j2 += 1
                        d[key] = "".join(buf)
                    elif chunk[j] == '{' or chunk[j] == '[':
                        dd = 0
                        j2 = j; in_s=None; e2=False
                        while j2 < len(chunk):
                            ch = chunk[j2]
                            if in_s:
                                if e2: e2=False
                                elif ch=='\\': e2=True
                                elif ch==in_s: in_s=None
                            else:
                                if ch in '"\'': in_s=ch
                                elif ch=='{': dd+=1
                                elif ch=='}': dd-=1
                                elif ch=='[': dd+=1
                                elif ch==']': dd-=1
                            if dd==0 and j2>j: break
                            j2+=1
                        d[key] = chunk[j:j2+1]
                out.append(d)
                start = None
    return out

PART_KW = {
    "leaf": ["leaf"],
    "seed": ["seed"],
    "bark": ["bark"],
    "root": ["root"],
    "flower": ["flower"],
    "stem": ["stem"],
    "fruit": ["fruit"],
    "latex": ["latex"],
    "whole": ["plant"],
    "pod": ["pod"],
    "capsule": ["pod"],
    "spore": ["spore"],
    "fruitbody": ["cap"],
    "heartwood": ["wood"],
    "bud": ["bud"],
    "branch": ["branch"],
}
USE_KW = ["tea","infusion","decoction","chew","chewing","smoke","smoking","smoked",
          "snuff","incense","smudge","bath","ritual","ceremony","ceremonial","powder",
          "tincture","oil","resin","latize","honey","wine","beer","distill","drink",
          "dried","drying","preparation","people","village","market"]

def detect(words, text):
    t = text.lower()
    hits = []
    for w in words:
        if re.search(r'\b'+re.escape(w)+r'\b', t):
            hits.append(w)
    return hits

def queries_for(p):
    name = p.get("name","").strip()
    sci = p.get("sci","").strip()
    if "+" in sci:
        sci = sci.split("+")[0].strip()
    genus = sci.split()[0] if sci else ""
    parts = (p.get("parts","") or "").lower()
    prep = (p.get("prep","") or "").lower()
    # part keyword: match the concept name (family key) against the parts text
    part_kw = None
    for fam, kws in PART_KW.items():
        if re.search(r'\b'+re.escape(fam)+r'\w*', parts) or (fam in ("fruitbody","fruit") and any(w in parts for w in ("mushroom","fungus","spore","cap","button","crown"))):
            part_kw = kws[0]
            break
    if not part_kw:
        part_kw = "plant"
    # use keywords from prep text
    use_hits = detect(USE_KW, prep)
    if not use_hits:
        use_hits = ["dried", "tea"]
    use1 = use_hits[0]
    use2 = use_hits[1] if len(use_hits) > 1 else "preparation"
    qs = []
    if sci:
        qs.append(("part", f"filetype:bitmap {sci} {part_kw}"))
    if name and name != sci:
        qs.append(("part", f"filetype:bitmap {name} {part_kw}"))
    qs.append(("use", f"filetype:bitmap {name} {use1}"))
    qs.append(("use", f"filetype:bitmap {name} {use2}"))
    return qs, part_kw, (use1, use2)

# ---------- commons api ----------
API = "https://commons.wikimedia.org/w/api.php"
def commons_search(query, limit=20):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrlimit": str(limit),
        "gsrnamespace": "6",
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": "1280",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:
            last_err = e
            wait = 10 * (attempt + 1)
            print(f"    retry {attempt+1} after {type(e).__name__} — sleeping {wait}s", flush=True)
            time.sleep(wait)
    else:
        raise last_err
    pages = data.get("query", {}).get("pages", {})
    out = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata", {})
        desc = (em.get("ImageDescription", {}).get("value","") or "")
        cats = (em.get("Categories", {}).get("value","") or "")
        out.append({
            "title": pg.get("title",""),
            "thumb": ii.get("thumburl",""),
            "url": ii.get("url",""),
            "width": ii.get("width",0), "height": ii.get("height",0),
            "license": em.get("LicenseShortName",{}).get("value",""),
            "artist": re.sub(r'<[^>]+>','', em.get("Artist",{}).get("value","") or "")[:120],
            "desc": re.sub(r'<[^>]+>',' ', desc)[:300],
            "cats": re.sub(r'<[^>]+>',' ', cats)[:300],
        })
    return out

BAD_WORDS = re.compile(r'chemical structure|formula|molecule|crystal|diagram|map |icon|logo|'
                       r'line drawing|cartoon|3d render|rendering|skeletal|'
                       r'image from page|bulletin|plate |scanned|book page|encyclopaedia|encyclopedia', re.I)

def score(c, ident_names, kw, kind):
    s = 0
    title = c["title"].lower()
    txt = (c["title"] + " " + c["desc"] + " " + c["cats"]).lower()
    idents = [n.lower() for n in ident_names if n]
    # species must be confirmed in the FILE TITLE (desc alone lets in book scans / chemical diagrams)
    if not any(n in title for n in idents):
        return None
    matched = [n for n in idents if n in txt]
    s += 10 * (len(matched) >= 2) + 6 * (len(matched) == 1)
    if kw and re.search(r'\b'+re.escape(kw.lower())+r's?\b', txt): s += 8
    if c["width"] >= 900: s += 4
    elif c["width"] >= 600: s += 2
    if c["width"] < 450 or c["height"] < 320: return None
    if c["width"] and c["height"] and (c["width"]/c["height"] > 4 or c["height"]/c["width"] > 4): return None
    lic = c["license"].lower()
    if not lic or "no license" in lic: return None
    if BAD_WORDS.search(txt): return None
    if kind == "use" and not re.search(r'\b(tea|infusion|chew|smoke|snuff|incense|smudge|ritual|ceremon|dried|powder|tincture|bath|brew|prepar|people|market|village|drink|eat|cook|distill)\w*', txt):
        s -= 6
    if kind == "part" and not re.search(r'\b(leaf|leaves|seed|seeds|bark|root|roots|flower|flowers|fruit|fruits|stem|stems|vine|latex|resin|sap|whole|pod|pods|capsule|spore|cap|mushroom|wood|bud|buds|branch|twig|inflorescence|rhizome|plant)\w*', txt):
        s -= 6
    return s

def main():
    html = open(HTML, encoding="utf-8").read()
    plants = parse_plants(html)
    print(f"parsed {len(plants)} plants", flush=True)
    prog = {}
    if os.path.exists(PROG):
        prog = json.load(open(PROG, encoding="utf-8"))
    todo = [p for p in plants if p.get("id") and p["id"] not in prog]
    print(f"{len(todo)} to process, {len(plants)-len(todo)} already done", flush=True)
    zero_streak = 0  # consecutive zero-result calls (soft rate limit signal)
    for n, p in enumerate(todo):
        pid = p["id"]
        name = p.get("name",""); sci = p.get("sci","")
        if "+" in sci: sci = sci.split("+")[0].strip()
        ident = [x for x in [name, sci] if x]
        if sci:
            ident.append(sci.split()[0])
        main_img_file = os.path.basename(p.get("image","").split("?")[0])
        qs, part_kw, use_kws = queries_for(p)
        res = {"part": [], "use": []}
        seen = set()

        def good(kind):
            return len(res[kind])

        for qi, (kind, q) in enumerate(qs):
            kw = part_kw if kind == "part" else (use_kws[0] if q.endswith(use_kws[0]) else use_kws[-1])
            # adaptive skip: don't spend a call if we already have enough of this kind
            if qi > 0 and good(kind) >= 2:
                continue
            cands = None
            for attempt in range(2):
                try:
                    cands = commons_search(q)
                except Exception as e:
                    print(f"  {pid} ERROR {q!r}: {e}", flush=True)
                    time.sleep(3)
                    cands = None
                if cands and len(cands) > 0:
                    break
                if attempt == 0 and zero_streak >= 3:
                    # API looks soft-rate-limited -> pause and retry once
                    print(f"  {pid} soft-limit pause for {q!r}", flush=True)
                    time.sleep(15)
                    continue
                break  # zero results, treat as legitimate "no match"
            if not cands:
                zero_streak += 1
                continue
            zero_streak = 0
            time.sleep(2.0)
            best = []
            for c in cands:
                base = os.path.basename(c["url"].split("?")[0])
                if base == main_img_file or base in seen: continue
                sc = score(c, ident, kw, kind)
                if sc is not None:
                    c2 = dict(c); c2["score"] = sc; c2["query"] = q
                    best.append(c2)
            best.sort(key=lambda x: -x["score"])
            for b in best[:4]:
                seen.add(os.path.basename(b["url"].split("?")[0]))
                res[kind].append(b)
        prog[pid] = {"name": name, "sci": p.get("sci",""), "part_kw": part_kw,
                     "use_kws": list(use_kws), "part": res["part"][:6], "use": res["use"][:6]}
        json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False)
        if (n+1) % 10 == 0 or n == len(todo)-1:
            print(f"{n+1}/{len(todo)} done", flush=True)
    print("ALL DONE", flush=True)

if __name__ == "__main__":
    main()
