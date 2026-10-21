#!/usr/bin/env python3
"""Integrate the Psychoactive Plants Atlas dataset into sacred-botany index.html.

Inserts: (1) atlas CSS into <style>, (2) atlas section between grid-sec and
footer, (3) <script src=atlas_data.js> before main script, (4) atlas renderer
after the main script. Idempotent: skips if already integrated.
"""
import re
import sys

PATH = "/Users/fathomers/workspace/sacred-botany/index.html"
t = open(PATH).read()

if 'id="atlas-sec"' in t:
    print("already integrated"); sys.exit(0)

CSS = """
/* ---------- Atlas dataset ---------- */
.at-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:26px}
.at-stat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
.at-stat b{display:block;font-size:24px;color:var(--gold2);font-variant-numeric:tabular-nums}
.at-stat span{font-size:12px;color:var(--muted)}
.at-tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.at-tools input,.at-tools select{background:var(--panel);border:1px solid var(--line2);color:var(--text);border-radius:10px;padding:10px 14px;font-size:14px;min-width:160px}
.at-tools input{flex:1}
.at-list{display:flex;flex-direction:column;gap:10px}
.at-row{display:grid;grid-template-columns:1.6fr 1.4fr 1fr auto;gap:14px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 18px;transition:border-color .2s}
.at-row:hover{border-color:var(--line2)}
.at-row .nm{font-weight:600}
.at-row .nm .sci{display:block;font-weight:400;font-size:12px;color:var(--faint);font-style:italic}
.at-row .cul{font-size:13px;color:var(--muted)}
.at-row .cul b{color:var(--text);font-weight:600;display:block;font-size:13px}
.at-row .nums{display:flex;gap:14px;font-size:12px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.at-row .nums b{display:block;color:var(--green2);font-size:15px}
.at-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.at-chip{font-size:11px;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 10px;color:var(--muted)}
.at-chip b{color:var(--gold2);font-weight:600}
.at-src{margin-top:22px;font-size:12px;color:var(--faint);line-height:1.7}
.at-src a{color:var(--muted)}
.at-tabs{display:flex;gap:8px;margin-bottom:16px}
.at-tab{background:var(--panel);border:1px solid var(--line);color:var(--muted);border-radius:999px;padding:8px 18px;font-size:13px;cursor:pointer}
.at-tab.on{border-color:var(--gold);color:var(--gold2)}
@media(max-width:820px){
  .at-row{grid-template-columns:1fr auto}
  .at-row .cul{grid-column:1/-1}
  .at-row .nums{gap:18px}
}
"""

HTML = """
<section id="atlas-sec">
  <div class="wrap">
    <div class="sec-head">
      <div>
        <h2>The Living Dataset</h2>
        <p>Every species joined with global biodiversity records, field observations, and phytochemistry &mdash; a quantitative companion to the profiles above.</p>
      </div>
      <span class="count" id="atlascount"></span>
    </div>
    <div class="at-stats" id="atstats"></div>
    <div class="at-tabs">
      <button class="at-tab on" data-tab="taxa" id="attab-taxa">By Species</button>
      <button class="at-tab" data-tab="compounds" id="attab-compounds">By Compound</button>
    </div>
    <div class="at-tools" id="attools">
      <input id="atq" type="search" placeholder="Search species, culture, compound&hellip;" aria-label="Search atlas">
      <select id="atregion" aria-label="Filter by region"><option value="">All regions</option></select>
    </div>
    <div class="at-list" id="atlist"></div>
    <p class="at-src">Data joined live from <a href="https://www.gbif.org" target="_blank" rel="noopener">GBIF</a> (biodiversity occurrences &amp; living botanical-garden collections), <a href="https://www.inaturalist.org" target="_blank" rel="noopener">iNaturalist</a>, <a href="https://pubchem.ncbi.nlm.nih.gov" target="_blank" rel="noopener">PubChem</a>, <a href="https://psychonautwiki.org" target="_blank" rel="noopener">PsychonautWiki</a>, <a href="https://openalex.org" target="_blank" rel="noopener">OpenAlex</a> and <a href="https://wikidata.org" target="_blank" rel="noopener">Wikidata</a>. Updated <span id="atgen"></span>.</p>
  </div>
</section>
"""

