"""
Alternative approach:
1. Use Polymarket Profile API to get user info (username, social, linked accounts)
2. Use The Graph UMA subgraph for ProposePrice events
3. Use 1rpc with small 10000-block chunks for eth_getLogs
"""

import requests
import json
import time
from datetime import datetime, timezone

RPC_URL = "https://1rpc.io/matic"

# All 16 proxy wallets
ALL_PROXIES = {
    "0x5f390e4b7d6f06d6756a6c92afdbf7b3176aa78c": "oVyg7f",
    "0x92a3e93b432ca24061bb86e2d448a86fc1d04a7d": "Donanza",
    "0x9a6b3684e3e6a98654eb9b4c9c3392f2c965a116": "Quantitative",
    "0x4f669af655fde97dff3356001d63d469ec662da4": "(no name)",
    "0xbc7c974eea213c5d59ccc93c8b1aa7c76d95c08e": "lilili99",
    "0x8fce065d5820ea3deb72976640290959bb952566": "CarolBeer",
    "0xe947b0748c6f37c656c7674636f93b4c527c7a45": "RepublicOfChina",
    "0xbc7096797e1fcff04d6aa66df1c61122c033574c": "batonchyk",
    "0x67948beb458a078ba926709e42ff4c8c269fec48": "(no name2)",
    "0xd218e474776403a330142299f7796e8ba32eb5c9": "cigarettes",
    "0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1": "wokerjoesleeper",
    "0x30cecdf29f069563ea21b8ae94492e41e53a6b2b": "ZXWP",
    "0xf6abc9dd44b3eaa78994e5eff04c395b0ee45514": "Hbk050816",
    "0x7ba5354929bf388707f397c8b21b8322dc954252": "Snpe",
    "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418": "ArmageddonRewardsBilly",
    "0xfdc9c2063b6c393c6a6badc74925e945f1a2c89b": "crawlidea",
}

OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"
PROPOSE_PRICE_TOPIC = (
    "0x0fe54f4630d87bad5e6f73a592644e3d66e41ec4b9a32a065ff8ededbed89b68"
)

# ============================================================
# STEP 1: Polymarket Profile API
# ============================================================
print("=" * 60)
print("STEP 1: Fetching Polymarket Profile API for each proxy")
print("=" * 60)

profile_data = {}
for proxy, name in ALL_PROXIES.items():
    # Try various profile endpoints
    urls_to_try = [
        f"https://data-api.polymarket.com/profiles?address={proxy}",
        f"https://data-api.polymarket.com/profile?address={proxy}",
        f"https://gamma-api.polymarket.com/profile?address={proxy}",
        f"https://data-api.polymarket.com/users/{proxy}",
    ]

    found = None
    for url in urls_to_try[:1]:  # try first one
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                found = data
                break
        except Exception as e:
            pass

    profile_data[proxy] = found
    if found:
        print(f"  [{name}]: {json.dumps(found)[:200]}")
    else:
        print(f"  [{name}]: no profile data")
    time.sleep(0.2)

# ============================================================
# STEP 2: Use The Graph UMA subgraph
# ============================================================
print()
print("=" * 60)
print("STEP 2: Query The Graph UMA subgraph for ProposePrice")
print("=" * 60)

# UMA has subgraphs on The Graph
# Try the official UMA subgraph for Polygon
UMA_SUBGRAPH_URLS = [
    "https://api.thegraph.com/subgraphs/name/umaprotocol/mainnet-optimistic-oracle",
    "https://api.thegraph.com/subgraphs/name/umaprotocol/polygon-optimistic-oracle",
    "https://thegraph.com/hosted-service/subgraph/umaprotocol/polygon-optimistic-oracle",
]

# GraphQL query for ProposePrice events related to our requester (UmaCtf Adapter)
query = """
{
  priceProposeds(
    first: 100
    orderBy: blockTimestamp
    orderDirection: desc
    where: { requester: "%s" }
  ) {
    id
    requester
    identifier
    time
    ancillaryData
    proposedPrice
    proposer
    expirationTimestamp
    blockTimestamp
    transactionHash
  }
}
""" % UMA_CTF_ADAPTER.lower()

