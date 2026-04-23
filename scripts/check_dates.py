import requests

for mid in [814612, 814613, 814614]:
    resp = requests.get(f"https://gamma-api.polymarket.com/markets/{mid}", timeout=15)
    d = resp.json()
    created = str(d.get("createdAt", "?"))[:19]
    start = str(d.get("startDate", "?"))[:19]
    end = str(d.get("endDate", "?"))[:19]
    q = d.get("question", "")[:60]
    print(f"ID {mid}")
    print(f"  question : {q}")
    print(f"  createdAt: {created}")
    print(f"  startDate: {start}")
    print(f"  endDate  : {end}")
    print()
