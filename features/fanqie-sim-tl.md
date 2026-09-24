---
feature: fanqie-sim-tl
source_commit: cc306005f532ecfff2484a10357ae6e507a3f06c
last_verified_at: 2026-09-24
verification_status: verified
acceptance: [AC2, AC3, AC5]
---

# 反切 × ytenx 中古層 join、`sim_tl` 模擬文讀

## 入口（`a-tsioh_sandbox/build_unified_index.py`）

| 符號 | 角色 |
|---|---|
| `Ytenx(root).join_fanqie(speller, yun_norm, ps)` | 反切二字＋韻目 → `(method, rec)`；method ∈ `廣韻反切`、`正韻反切`、`廣韻反切·平水寬`、`正韻反切·寬` |
| `Pingshui().normalize_yun(yun)`／`.lookup(yun)` | 韻目異體正規化（真→眞…）；韻目 → 平水部＋`expected_tl` |
| `derive_sim_tl(entry, ytenx)` | 中古聲母類 × 平水預期韻母 × 文讀調 → `sim_tl` 候選 |
| `build_reading_profile(coll, attest=None)` | 反切上下字的現代讀音關鍵點；文/甘文 → 非白/語/俗/訓 → 全部 |
| `enrich_mc_with_reading_profile(coll, ytenx, profile)` | 上字聲母（≤2 類）× 下字韻母（≤3 型）＋反切調 → `sim_tl.keypoint_composed`，併入 `syllables` |
| `add_ytenx_char_fallback(coll, ytenx, ps, ch)` | 無引註字頭以 `Dzih.txt` 歸小韻（`字頭歸小韻·外字`） |
| `norm_registers(label)` | 文音/文讀/皆文音 → `文`；`文白` 保留 |

外部資料：`~/dev/ytenx/ytenx/sync/kyonh/`（廣韻）、`~/dev/ytenx/ytenx/sync/tcenghyonhtsen/`（洪武正韻牋）；先驗表 `a-tsioh_sandbox/data/kuangx_pingshui.json`、`pingshui_tl.json`；額外字頭 `a-tsioh_sandbox/data/literature_extra_chars.txt`。

## 驅動

單元測試（0.3 秒）：

```sh
cd a-tsioh_sandbox && python3 -m unittest test_join_fanqie -v; cd ..
python3 checks/koktai_checks.py unittest --min-tests 13      # 閘門版（禁 skip、禁測試數下降）
```

命中率。AC5 量的是**目前程式碼重建的 scratch 索引**（不帶 `--index`，讀 `$KOKTAI_SCRATCH/index/`；需同一 scratch 先跑過 `rebuild-json`＋`build-index`，或沿用 `checks/verify.sh` 印出的 scratch）；
帶 `--index index/unified_phonology.json` 量的是**入庫的 oracle 索引**。兩者分歧＝程式碼行為已偏離基線：

```sh
python3 checks/koktai_checks.py hit-rate --min-hits 4173 --max-avg-cand 4.36                     # scratch（現行程式碼）
python3 checks/koktai_checks.py hit-rate --index index/unified_phonology.json --min-hits 4173 --max-avg-cand 4.36   # oracle
python3 checks/koktai_checks.py hit-rate --dump-misses "$(mktemp -d "${TMPDIR:-/tmp}/koktai-miss.XXXXXX")"   # 未命中依 join.method 分桶
```

命中率定義（與 `docs/unified-index.md` 的 78.94% 相同）：分母＝`han[ch].mc[]` 中 `sim_tl.syllables` 非空、且該字有文讀 gold 的條目；gold＝同字 `taigi[]` 中 `registers` 任一標籤含「文」（含 `文白`）或 `attest` 含 `甘文` 的 `tl`；命中＝候選與 gold 交集非空。

join 分佈與 sim_tl 抽查（需先有 scratch 索引）：

```sh
grep -E 'join_|sim_tl' "$KOKTAI_SCRATCH/index.stderr"
python3 - index/unified_phonology.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for ch in ("人", "中"):
    for m in d["han"][ch]["mc"][:2]:
        print(ch, m.get("fanqie"), (m.get("join") or {}).get("method"), (m.get("sim_tl") or {}).get("syllables"))
EOF
```

## 可觀察結果（cc306005 實測）

- `Ran 13 tests … OK`；閘門版 `[PASS] unittest: 13 測試 OK`。
- `[PASS] hit-rate: 4173/5286（78.94%），平均候選 4.36`；分桶目錄有 `MANIFEST.tsv` 與 `miss-NN.tsv`。
- `index.stderr`：`join_廣韻反切: 2778`、`join_正韻反切: 1884`、`join_廣韻反切·平水寬: 233`、`join_正韻反切·寬: 1446`、`join_none: 4661`、`join_char_fallback: 3414`、`sim_tl: 13506`、`sim_tl_keypoint_enriched: 9153`、`sim_tl_keypoint_added: 25824`。
- 抽查：`人 而鄰切 正韻反切 ['jin5', 'jun5', 'lin5', 'lun5']`；`中 陟隆切 正韻反切 ['tong1', 'tiong1', 'thiong1', 'thang1', 'the1', 'tang1', 'te1']`；`中 陟仲切 廣韻反切 ['tong3', 'tiong3', 'thiong3']`。

## 失敗路徑

| 症狀 | 分類線索 |
|---|---|
| `[FAIL] unittest: 13 測試，失敗 [...]` | 測試名稱即定位（join 精確度、日母/知母聲母、甘文排序、keypoint 補強）；產品碼有改 → product regression |
| `[HARNESS] unittest: unittest 被略過` | `~/dev/ytenx` 缺席（測試寫死路徑） |
| `[FAIL] unittest: 只跑 N 測試 < 最低 13` | 測試被刪 → 視同削弱 oracle，交 human |
| `[FAIL] hit-rate: … 命中 N < 4173` | sim_tl 規則或關鍵點排序退步 → product regression；用 `--dump-misses` 比較退步前後的桶 |
| `[FAIL] hit-rate: … 平均候選 X > 4.36（候選膨脹）` | 以擴張候選集換命中率——即使命中率上升也不接受（候選上限 2×3 是刻意設計） |
| AC2 差異只落在 `mc`/`pingshui`，AC3/AC5 仍 PASS | 反切層行為改變但未跌破門檻：若非刻意改動 → product regression；刻意改進 → 走 VERIFY.md §5 re-baseline |
| `join_*` 分佈變、程式碼未變 | ytenx commit 漂移 → harness |

## 證據

unittest `-v` 全文、`hit-rate` 行、`MANIFEST.tsv`、`index.stderr` 的 join/sim_tl 統計、抽查輸出。
