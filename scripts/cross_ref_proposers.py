"""
把已知的 UMA proposePrice 提交者地址，
丟進 Polymarket trades API 查有無交易記錄
"""

import requests, time

# 從 Blockscout 抓到的 proposePrice 提交者（近期，非bot重複的）
PROPOSERS = [
    ("0x52764DD44Eb51b0D21cD08E5497035f256eA7754", "最活躍/用UmaCtfAdapter"),
    ("0x6e3b09f43F723EF34702E6cf252A1611677150Ff", "自己當requester"),
    ("0xbfF43458d79aE37E87F2c9973DbcA9569706E456", "另一adapter"),
    ("0x129dd4F3BBE4b9584512453179264582De944FF0", "多次提案"),
    ("0xC33780D8841Dd80fE3dE83BFf881218372c3d42C", "批次bot"),
    ("0x9c1F9B97cd995A9c0cF0Ffe20F4d2f5e9C830c09", "大量同時提案"),
    ("0x56822f28672D4d6d4771Cc9e60bABb61773A826c", "定期提案"),
    ("0xDc0f07E80113a4b4205d623E1718Bc93490BbA1F", "散發提案"),
    ("0x25AC76d412560483E17cf1C24864b99F045B159c", "連續20筆"),
    ("0xbe2ebda7253a34BD38ebb17a86E97873C2294f56", ""),
    ("0x96719837E8d146b1D695Bd4aFc4BD468C2ab4Efd", ""),
    ("0x7b46E27Cfa3A6A0EEEb4D1DEE25491b8cfaf27Ae", ""),
    ("0x6D1fadCBa711aA3cA472EFd5bB21eB89F8A864C2", ""),
    ("0x0DB5Aea9F41Ce8398104e9d4694cfb18f146C493", ""),
    ("0xca249BE2E25E0889866E31DDbc5A635B69D99649", ""),
    ("0x8DfE4dCB552A47C190d37C3F91111139D1Fa6Db9", ""),
    ("0xc5aE9335d2efcA544dD64809D290b11B8D1C13C7", ""),
    ("0xe0AB8c43E72583cEF977b6BaB4933d99072a9B2f", ""),
    ("0x5104cE033200103691eDB20e56a25F6851379355", ""),
    ("0xDFabAc56D5A0B2dD4d5DA90528E791d42f2A83f4", ""),
    ("0x807568A87002f307d0880421e3b9fC8717AF3611", ""),
    ("0xEf3990A7c8fA92D84DcE0E7816CA3410820c1D36", ""),
    ("0x6B868D62Ff951DE97085E564F431CB682De3087B", ""),
    ("0x7F56658341f1C660D9C93B01a6B087e39e84d456", ""),
    ("0x2597C36CE477d6E28E81027be04Ca41cE1B7442b", ""),
    ("0x9188418d67018D2dEA9Beb2f81a95B31BAd3fBb5", ""),
    ("0xd437bAe9A9380D5b03b7A0C9E7322b3Ce96b56bd", ""),
    ("0x4aBADbe16A0691041122aC4f44d178a1960d8046", ""),
    ("0x8967e05470f620f60523DA10Cd15C03D685BA3D5", ""),
    ("0xcf12F5b99605CB299Fb11d5EfF4fB304De008d02", ""),
    ("0xe1555eF2B17bAcb6bA8394FbB4b18fb509dDE0f3", ""),
    ("0xAAbb9dA34f07e5ACB1941C38997d45240C27f22a", ""),
    ("0x8FD5333F071dceC98CF937D37d79367932161058", ""),
    ("0xAcE04Ac853C6E4c38E43D3185C6639CEb983903F", ""),
    ("0x4787a7f8432cb1EECe2f4D21427F330D91fd0C43", ""),
    ("0x490D780566F14Ba4d851C4671dc2d96442d63B66", ""),
    ("0xce9A8f3b04dED54414992a8f7bb24571c4f63B67", ""),
    ("0x58675D3AA3B1aFDc7705A97aD7A9C86088373AcC", ""),
    ("0xcccdEA09445F16D5Ca11CE090AEfA972001aA0F2", ""),
    ("0x27B42CE49B7D7996fbed257e17D448e0b28CB02D", ""),
    ("0xE18f5324885B4D924d400570950F82Bb25eB8C0E", ""),
    ("0x7b107A2d396D2947B125a9BCA95f5ACe30e2618E", ""),
    ("0x4ADe37f58C505aCd00528a062615E26d67c423b3", ""),
    ("0x5104cE033200103691eDB20e56a25F6851379355", ""),
    ("0x0215598391674d05C6fE0A1e8FD646b2a1FF4B66", ""),
    ("0x12532f45F74CDd6c5b014d0D6B7C873D5095709A", ""),
    ("0xD0Fc984EF483D75D5fad895EF4aBc3665e09914B", ""),
    ("0x771551CcEF6eC13af2D39391b1d27768c818Fa8b", ""),
]

print(f"{'地址':<44} {'Polymarket交易筆數':<20} {'暱稱/名稱':<20} {'備註'}")
print("-" * 100)

hits = []
for addr, note in PROPOSERS:
    try:
        url = f"https://data-api.polymarket.com/trades?maker={addr}&limit=10"
        resp = requests.get(url, timeout=10).json()
        count = len(resp) if isinstance(resp, list) else 0
        name = ""
        if count > 0:
            name = resp[0].get("name") or resp[0].get("pseudonym") or ""
            hits.append((addr, count, name, note))
            print(f"*** {addr}  {count:<20} {name:<20} {note}")
        else:
            # 也試試 proxyWallet
            url2 = f"https://data-api.polymarket.com/trades?proxyWallet={addr}&limit=10"
            resp2 = requests.get(url2, timeout=10).json()
            count2 = len(resp2) if isinstance(resp2, list) else 0
            if count2 > 0:
                name = resp2[0].get("name") or resp2[0].get("pseudonym") or ""
                hits.append((addr, count2, name, note + "(proxy)"))
                print(f"*** {addr}  {count2:<20} {name:<20} {note}(proxy)")
            else:
                print(f"    {addr}  0                    -                    {note}")
    except Exception as e:
        print(f"ERR {addr}: {e}")
    time.sleep(0.15)

print(f"\n==== 有 Polymarket 交易記錄的 proposePrice 提交者：{len(hits)} 人 ====")
for addr, count, name, note in hits:
    print(f"  {addr}  {count} 筆  暱稱:{name}  {note}")
