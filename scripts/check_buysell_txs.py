"""
check_buysell_txs.py
確認 missing_onchain_txs.json 中 BUY/SELL 類型是否為方向性交易或 split/merge
"""

import requests, json, time

missing = json.load(open("E:/polymarket選舉賭博/missing_onchain_txs.json"))
buysell = [x for x in missing if x["side"] in ("BUY", "SELL")]
print(f"BUY/SELL entries: {len(buysell)}")

TOKEN_MAP = {
    "85632914518786177256583369552125280053108667306405854845853340618248288927460": (
        "KMT",
        "Yes",
    ),
    "4696955573632845407532815267539406678302911508204032661527405293140196109387": (
        "KMT",
        "No",
    ),
    "13628189982642424912108657221169198338993179248246381972030640500448717195916": (
        "DPP",
        "Yes",
    ),
    "91004506882941445266754771479824617369805789899332711132070603219216406556613": (
        "DPP",
        "No",
    ),
    "14999500579901383072635205035227864886528710236540822730141548371372688859422": (
        "TPP",
        "Yes",
    ),
    "16222840603445450947154718759167300491302153317593739623696847197718420087623": (
        "TPP",
        "No",
    ),
}

CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"

real_trades = []
splits_merges = []

for entry in buysell[:20]:  # check first 20
    tx = entry["tx_hash"]
    r = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx}/token-transfers",
        timeout=20,
    )
    items = r.json().get("items", []) if r.status_code == 200 else []

    # Group ERC-1155 by token_id and track user interactions
    usdc_to_user = 0
    usdc_from_user = 0
    erc1155_to_user = {}  # token_id -> amount
    erc1155_from_user = {}  # token_id -> amount

    user_addrs_lower = [a.lower() for a in entry["user_addrs"]]
    # Remove known contracts from user_addrs
    known = {
        "0xd91e80cf2e7be2e162c6513ced06f1dd0da35296",
        "0x4d97dcd97ec945f40cf65f87097ace5ea0476045",
        "0xc5d563a36ae78145c45a50134d48a1215220f80a",
        "0x0000000000000000000000000000000000000000",
        "0x3a3bd7bb9528e1ac2bc9d5ee5ec46c4b5ceaede1",
    }
    real_user = next((a for a in user_addrs_lower if a not in known), None)

    for item in items:
        sym = item.get("token", {}).get("symbol") or ""
        frm = item.get("from", {}).get("hash", "").lower()
        to_ = item.get("to", {}).get("hash", "").lower()
        val_raw = item.get("total", {}).get("value", 0)
        try:
            val = int(val_raw) / 1e6
        except:
            val = 0

        # USDC
        if "USDC" in sym.upper():
            if real_user and to_ == real_user:
                usdc_to_user += val
            elif real_user and frm == real_user:
                usdc_from_user += val

        # ERC-1155 (sym=?)
        if sym == "?" or sym == "":
            token_addr = item.get("token", {}).get("address", "").lower()
            # Try to get token_id
            token_id = str(item.get("token", {}).get("id") or "")
            if token_id in TOKEN_MAP:
                party, outcome = TOKEN_MAP[token_id]
                key = f"{party}-{outcome}"
                if real_user and to_ == real_user:
                    erc1155_to_user[key] = erc1155_to_user.get(key, 0) + val
                elif real_user and frm == real_user:
                    erc1155_from_user[key] = erc1155_from_user.get(key, 0) + val

    # Determine type
    is_merge_or_split = False
    if usdc_to_user > 0 and usdc_from_user == 0:
        # User received USDC - either selling or redeeming
        # If equal Yes+No amounts from user → merge
        yes_out = sum(v for k, v in erc1155_from_user.items() if "Yes" in k)
        no_out = sum(v for k, v in erc1155_from_user.items() if "No" in k)
        if yes_out > 0 and no_out > 0 and abs(yes_out - no_out) < 0.01:
            is_merge_or_split = True

    status = "MERGE/SPLIT" if is_merge_or_split else "POSSIBLE_TRADE"

    print(
        f"{tx[:24]} {entry['side']:4} {entry['parties']:12} USDC_in={usdc_from_user:.2f} USDC_out={usdc_to_user:.2f}"
    )
    print(f"  erc1155_to_user={erc1155_to_user} from_user={erc1155_from_user}")
    print(f"  STATUS: {status}")
    if not is_merge_or_split and (usdc_to_user > 0 or usdc_from_user > 0):
        real_trades.append(tx)
    else:
        splits_merges.append(tx)
    time.sleep(0.3)

print(f"\nReal trades: {len(real_trades)}")
print(f"Splits/Merges: {len(splits_merges)}")
