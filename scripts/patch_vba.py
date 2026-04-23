"""
patch_vba.py
修補 build_complete_excel.py 中的 VBA 程式碼：
1. 把 Chr(26597) & Chr(35770) 改成 ThisWorkbook.Sheets(8)
2. 把 loop 內的 Dim 移到 Sub 頂部
3. 注入 Worksheet_Change 事件的方式也一併修正
"""

path = r"E:\polymarket選舉賭博\scripts\build_complete_excel.py"
content = open(path, encoding="utf-8").read()

# 修正 wsQ 的取得方式
old = '    Set wsQ = ThisWorkbook.Sheets(Chr(26597) & Chr(35770))  \' "查詢"'
new = "    Set wsQ = ThisWorkbook.Sheets(8)  '  查詢分頁（第8個）"
assert old in content, f"找不到：{repr(old)}"
content = content.replace(old, new, 1)

# 把 loop 內的 Dim 宣告移出（加到頂部 Dim 列表後）
old2 = (
    "            ' 累計統計\n"
    "            Dim direction As String\n"
    "            direction = CStr(wsData.Cells(i, 3).Value)\n"
    "            Dim shares As Double, usdVal As Double\n"
    "            shares = CDbl(wsData.Cells(i, 5).Value)\n"
    "            usdVal = CDbl(wsData.Cells(i, 7).Value)"
)
new2 = (
    "            direction = CStr(wsData.Cells(i, 3).Value)\n"
    "            shares    = CDbl(wsData.Cells(i, 5).Value)\n"
    "            usdVal    = CDbl(wsData.Cells(i, 7).Value)"
)
assert old2 in content, "找不到 loop Dim 區塊"
content = content.replace(old2, new2, 1)

# 在 Dim matchCount 後面加入 direction/shares/usdVal 的宣告
old3 = "    Dim matchCount As Long\n    \n    Set wsData"
new3 = "    Dim matchCount As Long\n    Dim direction As String\n    Dim shares As Double, usdVal As Double\n    \n    Set wsData"
assert old3 in content, "找不到 Dim matchCount 位置"
content = content.replace(old3, new3, 1)

# 清空舊結果也修一下（改成明確的 Range）
old4 = '    wsQ.Rows("10:" & wsQ.Rows.Count).ClearContents\n    wsQ.Rows("10:" & wsQ.Rows.Count).Interior.ColorIndex = xlNone'
new4 = '    wsQ.Range("A10:J" & wsQ.Rows.Count).ClearContents\n    wsQ.Range("A10:J" & wsQ.Rows.Count).Interior.ColorIndex = xlNone'
assert old4 in content, "找不到 ClearContents 區塊"
content = content.replace(old4, new4, 1)

open(path, "w", encoding="utf-8").write(content)
print("patch 完成")
