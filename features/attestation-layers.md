---
feature: attestation-layers
source_commit: cc306005f532ecfff2484a10357ae6e507a3f06c
last_verified_at: 2026-09-24
verification_status: verified
acceptance: [AC2]
---

# 外典佐證層與權重

## 入口

| 符號／CLI | 位置 | 產物 |
|---|---|---|
| `load_attestation(csv_dir)`；`--attest-stats` | `a-tsioh_sandbox/chhoetaigi.py` | `{(漢字, 台羅): {辭典標籤}}`；甘字典漢文音另掛 `甘文` |
| `load_sutsha(ods)`；`python3 a-tsioh_sandbox/sutian.py [--ods]` | `a-tsioh_sandbox/sutian.py` | 教育部詞彙比較 `比` 標籤＋十腔別 `dialects` |
| `load_appendices(dir)` | 同上 | 附錄 `新`／`共`／`諺` 標籤 |
| `load_attestation(md)`；`python3 a-tsioh_sandbox/chhiankimpho.py [--md]` | `a-tsioh_sandbox/chhiankimpho.py` | 千金譜 `金` 標籤（權重 2） |
| `main()` 內合併 → `build_outputs` | `a-tsioh_sandbox/build_unified_index.py` | `taigi[].attest`、`w = n + Σ 辭典權重`、`dialects`、`chhoetaigi_gaps.tsv` |

任一外部源缺席時，索引**靜默略過**該層（`_meta.sources.<層>` 為 `None`）→ AC2 一定不一致；先跑 `checks/doctor.sh`。

## 驅動

各層獨立統計（皆寫 stderr，結束碼恆 0；是量測不是閘門）：

```sh
python3 a-tsioh_sandbox/chhoetaigi.py --attest-stats
python3 a-tsioh_sandbox/sutian.py 2>&1 >/dev/null | grep -E '^\[sutian\] (\{|泉腔|附錄)'
python3 a-tsioh_sandbox/chhiankimpho.py 2>&1 >/dev/null | head -1
```

合併後效果（需先有 scratch 索引，見 `features/unified-index.md`）：

```sh
grep -E 'ChhoeTaigi|教育部|千金譜|佐證' "$KOKTAI_SCRATCH/index.stderr"
```

## 可觀察結果（cc306005 實測）

- `--attest-stats`：`[attest] pairs: 27290`；逐典 `aligned_rows`：700=451、教=23855、線=80533、iT=14049、日=61981、甘=18023、植=1628。
- `sutian.py`：`{'rows': 12271, 'aligned': 12022, 'skipped': 249, 'pairs': 2976}`、`泉腔形（ir/er/調6）共 296 對`、附錄 新 120/120 列 238 對、共 350/350 列 464 對、諺 39/40 列 182 對。
- `chhiankimpho.py`：`{'lines': 472, 'aligned': 472, 'skipped': 0, 'pairs': 1181}`。
- `index.stderr`：`ChhoeTaigi 佐證表：27290`、`教育部詞彙比較：12022/12271 列對齊，2976`、`千金譜：472/472 行對齊，1181`、`ChhoeTaigi 佐證：15244 對 （對 53.0% / token 88.7%）；高頻缺口 424 筆`。

## 失敗路徑

| 症狀 | 分類線索 |
|---|---|
| AC2 差異只在 `taigi[].attest`／`w`／`dialects` 或 `chhoetaigi_gaps.tsv` | 對齊規則（`_align`、`norm_kip_word`、權重表 `DICT_WEIGHT`）有改 → product regression；外部檔變 → harness |
| 單層統計數字變、程式碼未變 | `ExternalRef/` 檔案版本變（附錄以 glob 取最新版）→ harness |
| `_meta.sources.chhoetaigi`（或他層）為 `None` | 該層源檔缺席 → harness |

## 證據

三個 CLI 的 stderr 全文、`index.stderr` 佐證行、差異定位輸出中的 `attest`/`w` 欄位統計。
