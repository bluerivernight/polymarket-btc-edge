"""PolyEdge BTC 15m — free research snapshot. Run: python run.py snapshot"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
if getattr(sys.stdout, "reconfigure", None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import deribit_flow
import model
import polymarket_feed
import ajaib

USD_IDR_FALLBACK = 16500.0


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "polyedge/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def usd_idr():
    """Yahoo IDR=X rate; free, keyless."""
    try:
        d = _get("https://query1.finance.yahoo.com/v8/finance/chart/IDR=X")
        v = d["chart"]["result"][0]["meta"].get("regularMarketPrice")
        if v:
            return float(v)
    except Exception:
        pass
    return USD_IDR_FALLBACK


def cmd_snapshot():
    now_ms = int(time.time() * 1000)
    flow = deribit_flow.compute_flow()
    st = model.snapshot(now_ms)
    usd = usd_idr()
    markets = polymarket_feed.find_btc_updown()

    print("== PolyEdge BTC snapshot  now={} UTC".format(
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())))
    print("BTC spot        : ${:,.0f}  (~Rp {:,.0f})".format(
        st["spot"], st["spot"] * usd))
    print("USDIDR          : {:,.0f}".format(usd))

    print("\n-- Model: P(close > window open) this 15m window")
    print("  window open    : {} UTC  opened at ${:,.0f}".format(st["window_utc"], st["open_px"]))
    print("  price now      : ${:,.0f}  ({:+.2%} vs open)".format(
        st["spot"], st["spot"] / st["open_px"] - 1.0))
    print("  seconds left   : {:d}   per-min sd: {:.5f}".format(st["sec_left"], st["sd_min"]))
    print("  P(up) model    : {:.1%}   (Monte Carlo, 10k runs, bootstrap 1m returns)".format(st["p_up"]))
    open_direction = "UP" if st["spot"] > st["open_px"] else "DOWN"

    print("\n-- Deribit BTC option flow D={mean signed pressure}, delta-bucketed")
    if flow.get("deribit_blocked"):
        print("  DERIBIT UNREACHABLE from this network (TCP-blocked).")
        print("  Fix: set HTTPS_PROXY env var, or run on unfiltered network. All keyless = free.")
    else:
        for minutes, buckets in flow["windows"].items():
            b = buckets["otm_dotm"]
            print("  {:>2}m  otm/dotm D {:+8.1f}  V {:8.1f}  n {:4d}   atm D {:+8.1f}  n {:4d}".format(
                minutes, b["D"], b["V"], b["n"], buckets["atm"]["D"], buckets["atm"]["n"]))
        print("  Spot(recent): ${:,.0f}".format(flow["spot"] or 0))

    print("\n-- Polymarket BTC Up/Down markets (may be geo-restricted; read-only)")
    if markets:
        for m in markets:
            q = m.get("question", "?")
            end = m.get("endDate", "?")
            print("  - {}  closes {}".format(q, end))
            tok = None
            for key in ("clobTokenIds", "clob_token_ids"):
                raw = m.get(key)
                if raw:
                    tok = raw if isinstance(raw, list) else json.loads(raw)
                    break
            if tok:
                p = polymarket_feed.price_of(tok[0])
                if p.get("mid") is not None:
                    edge = st["p_up"] - float(p["mid"])
                    print("    UP price  (mid): {:.2f}c   model-prob vs market edge: {:+.1%}".format(
                        float(p["mid"]) * 100, edge))
    else:
        print("  no active/upcoming BTC up/down market found via gamma API.")
        print("  Compare with model alone, or open https://polymarket.com search 'Bitcoin Up or Down'.")

    print("\n-- Honest note (upstream verdict)")
    print("  The upstream fed this EXACT D-signal to 9225 backfilled windows and consistently")
    print("  landed a 'thin edge / round-trip costs bleed' message. Treat D as a sentiment")
    print("  thermometer for the 15m window, never a bet trigger.")
    print("Paper/only. Read-only. Not financial advice.")


def cmd_ajaib():
    t = ajaib.server_time()
    info = ajaib.exchange_info()
    usd = usd_idr()
    try:
        d = _get("https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD")
        spot = float(d["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception:
        spot = None
    print("== Ajaib Coin Exchange")
    if t:
        print("server time  :", t)
    if info:
        pairs = info if isinstance(info, list) else info.get("pairs", info)
        if isinstance(pairs, list):
            btc_pair = [p for p in pairs if str(p).upper().find("BTC") >= 0]
            if btc_pair:
                print("listed BTC pairs (first 10):", btc_pair[:10])
        else:
            print("exchange-info:", json.dumps(info)[:400])
    if spot:
        print("BTC spot     : ${:,.0f}   targeted induction: Rp {:,.0f} (spot x {:,.0f})".format(
            spot, spot * usd, usd))
    print("\nTicket (manual in Ajaib app, IDR):")
    if spot:
        for usd_budget in (10.0, 25.0):
            print("  budget ${:.0f} = Rp {:,.0f} / price Rp {:,.0f} -> ~{:g} sats BTC".format(
                usd_budget, usd_budget * usd, spot * usd,
                round((usd_budget / spot) * 1e8 / 100)))
    print(ajaib.key_setup_hint())


def cmd_watch(every: int, minutes: int = 60):
    deadline = time.time() + minutes * 60
    try:
        while time.time() < deadline:
            cmd_snapshot()
            time.sleep(every)
            print("\n" + "-" * 60 + "\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    if what == "snapshot":
        cmd_snapshot()
    elif what == "ajaib":
        cmd_ajaib()
    elif what == "watch":
        every = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        cmd_watch(every, minutes)
    else:
        print(__doc__)
