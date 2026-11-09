# PolyEdge BTC (free, no cost)

Free reproduction of [EVERYTHINGAICO/polymarket-btc-edge](https://github.com/EVERYTHINGAICO/polymarket-btc-edge) —
the Deribit options-flow signal (D) researched against Polymarket BTC Up/Down 15-minute
markets — plus Ajaib (Indonesia) support. **0 dependencies, 0 API keys, 0 paid tiers.**
Stdlib Python 3.8+ only. **Read-only: this tool never places an order.**

## Install

    # nothing. it is a folder of .py files. requires Python 3.8+

## Run

    python run.py snapshot      # full research card
    python run.py ajaib         # IDR ticket for manual Ajaib execution
    python run.py watch 30 10   # loop: every 30s, for 10 minutes

## What a snapshot shows

| Block | Source (all free) | What it is |
|---|---|---|
| BTC spot + USD/IDR | Yahoo `BTC-USD`, `IDR=X` | price in USD and Rp |
| P(up) model | Binance mirror `data-api.binance.vision` 1m klines | Monte Carlo (10k runs, seeded): P(close > window open) this 15m window |
| D / V flow | Deribit `public/get_last_trades_by_currency` | Net Buying Pressure per Alexander et al. 2022, Black-76 delta recomputed from each trade's own IV, OTM/DOTM+ATM buckets, 5/10/15m windows — bit-faithful to upstream `signal.py`/`signal_bs76.py` |
| Polymarket edge | gamma-api + CLOB price endpoints | live UP price vs the model probability → the edge in cents |
| Ajaib ticket | Yahoo rate | "buy Rp X ≈ N sats BTC" manual-execute card |

## Network notes (this build machine)

`binance.com`, `deribit.com`, and `gamma-api.polymarket.com` are TCP-blocked by the
local network filter. The tool auto-degrades: model + IDR run off Yahoo + the
Binance **public data mirror** (`binance.vision`), and the D/Polymarket blocks print
as unavailable. On an unfiltered network (or `set HTTPS_PROXY=...`) everything turns on —
all sources are keyless, so nothing new to pay for.

## Ajaib

- Public, keyless: `api.ajaib.co.id/coin/internal/v1/public/time` + `/exchange-info`
  (the machine's filter currently 403's them — codes still handle it).
- Full price/depth/order API exists but is **not self-service**: generate an
  ECDSA keypair, email the PUBLIC key to `tech@ajaib.co.id`, get an `X-API-KEY`.
  `ajaib.py` signs requests (`timestamp + METHOD + path + query + body`) the moment
  you drop `polyedge/ajaib_keys/*.pem` in. Until then the ticket is manual in the
  Ajaib Kripto app (min Rp 10.000, OJK/Bappebti-regulated).

## Honest verdict — read before trusting anything

Upstream ran this exact D-signal through **9,225 historical windows** (Dec 2025–Apr 2026)
plus live capture and retracted its one "edge" after a lookahead-bias audit. Published
verdict: **no robust, executable, cost-surviving edge was established.** This tool is a
reproducible research instrument: a thermometer for the 15m window, a reproducibility
harness, an IDR ticket writer. It is not alpha.

Also honest: Polymarket is geo-restricted in many jurisdictions and prediction-market
participation is a legal question of its own in Indonesia (Kominfo blocks gambling
sites; Ajaib Kripto for spot BTC is the regulated Indonesia path). Check the law where
you are. Nothing here is legal or financial advice.

## Files

    deribit_flow.py     D/V signal, Black-76, delta buckets
    model.py            window state + Monte Carlo P(up)
    polymarket_feed.py  gamma+CLOB market lookup (read-only)
    ajaib.py            Ajaib adapter + optional signer
    run.py              snapshot / ajaib / watch CLI
    _about.py           provenance notes
