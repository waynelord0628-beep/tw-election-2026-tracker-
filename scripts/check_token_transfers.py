"""
查詢 ChiangWan-an 和 Kuomintang 的代幣來源
"""

import requests
import json

KMT_CONDITION_ID = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
KMT_YES_TOKEN_ID = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
KMT_NO_TOKEN_ID = (
    "4696955573632845407532815267539406678302911508204032661527405293140196109387"
)

ADDRESSES = {
    "ChiangWan-an": "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24",
    "Kuomintang": "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa",
}


def fetch_address_trades_limited(address, max_pages=7):
    """取得最多 max_pages * 500 筆交易"""
    url = "https://data-api.polymarket.com/trades"
    all_trades = []
    offset = 0
    limit = 500
    for _ in range(max_pages):
        resp = requests.get(
            url,
            params={"proxyWallet": address, "limit": limit, "offset": offset},
            timeout=30,
        )
        data = resp.json()
        if not data or not isinstance(data, list):
            break
        trades = [t for t in data if isinstance(t, dict)]
        all_trades.extend(trades)
        print(f"  offset={offset}, 本頁 {len(trades)} 筆")
        if len(data) < limit:
            break
        offset += limit
    return all_trades


def fetch_blockscout_erc1155(address, retries=3):
    """查詢 Blockscout ERC-1155 transfers，含重試"""
    url = "https://polygon.blockscout.com/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": 79887801,
        "endblock": 99999999,
        "sort": "asc",
    }
    for attempt in range(retries):
        try:
            print(f"  Blockscout 查詢（第{attempt + 1}次）...")
            resp = requests.get(url, params=params, timeout=60)
            data = resp.json()
            if data.get("status") == "1":
                return data.get("result", [])
            else:
                print(
                    f"  回應: {data.get('message')} - {str(data.get('result', ''))[:100]}"
                )
                return []
        except Exception as e:
            print(f"  錯誤: {e}")
    return []


def fetch_polygonscan_erc1155(address):
    """備用：用 Polygonscan API 查 ERC-1155 transfers"""
    # 不需要 API key 也能查，但有速率限制
    url = "https://api.polygonscan.com/api"
    params = {
        "module": "account",
        "action": "token1155tx",
        "address": address,
        "startblock": 79887801,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": "YourApiKeyToken",
    }
    try:
        print(f"  Polygonscan 查詢...")
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        print(f"  狀態: {data.get('status')} / {data.get('message')}")
        result = data.get("result", [])
        if isinstance(result, list):
            return result
        else:
            print(f"  回應: {str(result)[:200]}")
            return []
    except Exception as e:
        print(f"  錯誤: {e}")
        return []


print("=" * 60)

for name, addr in ADDRESSES.items():
    print(f"\n【{name}】{addr}")

    # 1. 查 Polymarket trades
    print("\n[1] 查詢 Polymarket 交易（最多 3500 筆）...")
    trades = fetch_address_trades_limited(addr, max_pages=7)
    print(f"    共 {len(trades)} 筆")

    # 顯示前 2 筆 trade 的所有欄位（debug）
    if trades:
        print(f"    範例欄位: {list(trades[0].keys())}")

    # 用 lower() 比較 conditionId
    kmt_trades = [
        t
        for t in trades
        if str(t.get("conditionId", "")).lower() == KMT_CONDITION_ID.lower()
    ]
    print(f"    KMT 市場交易: {len(kmt_trades)} 筆")
    for t in kmt_trades:
        print(
            f"      {str(t.get('timestamp', ''))[:19]}  {t.get('side', ''):4}  {t.get('outcome', ''):3}  {t.get('size', ''):>10} shares @ ${t.get('price', '')}"
        )

    # 2. 查 Polygonscan ERC-1155
    print("\n[2] 查詢 Polygonscan ERC-1155 transfers...")
    transfers = fetch_polygonscan_erc1155(addr)
    print(f"    共 {len(transfers)} 筆 token transfer")

    kmt_transfers = [
        t
        for t in transfers
        if isinstance(t, dict)
        and t.get("tokenID") in [KMT_YES_TOKEN_ID, KMT_NO_TOKEN_ID]
    ]
    if kmt_transfers:
        print(f"    KMT 代幣 transfer {len(kmt_transfers)} 筆：")
        for t in kmt_transfers:
            direction = "IN " if t.get("to", "").lower() == addr.lower() else "OUT"
            token_name = "Yes" if t.get("tokenID") == KMT_YES_TOKEN_ID else "No"
            print(
                f"      {direction}  KMT-{token_name}  數量:{t.get('value', ''):>12}  from:{t.get('from', '')[:20]}  hash:{t.get('hash', '')[:20]}..."
            )
    elif transfers:
        print("    未找到 KMT 代幣（顯示前3筆tokenID）：")
        for t in transfers[:3]:
            print(
                f"      tokenID={t.get('tokenID', '')} contractAddress={t.get('contractAddress', '')}"
            )

print("\n完成。")
