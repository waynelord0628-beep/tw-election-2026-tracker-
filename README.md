# 2026 台灣地方選舉 · Polymarket 即時監控

[![Live Site](https://img.shields.io/badge/Live-GitHub%20Pages-2ea44f?style=flat-square)](https://waynelord0628-beep.github.io/tw-election-2026-tracker-/)
[![Refresh](https://img.shields.io/badge/Refresh-30s-blue?style=flat-square)]()
[![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20SQLite%20%2B%20JS-orange?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)]()

> 全自動追蹤 Polymarket「Which party will win the most head of local government elections in the 2026 Taiwan local elections?」三大政黨（國民黨 / 民進黨 / 民眾黨）Yes / No 共六個結算 token 的鏈上成交，毫秒級寫盤、30 秒推播、零成本部署。

**公開網站** → <https://waynelord0628-beep.github.io/tw-election-2026-tracker-/>

---

## 為什麼做這個

Polymarket 大盤頁雖即時，但：

- 無法**單獨追台灣選舉**（被埋在數百個市場裡）
- 無法**長期累積歷史**（前端只給最近幾百筆）
- 無法**繁中化、無法依錢包過濾、無法 PnL 分析**

本專案把六個 token 的每一筆成交都收進 SQLite，前端做純前端分頁、即時動態、政黨比例、未具名錢包優雅降級顯示。

---

## 架構一覽

```
┌────────────────────┐    poll 30s    ┌──────────────────────┐
│ Polymarket data-api│ ─────────────▶│  monitor.py (VPS)     │
│  /trades           │ takerOnly=true│  ├─ dedup by tx+token │
│  /profile          │                │  ├─ name backfill x5n │
└────────────────────┘                │  └─ rename sync       │
                                      └──────────┬────────────┘
                                                 │ commit + push
                                                 ▼
                              ┌──────────────────────────────────┐
                              │ GitHub repo (docs/data.json)     │
                              └──────────┬───────────────────────┘
                                         │ static hosting
                                         ▼
                              ┌──────────────────────────────────┐
                              │ GitHub Pages (Vanilla JS 前端)   │
                              │  ├─ 即時動態流                  │
                              │  ├─ 分頁交易表                  │
                              │  └─ 政黨比例 / 篩選 / 搜尋     │
                              └──────────────────────────────────┘
```

---

## 資料來源與正確性

| 來源 | 用途 | 備註 |
|---|---|---|
| `data-api.polymarket.com/trades?takerOnly=true` | 主要成交流 | 每筆鏈上 match 只回 taker 一行，避免雙計 |
| `data-api.polymarket.com/profile` | 名稱補抓 | 部分裸錢包回 404，正常現象 |
| `data-api.polymarket.com/positions` | 預留持倉同步 | 尚未啟用 |

**已知限制**：少數從未登入過 Polymarket UI 的錢包，data-api 連系統擬名 (`pseudonym`) 都是空字串，前端會以短地址 `0xabcd…1234` 呈現並 hover 顯示完整地址。

---

## 專案結構

```
.
├── docs/                      ← GitHub Pages 根目錄
│   ├── index.html             前端入口（CSS/JS 帶版號避快取）
│   ├── app.js                 動態 + 分頁 + 篩選邏輯
│   ├── style.css              樣式（深色主題、政黨配色）
│   └── data.json              ← monitor 自動 push 的資料快照
│
├── scripts/
│   ├── monitor.py             主監控（核心）
│   ├── build_complete_excel.py
│   └── fetch_*.py             一次性歷史抓取工具
│
├── monitor.db                 SQLite（trades 表）
├── wallet_names.json          錢包→名稱快取（持久化）
└── README.md
```

---

## 快速開始

### 本機執行

```bash
git clone https://github.com/waynelord0628-beep/tw-election-2026-tracker-.git
cd tw-election-2026-tracker-
pip install requests
python scripts/monitor.py 30          # 30 秒輪詢
```

第一次啟動會：

1. 從 data-api 完整 backfill 六個 token 的歷史成交
2. 建立 SQLite + `docs/data.json`
3. 之後每輪只抓增量、毫秒級寫入

### VPS 常駐部署

```bash
# /etc/systemd/system/tracker.service
[Unit]
Description=Polymarket TW Election Tracker
After=network.target

[Service]
WorkingDirectory=/opt/tracker
ExecStart=/opt/tracker/.venv/bin/python /opt/tracker/scripts/monitor.py 30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now tracker
journalctl -u tracker -f
```

---

## 核心機制

### 1. takerOnly 去重
鏈上每筆 match 都包含 maker + taker 兩端，過去用 Blockscout `/transfers` 會把兩端都當交易紀錄 → **筆數膨脹一倍**。改用 `data-api?takerOnly=true` 後每筆 match 只回一行。

### 2. 名稱三層解析
```
新交易 ─▶ 用 data-api 的 name (用戶自訂) 寫入
         └─ 為空則用 pseudonym (系統擬名)
            └─ 都為空則進 backfill 佇列

每 5 輪輪詢 ─▶ 掃描 name='' 的錢包
            └─ 呼叫 /profile?address= 補抓
               └─ 找到 → UPDATE 該錢包所有歷史紀錄

改名同步 ─▶ 每次抓到的 name ≠ 快取
         └─ 立即更新該錢包全部歷史紀錄
```

### 3. 推播節流
`export_web_data` 每次更新 `docs/data.json`，但 `git commit + push` 限制每 2 分鐘最多一次，避免無謂提交。

---

## 開發備忘

- **前端改完務必升 `?v=`**：GitHub Pages 邊緣快取很兇
- **VPS 跑 monitor 後本機別跑**：兩邊同時 push 會打架
- **PowerShell 改中文檔案會炸**：用編輯器或 `Edit` 工具，不要走 `Get-Content`

---

## 路線圖

- [ ] 持倉視角（每個地址當前 PnL）
- [ ] 大戶榜（依累計成交額）
- [ ] 隱藏未具名錢包的開關
- [ ] WebSocket 改即時推送（取代 polling）
- [ ] 多市場：總統、立委大選

---

## 授權

MIT。資料來源歸 Polymarket Inc. 所有，本專案僅做公開 API 的彙整呈現。
