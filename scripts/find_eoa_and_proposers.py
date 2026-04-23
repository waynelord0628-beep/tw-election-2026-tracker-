"""
Script to:
1. Find EOA (owner) behind each opening-day proxy wallet via Polygon RPC
2. Fetch ProposePrice event logs from UMA OOV2 for this specific market
3. Cross-reference to see if any opening-day trader also submitted a UMA proposal
"""

import requests
import json
import time
from datetime import datetime, timezone

# Polygon public RPC (drpc, no auth required)
RPC_URL = "https://polygon.drpc.org"

# UMA OptimisticOracleV2 on Polygon
OOV2_ADDRESS = "0xee3afe347d5c74317041e2618c49534daf887c24"

# UmaCtf Adapter (used for this market)
UMA_CTF_ADAPTER = "0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d"

# The 16 unique opening-day KMT proxy wallets
PROXY_WALLETS = [
    "0x5f390e4b7d6f06d6756a6c92afdbf7b3176aa78c",  # oVyg7f
    "0x92a3e93b432ca24061bb86e2d448a86fc1d04a7d",  # Donanza
    "0x9a6b3684e3e6a98654eb9b4c9c3392f2c965a116",  # Quantitative
    "0x4f669af655fde97dff3356001d63d469ec662da4",  # (no name)
    "0xbc7c974eea213c5d59ccc93c8b1aa7c76d95c08e",  # lilili99
    "0x8fce065d5820ea3deb72976640290959bb952566",  # CarolBeer
    "0xe947b0748c6f37c656c7674636f93b4c527c7a45",  # RepublicOfChina
    "0xbc7096797e1fcff04d6aa66df1c61122c033574c",  # batonchyk
    "0x67948beb458a078ba926709e42ff4c8c269fec48",  # (no name)
    "0xd218e474776403a330142299f7796e8ba32eb5c9",  # cigarettes
    "0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1",  # wokerjoesleeper
    "0x30cecdf29f069563ea21b8ae94492e41e53a6b2b",  # ZXWP
    "0xf6abc9dd44b3eaa78994e5eff04c395b0ee45514",  # Hbk050816
    "0x7ba5354929bf388707f397c8b21b8322dc954252",  # Snpe
    "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418",  # ArmageddonRewardsBilly
    "0xfdc9c2063b6c393c6a6badc74925e945f1a2c89b",  # crawlidea
]