JS = """
/* ============================== ATLAS DATASET ============================== */
(function(){
  if (!window.ATLAS) return;
  const A = window.ATLAS;
  const $ = id => document.getElementById(id);
  const COUNTRY = {US:"United States",NL:"Netherlands",GB:"United Kingdom",DE:"Germany",FR:"France",SE:"Sweden",BE:"Belgium",DK:"Denmark",BR:"Brazil",AR:"Argentina",BO:"Bolivia",PY:"Paraguay",PE:"Peru",MX:"Mexico",CO:"Colombia",EC:"Ecuador",VE:"Venezuela",CL:"Chile",AU:"Australia",NZ:"New Zealand",PG:"Papua New Guinea",ID:"Indonesia",PF:"French Polynesia",PH:"Philippines",SB:"Solomon Islands",FJ:"Fiji",IN:"India",CN:"China",JP:"Japan",TH:"Thailand",VN:"Vietnam",MY:"Malaysia",ZA:"South Africa",ET:"Ethiopia",KE:"Kenya",YE:"Yemen",EG:"Egypt",MA:"Morocco",TN:"Tunisia",IR:"Iran",TR:"Turkey",RU:"Russia",UA:"Ukraine",PL:"Poland",CZ:"Czechia",IT:"Italy",ES:"Spain",PT:"Portugal",CA:"Canada",NO:"Norway",FI:"Finland",CH:"Switzerland",AT:"Austria",HU:"Hungary",RO:"Romania",GR:"Greece",BG:"Bulgaria",CR:"Costa Rica",GT:"Guatemala",PA:"Panama",CU:"Cuba",DO:"Dominican Rep.",HT:"Haiti",JM:"Jamaica",MW:"Malawi",MZ:"Mozambique",TZ:"Tanzania",UG:"Uganda",ZM:"Zambia",ZW:"Zimbabwe",GH:"Ghana",NG:"Nigeria",SN:"Senegal",CM:"Cameroon",CD:"DR Congo",GA:"Gabon",CG:"Congo",CMR:"Cameroon",LA:"Laos",KH:"Cambodia",MM:"Myanmar",NP:"Nepal",PK:"Pakistan",BD:"Bangladesh",LK:"Sri Lanka",TW:"Taiwan",KR:"South Korea",KP:"North Korea",MN:"Mongolia",KZ:"Kazakhstan",UZ:"Uzbekistan",TM:"Turkmenistan",AF:"Afghanistan",IQ:"Iraq",SY:"Syria",LB:"Lebanon",IL:"Israel",JO:"Jordan",SA:"Saudi Arabia",AE:"UAE",OM:"Oman",QA:"Qatar",KW:"Kuwait",BH:"Bahrain",YE2:"Yemen"};
  // link ATLAS taxa to site PLANTS profiles (fuzzy sci-name match)
  const plantBySci = {};
  (window.PLANTS||[]).forEach(p=>{
    const key = (p.sci||"").split(/[(+]/)[0].trim().toLowerCase();
    if (key) plantBySci[key] = p;
  });
  const linkFor = t => {
    const hit = plantBySci[t.scientific_name.toLowerCase()] ||
                Object.keys(plantBySci).find(k => t.scientific_name.toLowerCase().startsWith(k));
    return hit ? plantBySci[hit] : null;
  };
  const REGIONS = ["Amazonia","Andes","Mesoamerica","Mexico","South America","Africa","Europe","Asia","India","China","Thailand","SE Asia","Pacific","Middle East","Worldwide","global"];
  const regionOf = t => {
    const c = (t.culture||"").toLowerCase();
    if (/amazon/.test(c)) return "Amazonia";
    if (/ande/.test(c)) return "Andes";
    if (/aztec|mexic|mesoam/.test(c)) return "Mesoamerica";
    if (/africa/.test(c)) return "Africa";
    if (/europe/.test(c)) return "Europe";
    if (/india|sanskrit|vedic/.test(c)) return "India";
    if (/china|chinese|tcm/.test(c)) return "China";
    if (/thailand|thai/.test(c)) return "Thailand";
    if (/se asia|pacific/.test(c)) return "SE Asia & Pacific";
    if (/polynesia|pacific/.test(c)) return "Pacific";
    if (/siberia|russia/.test(c)) return "Siberia";
    if (/egypt|middle east|persia|mesopotamia|near east/.test(c)) return "Middle East";
    if (/global|worldwide/.test(c)) return "Global";
    return "Other";
  };

  function fmt(n){ return (n||0).toLocaleString("en-US"); }

  function renderStats(){
    const occ = A.taxa.reduce((s,t)=>s+(t.occurrence_count||0),0);
    const liv = A.taxa.reduce((s,t)=>s+(t.living_specimen_count||0),0);
    const inat = A.taxa.reduce((s,t)=>s+(t.inat_observations||0),0);
    $("atstats").innerHTML = [
      [fmt(A.taxa.length),"species &amp; fungi"],
      [fmt(A.compounds.length),"compounds mapped"],
      [fmt(occ),"GBIF occurrence records"],
      [fmt(liv),"living garden specimens"],
      [fmt(inat),"field observations"]
    ].map(([b,s])=>`<div class="at-stat"><b>${b}</b><span>${s}</span></div>`).join("");
    $("atgen").textContent = A.generated;
    $("atlascount").textContent = A.taxa.length + " entries";
  }

  let TAB = "taxa";
  function renderTabs(){
    ["taxa","compounds"].forEach(x=>{
      const el=$("attab-"+x); if(!el) return;
      el.onclick=()=>{ TAB=x; document.querySelectorAll(".at-tab").forEach(b=>b.classList.toggle("on",b.dataset.tab===x)); renderList(); };
    });
  }

  function chipsFor(t){
    return (t.compounds||[]).slice(0,4).map(c=>`<span class="at-chip"><b>${esc(c.name)}</b>${c.formula?` · ${esc(c.formula)}`:""}</span>`).join("");
  }

  function renderList(){
    const q = ($("atq").value||"").toLowerCase().trim();
    const reg = $("atregion").value;
    const list = $("atlist");
    if (TAB==="compounds"){
      const rows = A.compounds.filter(c=>!q || c.name.toLowerCase().includes(q) || (c.plants||[]).join(" ").toLowerCase().includes(q))
        .sort((a,b)=>(b.plants||[]).length-(a.plants||[]).length);
      list.innerHTML = rows.map(c=>`
        <div class="at-row" style="grid-template-columns:1fr 1.2fr auto">
          <div class="nm">${esc(c.name)}${c.formula?`<span class="sci">${esc(c.formula)}${c.mw?` · ${c.mw} g/mol`:""}</span>`:""}</div>
          <div class="cul"><b>${(c.plants||[]).length} species</b>${esc((c.plants||[]).slice(0,4).join(", "))}${(c.plants||[]).length>4?" &hellip;":""}</div>
          <div></div>
        </div>`).join("");
      $("atregion").style.display="none";
      return;
    }
    $("atregion").style.display="";
    const rows = A.taxa.filter(t=>{
      if (reg && regionOf(t)!==reg) return false;
      if (!q) return true;
      const hay = [t.scientific_name,t.common_names,t.culture,t.compounds_str,(t.compounds||[]).map(c=>c.name).join(" ")].join(" ").toLowerCase();
      return hay.includes(q);
    }).sort((a,b)=>(b.occurrence_count||0)-(a.occurrence_count||0));
    list.innerHTML = rows.map(t=>{
      const p = linkFor(t);
      const top = Object.entries(t.top_countries||{}).slice(0,2).map(([k,v])=>`${COUNTRY[k]||k}`).join(", ");
      return `
        <div class="at-row">
          <div class="nm">${esc(t.common_names?t.common_names.split(",")[0]:t.scientific_name)}
            <span class="sci">${esc(t.scientific_name)}</span>
            <div class="at-chips">${chipsFor(t)}</div>
          </div>
          <div class="cul"><b>${esc(t.culture||"")}</b>part used: ${esc(t.part_used||"—")}${top?` · recorded in ${esc(top)}&hellip;`:""}</div>
          <div class="nums">
            <div><b>${fmt(t.occurrence_count)}</b>records</div>
            <div><b>${fmt(t.living_specimen_count)}</b>in gardens</div>
            <div><b>${fmt(t.inat_observations)}</b>field obs</div>
          </div>
          <div>
            ${p?`<button class="at-chip" style="cursor:pointer" onclick="openDetail('${p.id}')">View profile &rarr;</button>`:""}
            ${t.gbif_usage_key?`<a class="at-chip" href="https://www.gbif.org/occurrence/search?taxonKey=${t.gbif_usage_key}" target="_blank" rel="noopener">GBIF ↗</a>`:""}
          </div>
        </div>`;
    }).join("");
  }

  function init(){
    // region filter options
    const regs = [...new Set(A.taxa.map(regionOf))].sort();
    const sel = $("atregion");
    regs.forEach(r=>{ const o=document.createElement("option"); o.value=r; o.textContent=r; sel.appendChild(o); });
    $("atq").addEventListener("input", renderList);
    sel.addEventListener("change", renderList);
    renderStats(); renderTabs(); renderList();
  }
  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
"""

# ---- 1. CSS (append before closing </style>)
anchor = t.rfind("</style>")
assert anchor > 0, "style anchor missing"
t = t[:anchor] + CSS + t[anchor:]

# ---- 2. HTML section: insert after grid-sec's closing </section>, before <footer>
m = re.search(r'(<section id="grid-sec".*?</section>)', t, re.S)
assert m, "grid-sec anchor missing"
t = t.replace(m.group(1), m.group(1) + HTML, 1)

# ---- 3. atlas_data.js script before the main inline script
m2 = re.search(r'<script>\s*\n/\* =+ DATA', t)
assert m2, "main script anchor missing"
t = t.replace(m2.group(0), '<script src="atlas_data.js"></script>\n' + m2.group(0), 1)

# ---- 4. renderer after the main script's closing tag, before </body>
m3 = re.search(r'(</script>)\s*</body>', t)
assert m3, "body-close anchor missing"
t = t.replace(m3.group(0), m3.group(1) + "\n<script>\n" + JS + "\n</script>\n</body>", 1)

open(PATH, "w").write(t)
print("integrated: CSS %d B, HTML %d B, JS %d B -> index.html now %d KB" % (
    len(CSS), len(HTML), len(JS), len(t) // 1024))
