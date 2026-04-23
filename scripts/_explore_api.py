import requests, json, time

with open("E:\\polymarket選舉賭博\\missing_onchain_txs.json", "r") as f:
    missing = json.load(f)

samples = [tx for tx in missing if tx["side"] in ("BUY", "SELL") and tx["amount"] > 0][
    :5
]

for tx in samples:
    tx_hash = tx["tx_hash"]
    print(f"\n=== {tx_hash[:20]} {tx['parties']} {tx['side']} {tx['amount']} ===")
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}/token-transfers",
        timeout=20,
    )
    trs = r.json().get("items", []) if r.status_code == 200 else []
    print(f"  tx token-transfers: {len(trs)}")
    for tr in trs:
        sym = tr.get("token", {}).get("symbol") or "?"
        val = tr.get("total", {}).get("value", 0)
        dec = tr.get("total", {}).get("decimals") or "?"
        frm = tr.get("from", {}).get("hash", "")[:16]
        to_ = tr.get("to", {}).get("hash", "")[:16]
        typ = tr.get("type", "")
        print(f"    {typ:<22} sym={sym:<8} from={frm} to={to_} val={val} dec={dec}")
    time.sleep(0.4)
