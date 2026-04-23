# 2026 台灣地方選舉 Polymarket 監控

即時追蹤 Polymarket 上 2026 台灣地方選舉預測市場（KMT / DPP / TPP）的鏈上交易。

## 公開網站

https://waynelord0628-beep.github.io/tw-election-2026-tracker/

每 30 秒自動刷新；顯示最新交易者名稱、錢包、Hash、Shares、價格與金額。

## 結構

```
docs/                  GitHub Pages 網頁前端 + data.json
scripts/monitor.py     主監控腳本（10 秒輪詢 Blockscout）
scripts/build_complete_excel.py  歷史 Excel 重建
```

## 執行

```bash
python scripts/monitor.py        # 預設 10 秒輪詢
python scripts/monitor.py 30     # 30 秒輪詢
```

監控啟動後會：

1. 每輪查 6 個 token（KMT/DPP/TPP × Yes/No）的最新轉帳
2. 寫入本地 SQLite `monitor.db`
3. 更新 `監控_即時_最新動態.xlsx`
4. 匯出 `docs/data.json` 並自動 `git commit + push`（節流 2 分鐘）

## 資料來源

只用 Blockscout 公開 API（免 key），名稱來自 Polymarket data-api。
