"""Fetch six market-regime indicators, score them on a -1..+1 fear/hope scale,
build three axes and a composite, record regime flips and a theme ledger.

Runs in GitHub Actions (open internet). Writes:
  data/market/series.json   daily rows since START for the page
  data/market/themes.json   theme ledger (ride-the-wave check)
  data/market/status.json   what worked, what failed

Scores are point-in-time: each day's percentile uses only the trailing
5 years, so history on the page is what you would have seen that day.
"""
import io
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'market')
os.makedirs(OUT, exist_ok=True)

START = '2021-10-01'          # page history
WARMUP = '2015-01-01'         # percentile warm-up
WIN = 1260                    # 5 trading years
ON, OFF = 0.15, -0.15         # regime thresholds (hysteresis)

status = {'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'ok': [], 'failed': []}


def fred(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    for i in range(3):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text), na_values='.')
            df.columns = ['date', 'v']
            s = pd.Series(df['v'].values, index=pd.to_datetime(df['date'])).dropna()
            status['ok'].append(series)
            return s
        except Exception as e:  # noqa
            err = str(e)
            time.sleep(3)
    status['failed'].append(f'{series}: {err}')
    return None


def yahoo(tickers):
    import yfinance as yf
    for i in range(3):
        try:
            df = yf.download(tickers, start=WARMUP, auto_adjust=True, progress=False, threads=True)
            close = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']].rename(columns={'Close': tickers[0]})
            close = close.dropna(how='all')
            got = [t for t in tickers if t in close.columns and close[t].notna().sum() > 100]
            miss = [t for t in tickers if t not in got]
            status['ok'].append(f'yahoo {len(got)}/{len(tickers)}')
            if miss:
                status['failed'].append('yahoo missing: ' + ','.join(miss))
            return close
        except Exception as e:  # noqa
            err = str(e)
            time.sleep(5)
    status['failed'].append(f'yahoo: {err}')
    return pd.DataFrame()


def pctl(s, win=WIN, minp=250):
    """Rolling percentile of the last value within the trailing window, 0..1."""
    def f(w):
        x = w[-1]
        return float((w[:-1] < x).mean()) if len(w) > 1 else math.nan
    return s.rolling(win, min_periods=minp).apply(f, raw=True)


# ---------- G20 country ETFs (Russia excluded: no listed ETF since 2022; African Union: none) ----------
G20 = {'SPY': 'United States', 'MCHI': 'China', 'EWJ': 'Japan', 'EWG': 'Germany', 'EWQ': 'France', 'EWU': 'United Kingdom',
       'EWI': 'Italy', 'EWC': 'Canada', 'EWA': 'Australia', 'EWY': 'South Korea', 'INDA': 'India', 'EWZ': 'Brazil',
       'EWW': 'Mexico', 'EIDO': 'Indonesia', 'TUR': 'Turkey', 'EZA': 'South Africa', 'KSA': 'Saudi Arabia',
       'ARGT': 'Argentina', 'VGK': 'Europe (EU proxy)'}

COORD = {'SPY': (38.90, -77.04), 'MCHI': (39.90, 116.40), 'EWJ': (35.68, 139.69), 'EWG': (52.52, 13.40), 'EWQ': (48.86, 2.35),
         'EWU': (51.51, -0.13), 'EWI': (41.90, 12.50), 'EWC': (45.42, -75.70), 'EWA': (-35.28, 149.13), 'EWY': (37.57, 126.98),
         'INDA': (28.61, 77.21), 'EWZ': (-15.79, -47.88), 'EWW': (19.43, -99.13), 'EIDO': (-6.21, 106.85), 'TUR': (39.93, 32.86),
         'EZA': (-25.75, 28.19), 'KSA': (24.71, 46.68), 'ARGT': (-34.60, -58.38), 'VGK': (50.85, 4.35)}

