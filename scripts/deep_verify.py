"""
deep_verify.py
深入分析為何 API 漏了 ArmageddonRewardsBilly 大量交易
"""

import requests, time
from collections import defaultdict

KMT_COND = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
KMT_YES = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
ARM = "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418"

# Step 1: 取得 API 所有 KMT 交易 tx hashes
print("=== Step 1: Fetch ALL KMT trades from API (full pagination) ===")
all_kmt = []
offset = 0
while True:
    r = requests.get(
        f"https://data-api.polymarket.com/trades?market={KMT_COND}&limit=500&offset={offset}",
        timeout=30,
    )
    batch = r.json()
    if not batch:
        break
    all_kmt.extend(batch)
    print(f"  offset={offset}: got {len(batch)} (total so far: {len(all_kmt)})")
    if len(batch) < 500:
        break
    offset += 500
    time.sleep(0.3)

api_hashes = set(
    t.get("transactionHash", "").lower() for t in all_kmt if t.get("transactionHash")
)
print(f"API total: {len(all_kmt)} trades, {len(api_hashes)} unique tx hashes")

# Step 2: ArmageddonRewardsBilly 的所有 KMT-Yes Blockscout transfers
print("\n=== Step 2: ArmageddonRewardsBilly KMT-Yes tx hashes (from Blockscout) ===")
arm_transfers = []
url = (
    f"https://polygon.blockscout.com/api/v2/tokens/{CTF}/instances/{KMT_YES}/transfers"
)
page_params = None
while True:
    r = requests.get(url, params=page_params, timeout=30)
    if r.status_code != 200:
        break
    d = r.json()
    items = d.get("items", [])
    for item in items:
        frm = item.get("from", {}).get("hash", "").lower()
        to_ = item.get("to", {}).get("hash", "").lower()
        if ARM.lower() in (frm, to_):
            arm_transfers.append(item)
    nxt = d.get("next_page_params")
    if not nxt:
        break
    page_params = nxt
    time.sleep(0.3)

print(f"ARM has {len(arm_transfers)} KMT-Yes transfers")
in_api = 0
not_in_api = []
for item in arm_transfers:
    txh = item.get("transaction_hash", "").lower()
    frm = item.get("from", {}).get("hash", "").lower()
    to_ = item.get("to", {}).get("hash", "").lower()
    val = int(item.get("total", {}).get("value", 0)) / 1e6
    ts = item.get("timestamp", "")[:10]
    if txh in api_hashes:
        # Is ARM the wallet in the API record?
        api_rec = [t for t in all_kmt if t.get("transactionHash", "").lower() == txh]
        arm_in_api = any(
            t.get("proxyWallet", "").lower() == ARM.lower() for t in api_rec
        )
        in_api += 1
        print(
            f"  IN API: {ts} {val:8.2f}  tx={txh[:20]}  ARM_in_api={arm_in_api}  api_wallets={list(set(t.get('proxyWallet', '')[:12] for t in api_rec))[:3]}"
        )
    else:
        not_in_api.append((ts, val, txh, frm, to_))
        print(f"  NOT IN API: {ts} {val:8.2f}  tx={txh[:20]}")

print(f"\nSummary: {in_api} in API, {len(not_in_api)} NOT in API")

# Step 3: Check one NOT-in-API tx to understand what kind of trade it is
if not_in_api:
    ts, val, txh, frm, to_ = not_in_api[0]
    print(f"\n=== Step 3: Inspect NOT-in-API tx {txh} ===")
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{txh}/token-transfers",
        timeout=20,
    )
    if r.status_code == 200:
        items = r.json().get("items", [])
        print(f"  Total token-transfers: {len(items)}")
        # Show unique wallet patterns
        seen = set()
        for item in items:
            sym = item.get("token", {}).get("symbol") or "?"
            frm2 = item.get("from", {}).get("hash", "")[:20]
            to_2 = item.get("to", {}).get("hash", "")[:20]
            val2 = int(item.get("total", {}).get("value", 0)) / 1e6
            typ = item.get("type", "")
            key = f"{typ[:15]:<15} {sym:<8} {frm2} -> {to_2} {val2:.4f}"
            if key not in seen:
                seen.add(key)
                print(f"    {key}")

    # Also check the tx details
    r2 = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{txh}", timeout=20
    )
    if r2.status_code == 200:
        tx_info = r2.json()
        print(f"  method: {tx_info.get('method')}")
        print(f"  to (contract): {tx_info.get('to', {}).get('hash')}")
        print(f"  from: {tx_info.get('from', {}).get('hash')}")

# Step 4: 比較官方 positions API 數字 vs 我們計算的 vs 截圖
print("\n=== Step 4: Summary comparison ===")
WALLETS = {
    "ArmageddonRewardsBilly": (
        "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418",
        7561,
        "Yes",
    ),
    "Anon-0xCE": ("0xc2358d03312b05b244bde5286dee03bc60ac99f8", 1919, "Yes"),
    "varch01": ("0x0362bb926368b144e0ff98f6828a251e4cb6449e", 1100, "Yes"),
    "SirJason": ("0x0cd7bea497efb9220105858617f0cd660d0a78e0", 2251, "No"),
    "cheesymm": ("0x06d248d4f372601d24192284bff919a2c05dfb27", 638, "No"),
    "jamieamoy": ("0xfde3a53d58320a3db74dbe1092979c401e35719a", 1445, "Yes"),
    "TTbilly": ("0xc25120b27e01031b2122f74488dcdb077a78b9c3", 700, "No"),
}

print(f"{'Name':30} {'Screenshot':>12} {'Pos.API':>10} {'Calc(API)':>10}")
print("-" * 70)
for name, (wallet, screenshot_val, outcome) in WALLETS.items():
    r = requests.get(
        f"https://data-api.polymarket.com/positions?user={wallet}", timeout=15
    )
    pos_api_val = 0
    if r.status_code == 200:
        for p in r.json():
            if p.get("conditionId", "").lower() == KMT_COND.lower():
                if p.get("outcome", "").lower() == outcome.lower():
                    pos_api_val = p.get("size", 0)

    # Calc from API trades
    calc = 0
    for t in all_kmt:
        if t.get("proxyWallet", "").lower() == wallet.lower():
            s = float(t.get("size", 0))
            if (
                t.get("side") == "BUY"
                and t.get("outcome", "").lower() == outcome.lower()
            ):
                calc += s
            elif (
                t.get("side") == "SELL"
                and t.get("outcome", "").lower() == outcome.lower()
            ):
                calc -= s

    print(f"{name:30} {screenshot_val:>12} {pos_api_val:>10.1f} {calc:>10.1f}")
    time.sleep(0.2)
