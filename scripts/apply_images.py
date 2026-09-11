#!/usr/bin/env python3
"""Curation + injection step.

Reads more_images_progress.json (candidate images per plant found via the
Wikimedia Commons API), curates up to 2 'part' + 2 'use' images per plant,
and injects a `gimg:[...]` field into each PLANTS entry in index.html.

Also applies (idempotently):
  - CSS for the .gimg gallery
  - an "In Pictures" block in the detail-sheet template
  - renumbering of the following numbered sections

Usage: python3 scripts/apply_images.py [--dry-run]
"""
import json, os, re, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
PROG = os.path.join(ROOT, "more_images_progress.json")
MAX_PER_KIND = 2


def plant_spans(html):
    """[(id, start, end)] for top-level objects in `const PLANTS = [...]` (file offsets)."""
    m = re.search(r'const PLANTS\s*=\s*\[', html)
    if not m:
        raise SystemExit("PLANTS array not found")
    s = html.index('[', m.start())
    i = s
    depth = 0
    in_str = None
    esc = False
    while i < len(html):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == in_str:
                in_str = None
        else:
            if c in '"\'':
                in_str = c
            elif c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    break
        i += 1
    arr_end = i
    out = []
    depth = 0
    start = None
    in_str = None
    esc = False
    for j in range(s, arr_end + 1):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == in_str:
                in_str = None
            continue
        if c in '"\'':
            in_str = c
            continue
        if c == '{':
            if depth == 0:
                start = j
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = html[start:j + 1]
                mm = re.search(r'(?:\{|\,)\s*(?:"id"|id)\s*:\s*"([^"]+)"', chunk)
                pid = mm.group(1) if mm else None
                out.append((pid, start, j))
                start = None
    return out


def caption(title):
    t = title or ""
    if t.startswith("File:"):
        t = t[5:]
    t = re.sub(r'\.(jpe?g|png|gif|tiff?|svg|webp)$', '', t, flags=re.I)
    t = t.replace('_', ' ').strip()
    return t


USE_WORDS_T = re.compile(r'\b(tea|infusion|decoction|chew|chewing|smoke|smoking|snuff|incense|smudge|ritual|ceremon|dried|drying|powder|tincture|bath|brew|prepar\w*|people|market|village|drink\w*|eat\w*|cook\w*|distill\w*|ceremony)\w*', re.I)
PART_WORDS_T = re.compile(r'\b(leaf|leaves|seed|seeds|bark|root|roots|flower|flowers|stem|stems|vine|vines|latex|resin|sap|whole|pod|pods|capsule|spore|cap|caps|gill|gills|mushroom|fungus|wood|bud|buds|branch|twigs?|inflorescence|rhizome|plant|herb|herbs|flowering|inflorescen)\w*', re.I)
BAD_WORDS_APPLY = re.compile(r'anaglyph|stereo pair|cross-?eyed|chemical structure|formula|molecule|crystal|diagram|distmap|distribution map|range map|\bmap\b|icon|logo|line drawing|cartoon|3d render|rendering|skeletal|image from page|bulletin|plate |scanned|book page|encyclopaedia|encyclopedia|prohibited|billboard|road sign|traffic sign|wellcome [lm]\d{4,}|leaf plate', re.I)

# Manual rejects from manual review: pid -> lowercase title substrings
MANUAL_REJECTS = {
    "acacia_confusa": ["kudzu"],            # those photos are Pueraria (different genus)
    "senegalia_mellifera": ["palustris", "cousin itt", "kaleidoscope"],
    "vachellia_nilotica": ["cousin itt", "kaleidoscope"],
    "citrus_limon": ["citrus flower 2019"], # generic citrus flower, species unverified
    "papaver_paeoniflorum": ["papaversomniferum"],  # P. somniferum photo
    # generic passionflower photos don't verify the specific species
    "passiflora_actinia": ["passiflorae herba"],
    "passiflora_bryonoides": ["passiflorae herba"],
    "passiflora_capsularis": ["passiflorae herba"],
    "passiflora_decaisneana": ["income tax colony", "wide passion flower"],
    "passiflora_edulis": ["unidentified"],
    "passiflora_ruberosa": ["lobby card", "income tax colony", "passion flower passiflora flower", "the passion flower (1921)", "wide passion flower"],
    "passiflora_subpeltata": ["passiflorae herba"],
    "passiflora_warmingii": ["genus passiflora", "in bloom", "passiflorae herba", "sinking passionflower"],
    "tribulus_terrestris": ["uziza", "pine bark"],  # multi-product vendor listing
}