for url in UMA_SUBGRAPH_URLS:
    print(f"\n  Trying: {url}")
    try:
        resp = requests.post(url, json={"query": query}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and data["data"]:
                proposals = data["data"].get("priceProposeds", [])
                print(f"  OK! Found {len(proposals)} proposals")
                for p in proposals[:5]:
                    ts = int(p.get("blockTimestamp", 0))
                    dt = (
                        datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                        if ts
                        else "N/A"
                    )
                    anc = (
                        bytes.fromhex(p.get("ancillaryData", "")[2:]).decode(
                            "utf-8", errors="replace"
                        )[:80]
                        if p.get("ancillaryData")
                        else ""
                    )
                    print(
                        f"    [{dt}] proposer={p.get('proposer')} price={p.get('proposedPrice')}"
                    )
                    print(f"          ancillary: {anc}")
                break
            elif "errors" in data:
                print(f"  GraphQL errors: {data['errors']}")
            else:
                print(f"  Unexpected response: {str(data)[:200]}")
        else:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  FAILED: {e}")

# ============================================================
# STEP 3: eth_getLogs with small 10000-block chunks via 1rpc
# ============================================================
print()
print("=" * 60)
print("STEP 3: eth_getLogs via 1rpc (10k block chunks)")
print("=" * 60)

# Market created Dec 4 2025 ~block 68.5M
# Today Apr 2026 = block ~85.85M
# That's ~17.35M blocks to scan = 1735 chunks of 10000
# Too many - let's focus on a tighter window
# Resolution proposals would come AFTER the Nov 2026 election
# But let's scan from market creation to now (market is still open)

# First find approximate block for Dec 4 2025
# Current block 85,850,858 at Apr 22 2026
# Days between Dec 4 2025 and Apr 22 2026 = 139 days
# 139 days * 43200 blocks/day = 6,004,800 blocks
# Dec 4 block ≈ 85,850,858 - 6,004,800 = 79,846,058


# Let's verify with a binary search approach using eth_getBlockByNumber
def get_block_timestamp(block_num):
    try:
        result = requests.post(
            RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBlockByNumber",
                "params": [hex(block_num), False],
            },
            timeout=10,
        ).json()
        ts = int(result["result"]["timestamp"], 16)
        return ts
    except:
        return None


print("  Finding block number for Dec 4 2025...")
# Dec 4 2025 00:00 UTC = 1764892800
target_ts = 1764892800

# Binary search
lo, hi = 79_000_000, 81_000_000
while hi - lo > 100:
    mid = (lo + hi) // 2
    ts = get_block_timestamp(mid)
    if ts is None:
        break
    if ts < target_ts:
        lo = mid
    else:
        hi = mid

dec4_block = lo
ts_check = get_block_timestamp(dec4_block)
    print(f"  Dec 4 2025 ~ block {dec4_block:,} (ts={ts_check}, target={target_ts})")

# Now scan from dec4_block to current
# Use 1rpc with 10000-block chunks
# Limit scan to important range only
padded_requester = "0x" + "0" * 24 + UMA_CTF_ADAPTER[2:].lower()

all_logs = []
chunk_size = 10000
start = dec4_block
current_block = 85_850_858
total_chunks = (current_block - start) // chunk_size + 1
print(f"  Scanning {start:,} to {current_block:,} in {total_chunks} chunks...")
print("  (This may take a while - will print progress every 50 chunks)")

for i, chunk_start in enumerate(range(start, current_block, chunk_size)):
    chunk_end = min(chunk_start + chunk_size - 1, current_block)
    try:
        result = requests.post(
            RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": OOV2_ADDRESS,
                        "topics": [PROPOSE_PRICE_TOPIC, padded_requester],
                        "fromBlock": hex(chunk_start),
                        "toBlock": hex(chunk_end),
                    }
                ],
            },
            timeout=30,
        ).json()

        if "result" in result:
            logs = result["result"]
            all_logs.extend(logs)
            if logs:
                print(
                    f"  Chunk {i + 1}/{total_chunks} (blocks {chunk_start:,}-{chunk_end:,}): {len(logs)} logs!"
                )
        elif "error" in result:
            if i % 100 == 0:
                print(f"  Chunk {i + 1} error: {result['error']}")
    except Exception as e:
        if i % 100 == 0:
            print(f"  Chunk {i + 1} exception: {e}")

    if i % 50 == 0 and i > 0:
        print(
            f"  Progress: {i + 1}/{total_chunks} chunks, {len(all_logs)} logs found so far"
        )

    time.sleep(0.05)  # gentle rate limiting

print(f"\n  Total ProposePrice logs found: {len(all_logs)}")

# Decode and save
output = {
    "profiles": profile_data,
    "propose_price_logs": all_logs,
}
with open("E:\\polymarket選舉賭博\\profile_and_logs.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print("Saved to profile_and_logs.json")
