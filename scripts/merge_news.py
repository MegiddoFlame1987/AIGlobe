"""Merge collected news batches into the AIGlobe data files.

Usage: python3 -I scripts/merge_news.py <batch.json>... [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--write]

Each batch is a JSON array of event records (RUBRIC.md section 3, without "added").
Without --write it only validates and prints language and country shares.
With --write it appends new events to data/events.json (keeps 180 days), rebuilds data/archive.json,
adds today's snapshot to data/snapshots.json and updates data/status.json.
Defaults: --from = latest event date already in events.json, --to = today (UTC).
"""
import collections
import datetime as dt
import json
import re
import subprocess
import sys

import os

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[1:]


def opt(name):
    return args[args.index(name) + 1] if name in args else None


files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--from', '--to'))]
WRITE = '--write' in args
TODAY = dt.datetime.now(dt.timezone.utc).date()
LANGS = {'en', 'zh', 'ja', 'ko', 'ru', 'es', 'hi', 'ar'}
CATS = {'incident', 'safety', 'research', 'agents', 'policy', 'economy'}
REQ = ['id', 'date', 'lang', 'place', 'lat', 'lon', 'title', 'summary', 'cat', 'k', 'u', 'r', 'g', 't', 'src', 'srcName']

ev = json.load(open(f'{repo}/data/events.json'))
D0 = opt('--from') or max(e['date'] for e in ev)
D1 = opt('--to') or TODAY.isoformat()


def toks(s):
    return set(w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w) > 3)


def similar(a, b):
    ta, tb = toks(a['title']), toks(b['title'])
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) > 0.45


new, rej = [], []
for f in files:
    for e in json.load(open(f)):
        miss = [k for k in REQ if k not in e]
        why = None
        if miss:
            why = f'missing {miss}'
        elif not (D0 <= e['date'] <= D1):
            why = f'date {e["date"]}'
        elif e['lang'] not in LANGS:
            why = f'lang {e["lang"]}'
        elif e['cat'] not in CATS:
            why = f'cat {e["cat"]}'
        elif any(e[k] not in (-1, 0, 1) for k in 'kurgt'):
            why = 'score'
        elif not str(e['src']).startswith('http'):
            why = 'src'
        elif not isinstance(e['lat'], (int, float)) or not isinstance(e['lon'], (int, float)):
            why = 'latlon'
        elif len(e['title']) > 170:
            why = 'title length'
        elif any(x['id'] == e['id'] or x['src'] == e['src'] or (abs((dt.date.fromisoformat(x['date']) - dt.date.fromisoformat(e['date'])).days) <= 3 and similar(x, e)) for x in ev + new):
            why = 'duplicate'
        if why:
            rej.append((e.get('id'), why))
            continue
        e = {k: e[k] for k in REQ}
        e['added'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        new.append(e)

print(f'new {len(new)}, rejected {len(rej)}')
for r in rej:
    print('  reject', r)
lang = collections.Counter(e['lang'] for e in new)
cty = collections.Counter(e['place'].split(',')[-1].strip() for e in new)
n = len(new) or 1
print('languages', {k: f'{v} ({v / n:.0%})' for k, v in lang.most_common()})
print('countries', {k: f'{v} ({v / n:.0%})' for k, v in cty.most_common()})
print('G nonzero:', [(e['id'], e['g']) for e in new if e['g']])

if WRITE:
    cut = (TODAY - dt.timedelta(days=180)).isoformat()
    allev = [e for e in ev if e['date'] >= cut] + sorted(new, key=lambda e: (e['date'], e['id']))
    open(f'{repo}/data/events.json', 'w').write(json.dumps(allev, ensure_ascii=False, indent=0))
    print(subprocess.run([sys.executable, '-I', f'{repo}/scripts/build_archive.py'], capture_output=True, text=True).stdout.strip())
    A = json.load(open(f'{repo}/data/archive.json'))

    def snap(day):
        out = {'date': day.isoformat()}
        for w, lo in ((30, 29), (7, 7)):
            rows = [r for r in A if day - dt.timedelta(days=lo) <= dt.date.fromisoformat(r[0]) <= day]
            m = len(rows)
            for i, ax in enumerate('kurgt', 1):
                p = sum(1 for r in rows if r[i] > 0)
                q = sum(1 for r in rows if r[i] < 0)
                out[f'{ax}{w}'] = round(((p - q) / m if m else 0) if ax == 't' else ((p - q) / (p + q) if p + q else 0), 2)
            out[f'n{w}'] = m
        return out

    S = [s for s in json.load(open(f'{repo}/data/snapshots.json')) if s['date'] != TODAY.isoformat()]
    S.append(snap(TODAY))
    json.dump(S, open(f'{repo}/data/snapshots.json', 'w'), indent=1)
    st = {'updated': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'events': len(A),
          'languages': sorted(LANGS, key=['en', 'zh', 'ja', 'ko', 'ru', 'es', 'hi', 'ar'].index), 'lastRun': 'ok'}
    json.dump(st, open(f'{repo}/data/status.json', 'w'))
    print('snapshot', S[-1])
    print('events.json', len(allev))
