import urllib.request, json

addrs = {
    "0xd8dd45139269031b16a54717cabad4af6a3980d6",
    "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24",
    "0xfde3a53d58320a3db74dbe1092979c401e35719a",
    "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa",
}
markets = {
    "DPP": "0xea3b1d0099085f43a3098b3e1fbcbe62284ce1bda99384b3d46b82ff202ac016",
    "TPP": "0x68fc8d466ddc10a1ae37b52642f36b93e413cf98ba5fe3947c242a9a727b2e94",
}
for party, cid in markets.items():
    offset = 0
    matches = []
    total = 0
    while True:
        req = urllib.request.Request(
            f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset={offset}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        d = json.loads(urllib.request.urlopen(req, timeout=20).read())
        if not d:
            break
        total += len(d)
        matches += [t for t in d if t.get("proxyWallet", "").lower() in addrs]
        if len(d) < 500 or offset >= 3000:
            break
        offset += 500
    print(f"{party}: total_trades={total}, matches={len(matches)}")
    for m in matches:
        pw = m.get("proxyWallet", "")[:16]
        nm = m.get("name", "")
        sd = m.get("side", "")
        sz = m.get("size", "")
        print(f"  {pw} {nm} {sd} {sz}")
