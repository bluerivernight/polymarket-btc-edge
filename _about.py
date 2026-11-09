"""Free market model for Polymarket BTC up/down edge research.

No pip install. Python 3.8+ stdlib only. All endpoints public and read-only.

Data sources (tried in order, first working wins):
  Deribit(BTC options trades): www.deribit.com — blocked on some networks, tool degrades.
  Binance BTC spot/klines  :   data-api.binance.vision (public mirror) -> Yahoo BTC-USD.
  USD/IDR rate             :   Yahoo IDR=X.
  Polymarket markets/price :   gamma-api + clob (GET only) — blocked on some networks, tool degrades.
  Ajaib Coin Exchange      :   api.ajaib.co.id public/time + exchange-info; BTC/IDR via Yahoo
                               (spot x rate) until your approved X-API-KEY arrives.

Network filter on the build machine: Binance main + Deribit + Polymarket TCP-blocked.
Mitigation: set HTTPS_PROXY or run on a network without filter — everything is
keyless, so a VPN/proxy works with zero cost.

Honest verdict inherited from upstream EVERETEST research: the D-signal was
run over 9,225 historical windows and no robust, cost-surviving edge was proven.
This tool reproduces the metric as a sentiment thermometer, prints the edge vs
market, and tells you when data is unavailable. It places no orders.

Commands:
  python run.py snapshot        one full research card
  python run.py snapshot --fast skip Monte Carlo (pure data card)
  python run.py ajaib           Ajaib ticket in IDR, manual execution
  python run.py watch 30 10     loop every 30s for 10 minutes
"""
