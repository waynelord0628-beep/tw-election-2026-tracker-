"""
找出三個市場在上線後第一小時內（20:43–21:43 UTC, Dec 4 2025）的交易者
市場上線時間: 1764966201 (2025-12-04T20:43:21Z)
第一小時結束: 1764969801 (2025-12-04T21:43:21Z)
"""

import requests
import time
from datetime import datetime, timezone

MARKETS = {
    "KMT": "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "DPP": "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016",
    "TPP": "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94",
}

MARKET_OPEN = 1764966201  # 20:43:21 UTC
FIRST_HOUR = 1764969801  # 21:43:21 UTC


def ts(unix):
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%H:%M:%S")


all_first_hour = []

for party, cid in MARKETS.items():
    url = f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset=0"
    resp = requests.get(url, timeout=30).json()
    for t in resp:
        unix = t.get("timestamp", 0)
        if MARKET_OPEN <= unix <= FIRST_HOUR:
            all_first_hour.append(
                {
                    "party": party,
                    "time_utc": ts(unix),
                    "unix": unix,
                    "side": t.get("side"),
                    "outcome": t.get("outcome"),
                    "size": round(t.get("size", 0), 2),
                    "price": round(t.get("price", 0), 4),
                    "amount": round(t.get("size", 0) * t.get("price", 0), 2),
                    "name": t.get("name") or t.get("pseudonym") or "",
                    "wallet": t.get("proxyWallet", ""),
                    "tx": t.get("transactionHash", ""),
                }
            )
    time.sleep(0.3)

# 按時間排序
all_first_hour.sort(key=lambda x: x["unix"])

print(f"市場上線後第一小時內共 {len(all_first_hour)} 筆交易")
print(
    f"{'時間(UTC)':<10} {'政黨':<5} {'方向':<5} {'標的':<5} {'金額$':<8} {'交易者':<25} {'錢包(前18)'}"
)
print("-" * 95)
for t in all_first_hour:
    print(
        f"{t['time_utc']:<10} {t['party']:<5} {t['side']:<5} {t['outcome']:<5} "
        f"{t['amount']:<8} {t['name']:<25} {t['wallet'][:18]}"
    )

# 唯一交易者
wallets = {}
for t in all_first_hour:
    w = t["wallet"]
    if w not in wallets:
        wallets[w] = {
            "name": t["name"],
            "parties": set(),
            "first_trade": t["time_utc"],
            "total": 0,
        }
    wallets[w]["parties"].add(t["party"])
    wallets[w]["total"] += t["amount"]

print(f"\n第一小時唯一交易者：{len(wallets)} 人")
print(f"{'交易者':<25} {'首次交易':<10} {'市場':<15} {'總金額$'}")
print("-" * 65)
for w, info in sorted(wallets.items(), key=lambda x: x[1]["first_trade"]):
    print(
        f"{info['name']:<25} {info['first_trade']:<10} {','.join(info['parties']):<15} {info['total']:.2f}"
    )
