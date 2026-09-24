<!-- stub-marker: triage-synthesize -->
# 反切未命中分診合成

你是唯讀合成 agent：只能讀取 repo 檔案，不得修改任何檔案。

## 任務

下方是 `MANIFEST.tsv`（各 `miss-NN.tsv` 對應的 join.method 與未命中數）與各分支
診斷報告。請合併為一份總報告，供後續修復迭代（fanqie-loop）參考。

## 輸出格式（嚴格，四個標題缺一不可）

```markdown
## 假說
（跨桶合併後的系統性假說，按預期收益排序；每條註明涵蓋哪些 miss-NN 桶）

## 證據
（引用具體 miss-NN 檔名與其中的漢字／反切实例；只引用 MANIFEST 中存在的桶）

## 建議修改
（每條建議：預期提升的命中方向、對「平均候選」數的影響、涉及的函式；
 不得提議放寬 2×3 候選上限或修改 checks/測試/acceptance.yaml）

## 風險
（index parity、非 mc 欄位、register alias 邊界等）
```

## 禁止事項

- 不得修改任何檔案（唯讀）
- 不得輸出 TODO／TBD／PLACEHOLDER 等佔位文字
- 引用桶檔名必須是 MANIFEST 中存在的 `miss-NN`
