"""
Try Blockscout API for Polygon (open, no key needed)
and also try direct UMA oracle API
"""

import requests
import json
import time
from datetime import datetime, timezone

OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"
PROPOSE_PRICE_TOPIC = (
    "0x0fe54f4630d87bad5e6f73a592644e3d66e41ec4b9a32a065ff8ededbed89b68"
)
padded_requester = "0x" + "0" * 24 + UMA_CTF_ADAPTER[2:].lower()

# ============================================================
# STEP 1: Blockscout for Polygon
# ============================================================
print("=== Blockscout Polygon API ===")

BLOCKSCOUT_BASE = "https://polygon.blockscout.com/api"

# Get logs for OOV2 from Blockscout
params = {
    "module": "logs",
    "action": "getLogs",
    "address": OOV2_ADDRESS,
    "topic0": PROPOSE_PRICE_TOPIC,
    "topic1": padded_requester,
    "topic0_1_opr": "and",
    "fromBlock": 79875000,
    "toBlock": 99999999,
}

try:
    resp = requests.get(BLOCKSCOUT_BASE, params=params, timeout=30)
    print(f"Status code: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Blockscout getLogs error: {e}")

# Try Blockscout REST v2 API for txns
print("\n=== Blockscout V2 REST API - OOV2 txns ===")
try:
    resp = requests.get(
        f"https://polygon.blockscout.com/api/v2/addresses/{OOV2_ADDRESS}/transactions",
        params={"filter": "to"},
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        txns = data.get("items", [])
        print(f"Got {len(txns)} txns")
        # Look for proposePrice calls
        for tx in txns[:20]:
            method = tx.get("method", "")
            decoded = tx.get("decoded_input", {})
            frm = tx.get("from", {}).get("hash", "")
            ts_str = tx.get("timestamp", "")
            if "propose" in (method or "").lower() or "propose" in str(decoded).lower():
                print(f"  PROPOSE: {frm[:20]} at {ts_str} method={method}")
            else:
                print(f"  {frm[:20]} method={method} ts={ts_str[:10]}")
    else:
        print(resp.text[:300])
except Exception as e:
    print(f"Error: {e}")

# ============================================================
# STEP 2: UMA Oracle API / oracle.uma.xyz backend
# ============================================================
print("\n=== UMA Oracle API ===")

# Try UMA's oracle API (used by oracle.uma.xyz frontend)
uma_api_urls = [
    "https://oracle.uma.xyz/api/requests?chainId=137&limit=50",
    "https://oracle-api.uma.xyz/requests?chainId=137&limit=50",
    "https://api.uma.xyz/requests?network=polygon&limit=50",
]

for url in uma_api_urls:
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        print(f"{url[:50]}: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Content: {resp.text[:400]}")
    except Exception as e:
        print(f"{url[:50]}: {e}")

# ============================================================
# STEP 3: Direct check - is this market's resolution visible
# on Polymarket's own resolution data feed?
# ============================================================
print("\n=== Polymarket Resolution Feed ===")
urls = [
    "https://clob.polymarket.com/resolution?market=0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "https://gamma-api.polymarket.com/resolution?conditionId=0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "https://data-api.polymarket.com/resolution?conditionId=0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
]
for url in urls:
    try:
        resp = requests.get(url, timeout=10)
        print(f"{url[:70]}: {resp.status_code} -> {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

# ============================================================
# STEP 4: Check OOV2 via Alchemy free RPC (might allow getLogs)
# ============================================================
print("\n=== Alchemy Public RPC for Polygon ===")
alchemy_url = "https://polygon-mainnet.g.alchemy.com/v2/demo"
try:
    resp = requests.post(
        alchemy_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getLogs",
            "params": [
                {
                    "address": OOV2_ADDRESS,
                    "topics": [PROPOSE_PRICE_TOPIC, padded_requester],
                    "fromBlock": hex(85_840_000),
                    "toBlock": "latest",
                }
            ],
        },
        timeout=15,
    )
    data = resp.json()
    if "result" in data:
        logs = data["result"]
        print(f"Alchemy: Got {len(logs)} logs (recent ~10k blocks)")
    else:
        print(f"Alchemy error: {data.get('error', {}).get('message', '')[:200]}")
except Exception as e:
    print(f"Alchemy: {e}")
