"""Delta-neutral paper strategies, GBP 1,000 of paper money each. Nothing is invested.

1. Crypto funding carry (Kraken): hold the coin, short the same amount of its perpetual.
   Price moves cancel; the short collects funding while longs pay it (and pays when funding turns negative).
2. Stock pairs: long the cheap one, short the expensive one when the usual gap between two similar
   companies stretches, close when it closes. Executable for UK retail through spread bets or CFDs.

Writes data/neutral/carry.json, pairs.json, status.json. Run by the `market` GitHub Action.
"""
import json
import math
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'neutral')
os.makedirs(OUT, exist_ok=True)

CAP = 1000.0
START = '2021-10-01'
status = {'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'ok': [], 'failed': []}


def dump(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), 'w'), separators=(',', ':'),
              default=lambda o: o.item() if hasattr(o, 'item') else str(o))


# ======================= 1. crypto funding carry (Kraken) =======================
CARRY = {'BTC': ['PF_XBTUSD', 'PF_BTCUSD'], 'ETH': ['PF_ETHUSD']}
SPOT_FEE, PERP_FEE = 0.0040, 0.0002   # Kraken lowest tier, maker, per side (spot 0.40%, perps 0.02%)
NOTIONAL = CAP / 2                    # GBP 500 of coin + GBP 500 margin for a 1x short of GBP 500


def kraken_rates(symbols):
    err = 'no data'
    for sym in symbols:
        for url in (f'https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol={sym}',
                    f'https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol={sym}'):
            for _ in range(2):
                try:
                    r = requests.get(url, timeout=30)
                    if r.status_code != 200:
                        err = f'{sym} HTTP {r.status_code}'
                        break
                    rates = r.json().get('rates') or []
                    if len(rates) < 100:
                        err = f'{sym}: {len(rates)} rows'
                        break
                    df = pd.DataFrame(rates)
                    df['t'] = pd.to_datetime(df['timestamp'], utc=True)
                    df = df.sort_values('t').drop_duplicates('t')
                    status['ok'].append(f'kraken {sym} {len(df)}')
                    return sym, df
                except Exception as e:  # noqa
                    err = f'{sym}: {e}'
                    time.sleep(3)
    status['failed'].append(f'kraken {symbols}: {err}')
    return None, None


carry = {'notional': NOTIONAL, 'capital': CAP, 'fees': {'spot': SPOT_FEE, 'perp': PERP_FEE}, 'assets': {}}
for asset, syms in CARRY.items():
    sym, df = kraken_rates(syms)
    if df is None:
        continue
    # relativeFundingRate is per hour (Kraken standardises funding to a per-hour basis);
    # each row applies until the next row, so accrual = rate x hours in the period
    t = df['t']
    hours = (t.shift(-1) - t).dt.total_seconds() / 3600
    hours.iloc[-1] = min(1.0, float(hours.median()))
    df['earn'] = df['relativeFundingRate'].astype(float) * hours   # fraction of notional, + = short receives
    df['date'] = t.dt.tz_convert(None).dt.normalize()
    daily = df.groupby('date')['earn'].sum()
    entry_fee = NOTIONAL * (SPOT_FEE + PERP_FEE)
    eq = CAP - entry_fee + (daily * NOTIONAL).cumsum()
    monthly = daily.groupby(daily.index.to_period('M')).sum()
    days_m = daily.groupby(daily.index.to_period('M')).size()
    ann_m = (monthly / days_m * 365 * 100).round(1)
    yr_ago = daily.index[-1] - pd.Timedelta(days=365)
    last7 = df[df['t'] >= df['t'].iloc[-1] - pd.Timedelta(days=7)]
    span_days = (daily.index[-1] - daily.index[0]).days + 1
    carry['assets'][asset] = {
        'symbol': sym, 'start': daily.index[0].strftime('%Y-%m-%d'), 'end': daily.index[-1].strftime('%Y-%m-%d'),
        'final': round(float(eq.iloc[-1]), 2),
        'final_after_exit': round(float(eq.iloc[-1] - NOTIONAL * (SPOT_FEE + PERP_FEE)), 2),
        'ann_all': round(float(daily.sum() / span_days * 365 * 100), 2),
        'ann_12m': round(float(daily[daily.index > yr_ago].sum() * 100), 2),
        'ann_7d': round(float((last7['earn'].sum() / max(1, (last7['t'].iloc[-1] - last7['t'].iloc[0]).total_seconds() / 3600)) * 8760 * 100), 2),
        'neg_months': int((monthly < 0).sum()), 'months_n': int(len(monthly)),
        'months': [[str(p), float(v)] for p, v in ann_m.items()],
        'curve': [[d.strftime('%Y-%m-%d'), round(float(v), 2)] for d, v in eq.iloc[::3].items()] +
                 [[eq.index[-1].strftime('%Y-%m-%d'), round(float(eq.iloc[-1]), 2)]],
    }
