#!/usr/bin/env python3
import json
from collections import Counter
inv = json.load(open('/tmp/sb_inventory.json'))
inv_ids = [r['id'] for r in inv]
A = json.load(open('enrich_a.json'))
B = json.load(open('enrich_b.json'))
invset = set(inv_ids)
aset, bset = set(A), set(B)
print("inventory:", len(inv_ids), "unique:", len(invset))
print("enrich_a:", len(A), "unique:", len(aset))
print("enrich_b:", len(B), "unique:", len(bset))
dup_ab = aset.intersection(bset)
print("\ndup in A and B:", sorted(dup_ab) if dup_ab else "none")
missing = invset - (aset | bset)
print("MISSING (in inventory, not enriched):", len(missing))
for m in sorted(missing): print("  -", m)
extra = (aset | bset) - invset
print("EXTRA (enriched, not in inventory):", len(extra))
for e in sorted(extra): print("  +", e)
c = Counter(inv_ids)
print("\ndup inventory ids:", {k: v for k, v in c.items() if v > 1} or "none")
bad = []
for src, name in [(A, 'a'), (B, 'b')]:
    for k, v in src.items():
        for f in ['eng', 'thai', 'zh', 'psycho']:
            if f not in v:
                bad.append((name, k, f))
print("entries missing required field:", bad if bad else "none")
pc = Counter(v['psycho'] for v in list(A.values()) + list(B.values()))
print("\npsycho level distribution:", dict(sorted(pc.items())))
# non-empty thai / zh counts
thai = sum(1 for v in list(A.values()) + list(B.values()) if v.get('thai'))
zh = sum(1 for v in list(A.values()) + list(B.values()) if v.get('zh'))
print("entries with thai name:", thai)
print("entries with zh name:", zh)
