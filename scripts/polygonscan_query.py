"""
Use Polygonscan API V2 to:
1. Get txlist for UMA OOV2 and find proposePrice calls
2. Check proxy wallet transactions for any UMA interactions
"""

import requests
import json
import time
from datetime import datetime, timezone

# Polygonscan V2 (chainid=137 for Polygon)
# Without API key: limited to recent 10k tx, but might work
PSCAN_V2 = "https://api.polygonscan.com/v2/api"
PSCAN_V1 = "https://api.polygonscan.com/api"

OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"

# proposePrice function selector
# UMA OOV2 ABI: proposePrice(address,bytes32,uint256,bytes,int256)
# keccak256("proposePrice(address,bytes32,uint256,bytes,int256)") = 0x...
# Let's compute it
import hashlib


def keccak256_selector(sig):
    from hashlib import sha3_256

    # Need actual keccak256, not sha3_256 - they differ
    # Use a manual approach or just hardcode known selectors
    pass


# Known function selectors from UMA OOV2 source code / Polygonscan
# proposePrice = 0x6dfe7cf1 (check this)
# We'll search txns by looking at input data prefix

PROPOSE_PRICE_SELECTORS = [
    "0x6dfe7cf1",  # proposePrice(address,bytes32,uint256,bytes,int256) - to verify
    "0x9974f834",  # possible alternate
]

# ============================================================
# STEP 1: Get recent OOV2 transactions from Polygonscan (no key)
# ============================================================
print("=" * 60)
print("STEP 1: Get OOV2 transaction list from Polygonscan")
print("=" * 60)


def pscan_txlist(
    address, startblock=0, endblock=99999999, page=1, offset=100, sort="desc"
):
    """Get transaction list for an address."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": startblock,
        "endblock": endblock,
        "page": page,
        "offset": offset,
        "sort": sort,
        # No API key - will be rate limited but should work for small queries
    }
    resp = requests.get(PSCAN_V1, params=params, timeout=30)
    return resp.json()


# Try fetching recent OOV2 txns (last 100)
print(f"  Fetching last 100 txns for OOV2: {OOV2_ADDRESS}")
result = pscan_txlist(OOV2_ADDRESS, sort="desc", offset=100)
print(f"  Status: {result.get('status')}, Message: {result.get('message')}")
txns = result.get("result", [])
if isinstance(txns, list):
    print(f"  Got {len(txns)} transactions")

    # Find proposePrice calls
    propose_txns = []
    for tx in txns:
        inp = tx.get("input", "")
        if inp and len(inp) >= 10:
            selector = inp[:10]
            # Print first few txns to identify selector patterns
            if tx.get("from", "").lower() != "0x0cabe...":  # not the bot
                ts = int(tx.get("timeStamp", 0))
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"  [{dt}] from={tx.get('from', '')[:20]}... func={selector}")

    # Show all unique function selectors in recent 100 txns
    selectors = {}
    for tx in txns:
        inp = tx.get("input", "")
        if inp and len(inp) >= 10:
            sel = inp[:10]
            frm = tx.get("from", "")
            if sel not in selectors:
                selectors[sel] = {"count": 0, "callers": set()}
            selectors[sel]["count"] += 1
            selectors[sel]["callers"].add(frm.lower())

    print("\n  Function selector summary:")
    for sel, info in sorted(selectors.items(), key=lambda x: -x[1]["count"]):
        callers = list(info["callers"])[:3]
        print(f"    {sel}: {info['count']} calls, callers: {[c[:20] for c in callers]}")
else:
    print(f"  Error: {txns}")

# ============================================================
# STEP 2: Try Polygonscan V2
# ============================================================
print()
print("=" * 60)
print("STEP 2: Polygonscan V2 getLogs")
print("=" * 60)

PROPOSE_PRICE_TOPIC = (
    "0x0fe54f4630d87bad5e6f73a592644e3d66e41ec4b9a32a065ff8ededbed89b68"
)
padded_requester = "0x" + "0" * 24 + UMA_CTF_ADAPTER[2:].lower()

# V2 endpoint
params = {
    "chainid": "137",
    "module": "logs",
    "action": "getLogs",
    "address": OOV2_ADDRESS,
    "topic0": PROPOSE_PRICE_TOPIC,
    "topic1": padded_requester,
    "topic0_1_opr": "and",
    "fromBlock": 79875000,
    "toBlock": 99999999,
}
resp = requests.get(PSCAN_V2, params=params, timeout=30)
print(f"  Status code: {resp.status_code}")
data = resp.json()
print(f"  Status: {data.get('status')}, Message: {data.get('message')}")
logs = data.get("result", [])
if isinstance(logs, list):
    print(f"  Found {len(logs)} ProposePrice logs")
    for log in logs:
        block_num = int(log.get("blockNumber", "0x0"), 16)
        tx_hash = log.get("transactionHash", "")
        data_hex = log.get("data", "")
        topics = log.get("topics", [])

        # Decode proposer from data (last address in the encoded data)
        proposer = None
        if data_hex and len(data_hex) > 2:
            raw = data_hex[2:]
            words = [raw[i : i + 64] for i in range(0, len(raw), 64)]
            if len(words) >= 5:
                proposer = "0x" + words[4][-40:]

        ts = int(log.get("timeStamp", "0x0"), 16)
        dt = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if ts
            else "N/A"
        )
        print(f"\n  [{dt}] Block: {block_num:,}")
        print(f"    Tx:       {tx_hash}")
        print(f"    Proposer: {proposer}")
else:
    print(f"  Result: {str(logs)[:300]}")
