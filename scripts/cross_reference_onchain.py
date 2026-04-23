"""
cross_reference_onchain.py
從 Blockscout 抓取所有 6 個 token 的 ERC-1155 transfers，
與 Polymarket trades API 比對，找出漏網的鏈上交易。

NegRisk 規則：
  - token_minting  (from=0x0):  BUY
  - token_burning  (to=0x0):    SELL
  - 每筆 Polymarket 交易在 Blockscout 會有 2-3 條 transfer 記錄，同 tx_hash
  - 取唯一 tx_hash，確認哪些不在 Polymarket API 中
"""

import requests, time, json
from datetime import datetime, timezone, timedelta

TZ8 = timezone(timedelta(hours=8))
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
ZERO = "0x0000000000000000000000000000000000000000"

MARKETS = {
    "KMT": "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "DPP": "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016",
    "TPP": "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94",
}

TOKEN_MAP = {
    "85632914518786177256583369552125280053108667306405854845853340618248288927460": (
        "KMT",
        "Yes",
    ),
    "4696955573632845407532815267539406678302911508204032661527405293140196109387": (
        "KMT",
        "No",
    ),
    "13628189982642424912108657221169198338993179248246381972030640500448717195916": (
        "DPP",
        "Yes",
    ),
    "91004506882941445266754771479824617369805789899332711132070603219216406556613": (
        "DPP",
        "No",
    ),
    "14999500579901383072635205035227864886528710236540822730141548371372688859422": (
        "TPP",
        "Yes",
    ),
    "16222840603445450947154718759167300491302153317593739623696847197718420087623": (
        "TPP",
        "No",
    ),
}


def fetch_blockscout_transfers(token_id):
    """Fetch all token transfers from Blockscout for a given token ID."""
    url = f"https://polygon.blockscout.com/api/v2/tokens/{CTF}/instances/{token_id}/transfers"
    all_items = []
    page_params = None
    while True:
        r = requests.get(url, params=page_params, timeout=30)
        if r.status_code != 200:
            print(f"  Blockscout error {r.status_code}")
            break
        d = r.json()
        items = d.get("items", [])
        all_items.extend(items)
        nxt = d.get("next_page_params")
        if not nxt:
            break
        page_params = nxt
        time.sleep(0.3)
    return all_items


def fetch_polymarket_trades(condition_id):
    """Fetch all trades from Polymarket data-api."""
    trades = []
    offset = 0
    while True:
        r = requests.get(
            f"https://data-api.polymarket.com/trades?market={condition_id}&limit=500&offset={offset}",
            timeout=30,
        )
        batch = r.json()
        if not batch:
            break
        trades.extend(batch)
        offset += 500
        time.sleep(0.25)
        if len(batch) < 500:
            break
    return trades


def fetch_tx_details(tx_hash):
    """Get transaction details from Blockscout to find USDC value and caller."""
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}", timeout=20
    )
    if r.status_code == 200:
        return r.json()
    return {}


# ── Step 1: Fetch all Polymarket trades ──────────────────────────────────────
print("=== Step 1: Polymarket trades API ===")
poly_trades = {}  # {party: [trades]}
poly_hashes = set()  # all transaction hashes
for party, cid in MARKETS.items():
    trades = fetch_polymarket_trades(cid)
    trades.sort(key=lambda x: x.get("timestamp", 0))
    poly_trades[party] = trades
    for t in trades:
        h = t.get("transactionHash", "")
        if h:
            poly_hashes.add(h.lower())
    print(f"  {party}: {len(trades)} trades")
print(f"  Total unique tx hashes: {len(poly_hashes)}")

# ── Step 2: Fetch all Blockscout transfers ────────────────────────────────────
print("\n=== Step 2: Blockscout token transfers ===")
# tx_hash → {party, outcome, transfers: [...], side, user_addr, amount, timestamp}
onchain_txs = {}  # tx_hash -> dict

