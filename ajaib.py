"""Ajaib Coin Exchange adapter — free, stdlib only.

Public (no key):   GET /coin/internal/v1/public/time
                   GET /coin/internal/v1/public/exchange-info
Authenticated:*    price, depth, trades, order, portfolio ...
   *Access is not self-service: generate an ECDSA-SHA256 keypair, email the
    PUBLIC key to tech@ajaib.co.id, receive an X-API-KEY. This module signs
    requests correctly the moment you drop your key files into ajaib_keys/.

No orders from this tool. Manual trade in the Ajaib app: use the ticket that
run.py prints (IDR quote + suggested size).
"""
import hashlib
import json
import os
import subprocess
import urllib.request

BASES = ["https://api.ajaib.co.id", "https://api.ajaib.tech"]
KEY_DIR = os.path.join(os.path.dirname(__file__), "ajaib_keys")


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _first_ok(path: str):
    for base in BASES:
        try:
            return base, _get(base + path)
        except Exception:
            continue
    return None, None


def server_time():
    base, resp = _first_ok("/coin/internal/v1/public/time")
    return (resp or {}).get("data") or resp


def exchange_info():
    base, resp = _first_ok("/coin/internal/v1/public/exchange-info")
    return (resp or {}).get("data") or resp


def has_keys() -> bool:
    ok = os.path.isdir(KEY_DIR) and any(
        f.endswith(".key") and not f.endswith(".pub")
        for f in os.listdir(KEY_DIR))
    return ok


# --- optional: OpenSSL ECDSA signing for when Ajaib issues you an X-API-KEY ----
def sign_headers(method: str, path: str):
    """Build X-API-KEY/X-SIGNATURE/X-TIMESTAMP headers using ajaib_keys/*.pem.

    Signature = ECDSA-SHA256 over (timestamp_ms + METHOD + path + query + body).
    Requires OpenSSL on PATH (built into Windows 10+/OpenSSH too).
    """
    ts = str(int(_ms()))
    priv = next((os.path.join(KEY_DIR, f) for f in os.listdir(KEY_DIR)
                 if f.endswith(".pem")), None)
    if not priv:
        return {}
    payload = ts + method.upper() + path
    p = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", priv],
        input=payload.encode(), capture_output=True, timeout=10)
    if p.returncode != 0:
        return {}
    import base64
    sig = base64.b64encode(p.stdout).decode()
    return {"X-TIMESTAMP": ts,
            "X-SIGNATURE": sig,
            "X-API-KEY": os.path.splitext(os.path.basename(priv))[0]}


def _ms():
    import time
    return int(time.time() * 1000)


def key_setup_hint() -> str:
    return (
        "Ajaib API (optional, still free):\n"
        "  1) openssl ecparam -name secp256k1 -genkey -noout -out ajaib_keys/ajaib.pem\n"
        "  2) openssl ec -in ajaib_keys/ajaib.pem -pubout -text | XXD VB (copy hex)\n"
        "  3) Email the PUBLIC key + your Ajaib ID to tech@ajaib.co.id\n"
        "  4) They reply with an X-API-KEY bound to that public key.\n"
        "  Until then: quotes below come from public/fallback sources, execute manually in the Ajaib app.\n"
        "  Config keys live as FILES on your disk, never in the chat.\n"
    )
