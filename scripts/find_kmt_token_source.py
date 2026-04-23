"""
用 Blockscout v2 查詢 KMT Yes 代幣的 incoming transfers
持續翻頁直到到達 KMT 市場開始的區塊
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
KMT_START_BLOCK = 79887801  # KMT 市場開市區塊

ADDRESSES = {
    "ChiangWan-an": "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24",
    "Kuomintang": "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa",
}


def find_kmt_incoming_transfers(address):
    """翻頁查詢直到 block <= KMT_START_BLOCK，收集 KMT tokenId 的 transfer"""
    url = f"https://polygon.blockscout.com/api/v2/addresses/{address}/token-transfers"
    base_params = {
        "type": "ERC-1155",
        "filter": "to",
        "token": CTF_CONTRACT,
    }

    kmt_found = []
    page_count = 0
    next_page_params = None
    current_block = 99999999

    print(f"  開始翻頁查詢（目標：到達 block {KMT_START_BLOCK}）...")

    while current_block > KMT_START_BLOCK:
        params = {**base_params}
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
            print(f"  第{page_count + 1}頁無資料，結束")
            break

        # 從最後一筆取得目前 block
        last_item = items[-1]
        current_block = last_item.get("block_number", 0) or 0

        # 檢查此批次是否有 KMT token
        for t in items:
            total = t.get("total", {})
            token_id = None
            value = None
            if isinstance(total, dict):
                token_id = total.get("token_id")
                value = total.get("value")
            elif isinstance(total, list):
                for tk in total:
                    if isinstance(tk, dict):
                        token_id = tk.get("token_id")
                        value = tk.get("value")
                        break

            if token_id in [KMT_YES_TOKEN_ID, KMT_NO_TOKEN_ID]:
                kmt_found.append(
                    {
                        "block": t.get("block_number"),
                        "timestamp": t.get("timestamp"),
                        "hash": t.get("transaction_hash"),
                        "from": t.get("from", {}).get("hash", "")
                        if isinstance(t.get("from"), dict)
                        else str(t.get("from", "")),
                        "token": "Yes" if token_id == KMT_YES_TOKEN_ID else "No",
                        "value": value,
                    }
                )

        page_count += 1
        if page_count % 10 == 0:
            print(
                f"  已查 {page_count} 頁，目前 block={current_block}，KMT找到:{len(kmt_found)}"
            )

        next_page_params = data.get("next_page_params")
        if not next_page_params:
            print(f"  無更多頁面，結束（block={current_block}）")
            break

        # 小延遲避免過快
        time.sleep(0.2)

    print(f"  完成：共查 {page_count} 頁，到達 block={current_block}")
    return kmt_found


print("=" * 60)

for name, addr in ADDRESSES.items():
    print(f"\n【{name}】{addr}")
    results = find_kmt_incoming_transfers(addr)

    if results:
        print(f"\n  ✓ 找到 {len(results)} 筆 KMT 代幣 incoming transfer：")
        for r in results:
            print(f"    block={r['block']}  {r['timestamp']}")
            print(f"    KMT-{r['token']}  數量={r['value']}")
            print(f"    from={r['from']}")
            print(f"    hash={r['hash']}")
    else:
        print(f"\n  ✗ 未找到任何 KMT 代幣 incoming transfer")

print("\n完成。")
