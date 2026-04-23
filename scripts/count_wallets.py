import requests, time
from collections import defaultdict, Counter

MARKETS = {
    "KMT": "0xc0f076bc4d90a44df34a729277e9d1f294f0cb60d2c3b1b3800908b1e15b923b",
    "DPP": "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016",
    "TPP": "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94",
}

all_trades = []
for party, cid in MARKETS.items():
    offset = 0
    while True:
        r = requests.get(
            f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset={offset}",
            timeout=30,
        )
        batch = r.json()
        if not batch:
            break
        for t in batch:
            t["_party"] = party
        all_trades.extend(batch)
        offset += 500
        time.sleep(0.2)
        if len(batch) < 500:
            break

wallets = set(
    t.get("proxyWallet", "").lower() for t in all_trades if t.get("proxyWallet")
)
print("Trade count:", len(all_trades))
print("Unique wallets:", len(wallets))

by_party = defaultdict(set)
for t in all_trades:
    w = t.get("proxyWallet", "").lower()
    if w:
        by_party[t["_party"]].add(w)

for p in ["KMT", "DPP", "TPP"]:
    print(f"  {p}: {len(by_party[p])} unique wallets")

wallet_count = Counter(
    t.get("proxyWallet", "").lower() for t in all_trades if t.get("proxyWallet")
)
print()
print("Top 10 traders by trade count:")
for w, cnt in wallet_count.most_common(10):
    name = next(
        (
            t.get("name") or t.get("pseudonym") or ""
            for t in all_trades
            if t.get("proxyWallet", "").lower() == w
        ),
        "",
    )
    print(f"  {cnt:3}  {name or '(unnamed)'}  {w}")

# total USDC per wallet (top by volume)
wallet_usdc = defaultdict(float)
wallet_name = {}
for t in all_trades:
    w = t.get("proxyWallet", "").lower()
    if w:
        try:
            wallet_usdc[w] += float(t.get("size", 0)) * float(t.get("price", 0))
        except:
            pass
        nm = t.get("name") or t.get("pseudonym") or ""
        if nm:
            wallet_name[w] = nm

print()
print("Top 10 traders by USDC volume:")
for w, vol in sorted(wallet_usdc.items(), key=lambda x: -x[1])[:10]:
    name = wallet_name.get(w, "(unnamed)")
    print(f"  ${vol:10.2f}  {name}  {w}")