# ---------- theme ledger: date = when the theme was obvious to everyone (judgement, editable) ----------
THEMES = [
    {'id': 'covid-pharma', 'name': 'Covid: pharma', 'etf': 'PPH', 'date': '2020-03-11', 'why': 'WHO declares a pandemic'},
    {'id': 'stay-home-cloud', 'name': 'Stay at home: cloud', 'etf': 'CLOU', 'date': '2020-04-01', 'why': 'lockdowns across the G20'},
    {'id': 'reopening-travel', 'name': 'Reopening: airlines', 'etf': 'JETS', 'date': '2020-11-09', 'why': 'first vaccine efficacy result'},
    {'id': 'ev-boom', 'name': 'EV boom', 'etf': 'DRIV', 'date': '2021-01-08', 'why': 'Tesla passes USD 800bn'},
    {'id': 'ark-innovation', 'name': 'Disruptive innovation', 'etf': 'ARKK', 'date': '2021-02-01', 'why': 'peak retail inflows'},
    {'id': 'cannabis', 'name': 'Cannabis legalisation', 'etf': 'MSOS', 'date': '2021-02-10', 'why': 'US federal reform expected'},
    {'id': 'crypto-mainstream', 'name': 'Crypto goes mainstream', 'etf': 'BITO', 'date': '2021-10-19', 'why': 'first US bitcoin futures ETF'},
    {'id': 'ukraine-defence', 'name': 'War in Ukraine: defence', 'etf': 'ITA', 'date': '2022-02-24', 'why': 'full-scale invasion'},
    {'id': 'energy-shock', 'name': 'Energy shock', 'etf': 'XLE', 'date': '2022-03-08', 'why': 'Brent above USD 120'},
    {'id': 'ai-chips', 'name': 'AI: chips', 'etf': 'SMH', 'date': '2022-11-30', 'why': 'ChatGPT launch'},
    {'id': 'nuclear-revival', 'name': 'Nuclear revival', 'etf': 'URA', 'date': '2024-09-20', 'why': 'Microsoft restarts Three Mile Island'},
    {'id': 'quantum', 'name': 'Quantum computing', 'etf': 'QTUM', 'date': '2024-12-10', 'why': 'Google Willow chip'},
]

# ---------- scanner universe: US-listed sector, theme and commodity funds ----------
SCAN = {
    'XLE': ('Energy', 'sector'), 'XLV': ('Health care', 'sector'), 'XLF': ('Financials', 'sector'),
    'XLK': ('Technology', 'sector'), 'XLI': ('Industrials', 'sector'), 'XLU': ('Utilities', 'sector'),
    'XLB': ('Materials', 'sector'), 'XLP': ('Consumer staples', 'sector'), 'XLY': ('Consumer discretionary', 'sector'),
    'XLRE': ('Real estate', 'sector'), 'XLC': ('Communication', 'sector'),
    'ITA': ('Defence', 'theme'), 'SHLD': ('Defence tech', 'theme'), 'SMH': ('Chips', 'theme'), 'IGV': ('Software', 'theme'),
    'CIBR': ('Cybersecurity', 'theme'), 'BOTZ': ('Robotics and AI', 'theme'), 'QTUM': ('Quantum and AI', 'theme'),
    'URA': ('Uranium', 'theme'), 'NLR': ('Nuclear power', 'theme'), 'ICLN': ('Clean energy', 'theme'), 'TAN': ('Solar', 'theme'),
    'LIT': ('Lithium and batteries', 'theme'), 'PAVE': ('Infrastructure', 'theme'), 'IBB': ('Biotech', 'theme'),
    'XBI': ('Small biotech', 'theme'), 'PPH': ('Pharma', 'theme'), 'JETS': ('Airlines', 'theme'), 'XHB': ('Homebuilders', 'theme'),
    'KRE': ('Regional banks', 'theme'), 'ARKK': ('Disruptive innovation', 'theme'), 'MSOS': ('Cannabis', 'theme'),
    'IBIT': ('Bitcoin', 'theme'), 'KWEB': ('China internet', 'theme'), 'IYT': ('Transport', 'theme'),
    'GLD': ('Gold', 'commodity'), 'SLV': ('Silver', 'commodity'), 'GDX': ('Gold miners', 'commodity'),
    'COPX': ('Copper miners', 'commodity'), 'USO': ('Oil', 'commodity'), 'UNG': ('Natural gas', 'commodity'),
    'DBA': ('Agriculture', 'commodity'), 'REMX': ('Rare earths', 'commodity'),
}

