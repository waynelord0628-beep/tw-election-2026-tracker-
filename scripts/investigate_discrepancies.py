"""
investigate_discrepancies.py
深入調查：為何 ArmageddonRewardsBilly 計算值 (265) vs 截圖 (7,561) 差距懸殊
1. 從 Polymarket positions API 查個別錢包持倉
2. 從 Blockscout 直接查該錢包的 KMT token transfers
3. 確認 trades API 是否漏抓交易
"""

import requests, time
from collections import defaultdict

KMT_COND = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
KMT_YES_TOKEN = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
KMT_NO_TOKEN = (
    "4696955573632845407532815267539406678302911508204032661527405293140196109387"
)
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

WALLETS = {
    "ArmageddonRewardsBilly": "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418",
    "Anon-0xCE": "0xc2358d03312b05b244bde5286dee03bc60ac99f8",
    "varch01": "0x0362bb926368b144e0ff98f6828a251e4cb6449e",
    "SirJason": "0x0cd7bea497efb9220105858617f0cd660d0a78e0",
    "cheesymm": "0x06d248d4f372601d24192284bff919a2c05dfb27",
    "jamieamoy": "0xfde3a53d58320a3db74dbe1092979c401e35719a",
    "TTbilly": "0xc25120b27e01031b2122f74488dcdb077a78b9c3",
}

# ── Step 1: Polymarket positions API per wallet ───────────────────────────────
print("=== Step 1: Polymarket positions API per wallet ===")
for name, wallet in WALLETS.items():
    r = requests.get(
        f"https://data-api.polymarket.com/positions?user={wallet}", timeout=20
    )
    if r.status_code == 200:
        positions = r.json()
        kmt_pos = [
            p
            for p in positions
            if KMT_COND
            in str(p.get("conditionId", "") or p.get("market", "") or "").lower()
            or str(p.get("asset", "")) in [KMT_YES_TOKEN, KMT_NO_TOKEN]
        ]
        if not kmt_pos:
            # Also check by token asset IDs
            kmt_pos = [
                p
                for p in positions
                if str(p.get("asset", "")) in [KMT_YES_TOKEN, KMT_NO_TOKEN]
            ]
        print(f"  {name}: {len(positions)} total positions")
        for p in positions[:5]:
            print(f"    {p}")
        if kmt_pos:
            print(f"  -> KMT positions: {kmt_pos}")
    else:
        print(f"  {name}: HTTP {r.status_code}")
    time.sleep(0.3)

# ── Step 2: Trades API per wallet ────────────────────────────────────────────
print("\n=== Step 2: Trades API per wallet (user param) ===")
for name, wallet in WALLETS.items():
    # Try user-specific trade endpoint
    r = requests.get(
        f"https://data-api.polymarket.com/trades?user={wallet}&market={KMT_COND}&limit=500",
        timeout=20,
    )
    trades = r.json() if r.status_code == 200 else []
    if isinstance(trades, list):
        print(f"  {name}: {len(trades)} trades (user+market filter)")
    else:
        print(f"  {name}: {r.status_code} {str(trades)[:100]}")
    time.sleep(0.3)

# ── Step 3: Blockscout token transfers for ArmageddonRewardsBilly ────────────
print("\n=== Step 3: Blockscout KMT-Yes token transfers for ArmageddonRewardsBilly ===")
arm_wallet = WALLETS["ArmageddonRewardsBilly"].lower()

# Fetch all transfers of KMT Yes token
url = f"https://polygon.blockscout.com/api/v2/tokens/{CTF}/instances/{KMT_YES_TOKEN}/transfers"
all_arm_transfers = []
page_params = None
while True:
    r = requests.get(url, params=page_params, timeout=30)
    if r.status_code != 200:
        break
    d = r.json()
    items = d.get("items", [])
    # Filter for this wallet
    for item in items:
        frm = item.get("from", {}).get("hash", "").lower()
        to_ = item.get("to", {}).get("hash", "").lower()
        if arm_wallet in (frm, to_):
            all_arm_transfers.append(item)
    nxt = d.get("next_page_params")
    if not nxt:
        break
    page_params = nxt
    time.sleep(0.3)

print(f"  KMT Yes transfers involving ArmageddonRewardsBilly: {len(all_arm_transfers)}")
bought = 0
sold = 0
for item in all_arm_transfers:
    frm = item.get("from", {}).get("hash", "").lower()
    to_ = item.get("to", {}).get("hash", "").lower()
    ttype = item.get("type", "")
    val = int(item.get("total", {}).get("value", 0)) / 1e6
    ts = item.get("timestamp", "")[:19]
    tx = item.get("transaction_hash", "")[:20]
    direction = "RECV" if to_ == arm_wallet else "SENT"
    print(f"    {ts} {direction} {val:8.2f} shares  type={ttype}  tx={tx}")
    if to_ == arm_wallet:
        bought += val
    else:
        sold += val

print(f"  Total received: {bought:.2f}, sent: {sold:.2f}, net: {bought - sold:.2f}")

# ── Step 4: Check how many trades API returns for this wallet alone ───────────
print(
    "\n=== Step 4: How many API trades for ArmageddonRewardsBilly across all markets ==="
)
for party, cid in [
    ("KMT", KMT_COND),
    ("DPP", "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016"),
    ("TPP", "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94"),
]:
    r = requests.get(
        f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset=0",
        timeout=30,
    )
    all_t = r.json() if r.status_code == 200 else []
    arm_t = [t for t in all_t if t.get("proxyWallet", "").lower() == arm_wallet]
    print(
        f"  {party}: {len(arm_t)} trades for ArmageddonRewardsBilly (out of {len(all_t)} total in first 500)"
    )
    time.sleep(0.2)
