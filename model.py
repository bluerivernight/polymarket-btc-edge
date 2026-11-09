"""Model P(up) for the current 15-minute BTC window — free data, stdlib only.

Monte Carlo from Binance 1-minute klines (public, keyless): bootstrap per-minute
returns from the last 1000 bars, replay the remaining minutes of the open 15m
window N times, measure P(close > window open). A reality check, not a promise.
"""
import json
import math
import random
import statistics
import time
import urllib.request
from datetime import datetime, timezone

BINANCE_KLINES = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1000"
WINDOW = 900  # seconds in a 15-minute window


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "polyedge/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def window_state(now_ms: int | None = None) -> dict:
    now_s = (now_ms or int(time.time() * 1000)) // 1000
    open_ts = (now_s // WINDOW) * WINDOW
    klines = _get(BINANCE_KLINES)
    row = next((k for k in klines if int(k[0]) // 1000 == open_ts), None)
    open_px = float(row[1]) if row else float(klines[-1][4])
    spot = float(klines[-1][4])
    rets = [math.log(float(klines[i][4]) / float(klines[i - 1][4])) for i in range(1, len(klines))]
    return {"open_ts": open_ts, "open_px": open_px, "spot": spot,
            "sec_left": WINDOW - (now_s - open_ts),
            "sd_min": statistics.pstdev(rets)}


def p_up(spot: float, open_px: float, sec_left: int, sd_min: float,
         n: int = 10000, seed: int = 2026) -> float:
    need = max(1, math.ceil(sec_left / 60.0))
    rnd = random.Random(seed)
    hits = 0
    for _ in range(n):
        px = spot
        for _i in range(need):
            px *= math.exp(rnd.gauss(0.0, sd_min))
        if px > open_px:
            hits += 1
    return hits / n


def snapshot(now_ms: int | None = None) -> dict | None:
    st = window_state(now_ms)
    if st["spot"] <= 0:
        return None
    st["p_up"] = round(p_up(st["spot"], st["open_px"], st["sec_left"], st["sd_min"]), 4)
    st["window_utc"] = datetime.fromtimestamp(st["open_ts"], tz=timezone.utc).strftime("%H:%M")
    return st
