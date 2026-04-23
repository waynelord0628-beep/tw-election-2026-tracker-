"""
Deeper investigation:
1. Try more storage slots / function selectors to find EOA for remaining 10 proxy wallets
2. Investigate the shared EOA 0xe51abdf814f8854941b9fe8e3a4f65cab4e7a4a8
3. Try Polygonscan API for eth_getLogs on UMA OOV2
"""

import requests
import json
import time

RPC_URL = "https://polygon.drpc.org"
# Also try 1rpc for getLogs
RPC_URL_2 = "https://1rpc.io/matic"

SHARED_EOA = "0xe51abdf814f8854941b9fe8e3a4f65cab4e7a4a8"

# Wallets that returned None (unknown owner)
UNKNOWN_PROXIES = {
    "0x92a3e93b432ca24061bb86e2d448a86fc1d04a7d": "Donanza",
    "0x9a6b3684e3e6a98654eb9b4c9c3392f2c965a116": "Quantitative",
    "0x4f669af655fde97dff3356001d63d469ec662da4": "(no name)",
    "0xbc7c974eea213c5d59ccc93c8b1aa7c76d95c08e": "lilili99",
    "0x8fce065d5820ea3deb72976640290959bb952566": "CarolBeer",
    "0xe947b0748c6f37c656c7674636f93b4c527c7a45": "RepublicOfChina",
    "0xd218e474776403a330142299f7796e8ba32eb5c9": "cigarettes",
    "0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1": "wokerjoesleeper",
    "0xf6abc9dd44b3eaa78994e5eff04c395b0ee45514": "Hbk050816",
    "0x7ba5354929bf388707f397c8b21b8322dc954252": "Snpe",
}


def rpc_call(method, params, url=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = requests.post(url or RPC_URL, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")
    return result["result"]


def try_get_owner(proxy):
    """Try multiple methods to get EOA."""
    methods = [
        ("owner()", "0x8da5cb5b"),
        ("getOwner()", "0x893d20e8"),
        ("getOwners()", "0xa0e67e2b"),
    ]

    for name, selector in methods:
        try:
            result = rpc_call("eth_call", [{"to": proxy, "data": selector}, "latest"])
            if result and result != "0x" and len(result) >= 66:
                # Could be single address (32 bytes) or dynamic array
                # For single address: last 20 bytes of 32-byte result
                addr = "0x" + result[-40:]
                if addr.lower() != "0x" + "0" * 40:
                    return addr.lower(), name
        except:
            pass

    # Try storage slots 0-10
    for slot in range(11):
        try:
            result = rpc_call("eth_getStorageAt", [proxy, hex(slot), "latest"])
            if result and result != "0x" + "0" * 64:
                # Check if it looks like an address (20 bytes, non-zero)
                val = result[2:]  # strip 0x
                if val.startswith("0" * 24) and val[24:] != "0" * 40:
                    addr = "0x" + val[24:]
                    return addr.lower(), f"slot {slot}"
        except:
            pass

    return None, None


print("=" * 60)
print("STEP A: Deeper EOA discovery for remaining 10 proxy wallets")
print("=" * 60)

discovered = {}
for proxy, name in UNKNOWN_PROXIES.items():
    eoa, method = try_get_owner(proxy)
    discovered[proxy] = (name, eoa, method)
    status = f"{eoa} (via {method})" if eoa else "NOT FOUND"
    print(f"  [{name}] {proxy[:20]}... → {status}")
    time.sleep(0.2)


print()
print("=" * 60)
print(f"STEP B: Investigate shared EOA: {SHARED_EOA}")
print("=" * 60)

# Check tx count on Polygon for the shared EOA
try:
    tx_count = rpc_call("eth_getTransactionCount", [SHARED_EOA, "latest"])
    print(f"  TX count: {int(tx_count, 16):,}")
except Exception as e:
    print(f"  TX count error: {e}")

# Check MATIC balance
try:
    balance = rpc_call("eth_getBalance", [SHARED_EOA, "latest"])
    matic = int(balance, 16) / 1e18
    print(f"  MATIC balance: {matic:.4f}")
except Exception as e:
    print(f"  Balance error: {e}")


print()
print("=" * 60)
print("STEP C: Try eth_getLogs via 1rpc.io for UMA ProposePrice")
print("=" * 60)

OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"
PROPOSE_PRICE_TOPIC = (
    "0x0fe54f4630d87bad5e6f73a592644e3d66e41ec4b9a32a065ff8ededbed89b68"
)

# Try a small block range first to confirm it works
test_from = hex(85_800_000)
test_to = "latest"

padded_requester = "0x" + "0" * 24 + UMA_CTF_ADAPTER[2:].lower()

for rpc_url in [RPC_URL_2, "https://polygon.drpc.org"]:
    print(f"\n  Testing {rpc_url}...")
    try:
        logs = rpc_call(
            "eth_getLogs",
            [
                {
                    "address": OOV2_ADDRESS,
                    "topics": [PROPOSE_PRICE_TOPIC, padded_requester],
                    "fromBlock": test_from,
                    "toBlock": test_to,
                }
            ],
            url=rpc_url,
        )
        print(f"  OK! Got {len(logs)} logs for blocks 85.8M-latest")
        if logs:
            for log in logs[:3]:
                print(
                    f"    tx: {log.get('transactionHash')}, block: {int(log.get('blockNumber', '0x0'), 16):,}"
                )
    except Exception as e:
        print(f"  FAILED: {e}")

print()
print("=" * 60)
print("STEP D: Use Polygonscan API for getLogs (no auth needed for basic)")
print("=" * 60)

# Polygonscan free API (up to 5 calls/sec, 10K results max)
# getLogs endpoint
# fromBlock / toBlock in decimal
POLYGONSCAN_API = "https://api.polygonscan.com/api"


def polygonscan_get_logs(address, topic0, topic1=None, from_block=None, to_block=None):
    params = {
        "module": "logs",
        "action": "getLogs",
        "address": address,
        "topic0": topic0,
        "fromBlock": from_block or 68000000,
        "toBlock": to_block or "latest",
    }
    if topic1:
        params["topic1"] = topic1
        params["topic0_1_opr"] = "and"
    resp = requests.get(POLYGONSCAN_API, params=params, timeout=30)
    data = resp.json()
    return data


print("  Fetching ProposePrice logs via Polygonscan API (no API key)...")
print("  Blocks 68M - latest, requester = UmaCtf Adapter")

result = polygonscan_get_logs(
    address=OOV2_ADDRESS,
    topic0=PROPOSE_PRICE_TOPIC,
    topic1=padded_requester,
    from_block=68_000_000,
)

print(f"  Status: {result.get('status')}, Message: {result.get('message')}")
logs = result.get("result", [])
if isinstance(logs, list):
    print(f"  Found {len(logs)} ProposePrice events")
    for log in logs:
        block_num = int(log.get("blockNumber", "0x0"), 16)
        tx_hash = log.get("transactionHash", "")
        data = log.get("data", "")
        topics = log.get("topics", [])
        print(f"\n  Block: {block_num:,} | Tx: {tx_hash}")
        print(f"    Topics: {topics}")
        print(f"    Data: {data[:100]}...")
else:
    print(f"  Result: {logs}")
