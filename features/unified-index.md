---
feature: unified-index
source_commit: cc306005f532ecfff2484a10357ae6e507a3f06c
last_verified_at: 2026-09-24
verification_status: verified
acceptance: [AC2]
---

# 統一聲韻索引（漢字 ↔ 台羅）

## 入口

`python3 a-tsioh_sandbox/build_unified_index.py [--json GLOB] [--ytenx DIR] [--out DIR] [--chhoetaigi DIR] [--sutian ODS] [--moe-dir DIR] [--chhiankimpho MD] [--extra-chars TXT]`

- 預設 `--json 'json/*.json' --out index`：**會覆寫入庫的 `index/`，驗證時必帶 `--out` 指到 repo 外**。
- 外部源檔不存在時**自動略過該層**（只在 stderr 少一行），輸出仍產生 → 用 doctor 確認外部源齊全。
- 必須在 repo 根目錄執行（`_meta.sources.extra_chars` 記 `os.path.relpath`）。
- 輸出：`unified_phonology.json`、`han_to_tl.tsv`、`tl_to_han.tsv`、`chhoetaigi_gaps.tsv`；schema 見 `docs/unified-index.md`。

## 驅動

接在 `features/dic-to-json.md` 的 `rebuild-json` 之後（同一 `KOKTAI_SCRATCH`）：

```sh
python3 checks/koktai_checks.py build-index
python3 checks/koktai_checks.py index-parity --ref HEAD
grep -E '漢字 .* / 台羅音節|taigi_pairs|attest_pairs|佐證：' "$KOKTAI_SCRATCH/index.stderr"
```

AC2 不一致時的差異定位（哪些欄位、哪些字不同）：

```sh
git show HEAD:index/unified_phonology.json > "$KOKTAI_SCRATCH/head.json"
python3 - "$KOKTAI_SCRATCH/head.json" "$KOKTAI_SCRATCH/index/unified_phonology.json" <<'EOF'
import json, sys
a, b = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
sa, sb = a["_meta"]["stats"], b["_meta"]["stats"]
for k in sorted(set(sa) | set(sb)):
    if sa.get(k) != sb.get(k):
        print(f"stats {k}: {sa.get(k)} -> {sb.get(k)}")
fields = {}
for ch in set(a["han"]) | set(b["han"]):
    ra, rb = a["han"].get(ch, {}), b["han"].get(ch, {})
    for f in set(ra) | set(rb):
        if ra.get(f) != rb.get(f):
            fields.setdefault(f, []).append(ch)
for f, chs in sorted(fields.items()):
    print(f"han[].{f}: {len(chs)} 字不同，例 {''.join(sorted(chs)[:10])}")
print("tl 反查不同音節數:", sum(1 for t in set(a["tl"]) | set(b["tl"]) if a["tl"].get(t) != b["tl"].get(t)))
EOF
```

讀音抽查（對 repo 的 `index/` 或 scratch 索引皆可）：

```sh
python3 - index/unified_phonology.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
def row(ch, tl):
    return next({k: r.get(k) for k in ("n", "w", "registers")} for r in d["han"][ch]["taigi"] if r["tl"] == tl)
print("八 peh4", row("八", "peh4")); print("方 hong1", row("方", "hong1"))
print("hong5 反查字數", len(d["tl"]["hong5"]), "卷數", len(d["_meta"]["volumes"]))
EOF
```

## 可觀察結果（cc306005 實測）

- `[PASS] index-parity: 4 檔與 HEAD:index/ 一致`；健康時差異定位只印 `tl 反查不同音節數: 0`。
- `index.stderr`：`[index] 漢字 10185 / 台羅音節 3272 / 讀音對 28758`、`taigi_pairs: 627497`、`[index] ChhoeTaigi 佐證：15244 對 （對 53.0% / token 88.7%）；高頻缺口 424 筆`。
- 抽查：`八 peh4 {'n': 104, 'w': 180, 'registers': ['語']}`、`方 hong1 {'n': 649, 'w': 729, 'registers': ['文', '文白']}`、`hong5 反查字數 55 卷數 26`。
- 四檔輸出兩次建置位元一致（無時間戳、無隨機序）。

## 失敗路徑

| 症狀 | 分類線索 |
|---|---|
| `[FAIL] index-parity: 與 HEAD:index/ 不同：[…]` | 用差異定位：只有 `han[].mc`/`pingshui`＋`stats sim_tl*/join_*` → 反切層（`features/fanqie-sim-tl.md`）；`taigi` 的 `attest`/`w` → 佐證層（`features/attestation-layers.md`）；`taigi` 的 `tl`/`poj`/`n` 或 `mandarin` → 轉換/解析層 |
| 只有 `_meta.sources` 不同 | 外部源缺席（某層 `None`）或 cwd 不在 repo 根 → harness |
| `[HARNESS] build-index: scratch JSON 不足 26 卷` | 同一 scratch 沒先跑 `rebuild-json` |
| `[HARNESS] … git show HEAD:index/… 失敗` | 不在 git repo 或 `index/` 未入庫 |
| `[FAIL] build-index: 結束碼 N` | 看 `$KOKTAI_SCRATCH/index.stderr` traceback |

## 證據

`$KOKTAI_SCRATCH/index/*`、`index.stderr`、差異定位輸出、`index-parity` 的 `[PASS|FAIL]` 行。