tickers = sorted(set(list(G20) + ['HG=F', 'GC=F', 'SPY'] + [t['etf'] for t in THEMES] + list(SCAN)))
px = yahoo(tickers)

vix = fred('VIXCLS')
credit = fred('BAA10Y')  # Moody's Baa corporate yield minus 10y Treasury, daily, full history
curve = fred('T10Y2Y')
cash = fred('RMFSL')  # retail money market funds, monthly, USD bn (weekly WRMFSL was discontinued in 2021)

idx = pd.bdate_range(WARMUP, datetime.now(timezone.utc).date())
ind = {}


MAX_AGE = {'daily': 10, 'monthly': 100}  # calendar days since last observation


def put(key, raw, score, label, unit, freq='daily', lag=0):
    """lag: days between the observation date and its publication, so history only uses what was known."""
    last = raw.dropna().index.max()
    age = (pd.Timestamp(datetime.now(timezone.utc).date()) - last).days
    if age > MAX_AGE[freq]:
        status['failed'].append(f'{key}: stale, last observation {last.date()}')
        return
    lim = 5 if freq == 'daily' else 70
    if lag:
        raw, score = raw.copy(), score.copy()
        raw.index = raw.index + pd.Timedelta(days=lag)
        score.index = score.index + pd.Timedelta(days=lag)
    ind[key] = {'raw': raw.reindex(idx, method='ffill', limit=lim), 'score': score.reindex(idx, method='ffill', limit=lim),
                'label': label, 'unit': unit, 'last': str(last.date())}


if vix is not None:
    put('vix', vix, 1 - 2 * pctl(vix), 'VIX', 'pts')
if credit is not None:
    put('credit', credit, 1 - 2 * pctl(credit), 'Corporate credit spread (Baa − 10y)', 'pp')
if curve is not None:
    put('curve', curve, 2 * pctl(curve) - 1, 'Yield curve 10y−2y', 'pp')
if cash is not None:
    chg = cash.pct_change(6) * 100  # 6-month change, %
    put('cash', chg, 1 - 2 * pctl(chg, win=60, minp=24), 'Retail money funds, 6-month change', '%', 'monthly', lag=35)
if not px.empty and 'HG=F' in px and 'GC=F' in px:
    cg = (px['HG=F'] / px['GC=F']).dropna()
    put('cugold', cg * 1000, 2 * pctl(cg) - 1, 'Copper / gold ×1000', '')
if not px.empty:
    g20 = [t for t in G20 if t in px.columns]
    above = pd.DataFrame({t: (px[t] > px[t].rolling(200).mean()).where(px[t].notna()) for t in g20})
    breadth = above.mean(axis=1, skipna=True) * 100
    put('breadth', breadth, 2 * (breadth / 100) - 1, 'G20 breadth: countries above 200-day avg', '%')
    status['g20_etfs'] = len(g20)
    countries = []
    for t in g20:
        c = px[t].dropna()
        if len(c) < 210:
            continue
        ma200 = c.rolling(200).mean().iloc[-1]
        countries.append({'etf': t, 'name': G20[t], 'lat': COORD[t][0], 'lon': COORD[t][1],
                          'vs200': round((c.iloc[-1] / ma200 - 1) * 100, 1),
                          'r3m': round((c.iloc[-1] / c.iloc[-63] - 1) * 100, 1),
                          'r12m': round((c.iloc[-1] / c.iloc[-252] - 1) * 100, 1)})

axes = {
    'f': ['vix', 'credit'],          # fear <-> calm
    'g': ['cugold', 'breadth'],  # contraction <-> expansion
    'l': ['curve', 'cash'],      # tight <-> easy
}
ax = {}
for a, keys in axes.items():
    cols = [ind[k]['score'] for k in keys if k in ind]
    ax[a] = pd.concat(cols, axis=1).mean(axis=1) if cols else pd.Series(math.nan, index=idx)
comp = pd.concat(ax.values(), axis=1).mean(axis=1)