for tid, (party, outcome) in TOKEN_MAP.items():
    print(f"  Fetching {party}-{outcome}...", end="", flush=True)
    items = fetch_blockscout_transfers(tid)
    print(f" {len(items)} transfers")

    for item in items:
        tx_hash = item.get("transaction_hash", "").lower()
        if not tx_hash:
            continue

        from_addr = item.get("from", {}).get("hash", "").lower()
        to_addr = item.get("to", {}).get("hash", "").lower()
        amount_raw = item.get("total", {}).get("value", "0")
        try:
            amount = int(amount_raw) / 1_000_000  # 6 decimals
        except:
            amount = 0
        ts_str = item.get("timestamp", "")
        transfer_type = item.get("type", "")

        if tx_hash not in onchain_txs:
            onchain_txs[tx_hash] = {
                "tx_hash": tx_hash,
                "timestamp": ts_str,
                "transfers": [],
                "parties": set(),
            }

        onchain_txs[tx_hash]["transfers"].append(
            {
                "party": party,
                "outcome": outcome,
                "from": from_addr,
                "to": to_addr,
                "amount": amount,
                "type": transfer_type,
            }
        )
        onchain_txs[tx_hash]["parties"].add(party)

print(f"  Total unique tx hashes on-chain: {len(onchain_txs)}")

# ── Step 3: Find missing transactions ────────────────────────────────────────
print("\n=== Step 3: Cross-reference ===")
missing_hashes = set(onchain_txs.keys()) - poly_hashes
print(f"  Polymarket API hashes:  {len(poly_hashes)}")
print(f"  On-chain unique hashes: {len(onchain_txs)}")
print(f"  Missing from API:       {len(missing_hashes)}")

# Analyze missing transactions
print(f"\n=== Missing transactions detail ({len(missing_hashes)} txs) ===")
missing_details = []
for tx_hash in sorted(missing_hashes):
    tx = onchain_txs[tx_hash]
    parties = list(tx["parties"])
    transfers = tx["transfers"]
    ts = tx["timestamp"]

    # Determine side: if any transfer is minting → BUY; if burning → SELL
    sides = set()
    for tr in transfers:
        if tr["from"] == ZERO or tr["from"] == NEG_RISK_EXCHANGE.lower():
            if tr["to"] != ZERO:
                sides.add("BUY")
        if tr["to"] == ZERO:
            sides.add("SELL")
        if tr["type"] == "token_minting":
            sides.add("BUY")
        if tr["type"] == "token_burning":
            sides.add("SELL")

    # Find user (not CTF, not NEG_RISK_EXCHANGE, not ZERO)
    addrs = set()
    for tr in transfers:
        for addr in [tr["from"], tr["to"]]:
            if (
                addr
                and addr != ZERO
                and addr != CTF.lower()
                and addr != NEG_RISK_EXCHANGE.lower()
            ):
                addrs.add(addr)

    # Amount from Yes token transfer
    yes_amounts = [
        tr["amount"] for tr in transfers if tr["outcome"] == "Yes" and tr["amount"] > 0
    ]
    amount = max(yes_amounts) if yes_amounts else 0

    detail = {
        "tx_hash": tx_hash,
        "timestamp": ts,
        "parties": ",".join(sorted(parties)),
        "side": ",".join(sides) if sides else "?",
        "user_addrs": list(addrs),
        "amount": round(amount, 2),
        "transfer_count": len(transfers),
    }
    missing_details.append(detail)
    print(
        f"  {ts[:19]} {','.join(sorted(parties)):12} {','.join(sides) if sides else '?':6} {amount:8.2f} shares  {list(addrs)[:2]}"
    )
    print(f"    hash: {tx_hash}")

# Save to JSON for next step
with open(
    "E:\\polymarket選舉賭博\\missing_onchain_txs.json", "w", encoding="utf-8"
) as f:
    json.dump(missing_details, f, indent=2, default=str)

print(f"\nSaved {len(missing_details)} missing txs to missing_onchain_txs.json")
