#!/usr/bin/env node
/* Validate batches/out_XX.js against schema + input batches.
   Usage: node scripts/validate_out.js [NN ...]   (default: all existing)
*/
const fs = require('fs');
const BASE = '/Users/henry/sacred-botany';
const REQ = ['id','name','sci','family','form','continent','regions','coords','habitat',
  'image','alt','parts','compounds','pharmacology','id_features','lookalikes',
  'prep','culture','legality','safety'];

let nums = process.argv.slice(2);
if (!nums.length) {
  nums = fs.readdirSync(BASE + '/batches')
    .map(f => f.match(/^out_(\d{2})\.js$/))
    .filter(Boolean).map(m => m[1]).sort();
}

let allOk = true;
for (const n of nums) {
  const outPath = `${BASE}/batches/out_${n}.js`;
  const inPath = `${BASE}/batches/in_${n}.json`;
  if (!fs.existsSync(outPath)) { console.log(`${n}: MISSING out file`); allOk = false; continue; }
  const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));
  let arr;
  try { arr = eval(fs.readFileSync(outPath, 'utf8')); }
  catch (e) { console.log(`${n}: PARSE FAIL ${e.message}`); allOk = false; continue; }
  if (!Array.isArray(arr)) { console.log(`${n}: not an array`); allOk = false; continue; }

  const problems = [];
  if (arr.length !== input.length) problems.push(`count ${arr.length} != input ${input.length}`);
  const ids = new Set();
  arr.forEach((p, i) => {
    for (const k of REQ) if (!(k in p)) problems.push(`[${i}] missing ${k}`);
    if (ids.has(p.id)) problems.push(`[${i}] dup id ${p.id}`);
    ids.add(p.id);
    if (!/^[a-z0-9_]+$/.test(p.id || '')) problems.push(`[${i}] id not snake_case: ${p.id}`);
    const inp = input[i];
    if (inp) {
      if (p.sci !== inp.sci) problems.push(`[${i}] sci mismatch: ${p.sci} vs ${inp.sci}`);
      if (p.image !== inp.image) problems.push(`[${i}] image not verbatim`);
      if (typeof inp.compounds === 'string') {
        const c = (p.compounds || []).join(', ');
        for (const part of inp.compounds.split(/[;,]/).map(s => s.trim()).filter(Boolean)) {
          if (!c.toLowerCase().includes(part.toLowerCase().split(' ')[0]))
            problems.push(`[${i}] compound possibly missing: ${part}`);
        }
      }
    }
    if (!Array.isArray(p.regions) || p.regions.length < 2) problems.push(`[${i}] regions < 2`);
    if (!Array.isArray(p.coords) || p.coords.length !== 2 || p.coords.some(x => typeof x !== 'number'))
      problems.push(`[${i}] coords bad`);
    if (!Array.isArray(p.compounds) || !p.compounds.length) problems.push(`[${i}] compounds empty`);
    if (!Array.isArray(p.id_features) || p.id_features.length < 3) problems.push(`[${i}] id_features < 3`);
    if (!Array.isArray(p.lookalikes) || !p.lookalikes.length) problems.push(`[${i}] lookalikes empty`);
    if (!p.prep || typeof p.prep !== 'object') problems.push(`[${i}] prep not object`);
    else {
      for (const k of ['summary','steps','note']) if (!(k in p.prep)) problems.push(`[${i}] prep.${k} missing`);
      if (!Array.isArray(p.prep.steps) || p.prep.steps.length < 2) problems.push(`[${i}] prep.steps < 2`);
    }
    if (!p.culture || typeof p.culture !== 'object') problems.push(`[${i}] culture not object`);
    else {
      for (const k of ['cultures','ritual','context']) if (!(k in p.culture)) problems.push(`[${i}] culture.${k} missing`);
      if (!Array.isArray(p.culture.cultures) || p.culture.cultures.length < 2) problems.push(`[${i}] culture.cultures < 2`);
    }
    for (const k of ['name','family','form','continent','habitat','alt','parts','pharmacology','legality','safety'])
      if (typeof p[k] !== 'string' || p[k].length < 3) problems.push(`[${i}] ${k} too short/missing`);
  });

  if (problems.length) {
    allOk = false;
    console.log(`batch ${n}: FAIL (${arr.length}/${input.length})`);
    for (const p of problems.slice(0, 25)) console.log('  ' + p);
    if (problems.length > 25) console.log(`  ... +${problems.length - 25} more`);
  } else {
    console.log(`batch ${n}: OK (${arr.length} entries, all fields valid)`);
  }
}
process.exit(allOk ? 0 : 1);
