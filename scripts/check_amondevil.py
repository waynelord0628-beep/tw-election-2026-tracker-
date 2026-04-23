import requests
from datetime import datetime, timezone, timedelta

KMT = "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b"
DPP = "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016"
TPP = "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94"

all_trades = []
for mname, cid in [("KMT", KMT), ("DPP", DPP), ("TPP", TPP)]:
    r = requests.get(
        "https://data-api.polymarket.com/trades",
        params={"market": cid, "limit": 500},
        timeout=20,
    )
    for t in r.json():
        t["_market"] = mname
        all_trades.append(t)

TZ8 = timezone(timedelta(hours=8))

amondevil = [
    t
    for t in all_trades
    if (t.get("name") or t.get("pseudonym") or "").lower() == "amondevil"
]
print(f"amondevil 共 {len(amondevil)} 筆")
for t in sorted(amondevil, key=lambda x: int(x.get("timestamp", 0))):
    ts = datetime.fromtimestamp(int(t["timestamp"]), tz=TZ8).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    market = t["_market"]
    size = t.get("size")
    price = t.get("price")
    total = round(float(size) * float(price), 2)
    print(
        f"  {ts}  {market}  {t.get('side')}  {t.get('outcome')}  {size} shares @ ${price}  = ${total}"
    )

print()
if amondevil:
    print("proxyWallet:", amondevil[0].get("proxyWallet"))
    print("name:", amondevil[0].get("name"))
    print("pseudonym:", amondevil[0].get("pseudonym"))
    print("bio:", amondevil[0].get("bio"))
