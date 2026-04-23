"""
用 Blockscout v2 查詢 KMT-Yes token 的所有 transfers
直接從 token instance 角度查，找到 ChiangWan-an 的代幣來源
"""

import requests
import time

KMT_YES_TOKEN_ID = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
KMT_NO_TOKEN_ID = (
    "4696955573632845407532815267539406678302911508204032661527405293140196109387"
)
CTF_CONTRACT = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

CHIANGWAN_ADDR = "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24"


def fetch_token_instance_transfers(
    token_address, token_id, target_address=None, max_pages=200
):
    """查詢特定 token ID 的所有 transfers，可選過濾目標地址"""
    url = f"https://polygon.blockscout.com/api/v2/tokens/{token_address}/instances/{token_id}/transfers"

    all_transfers = []
    page_count = 0
    next_page_params = None

    while page_count < max_pages:
        params = {}
        if next_page_params:
            params.update(next_page_params)

        try:
            resp = requests.get(url, params=params, timeout=60)
            data = resp.json()
        except Exception as e:
            print(f"  第{page_count + 1}頁錯誤: {e}，等待後重試...")
            time.sleep(3)
            continue

        items = data.get("items", [])
        if not items:
            break

        # 過濾目標地址
        if target_address:
            matched = [
                t
                for t in items
                if (
                    isinstance(t.get("to"), dict)
                    and t["to"].get("hash", "").lower() == target_address.lower()
                )
                or (
                    isinstance(t.get("from"), dict)
                    and t["from"].get("hash", "").lower() == target_address.lower()
                )
            ]
            all_transfers.extend(matched)
        else:
            all_transfers.extend(items)

        page_count += 1
        if page_count % 20 == 0:
            last_block = items[-1].get("block_number", "?")
            print(
                f"  已查 {page_count} 頁，block={last_block}，找到目標:{len(all_transfers)}"
            )

        next_page_params = data.get("next_page_params")
        if not next_page_params:
            last_block = items[-1].get("block_number", "?") if items else "?"
            print(f"  無更多頁面，結束（block={last_block}，共 {page_count} 頁）")
            break

        time.sleep(0.2)

    return all_transfers


print("=" * 60)
print("查詢 KMT-Yes token 的所有 transfers（找 ChiangWan-an）")
print("=" * 60)

print(f"\n查詢 token: {KMT_YES_TOKEN_ID[:30]}...")
print(f"目標地址: {CHIANGWAN_ADDR}")
print()

transfers = fetch_token_instance_transfers(
    CTF_CONTRACT, KMT_YES_TOKEN_ID, target_address=CHIANGWAN_ADDR
)

if transfers:
    print(f"\n找到 {len(transfers)} 筆相關 transfer：")
    for t in transfers:
        from_addr = t.get("from", {})
        to_addr = t.get("to", {})
        if isinstance(from_addr, dict):
            from_addr = from_addr.get("hash", "")
        if isinstance(to_addr, dict):
            to_addr = to_addr.get("hash", "")

        total = t.get("total", {})
        value = total.get("value", "?") if isinstance(total, dict) else "?"

        direction = "IN " if to_addr.lower() == CHIANGWAN_ADDR.lower() else "OUT"
        print(
            f"  {direction}  block={t.get('block_number')}  {t.get('timestamp', '')[:19]}"
        )
        print(f"       from={from_addr}")
        print(f"       to  ={to_addr}")
        print(f"       value={value}")
        print(f"       hash={t.get('transaction_hash', '')[:20]}...")
        print()
else:
    print("未找到 ChiangWan-an 相關的 KMT-Yes transfer")

# 也查 KMT-No（用於 split 確認）
print("\n" + "=" * 60)
print("同時查 KMT-No token 是否有 ChiangWan-an 的 transfer")
print("=" * 60)
transfers_no = fetch_token_instance_transfers(
    CTF_CONTRACT, KMT_NO_TOKEN_ID, target_address=CHIANGWAN_ADDR
)
if transfers_no:
    print(f"\n找到 {len(transfers_no)} 筆相關 KMT-No transfer")
    for t in transfers_no:
        from_addr = t.get("from", {})
        to_addr = t.get("to", {})
        if isinstance(from_addr, dict):
            from_addr = from_addr.get("hash", "")
        if isinstance(to_addr, dict):
            to_addr = to_addr.get("hash", "")
        total = t.get("total", {})
        value = total.get("value", "?") if isinstance(total, dict) else "?"
        direction = "IN " if to_addr.lower() == CHIANGWAN_ADDR.lower() else "OUT"
        print(
            f"  {direction}  block={t.get('block_number')}  {t.get('timestamp', '')[:19]}  value={value}"
        )
else:
    print("未找到 ChiangWan-an 相關的 KMT-No transfer")
