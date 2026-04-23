import requests

KMT_COND = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
CHIANGWAN = "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24"
KUOMINTANG = "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa"

trades = []
offset = 0
while True:
    r = requests.get(
        "https://data-api.polymarket.com/trades",
        params={"market": KMT_COND, "limit": 500, "offset": offset},
        timeout=30,
    )
    data = r.json()
    if not data:
        break
    trades.extend(data)
    if len(data) < 500:
        break
    offset += 500

print(f"KMT total trades: {len(trades)}")
for t in trades:
    pw = t.get("proxyWallet", "").lower()
    if pw in [CHIANGWAN.lower(), KUOMINTANG.lower()]:
        name = "ChiangWan-an" if pw == CHIANGWAN.lower() else "Kuomintang"
        ts = str(t.get("timestamp", ""))[:19]
        side = t.get("side", "")
        outcome = t.get("outcome", "")
        size = t.get("size", "")
        price = t.get("price", "")
        txhash = t.get("transactionHash", "")
        print(
            f"{name}  {ts}  {side}  {outcome}  {size} shares @ {price}  hash={txhash}"
        )
