import requests
from datetime import datetime, timezone

KMT_YES = (
    "85632914518786177256583369552125280053108667306405854845853340618248288927460"
)
KMT_NO = "4696955573632845407532815267539406678302911508204032661527405293140196109387"
CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
NEGATIX = "0xc5d563a36ae78145c45a50134d48a1215220f80a"  # NegRiskCtfExchange

CHIANGWAN = "0x0d5ee5c536ccd78d179487b3d7e43ae4304d5c24"
KUOMINTANG = "0x426227d4a9c4ad5a1aae7f2706238f2154b9abaa"


def ts_to_dt(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except:
        return str(ts)


def inspect_tx(tx_hash, label):
    print(f"\n{'=' * 60}")
    print(f"【{label}】{tx_hash}")

    resp = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}", timeout=30
    )
    data = resp.json()
    from_info = data.get("from", {})
    to_info = data.get("to", {})
    from_hash = from_info.get("hash", "") if isinstance(from_info, dict) else ""
    to_contract = to_info.get("hash", "") if isinstance(to_info, dict) else ""
    to_name = to_info.get("name", "") if isinstance(to_info, dict) else ""
    print(f"  方法: {data.get('method')}")
    print(f"  時間: {data.get('timestamp', '')[:19]}")
    print(f"  發起人: {from_hash}")
    print(f"  合約: {to_contract} ({to_name})")

    resp2 = requests.get(
        f"https://polygon.blockscout.com/api/v2/transactions/{tx_hash}/token-transfers",
        timeout=30,
    )
    data2 = resp2.json()
    items = data2.get("items", [])

    print(f"\n  Token transfers ({len(items)} 筆)：")
    for t in items:
        from_a = t.get("from", {})
        to_a = t.get("to", {})
        from_h = from_a.get("hash", "") if isinstance(from_a, dict) else ""
        to_h = to_a.get("hash", "") if isinstance(to_a, dict) else ""
        total = t.get("total", {})
        token_type = t.get("type", "")

        if isinstance(total, dict):
            token_id = total.get("token_id", "")
            value = total.get("value", "")
            # 辨識 token
            if token_id == KMT_YES:
                tok_name = "KMT-Yes"
            elif token_id == KMT_NO:
                tok_name = "KMT-No"
            elif token_id:
                tok_name = f"tokenId={token_id[:15]}..."
            else:
                # ERC-20 (USDC?)
                tok_info = t.get("token", {})
                tok_name = (
                    tok_info.get("symbol", "ERC-20")
                    if isinstance(tok_info, dict)
                    else "ERC-20"
                )
        else:
            token_id = ""
            value = ""
            tok_name = "?"

        # 標記 target addresses
        def label_addr(h):
            if h.lower() == CHIANGWAN.lower():
                return "ChiangWan-an"
            if h.lower() == KUOMINTANG.lower():
                return "Kuomintang"
            if h.lower() == NEGATIX.lower():
                return "NegRiskExchange"
            if h.lower() == CTF.lower():
                return "CTF-Contract"
            if h == "0x0000000000000000000000000000000000000000":
                return "BURN/MINT"
            return h[:12] + "..."

        print(f"    [{token_type}] {tok_name}  value={value}")
        print(f"      {label_addr(from_h)} → {label_addr(to_h)}")


# ChiangWan-an SELL 80 (2026-04-10)
inspect_tx(
    "0x789c588349aadb4724642ee165a25d4dd79231909a03d757cd2c7edb471fa63c",
    "ChiangWan-an SELL 80 @ 0.86 (2026-04-10)",
)

# ChiangWan-an SELL 20 (2026-02-07)
inspect_tx(
    "0xbaa910668e8413051767f452e0750debe9d7f03bd578681bbccbdbd3270398e0",
    "ChiangWan-an SELL 20 @ 0.87 (2026-02-07)",
)

# Kuomintang SELL 100 (2026-02-07) - from Polymarket trades API
inspect_tx(
    "0x3d3c6abf90de71efc9775134c58afaf6f55c8d18d6e1fdfc8aa03f1bb380ad1a",
    "Kuomintang SELL 100 @ 0.87 (2026-02-07)",
)

# Kuomintang's earlier BUY transfer (2025-12-26)
inspect_tx(
    "0x23345629edb3f8ca6555eff4f1c88cd35ae83ec686d047132792768506161bd4",
    "Kuomintang 收到 100 KMT-Yes (2025-12-26)",
)

print("\n完成。")
