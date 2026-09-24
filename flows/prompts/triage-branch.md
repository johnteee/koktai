<!-- stub-marker: triage-branch -->
# 反切未命中分診（單一 join.method 桶）

你是唯讀診斷 agent：只能讀取 repo 檔案，不得修改任何檔案。

## 背景

koktai 的反切模擬音管線在 `a-tsioh_sandbox/build_unified_index.py`：

- `build_reading_profile`：由現有（漢字, 台羅）讀音建立反切上下字的 keypoint 表，
  排序為文讀／甘文優先 → 非白/語/俗/訓 → 全部讀音。
- `enrich_mc_with_reading_profile`：以反切上字聲母（上限 2 類）× 反切下字韻母
  （上限 3 型）＋推導聲調，合成 `mc[].sim_tl.syllables`。
- `derive_sim_tl`：中古聲母類 × 平水預期韻母 × 文讀調的規則候選。
- 驗收：`checks/koktai_checks.py hit-rate` 比對 `sim_tl` 候選與既有文讀
  （`taigi[].registers` 含「文」或 `attest` 含「甘文」）的 any-hit 命中率。

## 任務

下方給定一個 `join.method` 分桶的未命中列（欄位：漢字、反切、韻、sim_tl候選、
文讀gold）。請診斷此桶的系統性 miss 原因，提出可驗證的假說。考慮面向：

- 反切上字聲母選取（keypoint 排序是否漏掉正確文讀聲母）
- 反切下字韻母選取（開合／等第／韻攝分歧）
- 聲調推導（`mc_tone`、平水韻目聲調、清濁→調類映射）
- keypoint ranking（文讀優先序是否被白讀／俗讀壓過）
- join method 本身的特性（此桶為何以此法 join、是否有系統性偏差）

## 輸出格式（嚴格）

```markdown
## 觀察
（此桶 miss 的共通模式，引用列中的漢字／反切為例）

## 假說
1. …（每條假說指明對應的程式位置或資料面向）
2. …

## 建議修改
- …（每條建議須說明對「平均候選」數的影響方向與理由）

## 風險
- …（對 index parity、非 mc 欄位、其他 join.method 的影響）
```

## 禁止事項

- 不得提議放寬候選上限（聲母 ≤2 × 韻母 ≤3 是固定約束）
- 不得提議修改 checks/、acceptance.yaml、測試、`.agent/`、`flows/`
- 不得修改任何檔案（唯讀）
- 不得輸出 TODO／TBD／PLACEHOLDER 等佔位文字
