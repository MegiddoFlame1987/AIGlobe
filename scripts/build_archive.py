"""Rebuild data/archive.json.

Keeps every live row (retro flag 0) already in the archive, adds live events from
data/events.json that are missing, and regenerates all retro rows (flag 1) from
data/retro/*.json. Idempotent: run it after any change to events or retro files.

Row format: [date, k, u, r, g, t, lang, retro, region]
region: us | cn | eu | g20 (other G20 members incl. African Union) | choke (TW, NL, IL, AE) | other
"""
import glob
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'data', 'archive.json')

US = {'usa', 'us', 'united states', 'united states of america', 'u.s.'}
CN = {'china', 'prc', "people's republic of china", 'hong kong'}
CHOKE = {'taiwan', 'netherlands', 'the netherlands', 'israel', 'uae', 'united arab emirates'}
EU = {'eu', 'european union', 'belgium', 'germany', 'france', 'italy', 'spain', 'poland', 'austria',
      'ireland', 'sweden', 'finland', 'denmark', 'portugal', 'greece', 'czech republic', 'czechia',
      'hungary', 'romania', 'bulgaria', 'croatia', 'slovakia', 'slovenia', 'estonia', 'latvia',
      'lithuania', 'luxembourg', 'malta', 'cyprus'}
AFRICA = {'algeria', 'angola', 'benin', 'botswana', 'burkina faso', 'burundi', 'cameroon', 'chad',
          "cote d'ivoire", 'ivory coast', 'dr congo', 'drc', 'congo', 'egypt', 'ethiopia', 'ghana',
          'guinea', 'kenya', 'libya', 'madagascar', 'malawi', 'mali', 'morocco', 'mozambique',
          'namibia', 'niger', 'nigeria', 'rwanda', 'senegal', 'sierra leone', 'somalia', 'sudan',
          'tanzania', 'togo', 'tunisia', 'uganda', 'zambia', 'zimbabwe'}
G20 = {'uk', 'united kingdom', 'britain', 'japan', 'south korea', 'korea', 'republic of korea', 'india',
       'russia', 'saudi arabia', 'brazil', 'indonesia', 'turkey', 'türkiye', 'south africa', 'mexico',
       'argentina', 'canada', 'australia', 'african union'} | AFRICA


def region(place):
    c = (place or '').split(',')[-1].strip().lower()
    if c in US:
        return 'us'
    if c in CN:
        return 'cn'
    if c in CHOKE:
        return 'choke'
    if c in EU:
        return 'eu'
    if c in G20:
        return 'g20'
    return 'other'


def row(e, retro):
    return [e['date'], e['k'], e['u'], e['r'], e.get('g', 0), e.get('t', 0), e.get('lang', 'en'), retro,
            region(e.get('place'))]


archive = json.load(open(A)) if os.path.exists(A) else []
live_old = [r for r in archive if len(r) < 8 or r[7] == 0]
events = json.load(open(os.path.join(ROOT, 'data', 'events.json')))

# live rows: key = first 8 fields; region filled from events.json where missing
ev_rows = [row(e, 0) for e in events]
region_of = {}
for r in ev_rows:
    region_of.setdefault(tuple(r[:8]), r[8])
live = []
for r in live_old:
    r = (list(r) + ['en', 0])[:8] if len(r) < 8 else list(r)
    key = tuple(r[:8])
    live.append(r[:8] + [r[8] if len(r) > 8 else region_of.get(key, 'other')])

have = Counter(tuple(r[:8]) for r in live)
want = Counter(tuple(r[:8]) for r in ev_rows)
for key, n in want.items():
    for _ in range(max(0, n - have[key])):
        live.append(list(key) + [region_of[key]])

retro = [row(e, 1) for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'retro', '*.json'))) for e in json.load(open(f))]

rows = sorted(live + retro, key=lambda r: (r[0], r[7]))
json.dump(rows, open(A, 'w'), separators=(',', ':'))
reg = Counter(r[8] for r in rows)
print(f'archive: {len(rows)} rows ({len(live)} live, {len(retro)} retro); regions: ' +
      ', '.join(f'{k} {v}' for k, v in reg.most_common()))