# regime with hysteresis
state, states, flips = 0, [], []
spy = px['SPY'].reindex(idx).ffill() if 'SPY' in px else None
for d, v in comp.items():
    if math.isnan(v):
        states.append(0)
        continue
    new = state
    if v > ON:
        new = 1
    elif v < OFF:
        new = -1
    if new != state and d >= pd.Timestamp(START):
        f = {'date': d.strftime('%Y-%m-%d'), 'to': 'on' if new == 1 else 'off' if new == -1 else 'neutral', 'composite': round(v, 2)}
        if spy is not None:
            p0 = spy.get(d)
            for n in (20, 60):
                j = idx.get_loc(d) + n
                if p0 and j < len(idx) and not math.isnan(spy.iloc[j]):
                    f[f'spy{n}'] = round((spy.iloc[j] / p0 - 1) * 100, 1)
        flips.append(f)
    state = new
    states.append(state)
regime = pd.Series(states, index=idx)

# ---------- output series ----------
sl = idx[idx >= pd.Timestamp(START)]
def L(s, nd=2):
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), nd) for v in s.reindex(sl)]

series = {
    'updated': status['updated'],
    'dates': [d.strftime('%Y-%m-%d') for d in sl],
    'ind': {k: {'label': v['label'], 'unit': v['unit'], 'last': v['last'], 'raw': L(v['raw']), 'score': L(v['score'])}
            for k, v in ind.items()},
    'axes': {a: L(s) for a, s in ax.items()},
    'composite': L(comp),
    'regime': [int(x) for x in regime.reindex(sl).fillna(0)],
    'flips': flips,
    'spy': L(spy, 2) if spy is not None else [],
    'countries': countries if not px.empty else [],
}
json.dump(series, open(os.path.join(OUT, 'series.json'), 'w'), separators=(',', ':'))

# ---------- wave rule (shared by the ledger and the scanner) ----------
MA_N, CONFIRM, MIN_HOLD, JOLT = 100, 5, 20, 5.0


def wave_trades(p, b, entry=None):
    """Trades on one fund, judged against the benchmark b.

    IN  (scanner): relative strength p/b beats its 100-day average 5 days running AND p beat b by JOLT% over 20 days.
    IN  (ledger):  the given entry date, at that day's close.
    OUT: relative strength below its 100-day average 5 days running, after at least MIN_HOLD days in.
    Trades fill at the close of the day AFTER the signal, so no trade uses a price it could not have had.
    Returns (trades, state) where state describes today: in / watch / out.
    """
    df = pd.concat([p, b], axis=1, keys=['p', 'b']).dropna()
    if len(df) < MA_N + 30:
        return [], None
    rs = df['p'] / df['b']
    ma = rs.rolling(MA_N, min_periods=60).mean()
    up20 = (rs / rs.shift(20) - 1) * 100
    d, P, B = df.index, df['p'].values, df['b'].values
    above = (rs > ma).values
    trades, cur, ca, cb = [], None, 0, 0
    if entry is not None:
        i0 = int(d.searchsorted(pd.Timestamp(entry)))
        if i0 >= len(d) or (d[i0] - pd.Timestamp(entry)).days > 10:
            return [], None
        cur = {'i': i0}
        rng = range(i0, len(d))
    else:
        rng = range(len(d))
    for i in rng:
        if math.isnan(ma.iloc[i]):
            continue
        ca = ca + 1 if above[i] else 0
        cb = 0 if above[i] else cb + 1
        if cur is None:
            if entry is None and ca >= CONFIRM and up20.iloc[i] >= JOLT:
                cur = {'i': i + 1, 'sig': i}
        elif i - cur['i'] >= MIN_HOLD and cb >= CONFIRM:
            cur['o'] = i + 1
            trades.append(cur)
            cur = None
            if entry is not None:
                break
    if cur is not None:
        trades.append(cur)

    def row(t):
        i = t['i']
        if i >= len(d):  # signal on the last day, fills tomorrow
            return {'signal': d[t['sig']].strftime('%Y-%m-%d'), 'in': None}
        o = t.get('o')
        closed = o is not None and o < len(d)
        j = o if closed else len(d) - 1
        r = {'in': d[i].strftime('%Y-%m-%d'), 'out': d[j].strftime('%Y-%m-%d') if closed else None,
             'days': int(j - i), 'ret': round(float(P[j] / P[i] - 1) * 100, 1), 'bench': round(float(B[j] / B[i] - 1) * 100, 1)}
        r['edge'] = round(r['ret'] - r['bench'], 1)
        if o is not None and not closed:
            r['exit_signal'] = d[o - 1].strftime('%Y-%m-%d')  # out signal today, fills tomorrow
        return r

    rows = [row(t) for t in trades]
    last = len(d) - 1
    if rows and rows[-1].get('in') is None:
        state = 'new'          # entry signal today
    elif rows and rows[-1].get('exit_signal'):
        state = 'exit'         # exit signal today
    elif rows and rows[-1].get('out') is None:
        state = 'in'
    elif entry is None and ca >= 1 and up20.iloc[last] >= JOLT:
        state = 'watch'
    else:
        state = 'out'
    return rows, {'state': state, 'above_days': int(ca), 'up20': round(float(up20.iloc[last]), 1),
                  'vs_trend': round(float((rs.iloc[last] / ma.iloc[last] - 1) * 100), 1)}


