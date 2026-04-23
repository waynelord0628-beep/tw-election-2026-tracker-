import requests

tx_hash = "0x789c588349aadb4724"  # ChiangWan-an 送出 80 KMT-Yes (截斷版，需完整hash)
# 先查 ChiangWan-an 在 KMT-Yes 的完整 OUT transfer
import sys

# 實際上 find_chiangwan_kmt_source.py 輸出的 hash 被截斷了，先查
addr = "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24"
resp0 = requests.get(
    f"https://polygon.blockscout.com/api/v2/addresses/{addr}/token-transfers",
    params={
        "type": "ERC-1155",
        "filter": "from",
        "token": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
    },
    timeout=60,
)
data0 = resp0.json()
items0 = data0.get("items", [])
print(f"ChiangWan-an outgoing CTF transfers: {len(items0)} 筆（最近）")
kmt_yes = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
for t in items0:
    total = t.get("total", {})
    token_id = total.get("token_id", "") if isinstance(total, dict) else ""
    if token_id == kmt_yes:
        print(
            f"  KMT-Yes OUT: hash={t.get('transaction_hash', '')} block={t.get('block_number')} value={total.get('value', '')}"
        )
        tx_hash = t.get("transaction_hash", "")
        break
if not tx_hash or tx_hash.startswith("0x789"):
    print("未找到，結束")
    sys.exit(0)
print(f"分析 tx: {tx_hash}")

resp = requests.get(
    f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}", timeout=30
)
data = resp.json()
print("method:", data.get("method"))
print("status:", data.get("status"))
from_info = data.get("from", {})
to_info = data.get("to", {})
print("from:", from_info.get("hash") if isinstance(from_info, dict) else from_info)
print("to:", to_info.get("hash") if isinstance(to_info, dict) else to_info)
print("timestamp:", data.get("timestamp"))
decoded = data.get("decoded_input", {})
if isinstance(decoded, dict):
    print("decoded method:", decoded.get("method_call"))

print()
resp2 = requests.get(
    f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}/token-transfers",
    timeout=30,
)
data2 = resp2.json()
items = data2.get("items", [])
print(f"Token transfers: {len(items)} 筆")
for t in items:
    from_a = (
        t.get("from", {}).get("hash", "") if isinstance(t.get("from"), dict) else ""
    )
    to_a = t.get("to", {}).get("hash", "") if isinstance(t.get("to"), dict) else ""
    total = t.get("total", {})
    ttype = t.get("type", "")
    if isinstance(total, dict):
        print(
            f"  [{ttype}] tokenId={str(total.get('token_id', ''))[:35]}... value={total.get('value', '')}"
        )
    print(f"  from={from_a[:42]}  to={to_a[:42]}")
    print()