# Words that look like a binomial 'Genus word' but are common nouns/adjectives,
# not species epithets — used to avoid false same-genus conflicts.
NOT_SPECIES = {
    "flower", "flowers", "blossom", "blossoms", "seed", "seeds", "leaf", "leaves",
    "bark", "root", "roots", "stem", "stems", "fruit", "fruits", "plant", "plants",
    "habit", "whole", "wood", "bud", "buds", "branch", "branches", "grass", "herb",
    "herbs", "mushroom", "mushrooms", "cactus", "cacti", "tree", "trees", "shrub",
    "vine", "vines", "petal", "petals", "gill", "gills", "spore", "spores",
    "capsule", "capsules", "pod", "pods", "sap", "resin", "latex", "dried",
    "drying", "powder", "tea", "infusion", "decoction", "chew", "chewing",
    "smoke", "smoking", "snuff", "incense", "smudge", "ritual", "ceremony",
    "ceremonies", "bath", "tincture", "image", "photo", "picture", "file",
    "page", "wellcome", "dpla", "flickr", "commons", "wikipedia", "user",
    "self", "published", "work", "hybrid", "hibrida", "hibrida", "hybrida",
    "common", "japanese", "chinese", "indian", "american", "european",
    "australian", "african", "mexican", "brazilian", "korean", "thai",
    "vietnamese", "filipino", "hawaiian", "national", "botanical", "garden",
    "park", "reserve", "region", "county", "city", "town", "village",
    "mountain", "valley", "lake", "river", "beach", "coast", "forest",
    "jungle", "meadow", "field", "desert", "specimen", "herbarium",
    "collection", "museum", "library", "university", "institute",
    "red", "green", "yellow", "white", "black", "blue",
}


def parse_sci(sci):
    """genus, species, accepted binomials (synonyms from the sci string),
    any_species flag ('and related species' / 'various' entries)."""
    s = sci or ""
    any_species = bool(re.search(r'and\s+(related|relatives|other|various)|\bvarious\b', s, re.I))
    bins = re.findall(r'\b([A-Z][a-z]{1,20})\s+([a-z][a-z]{1,20})\b', s)
    accepted = {"%s %s" % (g.lower(), sp.lower()) for g, sp in bins}
    genus = bins[0][0] if bins else ""
    species = bins[0][1] if bins else ""
    return genus, species, accepted, any_species


def same_genus_conflict(title, genus, species, accepted, any_species):
    """Reject when the title shows the target genus with a DIFFERENT species,
    unless the target species/synonym is in the title, or the entry covers
    several species ('and related species')."""
    if not genus or not species or any_species:
        return False
    if re.search(r'\b' + re.escape(genus) + r'\s+' + re.escape(species) + r'\b', title, re.I):
        return False
    m = re.search(r'\b' + re.escape(genus) + r'\s+([a-z][a-z]{1,20})\b', title, re.I)
    if not m:
        return False
    w = m.group(1).lower()
    if w in NOT_SPECIES:
        return False
    if "%s %s" % (genus.lower(), w) in accepted:
        return False
    return True


def corroborated(c, kind, genus, weak_words=("plant", "herb", "whole")):
    """A name-in-title hit must be corroborated: a kind keyword in the title,
    or the genus appearing anywhere in title+desc+cats. Kills short common-name
    false positives ('San Pedro' city photos, people names, etc.).
    Weak keywords ('plant'/'herb'/'whole') also collide with factory names,
    so they additionally require the genus somewhere in the metadata."""
    t = c.get("title", "") or ""
    txt = (t + " " + (c.get("desc") or "") + " " + (c.get("cats") or "")).lower()
    if BAD_WORDS_APPLY.search(txt):
        return False
    wordre = USE_WORDS_T if kind == "use" else PART_WORDS_T
    m = wordre.search(t)
    if m:
        matched = m.group(0).lower()
        if any(w in matched for w in weak_words) and not (genus and genus.lower() in txt):
            return False
        return True
    if genus and genus.lower() in txt:
        return True
    return False


def pick(cands, excluded, n, name, kw, kind, pid, genus="", species="", accepted=frozenset(), any_species=False):
    out = []
    ranked = sorted([c for c in cands if c.get("score", 0) > 0], key=lambda x: -x["score"])
    rejects = MANUAL_REJECTS.get(pid, [])
    for c in ranked:
        base = os.path.basename(c.get("url", "").split("?")[0])
        if not base or base in excluded:
            continue
        if not c.get("thumb"):
            continue
        lic = (c.get("license") or "").lower()
        if not lic or "no license" in lic:
            continue
        title = c.get("title", "") or ""
        if any(r in title.lower() for r in rejects):
            continue
        if same_genus_conflict(title, genus, species, accepted, any_species):
            continue
        if not corroborated(c, kind, genus):
            continue
        out.append({
            "u": c["thumb"],
            "a": f"{name} — {kw}" if kw else name,
            "c": caption(c.get("title", "")),
            "k": kind,
        })
        excluded.add(base)
        if len(out) >= n:
            break
    return out


