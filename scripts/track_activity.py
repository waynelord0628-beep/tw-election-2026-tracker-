import requests
from datetime import datetime

SUBGRAPH = "https://api.thegraph.com/subgraphs/name/polymarket/polymarket-v3"

slug = "2026-taiwanese-local-elections-party-winner"

# ===== Step 1：抓 event =====
event = requests.get(
    f"https://gamma-api.polymarket.com/events/slug/{slug}"
).json()

# ===== Step 2：逐個 market 查第一筆 =====
for m in event["markets"]:
    condition_id = m["conditionId"]
    name = m["groupItemTitle"]

    query = f"""
    {{
      trades(
        first: 1,
        orderBy: timestamp,
        orderDirection: asc,
        where: {{
          conditionId: "{condition_id.lower()}"
        }}
      ) {{
        trader
        price
        amount
        timestamp
        txHash
      }}
    }}
    """

    res = requests.post(SUBGRAPH, json={"query": query})
    data = res.json()["data"]["trades"]

    if not data:
        print(f"{name} → 沒有交易")
        continue

    t = data[0]
    ts = int(t["timestamp"])
    time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    print("======")
    print("市場:", name)
    print("第一筆交易者:", t["trader"])
    print("時間:", time_str)
    print("價格:", t["price"])
    print("數量:", t["amount"])
    print("tx:", t["txHash"])