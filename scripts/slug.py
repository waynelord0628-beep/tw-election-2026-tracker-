target = "0x91430CaD2d3975766499717fA0D66A78D814E5c5"

results = []

for event in data:
    for m in event.get("markets", []):
        if m.get("submitted_by") == target:
            results.append({
                "event": event["title"],
                "market": m["question"]
            })

for r in results:
    print(r)