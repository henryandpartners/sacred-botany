#!/usr/bin/env node
/* Merge batches/out_XX.js entries into index.html PLANTS (dedupe by id + sci).
   Existing 29 entries are preserved verbatim; new entries appended as JSON.
   Usage: node scripts/merge_plants.js [--dry]
*/
const fs = require('fs');
const BASE = '/Users/henry/sacred-botany';
const DRY = process.argv.includes('--dry');

let html = fs.readFileSync(BASE + '/index.html', 'utf8');
const start = html.indexOf('const PLANTS = [');
if (start < 0) throw new Error('PLANTS array not found');
const openBracket = html.indexOf('[', start);
const closeMarker = html.indexOf('\n];', openBracket);
if (closeMarker < 0) throw new Error('PLATS close marker not found');
const inner = html.slice(openBracket + 1, closeMarker);

const existing = eval('[' + inner + ']');
const existingIds = new Set(existing.map(p => p.id));
const sciKey = s => (s || '').toLowerCase().replace(/[^a-z ]/g, '').trim().split(' ').slice(0, 2).join(' ');
const existingSci = new Set(existing.map(p => sciKey(p.sci)));

let added = 0;
const skipped = [];
const newParts = [];
for (let b = 1; b <= 11; b++) {
  const n = String(b).padStart(2, '0');
  const f = `${BASE}/batches/out_${n}.js`;
  if (!fs.existsSync(f)) { console.log(`MISSING ${f}`); continue; }
  const arr = eval(fs.readFileSync(f, 'utf8'));
  if (!Array.isArray(arr)) throw new Error(`out_${n}.js is not an array`);
  for (const p of arr) {
    const sk = sciKey(p.sci);
    if (existingIds.has(p.id) || existingSci.has(sk)) {
      skipped.push(`${p.id} (${p.sci})`);
      continue;
    }
    existingIds.add(p.id);
    existingSci.add(sk);
    newParts.push(JSON.stringify(p, null, 1));
    added++;
  }
}

const total = existing.length + added;
const continents = new Set([...existing, ...newParts.map(s => JSON.parse(s))].map(p => p.continent).filter(Boolean));
console.log(`existing=${existing.length} added=${added} skipped=${skipped.length} total=${total}`);
console.log(`continents=${continents.size}: ${[...continents].join(', ')}`);
if (skipped.length) {
  console.log('skipped duplicates:\n' + skipped.join('\n'));
}

if (!DRY && newParts.length) {
  const insert = ',\n' + newParts.join(',\n') + '\n';
  html = html.slice(0, closeMarker) + insert + html.slice(closeMarker);
  html = html.replace(/(<b>)29(<\/b> species profiled)/, `$1${total}$2`);
  if (continents.size !== 7) {
    console.log(`NOTE: continents=${continents.size} — update the "7 continents" chip manually?`);
  }
  fs.writeFileSync(BASE + '/index.html', html);
  console.log('index.html updated, count chip -> ' + total);
} else if (DRY) {
  console.log('dry run — no writes');
}
