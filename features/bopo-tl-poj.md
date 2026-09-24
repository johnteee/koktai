---
feature: bopo-tl-poj
source_commit: cc306005f532ecfff2484a10357ae6e507a3f06c
last_verified_at: 2026-09-24
verification_status: verified
acceptance: [AC1, AC2, AC4]
---

# 方音符號 → 台羅／白話字、逐字對齊

## 入口

| 符號 | 位置 | 角色 |
|---|---|---|
| `main()` | `a-tsioh_sandbox/rt2pronun.py` | stdin koktai-dic/2 → stdout 加上 `tl`/`poj`/`lang`/`tokens` |
| `analyze_bopo(bopo)` | 同上 | 方音串 → `{'lang', 'tl', 'poj'}`；國語注音歸 `cmn` |
| `convert_bopo_to_tl(bopo)` | 同上 | → `(tl, poj)` |
| `臺羅轉白話字.轉白話字(聲, 韻, 調)` | 同上（class method） | 台羅音節三段 → POJ Unicode |
| `tokenize_ruby(text)` | 同上 | ruby 句 → 逐字對齊 tokens |
| `validate_poj(csv_dir)` | `a-tsioh_sandbox/chhoetaigi.py` | 對 ChhoeTaigi `KipInput`↔`PojUnicode` 黃金對全量比對 |

## 驅動

黃金測試（約 2 秒；原 CLI 一律結束碼 0，是量測不是閘門）：

```sh
python3 a-tsioh_sandbox/chhoetaigi.py --validate-poj
python3 checks/koktai_checks.py poj-gold --min-ok 3554 --total 3638     # 閘門版
```

函式抽查（在 `a-tsioh_sandbox/` 內 import）：

```sh
cd a-tsioh_sandbox && python3 -c '
from rt2pronun import 臺羅轉白話字 as C, analyze_bopo, convert_bopo_to_tl
print(C.轉白話字("p","eh","4"), C.轉白話字("ts","iah","8"))
print(analyze_bopo("ㄅㆤㆷ"), convert_bopo_to_tl("ㄅㆤㆷ"))'; cd ..
```

## 可觀察結果（cc306005 實測）

- `--validate-poj` stderr 首行：`[poj-gold] 音節對 3638，符合 3554（97.69%）`，其後 12 行最大殘差桶（首桶 `韻 erh 調 8: ×3`；殘差多歸因於 gold 端家法，如 Embree 尾字母標調，見 `docs/methodology.md` §7）。
- 閘門版：`[PASS] poj-gold: 3554/3638（97.69%）`。
- 抽查：`peh chia̍h`；`{'lang': 'nan', 'tl': 'peh4', 'poj': 'peh'} ('peh4', 'peh')`。
- 轉換結果進入 `json/NN.json` 各層 `tl`/`poj` 與 `tokens[]`，再經 AC2 反映到 `index/han_to_tl.tsv` 的「台羅／白話字」欄。

## 失敗路徑

| 症狀 | 分類線索 |
|---|---|
| `[FAIL] poj-gold: N/3638 … < 最低 3554` | `rt2pronun.py` 有改 → product regression；看 `--validate-poj` 新增的殘差桶定位韻母/調 |
| `[HARNESS] poj-gold: 黃金對總數 X ≠ 3638` | `ExternalRef/ChhoeTaigiDatabase/*.csv` 或 `chhoetaigi.iter_poj_gold` 的過濾規則變了；CSV 變 → harness；過濾規則被改 → 視同改 oracle，交 human |
| AC1 PASS、AC2 的 `han_to_tl.tsv` 不同，但 AC4 PASS | 轉換對黃金對以外的音節（或方音→台羅段）有變；用 `features/unified-index.md` 差異定位看 `taigi[].tl/poj` |

## 證據

`--validate-poj` stderr 全文、`poj-gold` 的 `[PASS|FAIL]` 行、抽查輸出。
