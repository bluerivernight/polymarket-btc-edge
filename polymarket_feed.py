"""Polymarket BTC Up/Down market lookup + price — free, keyless, read-only.

Gamma API (markets/events metadata) + CLOB price endpoint. Public, no seller key,
no wallet. Read-only per PROJECT_DESIGN hard rules.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "polyedge/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def find_btc_updown():
    """Active BTC up-or-down markets closing soonest. Best effort across shapes."""
    urls = [
        GAMMA + "/markets?active=true&closed=false&limit=100&order=endDate&ascending=true",
        GAMMA + "/markets?closed=false&limit=100",
    ]
    for url in urls:
        try:
            markets = _get(url)
        except Exception:
            continue
        hits = []
        now = datetime.now(timezone.utc)
        for m in markets if isinstance(markets, list) else []:
            q = (m.get("question") or "").lower()
            slug = (m.get("slug") or "").lower()
            if ("bitcoin" in q or "btc" in q or "bitcoin" in slug) and (
                    "up or down" in q or "up-or-down" in slug or "up or down" in slug):
                # upcoming only
                end = m.get("endDate") or m.get("end_date_iso")
                try:
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                except Exception:
                    end_dt = None
                if end_dt and end_dt <= now:
                    continue
                hits.append(m)
        if hits:
            hits.sort(key=lambda m: m.get("endDate") or "")
            return hits[:3]
    return []


def price_of(token_id: str):
    """CLOB best bid/ask/mid for one outcome token. None if unavailable."""
    out = {}
    for side in ("buy", "sell"):
        try:
            resp = _get("{}/price?token_id={}&side={}".format(CLOB, token_id, side))
            out[side] = resp.get("price")
        except Exception:
            out[side] = None
    try:
        b, s = float(out.get("buy")), float(out.get("sell"))
        out["mid"] = round((b + s) / 2.0, 4)
    except Exception:
        out["mid"] = None
    return out
