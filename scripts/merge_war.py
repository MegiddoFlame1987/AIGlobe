"""Merge war-signal batches into data/war/events.json (see WAR_RUBRIC.md).

Usage: python3 -I scripts/merge_war.py <batch.json>... [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--write]

Without --write it validates and prints shares by language, actor, front, kind and score.
Defaults: --from = latest date already in the file (or 31 days ago), --to = today (UTC).
"""
import collections
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'data', 'war', 'events.json')
args = sys.argv[1:]


def opt(name):
    return args[args.index(name) + 1] if name in args else None


files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--from', '--to'))]
WRITE = '--write' in args
TODAY = dt.datetime.now(dt.timezone.utc).date()
ACTORS = {'us', 'eu', 'ru', 'cn', 'me', 'other'}
KINDS = {'word', 'deed'}
FRONTS = {'ukraine', 'taiwan', 'korea', 'middle-east', 'south-asia', 'other'}
LANGS = {'en', 'ru', 'uk', 'zh', 'ar', 'fa', 'fr', 'de', 'ja', 'hi', 'ko', 'es', 'he', 'tr'}
REQ = ['id', 'date', 'actor', 'kind', 'score', 'front', 'lang', 'place', 'lat', 'lon', 'title', 'summary', 'src', 'srcName']

ev = json.load(open(F)) if os.path.exists(F) else []
D0 = opt('--from') or (max(e['date'] for e in ev) if ev else (TODAY - dt.timedelta(days=31)).isoformat())
D1 = opt('--to') or TODAY.isoformat()


def toks(s):
    return set(w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w) > 3)


def dup(a, b):
    if a['id'] == b['id']:
        return True
    if a['actor'] != b['actor'] or abs((dt.date.fromisoformat(a['date']) - dt.date.fromisoformat(b['date'])).days) > 3:
        return False
    ta, tb = toks(a['title']), toks(b['title'])
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) > 0.45


new, rej = [], []
for f in files:
    for e in json.load(open(f)):
        miss = [k for k in REQ if k not in e]
        why = None
        if miss:
            why = f'missing {miss}'
        elif not (D0 <= e['date'] <= D1):
            why = f'date {e["date"]} outside {D0}..{D1}'
        elif e['actor'] not in ACTORS:
            why = f'actor {e["actor"]}'
        elif e['kind'] not in KINDS:
            why = f'kind {e["kind"]}'
        elif e['front'] not in FRONTS:
            why = f'front {e["front"]}'
        elif e['lang'] not in LANGS:
            why = f'lang {e["lang"]}'
        elif e['score'] not in (-1, 0, 1):
            why = 'score'
        elif not str(e['src']).startswith('http'):
            why = 'src'
        elif not isinstance(e['lat'], (int, float)) or not isinstance(e['lon'], (int, float)):
            why = 'latlon'
        elif len(e['title']) > 170:
            why = 'title length'
        elif any(dup(x, e) for x in ev + new):
            why = 'duplicate'
        if why:
            rej.append((e.get('id'), why))
            continue
        e = {**{k: e[k] for k in REQ}, **{k: e[k] for k in ('retro', 'approx') if e.get(k)}}
        e['added'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        new.append(e)

n = len(new) or 1
print(f'new {len(new)}, rejected {len(rej)}')
for r in rej:
    print('  reject', r)
for key in ('lang', 'actor', 'front', 'kind', 'score'):
    c = collections.Counter(e[key] for e in new)
    print(key, {k: f'{v} ({v / n:.0%})' for k, v in c.most_common()})

if WRITE:
    os.makedirs(os.path.dirname(F), exist_ok=True)
    allev = sorted(ev + new, key=lambda e: (e['date'], e['id']))
    open(F, 'w').write(json.dumps(allev, ensure_ascii=False, indent=0))
    st = {'updated': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'events': len(allev), 'lastRun': 'ok'}
    json.dump(st, open(os.path.join(os.path.dirname(F), 'status.json'), 'w'))
    print('war events.json', len(allev))
