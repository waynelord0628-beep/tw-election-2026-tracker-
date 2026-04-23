import urllib.request
import json
import urllib.error

# Brute force entity_entity_type values for GET
event_id = "96786"
types_to_try = [
    "event",
    "market",
    "prediction",
    "group",
    "neg_risk",
    "neg_risk_event",
    "election",
    "negrisk",
    "negRisk",
    "NegRisk",
    "prediction_market_group",
    "market_group",
    "marketGroup",
    "market_event",
    "marketEvent",
    "poly_market",
    "polymarket",
    "bet",
    "prediction_event",
]

for t in types_to_try:
    url = f"https://gamma-api.polymarket.com/comments?parent_entity_id={event_id}&entity_entity_type={t}&limit=5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            print(f"SUCCESS t={t}: {data}")
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        msg = json.loads(body).get("error", body) if body.startswith("{") else body[:50]
        print(f"t={t}: {msg}")