PROXY_NAMES = {
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

# Market opened 2025-12-04T20:43:21Z = block ~around 66,000,000 on Polygon
# Polygon ~2s block time, ~30M blocks/year
# Dec 2025 is roughly block 68,000,000 area
# Let's search a wide range around market creation
# The market was created 2025-12-04; resolution would come much later (election is 2026)
# For now we search from market creation forward - use hex blocks
# We'll use eth_getLogs with fromBlock/toBlock

# ProposePrice event signature:
# ProposePrice(address requester, bytes32 identifier, uint256 timestamp, bytes ancillaryData,
#              int256 proposedPrice, uint256 expirationTimestamp, address currency, address proposer)
# keccak256("ProposePrice(address,bytes32,uint256,bytes,int256,uint256,address,address)")
PROPOSE_PRICE_TOPIC = (
    "0x0fe54f4630d87bad5e6f73a592644e3d66e41ec4b9a32a065ff8ededbed89b68"
)

# RequestPrice event
REQUEST_PRICE_TOPIC = (
    "0x0497c7a01b3e67e3029a1eb9f6c1e8af7b02a00fbbcce37cd2b3fca6e7f9e0c8"
)


def rpc_call(method, params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = requests.post(RPC_URL, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")
    return result["result"]


def get_eoa_owner(proxy_address):
    """
    Try multiple methods to get the owner/EOA of a Polymarket proxy wallet.
    Polymarket proxy wallets implement owner() → address
    """
    # Method 1: call owner() - selector 0x8da5cb5b
    try:
        result = rpc_call(
            "eth_call", [{"to": proxy_address, "data": "0x8da5cb5b"}, "latest"]
        )
        if result and result != "0x" and len(result) >= 66:
            # Returns 32-byte padded address
            owner = "0x" + result[-40:]
            if owner != "0x" + "0" * 40:
                return owner.lower()
    except Exception as e:
        print(f"  owner() failed for {proxy_address}: {e}")

    # Method 2: storage slot 0 (common for simple proxies)
    try:
        result = rpc_call("eth_getStorageAt", [proxy_address, "0x0", "latest"])
        if result and result != "0x" + "0" * 64:
            owner = "0x" + result[-40:]
            return owner.lower()
    except Exception as e:
        print(f"  storage slot 0 failed for {proxy_address}: {e}")

    return None


def get_current_block():
    result = rpc_call("eth_blockNumber", [])
    return int(result, 16)


def get_propose_price_logs(from_block_hex, to_block_hex, requester=None):
    """
    Get ProposePrice events from UMA OOV2.
    Optionally filter by requester (UmaCtf Adapter address).
    """
    filter_params = {
        "address": OOV2_ADDRESS,
        "topics": [PROPOSE_PRICE_TOPIC],
        "fromBlock": from_block_hex,
        "toBlock": to_block_hex,
    }
    if requester:
        # requester is topic[1] (indexed)
        # pad address to 32 bytes
        padded = "0x" + "0" * 24 + requester[2:].lower()
        filter_params["topics"] = [PROPOSE_PRICE_TOPIC, padded]

    return rpc_call("eth_getLogs", [filter_params])


def decode_propose_price_log(log):
    """Decode a ProposePrice event log."""
    # topics[0] = event sig
    # topics[1] = requester (indexed, address)
    # topics[2] = identifier (indexed, bytes32)
    # topics[3] = timestamp (indexed, uint256)
    # data = ancillaryData(bytes) + proposedPrice(int256) + expirationTimestamp(uint256) + currency(address) + proposer(address)
    # Note: bytes is dynamic, so data layout is complex

    topics = log.get("topics", [])
    data = log.get("data", "")

    requester = None
    identifier = None
    timestamp = None
    proposer = None
    proposed_price = None

    if len(topics) >= 2:
        requester = "0x" + topics[1][-40:]
    if len(topics) >= 3:
        identifier = topics[2]
    if len(topics) >= 4:
        timestamp = int(topics[3], 16)

    # data is ABI-encoded: (bytes ancillaryData, int256 proposedPrice, uint256 expiration, address currency, address proposer)
    # But since ancillaryData is dynamic, offset structure:
    # [0:32]  offset to ancillaryData
    # [32:64] proposedPrice
    # [64:96] expirationTimestamp
    # [96:128] currency (address, padded)
    # [128:160] proposer (address, padded)
    # [at offset] length of ancillaryData + data

    if data and data != "0x" and len(data) > 2:
        raw = data[2:]  # strip 0x
        words = [raw[i : i + 64] for i in range(0, len(raw), 64)]
        if len(words) >= 5:
            try:
                proposed_price = int(words[1], 16)
                proposer = "0x" + words[4][-40:]
            except:
                pass

    return {
        "requester": requester,
        "identifier": identifier,
        "timestamp": timestamp,
        "proposer": proposer,
        "proposed_price": proposed_price,
        "block_number": int(log.get("blockNumber", "0x0"), 16),
        "tx_hash": log.get("transactionHash", ""),
    }


def find_block_at_timestamp(target_ts):
    """Binary search for block near timestamp (approximate)."""
    # Polygon avg block time ~2.2s
    # Current block ~approx - let's just use a known reference
    # Dec 4, 2025 = 1764892800
    # Polygon launched May 2020, at ~0.002M blocks/day, ~730 blocks/day
    # Actually Polygon does ~43200 blocks/day (2s/block)
    # Days from genesis (block 0 = May 30 2020) to Dec 4 2025 = ~2014 days
    # ~2014 * 43200 = ~86,904,800 blocks
    # Let's use a known block: block 68000000 ~ approx late 2025
    # We'll do rough estimate
    return hex(68_000_000)


# ============================================================
# STEP 1: Find EOA for each proxy wallet
# ============================================================
print("=" * 60)
print("STEP 1: Finding EOA owner for each proxy wallet")
print("=" * 60)

proxy_to_eoa = {}
for proxy in PROXY_WALLETS:
    name = PROXY_NAMES[proxy]
    eoa = get_eoa_owner(proxy)
    proxy_to_eoa[proxy] = eoa
    print(f"  [{name}] {proxy}")
    print(f"    → EOA: {eoa}")
    time.sleep(0.3)

print()
eoa_set = set(v.lower() for v in proxy_to_eoa.values() if v)
print(f"Found {len(eoa_set)} unique EOAs out of {len(PROXY_WALLETS)} proxies")

# ============================================================
# STEP 2: Search UMA OOV2 ProposePrice logs
# ============================================================
print()
print("=" * 60)
print("STEP 2: Searching UMA OOV2 ProposePrice events")
print("=" * 60)

# Market created Dec 4 2025. Election is Nov 2026.
# Resolution proposals would come after election results.
# But we also want to check if anyone proposed on OTHER markets (to gauge sophistication).
# Start from market creation block, search forward to latest.

# Approximate blocks:
# Dec 4 2025 = block ~68,500,000
# Latest (Apr 2026) = block ~68,500,000 + (140 days * 43200 blocks/day) = ~74,548,000

from_block = hex(68_000_000)
to_block = "latest"

# Due to RPC limits, eth_getLogs may reject huge ranges.
# We'll chunk in 500k block increments.
CHUNK_SIZE = 500_000

print(f"Fetching ProposePrice logs from block {int(from_block, 16):,} to latest...")
print(f"Filtering by requester = UmaCtf Adapter: {UMA_CTF_ADAPTER}")
print()

current_block_num = int(rpc_call("eth_blockNumber", []), 16)
print(f"Current block: {current_block_num:,}")

start = int(from_block, 16)
all_propose_logs = []
chunk_count = 0

while start < current_block_num:
    end = min(start + CHUNK_SIZE - 1, current_block_num)
    from_hex = hex(start)
    to_hex = hex(end)
    try:
        logs = get_propose_price_logs(from_hex, to_hex, requester=UMA_CTF_ADAPTER)
        all_propose_logs.extend(logs)
        print(
            f"  Blocks {start:,}-{end:,}: {len(logs)} ProposePrice events (total: {len(all_propose_logs)})"
        )
    except Exception as e:
        print(f"  Blocks {start:,}-{end:,}: ERROR - {e}")
        # Try smaller chunk
        mid = (start + end) // 2
        try:
            logs = get_propose_price_logs(
                hex(start), hex(mid), requester=UMA_CTF_ADAPTER
            )
            all_propose_logs.extend(logs)
            print(f"    Sub-chunk {start:,}-{mid:,}: {len(logs)} events")
            logs = get_propose_price_logs(
                hex(mid + 1), hex(end), requester=UMA_CTF_ADAPTER
            )
            all_propose_logs.extend(logs)
            print(f"    Sub-chunk {mid + 1:,}-{end:,}: {len(logs)} events")
        except Exception as e2:
            print(f"    Sub-chunk also failed: {e2}")
    start = end + 1
    chunk_count += 1
    time.sleep(0.3)

print(f"\nTotal ProposePrice events found: {len(all_propose_logs)}")

# ============================================================
# STEP 3: Decode logs and extract proposers
# ============================================================
print()
print("=" * 60)
print("STEP 3: Decoding proposers from logs")
print("=" * 60)

decoded_proposals = []
proposer_set = set()
for log in all_propose_logs:
    decoded = decode_propose_price_log(log)
    decoded_proposals.append(decoded)
    if decoded["proposer"]:
        proposer_set.add(decoded["proposer"].lower())

print(f"Unique proposers found: {len(proposer_set)}")
for p in sorted(proposer_set):
    print(f"  {p}")

# ============================================================
# STEP 4: Cross-reference
# ============================================================
print()
print("=" * 60)
print("STEP 4: Cross-referencing opening-day traders vs UMA proposers")
print("=" * 60)

matches = []
for proxy, eoa in proxy_to_eoa.items():
    if eoa and eoa.lower() in proposer_set:
        name = PROXY_NAMES[proxy]
        matches.append((name, proxy, eoa))
        print(f"  *** MATCH: {name} | proxy={proxy} | EOA={eoa}")

if not matches:
    print("  No direct matches found.")
    print()
    print("  All EOAs (opening-day traders):")
    for proxy, eoa in proxy_to_eoa.items():
        name = PROXY_NAMES[proxy]
        print(f"    {name}: {eoa}")
    print()
    print("  All proposers (UMA OOV2):")
    for p in sorted(proposer_set):
        print(f"    {p}")

# ============================================================
# STEP 5: Check proposals for THIS specific market
# ============================================================
print()
print("=" * 60)
print("STEP 5: Checking proposals specifically for this market")
print("=" * 60)

# The negRiskMarketID is 0x8f14f57ffaf0bbc777be06d4e275bf0dfe32fa40eeb588752f7ca9eab7afb400
# The ancillaryData would contain the question text about 2026 Taiwan elections
# Let's look at all decoded proposals and show their details

for i, proposal in enumerate(decoded_proposals):
    ts_str = (
        datetime.fromtimestamp(proposal["timestamp"] or 0, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if proposal["timestamp"]
        else "N/A"
    )
    print(f"\n  Proposal #{i + 1}:")
    print(f"    Block:     {proposal['block_number']:,}")
    print(f"    Tx Hash:   {proposal['tx_hash']}")
    print(f"    Proposer:  {proposal['proposer']}")
    print(f"    Price:     {proposal['proposed_price']}")
    print(f"    Timestamp: {ts_str}")

# Save results to JSON
output = {
    "proxy_to_eoa": proxy_to_eoa,
    "all_proposers": list(proposer_set),
    "decoded_proposals": decoded_proposals,
    "matches": [{"name": m[0], "proxy": m[1], "eoa": m[2]} for m in matches],
}
with open(
    "E:\\polymarket選舉賭博\\eoa_proposer_analysis.json", "w", encoding="utf-8"
) as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n結果を保存: E:\\polymarket選舉賭博\\eoa_proposer_analysis.json")
