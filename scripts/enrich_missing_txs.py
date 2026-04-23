"""
enrich_missing_txs.py
對 87 筆漏網交易：
1. 確認 0xa5ef39... 是什麼合約（NegRisk adapter？）
2. 分類：real trade vs merge/split
3. 對 real trade 抓 Blockscout tx details → USDC 金額 → 計算價格
4. 查使用者 Polymarket profile（name/pseudonym）
"""

import requests, json, time
from datetime import datetime, timezone, timedelta

TZ8 = timezone(timedelta(hours=8))
USDC_POLYGON = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"  # USDC.e
USDC_BRIDGED = "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"  # native USDC

NEG_RISK_ADAPTER_SUSPECT = "0xa5ef39c3d3e10d0b270233af41cac69796b12966"
CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
NEG_EX = "0xc5d563a36ae78145c45a50134d48a1215220f80a"

# ── 1. 確認 0xa5ef39... 合約身份 ────────────────────────────────────────────
print("=== 確認 0xa5ef39... 合約 ===")
r = requests.get(
    f"https://polygon.blockscout.com/api/v2/addresses/{NEG_RISK_ADAPTER_SUSPECT}",
    timeout=15,
)
if r.status_code == 200:
    d = r.json()
    print(f"  name: {d.get('name')}")
    print(f"  is_contract: {d.get('is_contract')}")
    print(f"  is_verified: {d.get('is_verified')}")
    print(f"  tags: {d.get('metadata')}")
    print(f"  implementations: {d.get('implementations')}")
print()

# Load missing txs
with open("E:\\polymarket選舉賭博\\missing_onchain_txs.json", "r") as f:
    missing = json.load(f)

# ── 2. 分類 ─────────────────────────────────────────────────────────────────
real_trades = []
merge_split = []
unclear = []

for tx in missing:
    parties = tx["parties"]
    side = tx["side"]
    amount = tx["amount"]

    # DPP,KMT,TPP 同時 + amount=0 → merge/split
    has_all_three = "KMT" in parties and "DPP" in parties and "TPP" in parties

    if has_all_three and amount == 0:
        merge_split.append(tx)
    elif side in ("BUY", "SELL") or amount > 0:
        real_trades.append(tx)
    else:
        unclear.append(tx)

print(f"分類結果:")
print(f"  real trades: {len(real_trades)}")
print(f"  merge/split: {len(merge_split)}")
print(f"  unclear:     {len(unclear)}")
print()

# ── 3. 對 real trades 補抓 tx 詳情 ──────────────────────────────────────────
print("=== 補抓 real trades 詳情 ===")


def get_tx_details(tx_hash):
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}/token-transfers",
        timeout=20,
    )
    if r.status_code == 200:
        return r.json().get("items", [])
    return []


def get_tx_info(tx_hash):
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}", timeout=20
    )
    if r.status_code == 200:
        return r.json()
    return {}


def get_polymarket_profile(wallet):
    r = requests.get(
        f"https://data-api.polymarket.com/profile?address={wallet}", timeout=10
    )
    if r.status_code == 200:
        d = r.json()
        if isinstance(d, list) and d:
            return d[0].get("name", "") or d[0].get("pseudonym", "")
        elif isinstance(d, dict):
            return d.get("name", "") or d.get("pseudonym", "")
    return ""


enriched = []
for i, tx in enumerate(real_trades):
    tx_hash = tx["tx_hash"]
    print(
        f"  [{i + 1}/{len(real_trades)}] {tx_hash[:16]}... {tx['parties']} {tx['side']} {tx['amount']}"
    )

    # Get token transfers in this tx
    transfers = get_tx_details(tx_hash)
    time.sleep(0.3)

    # Find USDC transfer amount
    usdc_amount = 0
    for tr in transfers:
        token_addr = tr.get("token", {}).get("address", "").lower()
        if token_addr in (USDC_POLYGON, USDC_BRIDGED):
            try:
                raw = int(tr.get("total", {}).get("value", "0"))
                usdc_amount = max(usdc_amount, raw / 1_000_000)  # 6 decimals
            except:
                pass

    # Find user address (not contract addresses)
    user_addr = ""
    for addr in tx["user_addrs"]:
        if addr.lower() not in (
            CTF,
            NEG_EX,
            NEG_RISK_ADAPTER_SUSPECT,
            "0x0000000000000000000000000000000000000000",
        ):
            user_addr = addr
            break

    # Get Polymarket profile
    name = get_polymarket_profile(user_addr) if user_addr else ""
    time.sleep(0.2)

    # Calculate price
    shares = tx["amount"]
    price = round(usdc_amount / shares, 4) if shares > 0 else 0

    # Parse timestamp
    ts_str = tx["timestamp"]
    try:
        dt_utc = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        dt8 = dt_utc.astimezone(TZ8)
        ts_display = dt8.strftime("%Y-%m-%d %H:%M:%S")
        ts_epoch = int(dt_utc.timestamp())
    except:
        ts_display = ts_str[:19]
        ts_epoch = 0

    enriched_tx = {
        "timestamp": ts_epoch,
        "timestamp_display": ts_display,
        "parties": tx["parties"],
        "side": tx["side"],
        "amount": shares,
        "usdc": round(usdc_amount, 4),
        "price": price,
        "user_addr": user_addr,
        "name": name,
        "tx_hash": tx_hash,
        "source": "onchain",
    }
    enriched.append(enriched_tx)
    print(
        f"    → user={user_addr[:12]} name={name} USDC={usdc_amount:.2f} price={price:.4f}"
    )

print()
print(f"enriched {len(enriched)} real trades")

# Save
with open(
    "E:\\polymarket選舉賭博\\enriched_missing_trades.json", "w", encoding="utf-8"
) as f:
    json.dump(
        {"real_trades": enriched, "merge_split_count": len(merge_split)}, f, indent=2
    )
print("Saved to enriched_missing_trades.json")

# ── 4. 分析 merge/split 樣本 ────────────────────────────────────────────────
print()
print("=== Merge/Split 樣本分析 ===")
if merge_split:
    sample = merge_split[0]
    print(f"  sample tx: {sample['tx_hash']}")
    transfers = get_tx_details(sample["tx_hash"])
    for tr in transfers[:8]:
        print(
            f"  {tr.get('type')} {tr.get('token', {}).get('symbol', '?')} "
            f"from={tr.get('from', {}).get('hash', '')[:16]} "
            f"to={tr.get('to', {}).get('hash', '')[:16]} "
            f"amount={tr.get('total', {}).get('value')}"
        )
