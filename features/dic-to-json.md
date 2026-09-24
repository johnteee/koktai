---
feature: dic-to-json
source_commit: cc306005f532ecfff2484a10357ae6e507a3f06c
last_verified_at: 2026-09-24
verification_status: verified
acceptance: [AC1]
---

# `.dic` → koktai-dic/2 JSON

## 入口

| 階段 | 命令 | 說明 |
|---|---|---|
| recode | `perl a-tsioh_sandbox/recode_utf8.pl betaNNk.dic` | Big5(CP950)→UTF-8；EUDC 造字 U+E000–F8FF → U+F0000＋Big5 碼位 |
| 解析 | `python3 a-tsioh_sandbox/dic2json.py` | stdin→stdout；`koktai_dic.parse_volume`；造字以 `font/m3.json`、`font/k.json`、`a-tsioh_sandbox/mapping.json` 解碼；stderr 一行統計 |
| 批次（**會覆寫 `json/`，驗證勿用**） | `perl gen_json.pl` | 26 卷串接 recode → dic2json → rt2pronun |

## 驅動

全 26 卷（寫到 scratch，不碰 `json/`）：

```sh
export KOKTAI_SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/koktai-f1.XXXXXX")
python3 checks/koktai_checks.py rebuild-json --expect-totals 1446,12857,43913,11002
```

單卷（例：卷 01），含與本機 `json/` 位元比對：

```sh
S=$(mktemp -d "${TMPDIR:-/tmp}/koktai-f1.XXXXXX")
perl a-tsioh_sandbox/recode_utf8.pl beta01k.dic | python3 a-tsioh_sandbox/dic2json.py 2>"$S/01.err" \
  | python3 a-tsioh_sandbox/rt2pronun.py > "$S/01.json"
cat "$S/01.err"
cmp "$S/01.json" json/01.json && echo "json/01.json 位元相同"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["format"], sorted(d), d["stats"])' "$S/01.json"
```

## 可觀察結果（cc306005 實測）

- `rebuild-json`：`[PASS] rebuild-json: 26 卷；章,單字,詞條,反切 = 1446,12857,43913,11002`，另有 `[info]` 行「本機 json/ 位元相同 26 卷、不同 0 卷」。
- 卷 01 stderr：`[dic2json] 章 67 / 單字 600 / 詞條 2197 / 反切 550`。
- 卷 01 JSON：`koktai-dic/2 ['chapters', 'format', 'stats', 'unassigned'] {'chapters': 67, 'hanzi_entries': 600, 'word_entries': 2197, 'fanqie_citations': 550}`。
- 各卷章／單字／詞條／反切數見 `docs/pipeline.md`「各卷產出統計」表；卷 11 只有 `5 / 5 / 4 / 3`（源檔截斷，屬已知界限）。

## 失敗路徑

| 症狀 | 分類線索 |
|---|---|
| `[FAIL] rebuild-json: 卷 NN 管線結束碼 …` | 看 `$KOKTAI_SCRATCH/NN.stderr` 的 traceback；解析器崩潰多為 product regression |
| `[FAIL] rebuild-json: 卷 NN stderr 無 [dic2json] 統計行` | dic2json 未跑完或統計格式被改（改格式也須同步 `checks/`，由 human 決定） |
| 總數不符 `章,單字,詞條,反切 = …，預期 1446,12857,43913,11002` | `.dic` 未變而數字變 → product regression（解析規則）；找差異卷：逐卷比 `NN.stderr` 與 `docs/pipeline.md` 表 |
| `[HARNESS] … beta NNk*.dic 應恰一檔` | 源檔缺或多 → harness |
| `[info] 卷 NN 與本機 json/NN.json 位元不同`（總數仍 PASS） | 僅診斷：本機 `json/` 可能是舊產物；總數不變但內容不同時，交 AC2 判定 |

## 證據

`$KOKTAI_SCRATCH/json/NN.json`、`$KOKTAI_SCRATCH/NN.stderr`、`rebuild-json` 的 `[PASS|FAIL]` 行。
