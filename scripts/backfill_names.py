#!/usr/bin/env python3
"""
backfill_names.py - 回填 monitor.db 中 name 為空的記錄
從 Polymarket data-api 反查名稱，更新 SQLite + 名稱快取。
"""

import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor import (
    DB_PATH,
    fetch_polymarket_name,
    load_name_cache,
    save_name_cache,
    _name_cache,
    rebuild_excel,
    update_recent_excel,
)


def main():
    load_name_cache()
    conn = sqlite3.connect(DB_PATH)

    # 取出所有 name 為空的不重複 wallet
    rows = conn.execute(
        "SELECT DISTINCT wallet FROM trades WHERE name='' OR name IS NULL"
    ).fetchall()
    wallets = [r[0] for r in rows]
    print(f"待補錢包數：{len(wallets)}")

    fetched = 0
    found = 0
    for i, w in enumerate(wallets, 1):
        # 已快取的直接用
        if w in _name_cache and _name_cache[w]:
            name = _name_cache[w]
        elif w in _name_cache and _name_cache[w] == "":
            # 之前查過確認沒名字
            name = ""
        else:
            name = fetch_polymarket_name(w)
            _name_cache[w] = name
            fetched += 1
            time.sleep(0.15)  # 避免打太快
            if fetched % 20 == 0:
                save_name_cache()
                print(f"  [進度] 已查 {fetched}（命中 {found}）")

        if name:
            conn.execute(
                "UPDATE trades SET name=? WHERE wallet=? AND (name='' OR name IS NULL)",
                (name, w),
            )
            found += 1

    conn.commit()
    save_name_cache()

    # 統計
    total_updated = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE name!='' AND name IS NOT NULL"
    ).fetchone()[0]
    total_all = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    print(f"\n完成：共 {found} 個錢包補上名稱")
    print(f"DB 中已命名：{total_updated} / {total_all} 筆")

    # 重建 Excel
    print("\n重建 Excel...")
    n = rebuild_excel(conn, silent_if_locked=False)
    update_recent_excel(conn)
    print(f"Excel 已更新（{n} 筆）")

    conn.close()


if __name__ == "__main__":
    main()
