"""Deribit BTC option order-flow signal D/V — free, read-only, stdlib only.

Replicates the D-signal of EVERYTHINGAICO/polymarket-btc-edge (Alexander et al.
2022 Net Buying Pressure): signed pressure = +(amount*|delta|) for buyer, -(...) for
seller, aggregated per option_type in OTM/DOTM+ATM delta buckets over 5/10/15-minute
windows. D = (A_C - A_P) / 2. Delta is recomputed with Black-76 from the trade's own
IV and index_price (never trust payload greeks).

Hard rules inherited from upstream PROJECT_DESIGN §0: READ-ONLY. No orders, no keys.
"""
import json
import math
import time
import urllib.request
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
# delta_abs bucket edges (paper Alexander 2022, mirrored from upstream signal_bs76)
DOTM = (0.02, 0.125)
OTM = (0.125, 0.375)
ATM = (0.375, 0.625)
WINDOW_MINUTES = (5, 10, 15)

DERIBIT_BASE = "https://www.deribit.com/api/v2"
DERIBIT_TIMEOUT = 15


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "polyedge/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=DERIBIT_TIMEOUT) as r:
        return json.loads(r.read().decode())


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def parse_instrument(name: str):
    """'BTC-26JUN26-150000-C' -> (strike, expiry_dt_utc, 'call'/'put') or None."""
    try:
        body = name.split("-", 1)[1]
        exp_s, strike_s, side = body.split("-")
        day, mon, yr = exp_s[:2], exp_s[2:5], exp_s[5:7]
        expiry = datetime(int("20" + yr), MONTHS[mon], int(day), 8, 0, tzinfo=timezone.utc)
        return float(strike_s), expiry, "call" if side.upper() == "C" else "put"
    except Exception:
        return None


def black76_delta(fwd: float, strike: float, t_years: float, sigma: float, is_call: bool):
    if any(v <= 0 for v in (fwd, strike, t_years, sigma)) or t_years > 5:
        return None
    d1 = (math.log(fwd / strike) + 0.5 * sigma * sigma * t_years) / (sigma * math.sqrt(t_years))
    d = norm_cdf(d1)
    return d if is_call else d - 1.0


def bucket_of(delta_abs: float):
    if DOTM[0] < delta_abs <= DOTM[1]:
        return "otm_dotm"
    if OTM[0] < delta_abs <= OTM[1]:
        return "otm_dotm"
    if ATM[0] < delta_abs <= ATM[1]:
        return "atm"
    return None


def fetch_trades(count: int = 800):
    """Last BTC option trades from Deribit REST (public, no key). None if blocked."""
    url = "{}/public/get_last_trades_by_currency?currency=BTC&kind=option&count={}".format(
        DERIBIT_BASE, count)
    try:
        return _get(url).get("result", {}).get("trades", [])
    except Exception:
        return None


def compute_flow(count: int = 800, now_ms: int | None = None):
    """Feed last trades through Black-76 delta buckets -> D/V per window."""
    trades = fetch_trades(count)
    now_ms = now_ms or int(time.time() * 1000)
    buf = deque()
    if trades is None:
        return {"spot": None, "windows": {}, "deribit_blocked": True}
    for t in trades:
        parsed = parse_instrument(t.get("instrument_name", ""))
        if not parsed:
            continue
        strike, expiry, side = parsed
        idx_price = t.get("index_price")
        iv = t.get("iv", -1.0)
        if not idx_price or iv is None or iv < 0 or iv > 300 or not t.get("amount"):
            continue
        ts = int(t["timestamp"])
        t_years = max((expiry - datetime.fromtimestamp(ts / 1000, tz=timezone.utc)).total_seconds(),
                      1.0) / (365.0 * 86400.0)
        delta = black76_delta(idx_price, strike, t_years, iv / 100.0, side == "call")
        if delta is None:
            continue
        bucket = bucket_of(abs(delta))
        if bucket is None:
            continue
        sign = 1.0 if t.get("direction") == "buy" else -1.0
        buf.append({"ts": ts, "sign": sign, "amount": float(t["amount"]),
                    "d": abs(delta), "bucket": bucket, "call": side == "call"})

    out = {"spot": (trades[0].get("index_price") if trades else None),
           "windows": {}}
    if trades is None:
        out["deribit_blocked"] = True
        return out
    out["deribit_blocked"] = False
    out["n_raw"] = len(trades)
    for minutes in WINDOW_MINUTES:
        cutoff = now_ms - minutes * 60 * 1000
        a = defaultdict(lambda: [0.0, 0.0, 0])  # bucket -> [A_C, A_P, n]
        for tr in buf:
            if tr["ts"] < cutoff:
                continue
            b = a[tr["bucket"]]
            p = tr["sign"] * tr["amount"] * tr["d"]
            if tr["call"]:
                b[0] += p
            else:
                b[1] += p
            b[2] += 1
        w = {}
        for bucket in ("otm_dotm", "atm"):
            ac, ap, n = a.get(bucket, [0.0, 0.0, 0])
            w[bucket] = {"A_C": round(ac, 2), "A_P": round(ap, 2),
                         "D": round((ac - ap) / 2.0, 2), "V": round((ac + ap) / 2.0, 2),
                         "n": n}
        out["windows"][minutes] = w
    return out
