"""
確認 Polymarket trades API 支援哪些查詢參數，
然後正確查詢 proposePrice 提交者是否有 Polymarket 帳號
"""

import requests, time, json

# 先確認幾個地址的實際情況
TEST_ADDRS = [
    "0x52764DD44Eb51b0D21cD08E5497035f256eA7754",
    "0x56822f28672D4d6d4771Cc9e60bABb61773A826c",
    "0x25AC76d412560483E17cf1C24864b99F045B159c",
]

print("=== 測試 API 參數 ===")
for addr in TEST_ADDRS:
    # 試不同 endpoint
    endpoints = [
        f"https://data-api.polymarket.com/trades?proxyWallet={addr}&limit=5",
        f"https://data-api.polymarket.com/trades?user={addr}&limit=5",
        f"https://data-api.polymarket.com/activity?proxyWallet={addr}&limit=5",
        f"https://data-api.polymarket.com/positions?user={addr}&limit=5",
        f"https://data-api.polymarket.com/profiles?address={addr}",
        f"https://data-api.polymarket.com/users?address={addr}",
        f"https://gamma-api.polymarket.com/users?address={addr}",
    ]
    print(f"\n{addr[:20]}...")
    for url in endpoints:
        try:
            r = requests.get(url, timeout=8)
            body = r.text[:120]
            # 判斷是否有實際資料（不是空陣列或null）
            if r.status_code == 200 and body not in ["[]", "null", "{}", ""]:
                data = (
                    r.json()
                    if r.headers.get("content-type", "").startswith("application/json")
                    else body
                )
                print(f"  OK [{r.status_code}] {url.split('polymarket.com')[1][:50]}")
                print(f"     -> {str(data)[:150]}")
            else:
                print(
                    f"  -- [{r.status_code}] {url.split('polymarket.com')[1][:50]} -> empty/null"
                )
        except Exception as e:
            print(f"  ERR {url.split('polymarket.com')[1][:40]}: {e}")
        time.sleep(0.1)
