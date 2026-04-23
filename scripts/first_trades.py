import requests
from datetime import datetime, timezone

KMT = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
DPP = "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016"
TPP = "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94"

all_trades = []
for mname, cid in [("KMT", KMT), ("DPP", DPP), ("TPP", TPP)]:
    r = requests.get(
        "https://data-api.polymarket.com/trades",
        params={"market": cid, "limit": 500, "offset": 0},
        timeout=20,
    )
    trades = r.json()
    for t in trades:
        t["_market"] = mname
    all_trades.extend(trades)

all_trades.sort(key=lambda t: int(t.get("timestamp", 0)))
print("最早 10 筆：")
for t in all_trades[:10]:
    ts = datetime.fromtimestamp(int(t["timestamp"]), tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    name = t.get("name") or t.get("pseudonym") or t.get("proxyWallet", "")[:12]
    print(
        f"  {ts}  {t['_market']}  {t.get('side')}  {t.get('outcome')}  {t.get('size')} @ ${t.get('price')}  [{name}]"
    )