dump('carry.json', carry)

# ======================= 2. stock pairs =======================
PAIRS = [
    ('KO', 'PEP', 'Coca-Cola', 'PepsiCo', 'US drinks'),
    ('XOM', 'CVX', 'Exxon', 'Chevron', 'US oil'),
    ('V', 'MA', 'Visa', 'Mastercard', 'US payments'),
    ('HD', 'LOW', 'Home Depot', "Lowe's", 'US home improvement'),
    ('SHEL.L', 'BP.L', 'Shell', 'BP', 'UK oil'),
    ('LLOY.L', 'NWG.L', 'Lloyds', 'NatWest', 'UK banks'),
    ('7203.T', '7267.T', 'Toyota', 'Honda', 'Japan cars'),
]
LEG = CAP / 2                 # GBP 500 long, GBP 500 short
BETA_N, Z_N = 250, 60         # hedge ratio window, z-score window (trading days)
Z_IN, Z_OUT, Z_STOP, MAX_DAYS = 2.0, 0.5, 4.0, 30
SPREAD_COST = 0.001           # 0.1% per leg per side (spread bet / CFD dealing spread)
FIN = 0.05                    # 5% a year net overnight financing on one leg while a trade is open


def yahoo(tickers):
    import yfinance as yf
    for _ in range(3):
        try:
            df = yf.download(tickers, start='2019-01-01', auto_adjust=True, progress=False, threads=True)
            close = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']]
            status['ok'].append(f'yahoo {close.notna().any().sum()}/{len(tickers)}')
            return close
        except Exception as e:  # noqa
            err = str(e)
            time.sleep(5)
    status['failed'].append(f'yahoo: {err}')
    return pd.DataFrame()