# ---------- theme ledger: enter on the obvious day, leave on the break ----------
themes = []
for t in THEMES:
    e = t['etf']
    if px.empty or e not in px.columns or 'SPY' not in px.columns:
        themes.append({**t, 'error': 'no prices'})
        continue
    tr, st = wave_trades(px[e], px['SPY'], entry=t['date'])
    if not tr or tr[0].get('in') is None:
        themes.append({**t, 'error': 'etf starts after date'})
        continue
    themes.append({**t, **tr[0], 'riding': tr[0]['out'] is None})
json.dump({'updated': status['updated'], 'benchmark': 'SPY', 'rule': {'ma': MA_N, 'confirm': CONFIRM, 'min_hold': MIN_HOLD},
           'themes': themes}, open(os.path.join(OUT, 'themes.json'), 'w'), separators=(',', ':'))

# ---------- wave scanner: same rule, mechanical entry, broad universe ----------
scan_rows, all_trades = [], []
for tk, (name, grp) in SCAN.items():
    if tk not in px.columns:
        continue
    tr, st = wave_trades(px[tk], px['SPY'])
    if st is None:
        continue
    hist = [x for x in tr if x.get('in') and x['in'] >= START]
    for x in hist:
        if x['out']:
            all_trades.append({'etf': tk, **x})
    cur = tr[-1] if tr and (tr[-1].get('in') is None or tr[-1]['out'] is None) else None
    last_closed = next((x for x in reversed(tr) if x.get('out')), None)
    scan_rows.append({'etf': tk, 'name': name, 'group': grp, **st, 'now': cur, 'last': last_closed,
                      'trades5y': len([x for x in hist if x['out']])})

closed = all_trades
def stat(xs):
    if not xs:
        return {}
    r = sorted(x['ret'] for x in xs)
    return {'n': len(xs), 'win': int(sum(x['ret'] > 0 for x in xs)), 'beat': int(sum(x['edge'] > 0 for x in xs)),
            'avg': round(sum(r) / len(r), 1), 'median': round(r[len(r) // 2], 1),
            'avg_edge': round(sum(x['edge'] for x in xs) / len(xs), 1),
            'avg_days': round(sum(x['days'] for x in xs) / len(xs)),
            'best': max(xs, key=lambda x: x['ret']), 'worst': min(xs, key=lambda x: x['ret'])}
json.dump({'updated': status['updated'], 'benchmark': 'SPY', 'start': START,
           'rule': {'ma': MA_N, 'confirm': CONFIRM, 'min_hold': MIN_HOLD, 'jolt': JOLT},
           'funds': scan_rows, 'backtest': stat(closed),
           'recent': sorted(closed, key=lambda x: x['out'], reverse=True)[:40]},
          open(os.path.join(OUT, 'scanner.json'), 'w'), separators=(',', ':'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
status['scanner'] = {'funds': len(scan_rows), 'trades5y': len(closed)}

status['rows'] = len(sl)
status['indicators'] = list(ind)
status['flips'] = len(flips)
json.dump(status, open(os.path.join(OUT, 'status.json'), 'w'), indent=1)
print(json.dumps(status, indent=1))
if len(ind) < 4:
    sys.exit('fewer than 4 indicators available')
