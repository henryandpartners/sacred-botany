#!/usr/bin/env node
/* Full audit: per-batch problem list (untruncated) + aggregate. */
const fs = require('fs');
const BASE = '/Users/henry/sacred-botany';
const REQ = ['id','name','sci','family','form','continent','regions','coords','habitat',
  'image','alt','parts','compounds','pharmacology','id_features','lookalikes',
  'prep','culture','legality','safety'];

// noise words: fragments that are location/part descriptions, not compound names
const NOISE = new Set(['the','and','in','on','of','stem','stems','leaves','leaf','bark','roots','root','seeds','seed','pods','pod','flowers','flower','fruits','fruit','beans','bean','whole','plant','etc','also','plus','plus','containing','contains','with','about','average','total','dried','fresh','trace','small','smaller','most','mostly','mainly','primarily','mostly','less','lesser','lower','higher','higher','higher','up','up-to','to','~','approx','approximately','syn.','synonyms','synonym','var','var.','subsp.','subspecies','sp.','species','aff.','aff','litorale','harazianum','taquimbalensis','malesiana','malesian','indica','indicus','orientalis','orientale','japonica','japonicus','japonicum','javanica','javanicus','javanicum','malabarica','madagascariensis','creta','cretica','terrestris','fabago','schoberi','nigellastrum','exelata','javanica','javanica']);

const AGG = {};
function agg(k){ (AGG[k] = AGG[k]||[]).length; }

const allIds = new Map(); // id -> [batch:i, ...]
for (let n = 1; n <= 11; n++) {
  const nn = String(n).padStart(2,'0');
  const outPath = `${BASE}/batches/out_${nn}.js`;
  const inPath = `${BASE}/batches/in_${nn}.json`;
  if (!fs.existsSync(outPath)) { console.log(`batch ${nn}: MISSING`); continue; }
  const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));
  const arr = eval(fs.readFileSync(outPath, 'utf8'));
  const problems = {};
  const idsIn = new Set();
  const sciSetOut = new Set(arr.map(p => (p.sci||'').trim().toLowerCase()));
  // sci coverage (order-independent)
  for (const inp of input) {
    const s = inp.sci.trim().toLowerCase();
    if (!sciSetOut.has(s) && !arr.some(p => (p.sci||'').toLowerCase().includes(s))) {
      (problems['sci_missing'] = problems['sci_missing']||[]).push(inp.sci);
    }
  }
  arr.forEach((p, i) => {
    const add = (k, v) => { (problems[k] = problems[k]||[]).push(v); };
    for (const k of REQ) if (!(k in p)) add('missing_field', `[${i}] ${k}`);
    if (idsIn.has(p.id)) add('dup_id_in_batch', p.id);
    idsIn.add(p.id);
    if (allIds.has(p.id)) allIds.get(p.id).push(`${nn}:${i}`); else allIds.set(p.id, [`${nn}:${i}`]);
    if (!/^[a-z0-9_]+$/.test(p.id || '')) add('bad_id', `[${i}] ${p.id}`);
    const inp = input[i];
    if (inp) {
      if ((p.sci||'').trim() !== inp.sci.trim()) add('sci_mismatch', `[${i}] out=${p.sci} in=${inp.sci}`);
      if (p.image !== inp.image) add('image_not_verbatim', `[${i}]`);
      if (typeof inp.compounds === 'string' && inp.compounds.trim()) {
        const c = (p.compounds || []).join(', ').toLowerCase();
        for (const frag of inp.compounds.split(/[;,]/).map(s => s.trim()).filter(Boolean)) {
          const first = frag.split(/\s+/)[0].replace(/^[~(\d].*$/,'').toLowerCase();
          if (NOISE.has(first) || first.length < 3) continue;
          if (!c.includes(first)) add('compound_missing', `[${i}] ${frag.slice(0,60)}`);
        }
      }
    }
    if (!Array.isArray(p.regions) || p.regions.length < 2) add('regions_lt2', `[${i}] ${(p.regions||[]).length}`);
    if (!Array.isArray(p.coords) || p.coords.length !== 2 || p.coords.some(x => typeof x !== 'number')) add('coords_bad', `[${i}]`);
    if (!Array.isArray(p.compounds) || !p.compounds.length) add('compounds_empty', `[${i}] ${p.sci}`);
    if (!Array.isArray(p.id_features) || p.id_features.length < 3) add('id_features_lt3', `[${i}]`);
    if (!Array.isArray(p.lookalikes) || !p.lookalikes.length) add('lookalikes_empty', `[${i}]`);
    if (!p.prep || typeof p.prep !== 'object') add('prep_bad', `[${i}]`);
    else {
      for (const k of ['summary','steps','note']) if (!(k in p.prep)) add('prep_field', `[${i}] ${k}`);
      if (!Array.isArray(p.prep.steps) || p.prep.steps.length < 2) add('prep_steps_lt2', `[${i}]`);
    }
    if (!p.culture || typeof p.culture !== 'object') add('culture_bad', `[${i}]`);
    else {
      for (const k of ['cultures','ritual','context']) if (!(k in p.culture)) add('culture_field', `[${i}] ${k}`);
      if (!Array.isArray(p.culture.cultures) || p.culture.cultures.length < 2) add('cultures_lt2', `[${i}] ${p.sci}: ${(p.culture.cultures||[]).join('; ')}`);
    }
    for (const k of ['name','family','form','continent','habitat','alt','parts','pharmacology','legality','safety'])
      if (typeof p[k] !== 'string' || p[k].length < 3) add('field_short', `[${i}] ${k}`);
  });
  const hard = ['sci_missing','sci_mismatch','image_not_verbatim','dup_id_in_batch','missing_field','compounds_empty','regions_lt2','cultures_lt2','coords_bad','prep_bad','culture_bad','prep_steps_lt2','id_features_lt3','lookalikes_empty'];
  console.log(`\n=== batch ${nn} (${arr.length}/${input.length}) ===`);
  const keys = Object.keys(problems).sort();
  if (!keys.length) console.log('  CLEAN');
  for (const k of keys) {
    const list = problems[k];
    console.log(`  ${k}: ${list.length}`);
    for (const v of list) console.log(`    ${v}`);
  }
}
const globalDups = [...allIds.entries()].filter(([k,v]) => v.length > 1);
if (globalDups.length) {
  console.log('\n=== GLOBAL ID COLLISIONS (across batches) ===');
  for (const [k,v] of globalDups) console.log(`  ${k}: ${v.join(', ')}`);
}
console.log('\nDONE');
