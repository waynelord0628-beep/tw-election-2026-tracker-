"""
用 Blockscout v2 REST API 查詢 KMT Yes/No 代幣的 ERC-1155 transfers
"""

import requests

KMT_YES_TOKEN_ID = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
KMT_NO_TOKEN_ID = (
    "4696955573632845407532815267539406678302911508204032661527405293140196109387"
)
# CTF (Conditional Token Framework) contract on Polygon
CTF_CONTRACT = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

ADDRESSES = {
    "ChiangWan-an": "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24",
    "Kuomintang": "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa",
}


def fetch_blockscout_v2_token_transfers(address):
    """Blockscout v2 API: 查詢特定地址的 ERC-1155 token transfers"""
    # 先試 /api/v2/addresses/{address}/token-transfers
    url = f"https://polygon.blockscout.com/api/v2/addresses/{address}/token-transfers"
    params = {
        "type": "ERC-1155",
        "filter": "to",  # 只看 incoming
        "token": CTF_CONTRACT,
    }
    results = []
    page_count = 0
    next_page_params = None

    while True:
        if next_page_params:
            p = {**params, **next_page_params}
        else:
            p = params

        try:
            print(f"    頁面 {page_count + 1}，params: {p}")
            resp = requests.get(url, params=p, timeout=60)
            data = resp.json()
        except Exception as e:
            print(f"    錯誤: {e}")
            break

        items = data.get("items", [])
        results.extend(items)
        print(f"    取得 {len(items)} 筆（累計 {len(results)}）")

        next_page_params = data.get("next_page_params")
        if not next_page_params or not items:
            break
        page_count += 1
        if page_count > 20:  # 安全上限
            break

    return results


def fetch_polygonscan_v2_erc1155(address):
    """Polygonscan V2 API"""
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 137,
        "module": "account",
        "action": "token1155tx",
        "address": address,
        "startblock": 79887801,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": "YourApiKeyToken",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        print(f"    Polygonscan V2 狀態: {data.get('status')} / {data.get('message')}")
        result = data.get("result", [])
        if isinstance(result, list):
            return result
        else:
            print(f"    回應內容: {str(result)[:300]}")
            return []
    except Exception as e:
        print(f"    錯誤: {e}")
        return []


print("=" * 60)

for name, addr in ADDRESSES.items():
    print(f"\n【{name}】{addr}")

    # 方法 A：Blockscout v2
    print("\n[A] Blockscout v2 - incoming ERC-1155 transfers:")
    transfers_in = fetch_blockscout_v2_token_transfers(addr)
    print(f"    共 {len(transfers_in)} 筆 incoming transfer")

    # 過濾 KMT 代幣
    kmt_in = []
    for t in transfers_in:
        for token in (
            t.get("total", [])
            if isinstance(t.get("total"), list)
            else [t.get("total", {})]
        ):
            if isinstance(token, dict) and token.get("token_id") in [
                KMT_YES_TOKEN_ID,
                KMT_NO_TOKEN_ID,
            ]:
                kmt_in.append((t, token))

    if kmt_in:
        print(f"    找到 KMT 代幣 incoming transfer {len(kmt_in)} 筆：")
        for t, token in kmt_in:
            tk_name = "Yes" if token.get("token_id") == KMT_YES_TOKEN_ID else "No"
            print(
                f"      KMT-{tk_name}  數量:{token.get('value', ''):>12}  from:{t.get('from', {}).get('hash', '')[:20]}  hash:{t.get('transaction_hash', '')[:20]}..."
            )
    else:
        # debug: 顯示前3筆的 token_id
        for t in transfers_in[:3]:
            total = t.get("total", {})
            if isinstance(total, dict):
                print(f"      token_id={str(total.get('token_id', ''))[:40]}")
            elif isinstance(total, list):
                for tk in total[:2]:
                    print(f"      token_id={str(tk.get('token_id', ''))[:40]}")

    # 方法 B：Polygonscan v2
    print("\n[B] Polygonscan V2 ERC-1155 transfers:")
    transfers_ps = fetch_polygonscan_v2_erc1155(addr)
    print(f"    共 {len(transfers_ps)} 筆")
    kmt_ps = [
        t
        for t in transfers_ps
        if isinstance(t, dict)
        and t.get("tokenID") in [KMT_YES_TOKEN_ID, KMT_NO_TOKEN_ID]
    ]
    if kmt_ps:
        print(f"    KMT 代幣 {len(kmt_ps)} 筆：")
        for t in kmt_ps:
            direction = "IN" if t.get("to", "").lower() == addr.lower() else "OUT"
            print(
                f"      {direction}  tokenID={t.get('tokenID', '')} value={t.get('tokenValue', '')} from={t.get('from', '')[:20]}"
            )
    elif transfers_ps:
        print(f"    未找到 KMT（前3筆 tokenID）：")
        for t in transfers_ps[:3]:
            print(f"      {t.get('tokenID', '')}")

print("\n完成。")
