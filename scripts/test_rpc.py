import requests

rpcs = [
    "https://polygon.llamarpc.com",
    "https://polygon.drpc.org",
    "https://1rpc.io/matic",
    "https://polygon-mainnet.public.blastapi.io",
]

for rpc in rpcs:
    try:
        r = requests.post(
            rpc,
            json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
            timeout=10,
        )
        data = r.json()
        if "result" in data:
            print(f"OK: {rpc} -> block {int(data['result'], 16):,}")
        else:
            print(f"ERR: {rpc} -> {data}")
    except Exception as e:
        print(f"FAIL: {rpc} -> {e}")
