import requests, time
from datetime import datetime, timezone

MARKETS = {
    "KMT": "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "DPP": "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016",
    "TPP": "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94",
}


def ts(unix):
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


for party, cid in MARKETS.items():
    resp = requests.get(
        f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset=0",
        timeout=30,
    ).json()
    # 找最早的5筆
    sorted_trades = sorted(resp, key=lambda x: x.get("timestamp", 0))
    print(f"\n{party} 最早5筆：")
    for t in sorted_trades[:5]:
        unix = t.get("timestamp", 0)
        name = t.get("name") or t.get("pseudonym") or "(no name)"
        print(
            f"  {ts(unix)}  {t.get('side'):<5} {t.get('outcome'):<4} ${round(t.get('size', 0) * t.get('price', 0), 2):<8}  {name}"
        )
    time.sleep(0.3)
