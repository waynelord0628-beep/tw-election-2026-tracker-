"""
verify_data.py
完整資料驗證：
1. 從 trades 計算各錢包淨持倉
2. 從 Polymarket positions API 取得官方持倉
3. 比對兩者差異
4. 抽樣驗證個別交易正確性（與Blockscout原始tx比對）
"""

import requests, time, json
from collections import defaultdict

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

# ── Step 1: Fetch all trades ──────────────────────────────────────────────────
print("=== Step 1: Fetching all trades ===")
all_trades = []
for party, cid in MARKETS.items():
    offset = 0
    while True:
        r = requests.get(
            f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset={offset}",
            timeout=30,
        )
        batch = r.json()
        if not batch:
            break
        for t in batch:
            t["_party"] = party
        all_trades.extend(batch)
        offset += 500
        time.sleep(0.2)
        if len(batch) < 500:
            break
    print(f"  {party}: fetched")

print(f"Total trades: {len(all_trades)}")

# ── Step 2: Calculate net positions from trades ───────────────────────────────
print("\n=== Step 2: Calculate net positions from trades ===")
# net_pos[wallet][party][outcome] = net shares
net_pos = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
wallet_names = {}

for t in all_trades:
    w = t.get("proxyWallet", "").lower()
    if not w:
        continue
    party = t["_party"]
    outcome = t.get("outcome", "")
    side = t.get("side", "")
    try:
        size = float(t.get("size", 0))
    except:
        size = 0
    nm = t.get("name") or t.get("pseudonym") or ""
    if nm:
        wallet_names[w] = nm

    if side == "BUY":
        net_pos[w][party][outcome] += size
    elif side == "SELL":
        net_pos[w][party][outcome] -= size

# KMT Yes top holders (calculated)
kmt_yes_holders = []
for w, parties in net_pos.items():
    shares = parties.get("KMT", {}).get("Yes", 0)
    if shares > 0.01:
        kmt_yes_holders.append((w, shares, wallet_names.get(w, "")))

kmt_yes_holders.sort(key=lambda x: -x[1])
print("\nKMT Yes top 15 (calculated from trades):")
for i, (w, shares, name) in enumerate(kmt_yes_holders[:15], 1):
    print(f"  {i:2}. {shares:8.1f}  {name or '(unnamed)':30}  {w}")

kmt_no_holders = []
for w, parties in net_pos.items():
    shares = parties.get("KMT", {}).get("No", 0)
    if shares > 0.01:
        kmt_no_holders.append((w, shares, wallet_names.get(w, "")))

kmt_no_holders.sort(key=lambda x: -x[1])
print("\nKMT No top 15 (calculated from trades):")
for i, (w, shares, name) in enumerate(kmt_no_holders[:15], 1):
    print(f"  {i:2}. {shares:8.1f}  {name or '(unnamed)':30}  {w}")

# ── Step 3: Fetch official positions from Polymarket API ─────────────────────
print("\n=== Step 3: Fetch official positions from Polymarket API ===")

# Try positions endpoint for top wallets
kmt_yes_cond = MARKETS["KMT"]

# Polymarket has a positions API
# GET https://data-api.polymarket.com/positions?market={conditionId}&limit=500
pos_url = f"https://data-api.polymarket.com/positions?market={kmt_yes_cond}&limit=500"
r = requests.get(pos_url, timeout=30)
print(f"  positions API status: {r.status_code}")
if r.status_code == 200:
    positions = r.json()
    print(f"  Got {len(positions)} position records")
    if positions:
        print(
            f"  Sample keys: {list(positions[0].keys()) if isinstance(positions, list) else 'not a list'}"
        )
        print(f"  First 3:")
        for p in positions[:3]:
            print(f"    {p}")
else:
    print(f"  Response: {r.text[:200]}")

# ── Step 4: Try alternative positions endpoint ────────────────────────────────
print("\n=== Step 4: Try alternative endpoints ===")

# Try activity endpoint
for endpoint in [
    f"https://data-api.polymarket.com/positions?conditionId={kmt_yes_cond}&limit=100",
    f"https://data-api.polymarket.com/holdings?market={kmt_yes_cond}&limit=100",
    f"https://gamma-api.polymarket.com/positions?conditionId={kmt_yes_cond}&limit=100",
]:
    r = requests.get(endpoint, timeout=15)
    print(f"  {endpoint.split('.com/')[1][:60]} -> {r.status_code} len={len(r.text)}")
    if r.status_code == 200 and len(r.text) > 10:
        try:
            data = r.json()
            if data and isinstance(data, list) and len(data) > 0:
                print(f"    Keys: {list(data[0].keys())}")
                print(f"    First: {data[0]}")
        except:
            pass
    time.sleep(0.3)

# ── Step 5: Verify individual trades via Blockscout ──────────────────────────
print("\n=== Step 5: Spot-check individual trades vs Blockscout ===")
# Pick ArmageddonRewardsBilly's trades to verify
armageddon_wallet = None
for w, name in wallet_names.items():
    if "Armageddon" in name:
        armageddon_wallet = w
        break

if armageddon_wallet:
    print(f"ArmageddonRewardsBilly wallet: {armageddon_wallet}")
    arm_trades = [
        t for t in all_trades if t.get("proxyWallet", "").lower() == armageddon_wallet
    ]
    print(f"Trades found: {len(arm_trades)}")
    arm_kmt = [t for t in arm_trades if t["_party"] == "KMT"]
    print(f"KMT trades: {len(arm_kmt)}")
    buy_yes = sum(
        float(t.get("size", 0))
        for t in arm_kmt
        if t.get("side") == "BUY" and t.get("outcome") == "Yes"
    )
    sell_yes = sum(
        float(t.get("size", 0))
        for t in arm_kmt
        if t.get("side") == "SELL" and t.get("outcome") == "Yes"
    )
    buy_no = sum(
        float(t.get("size", 0))
        for t in arm_kmt
        if t.get("side") == "BUY" and t.get("outcome") == "No"
    )
    sell_no = sum(
        float(t.get("size", 0))
        for t in arm_kmt
        if t.get("side") == "SELL" and t.get("outcome") == "No"
    )
    print(
        f"  KMT Yes: bought {buy_yes:.2f}, sold {sell_yes:.2f}, net = {buy_yes - sell_yes:.2f}"
    )
    print(
        f"  KMT No:  bought {buy_no:.2f}, sold {sell_no:.2f}, net = {buy_no - sell_no:.2f}"
    )

    # Verify one tx via Blockscout
    sample_tx = arm_kmt[0]
    tx_hash = sample_tx.get("transactionHash", "")
    print(f"\n  Spot-checking tx: {tx_hash}")
    print(
        f"  API says: side={sample_tx.get('side')}, outcome={sample_tx.get('outcome')}, size={sample_tx.get('size')}, price={sample_tx.get('price')}"
    )

    r2 = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}/token-transfers",
        timeout=20,
    )
    if r2.status_code == 200:
        items = r2.json().get("items", [])
        usdc_items = [
            x
            for x in items
            if "USDC" in str(x.get("token", {}).get("symbol") or "").upper()
        ]
        print(
            f"  Blockscout tx token-transfers: {len(items)} total, {len(usdc_items)} USDC"
        )
        for u in usdc_items:
            frm = u.get("from", {}).get("hash", "")[:22]
            to_ = u.get("to", {}).get("hash", "")[:22]
            val = int(u.get("total", {}).get("value", 0)) / 1e6
            print(f"    USDC: from={frm} to={to_} val={val}")