def run_pair(pa, pb):
    df = pd.concat([pa, pb], axis=1, keys=['a', 'b']).dropna()
    if len(df) < BETA_N + Z_N + 20:
        return None
    la, lb = np.log(df['a']), np.log(df['b'])
    beta = la.rolling(BETA_N).cov(lb) / lb.rolling(BETA_N).var()
    s = la - beta * lb
    z = (s - s.rolling(Z_N).mean()) / s.rolling(Z_N).std()
    ra, rb = df['a'].pct_change().fillna(0).values, df['b'].pct_change().fillna(0).values
    d, Z = df.index, z.values
    i0 = int(d.searchsorted(pd.Timestamp(START)))
    eq, cur, pend, trades, curve = CAP, None, None, [], []
    for i in range(i0, len(d)):
        # mark the open trade to market with today's moves (side +1 = long A / short B)
        if cur is not None:
            pnl = cur['side'] * LEG * (ra[i] - rb[i]) - LEG * FIN / 252
            eq += pnl
            cur['pnl'] += pnl
            cur['days'] += 1
        # fills decided yesterday happen at today's close
        if pend == 'exit' and cur is not None:
            cost = 2 * LEG * SPREAD_COST
            eq -= cost
            cur['pnl'] -= cost
            cur['out'] = d[i].strftime('%Y-%m-%d')
            trades.append(cur)
            cur, pend = None, None
        elif pend in (1, -1) and cur is None:
            cost = 2 * LEG * SPREAD_COST
            eq -= cost
            cur = {'side': pend, 'in': d[i].strftime('%Y-%m-%d'), 'z_in': round(float(Z[i - 1]), 2), 'pnl': -cost, 'days': 0}
            pend = None
        # signals at today's close
        zi = Z[i]
        if not math.isnan(zi):
            if cur is None and pend is None:
                if zi > Z_IN:
                    pend = -1          # A rich vs B: short A, long B
                elif zi < -Z_IN:
                    pend = 1           # A cheap vs B: long A, short B
            elif cur is not None and pend is None:
                if abs(zi) < Z_OUT:
                    pend, cur['why'] = 'exit', 'gap closed'
                elif abs(zi) > Z_STOP:
                    pend, cur['why'] = 'exit', 'stop: gap kept widening'
                elif cur['days'] >= MAX_DAYS:
                    pend, cur['why'] = 'exit', f'time stop {MAX_DAYS} days'
        curve.append((d[i], eq))
    c = pd.Series([v for _, v in curve], index=[k for k, _ in curve])
    dd = float((c / c.cummax() - 1).min() * 100)
    for t in trades + ([cur] if cur else []):
        t['pnl'] = round(float(t['pnl']), 2)
    return {
        'z': round(float(Z[-1]), 2) if not math.isnan(Z[-1]) else None, 'beta': round(float(beta.iloc[-1]), 2),
        'open': cur, 'pending': pend if pend is None or isinstance(pend, str) else ('long A' if pend == 1 else 'short A'),
        'trades': trades[-12:], 'n': len(trades), 'win': sum(t['pnl'] > 0 for t in trades),
        'final': round(float(eq), 2), 'max_dd': round(dd, 1),
        'z_hist': [[k.strftime('%Y-%m-%d'), round(float(v), 2)] for k, v in z.iloc[-130:].dropna().items()],
        'curve': c.iloc[::5].round(2), 'curve_last': (c.index[-1], round(float(c.iloc[-1]), 2)),
    }


px = yahoo(sorted({t for p in PAIRS for t in p[:2]}))
pairs, curves = [], []
for a, b, na, nb, grp in PAIRS:
    if px.empty or a not in px or b not in px:
        status['failed'].append(f'pair {a}/{b}: no prices')
        continue
    r = run_pair(px[a], px[b])
    if r is None:
        status['failed'].append(f'pair {a}/{b}: short history')
        continue
    curve = r.pop('curve')
    last_d, last_v = r.pop('curve_last')
    curves.append(curve)
    r['curve'] = [[k.strftime('%Y-%m-%d'), float(v)] for k, v in curve.items()] + [[last_d.strftime('%Y-%m-%d'), last_v]]
    pairs.append({'a': a, 'b': b, 'name_a': na, 'name_b': nb, 'group': grp, **r})

port = None
if curves:
    allc = pd.concat(curves, axis=1).sort_index().ffill().dropna(how='all')
    pc = allc.mean(axis=1)          # GBP 1,000 split evenly across the pairs
    n = sum(p['n'] for p in pairs)
    port = {'final': round(float(pc.iloc[-1]), 2), 'n': n, 'win': sum(p['win'] for p in pairs),
            'max_dd': round(float((pc / pc.cummax() - 1).min() * 100), 1),
            'curve': [[k.strftime('%Y-%m-%d'), round(float(v), 2)] for k, v in pc.items()]}
dump('pairs.json', {'capital': CAP, 'leg': LEG, 'start': START,
                    'rule': {'beta_n': BETA_N, 'z_n': Z_N, 'z_in': Z_IN, 'z_out': Z_OUT, 'z_stop': Z_STOP,
                             'max_days': MAX_DAYS, 'spread_cost': SPREAD_COST, 'financing': FIN},
                    'pairs': pairs, 'portfolio': port})

status['carry'] = list(carry['assets'])
status['pairs'] = len(pairs)
dump('status.json', status)
print(json.dumps(status, indent=1))
