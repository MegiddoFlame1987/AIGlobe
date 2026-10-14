"""Rebuild data/archive.json.

Keeps every live row (retro flag 0) already in the archive, adds live events from
data/events.json that are missing, and regenerates all retro rows (flag 1) from
data/retro/*.json. Idempotent: run it after any change to the retro files.

Row format: [date, k, u, r, g, t, lang, retro]
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'data', 'archive.json')

archive = json.load(open(A)) if os.path.exists(A) else []
live = [r for r in archive if len(r) < 8 or r[7] == 0]
live = [(r + ['en', 0])[:8] if len(r) < 8 else r for r in live]

# live events not yet in the archive (multiset match on date, five scores and language)
from collections import Counter
have = Counter(tuple(r) for r in live)
want = Counter()
for e in json.load(open(os.path.join(ROOT, 'data', 'events.json'))):
    want[(e['date'], e['k'], e['u'], e['r'], e.get('g', 0), e.get('t', 0), e.get('lang', 'en'), 0)] += 1
for row, n in want.items():
    for _ in range(max(0, n - have[row])):
        live.append(list(row))

retro = []
for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'retro', '*.json'))):
    for e in json.load(open(f)):
        retro.append([e['date'], e['k'], e['u'], e['r'], e['g'], e['t'], e['lang'], 1])

rows = sorted(live + retro, key=lambda r: (r[0], r[7]))
json.dump(rows, open(A, 'w'), separators=(',', ':'))
print(f'archive: {len(rows)} rows ({len(live)} live, {len(retro)} retro)')
