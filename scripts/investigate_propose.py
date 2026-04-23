"""
Investigate the proposePrice transaction from 2026-04-21
and get full address of settle bot.
"""

import requests
import json
from datetime import datetime, timezone

OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"

# ============================================================
# Get full addresses from Blockscout V2 API
# ============================================================
print("=== Get full transaction details from Blockscout V2 ===")

resp = requests.get(
    f"https://polygon.blockscout.com/api/v2/addresses/{OOV2_ADDRESS}/transactions",
    params={"filter": "to"},
    timeout=30,
)
data = resp.json()
txns = data.get("items", [])

settle_bot_addr = None
propose_txns = []

for tx in txns:
    method = tx.get("method", "")
    frm = tx.get("from", {}).get("hash", "")
    ts_str = tx.get("timestamp", "")
    tx_hash = tx.get("hash", "")

    if method == "settle":
        settle_bot_addr = frm  # all settle calls from same bot

    if method == "proposePrice":
        propose_txns.append(
            {
                "from": frm,
                "timestamp": ts_str,
                "hash": tx_hash,
                "decoded_input": tx.get("decoded_input", {}),
            }
        )
        print(f"  proposePrice: from={frm} at {ts_str}")
        print(f"  tx_hash: {tx_hash}")
        print(f"  decoded_input: {json.dumps(tx.get('decoded_input', {}))[:400]}")

if settle_bot_addr:
    print(f"\n  Settle bot FULL address: {settle_bot_addr}")

# ============================================================
# Get full transaction details for proposePrice txns
# ============================================================
print("\n=== Fetch full tx details for proposePrice calls ===")

for p in propose_txns:
    tx_hash = p["hash"]
    print(f"\n  Fetching tx: {tx_hash}")

    # Get tx details
    try:
        resp = requests.get(
            f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}", timeout=30
        )
        if resp.status_code == 200:
            tx_data = resp.json()
            frm = tx_data.get("from", {}).get("hash", "")
            decoded = tx_data.get("decoded_input", {})
            raw_input = tx_data.get("raw_input", "")

            print(f"  From: {frm}")
            print(f"  Timestamp: {tx_data.get('timestamp')}")
            print(f"  Status: {tx_data.get('status')}")
            print(f"  Decoded Input: {json.dumps(decoded, indent=2)[:600]}")
        else:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

# ============================================================
# Get ALL proposePrice calls by paginating Blockscout
# ============================================================
print("\n=== Paginate all OOV2 transactions to find all proposePrice ===")

all_propose = []
next_page_params = None
page = 0
MAX_PAGES = 50  # limit to avoid infinite loop

while page < MAX_PAGES:
    url = f"https://polygon.blockscout.com/api/v2/addresses/{OOV2_ADDRESS}/transactions"
    params = {"filter": "to"}
    if next_page_params:
        params.update(next_page_params)

    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  Page {page}: HTTP {resp.status_code}")
        break

    data = resp.json()
    items = data.get("items", [])

    for tx in items:
        method = tx.get("method", "")
        if method == "proposePrice":
            frm = tx.get("from", {}).get("hash", "")
            ts = tx.get("timestamp", "")
            h = tx.get("hash", "")
            all_propose.append({"from": frm, "timestamp": ts, "hash": h})
            print(f"  PAGE {page}: proposePrice from {frm} at {ts}")

    next_page_params = data.get("next_page_params")
    if not next_page_params:
        print(f"  Page {page}: reached end (no more pages)")
        break

    page += 1
    import time

    time.sleep(0.5)

print(f"\nTotal proposePrice calls found: {len(all_propose)}")
for p in all_propose:
    print(f"  {p['from']} at {p['timestamp']} tx={p['hash'][:20]}...")