GALLERY_BLOCK = """
      ${p.gimg && p.gimg.length ? `
      <div class="block">
        <h4><span class="n">3</span> In Pictures</h4>
        ${p.gimg.some(g=>g.k==="part") ? `
        <div class="gimg-sec">The psychoactive part</div>
        <div class="gimg">${p.gimg.filter(g=>g.k==="part").map(g=>`<figure><img src="${g.u}" alt="${esc(g.a)}" loading="lazy"><figcaption>${esc(g.c)}</figcaption></figure>`).join("")}</div>` : ""}
        ${p.gimg.some(g=>g.k==="use") ? `
        <div class="gimg-sec">How it's used</div>
        <div class="gimg">${p.gimg.filter(g=>g.k==="use").map(g=>`<figure><img src="${g.u}" alt="${esc(g.a)}" loading="lazy"><figcaption>${esc(g.c)}</figcaption></figure>`).join("")}</div>` : ""}
        <div class="credit" style="margin-top:10px">Photographs: Wikimedia Commons (freely licensed).</div>
      </div>` : ""}
"""

CSS = """
  .gimg{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-top:8px}
  .gimg figure{margin:0;background:var(--bg2);border:1px solid var(--line);border-radius:12px;overflow:hidden}
  .gimg img{width:100%;height:130px;object-fit:cover;display:block}
  .gimg figcaption{font-size:11.5px;color:var(--muted);padding:7px 9px;line-height:1.4}
  .gimg-sec{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--gold2);margin:14px 0 2px}
"""


def main():
    dry = "--dry-run" in sys.argv
    html = open(HTML, encoding="utf-8").read()
    prog = json.load(open(PROG, encoding="utf-8"))

    # ---- curate per plant ----
    gimg_by_id = {}
    for pid, rec in prog.items():
        excl = set()
        name = rec.get("name", "")
        genus, species, accepted, any_species = parse_sci(rec.get("sci", ""))
        part_kw = rec.get("part_kw", "plant")
        use_kws = rec.get("use_kws", ["", ""])
        parts = pick(rec.get("part", []), excl, MAX_PER_KIND, name, part_kw, "part", pid, genus, species, accepted, any_species)
        uses = pick(rec.get("use", []), excl, MAX_PER_KIND, name, use_kws[0] if use_kws else "", "use", pid, genus, species, accepted, any_species)
        g = parts + uses
        if g:
            gimg_by_id[pid] = g
    n_plants = len(gimg_by_id)
    n_imgs = sum(len(v) for v in gimg_by_id.values())
    print(f"curated {n_imgs} images for {n_plants} plants ({len(prog)} records)")

    # ---- inject gimg fields (idempotent) ----
    spans = plant_spans(html)
    print(f"found {len(spans)} PLANTS entries")
    edits = []  # (pos, text) insertions, applied right-to-left
    injected = 0
    for pid, start, end in spans:
        if pid not in gimg_by_id:
            continue
        if "gimg" in html[start:end]:
            continue
        payload = ",gimg:" + json.dumps(gimg_by_id[pid], ensure_ascii=False)
        edits.append((end, payload))
        injected += 1
    print(f"would inject gimg into {injected} entries" + (" (dry run)" if dry else ""))

    # ---- template + CSS patches (idempotent) ----
    patch_log = []
    if '.gimg{' not in html:
        i = html.find("</style>")
        if i == -1:
            raise SystemExit("no </style> found")
        edits.append((i, CSS))
        patch_log.append("css")
    else:
        patch_log.append("css (already)")
    if "In Pictures" not in html:
        anchor = '        <div class="note">${esc(p.prep.note)}</div>\n      </div>'
        j = html.find(anchor)
        if j == -1:
            raise SystemExit("template anchor not found (prep.note)")
        pos = j + len(anchor)
        edits.append((pos, GALLERY_BLOCK))
        # renumber following sections
        for old, new in [
            ('<span class="n">3</span> Pharmacology', '<span class="n">4</span> Pharmacology'),
            ('<span class="n">4</span> Where It Grows', '<span class="n">5</span> Where It Grows'),
            ('<span class="n">5</span> Culture &amp; Ritual', '<span class="n">6</span> Culture &amp; Ritual'),
        ]:
            k = html.find(old)
            if k == -1:
                print(f"WARNING: renumber anchor missing: {old[:40]}")
                continue
            edits.append((k, new))
        patch_log.append("template")
    else:
        patch_log.append("template (already)")
    print("patches:", ", ".join(patch_log))

    if dry:
        for pid, g in list(gimg_by_id.items())[:8]:
            print(f"  {pid}: {[x['k'] + ':' + x['c'][:38] for x in g]}")
        return

    # ---- apply edits (right-to-left to keep offsets valid) ----
    for pos, text in sorted(edits, key=lambda x: -x[0]):
        html = html[:pos] + text + html[pos:]

    bak = HTML + ".bak-imgx"
    if not os.path.exists(bak):
        shutil.copyfile(HTML, bak)
    open(HTML, "w", encoding="utf-8").write(html)
    print(f"wrote {HTML} ({len(html)} chars), backup at {bak}")


if __name__ == "__main__":
    main()
