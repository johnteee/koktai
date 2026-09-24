# VERIFY — koktai 驗證控制面

給**沒有對話脈絡的 agent**：照本檔即可啟動、體檢、驅動全部檢核並分類失敗。不需問路。
產品是**資料管線＋函式庫**（無 server、無 HTTP route）：`.dic` → `json/NN.json` → `index/`。

- 驗證基線：commit `cc306005`（2026-09-24 全掃 PASS，32 秒）
- 功能分區與逐區驅動命令：[features/README.md](features/README.md)
- 鎖定驗收規格（唯讀 0444）：[acceptance.yaml](acceptance.yaml)
- 檢核實作：`checks/koktai_checks.py`（結束碼 0 PASS／1 FAIL／2 HARNESS）

## 0. 環境須知（照抄，違反即 harness failure）

| 事項 | 內容 |
|---|---|
| 工作目錄 | 一律在 repo 根目錄執行。`build_unified_index.py` 把 `--extra-chars` 的 `os.path.relpath` 寫進 `_meta`，換 cwd 就不再位元一致 |
| Python | `python3` ≥ 3.8，只用標準庫；實測 3.13.0、3.14.7 皆全掃 PASS（pyenv 依目錄選版本） |
| ytenx | `~/dev/ytenx`（韻典網資料）@ `5f085b0c`；`a-tsioh_sandbox/test_join_fanqie.py` **寫死** `~/dev/ytenx`，缺席時整組測試 skip（checks 視為 HARNESS）。`YTENX=路徑` 只影響 build-index |
| 外部源 | `ExternalRef/ChhoeTaigiDatabase/*.csv`（11 部）、`ExternalRef/詞彙比較表.ods`、`sinsu120_*/kiongtongsu350_*/siokgan40_*.ods`、`chhian-kim-pho2.md`。缺席時索引**靜默略過**該層 → AC2 會不一致，先跑 doctor |
| `json/` | 本機產物（329 MB），**未入 git**，只作診斷參照；驗證一律在 scratch 重建 |
| `index/` | **入 git**；`HEAD:index/` 是 AC2 的 oracle |
| 禁用命令（會改 repo） | `perl gen_json.pl`（覆寫 `json/`）、`python3 a-tsioh_sandbox/build_unified_index.py` 不帶 `--out`（預設覆寫 `index/`）。驗證時只用 `checks/` 或把輸出導到 repo 外 |
| scratch | 必須在 repo 外；`checks/verify.sh` 自動 `mktemp -d $TMPDIR/koktai-verify.XXXXXX` |
| 已知資料界限（非失敗） | 卷 11 源檔截斷（5 單字）；`beta15k1.dic` 檔名多一碼；`ExternalRef/HanBunDatabase.accdb` 加密、未追蹤、不用 |

## 1. Launch

無需啟動服務。確認位於 repo 根目錄：

```sh
cd "$(git rev-parse --show-toplevel)"
```

## 2. Doctor（約 1 秒）

```sh
checks/doctor.sh
```

健康：最後一行 `doctor: healthy`、結束碼 0。任何 `[HARNESS]` 行 → 結束碼 2，先修環境再談產品。
`[warn]` 不擋：ytenx commit 不符釘選、`index/` 工作樹與 HEAD 不同、`acceptance.yaml` 可寫、`json/` 不足 26 卷。

## 3. Drive（全掃約 35 秒）

```sh
checks/verify.sh
```

健康輸出（2026-09-24 實測）：

```
AC1-dic-parse-totals           PASS     (22s)
    [PASS] rebuild-json: 26 卷；章,單字,詞條,反切 = 1446,12857,43913,11002
AC2-index-reproducible         PASS     (7s)
    [PASS] build-index: …/index（stderr：…/index.stderr）
    [PASS] index-parity: 4 檔與 HEAD:index/ 一致
AC3-fanqie-unittests           PASS     (0s)
    [PASS] unittest: 13 測試 OK
AC4-poj-golden                 PASS     (2s)
    [PASS] poj-gold: 3554/3638（97.69%）
AC5-fanqie-literary-hit-rate   PASS     (0s)
    [PASS] hit-rate: 4173/5286（78.94%），平均候選 4.36
verify: PASS (5 checks)
```

單項重跑（AC2、AC5 需要同一 scratch 已有 AC1／AC2 產物）：

```sh
ONLY=AC3 checks/verify.sh
KOKTAI_SCRATCH=/tmp/koktai-verify.XXXXXX ONLY=AC5 checks/verify.sh   # 沿用上次 scratch
```

逐功能深入驅動（單卷重建、索引差異定位、反切 join 抽查、佐證層統計）：見 `features/*.md`。

## 4. Evidence

| 位置 | 內容 |
|---|---|
| `$KOKTAI_SCRATCH/summary.tsv` | 每個 check 的 `id / status / exit / seconds` |
| `$KOKTAI_SCRATCH/<id>.log` | 該 check 全部輸出（`[PASS|FAIL|HARNESS]` 行＋`[info]` 診斷） |
| `$KOKTAI_SCRATCH/doctor.log` | 環境體檢 |
| `$KOKTAI_SCRATCH/json/NN.json`、`NN.stderr` | 重建的 26 卷與各卷 dic2json 統計行 |
| `$KOKTAI_SCRATCH/index/`、`index.stderr` | 重建索引四檔與 `[index]` 統計（join 方法分佈、sim_tl 補強數） |

回報時附：`summary.tsv` 全文、每個非 PASS check 的 `[FAIL]`/`[HARNESS]` 行、`git rev-parse HEAD`、`git -C ~/dev/ytenx rev-parse HEAD`。

## 5. 失敗分類

| Class | Meaning | Repair |
|---|---|---|
| Product regression | Product behavior changed for the worse | Report; never edit map/spec/tests to match |
| Doc drift | Docs no longer match a healthy product | Update the doc |
| Spec/oracle error | The acceptance spec or test expectation is wrong | Oracles read-only; propose change for review |
| Harness failure | Toolchain, launch, environment, external dep broke | Fix the harness |

### 判定程序

1. **結束碼 2／任何 `[HARNESS]` → Harness failure。** 例：ytenx 缺席、unittest 被 skip、CSV 黃金對總數 ≠ 3638、scratch 放在 repo 內、doctor 不健康。修好後重跑，之前的 FAIL 不算數。
2. **`[FAIL]` 且 `git status` 顯示產品原始碼（`a-tsioh_sandbox/*.py|*.pl`、`font/*.json`、`a-tsioh_sandbox/mapping.json`、`a-tsioh_sandbox/data/*`、`beta*.dic`）相對基線有改動 → 先假設 Product regression。** 用對應 feature 檔的定位命令找出哪一層變了（AC1 總數→解析；AC2 只有 `mc`/`pingshui` 不同→反切層；`taigi`/`tl` 不同→聚合/轉換/佐證層；AC4→台羅→白話字轉換；AC5→反切模擬音）。
3. **`[FAIL]` 但產品原始碼與外部依賴都等於基線** → 產品沒動卻不符：
   - ytenx commit ≠ `5f085b0c` 或 `ExternalRef/` 有變 → Harness failure（外部依賴漂移）。
   - 否則 oracle 本身錯 → **Spec/oracle error**：寫出不符的 check、預期值、實測值、證據，交 human；**不得**改 `acceptance.yaml`、`checks/`、測試。
4. **檢核全 PASS，但 `VERIFY.md`／`features/*.md`／`docs/*.md` 的命令、數字、函式名與實測不符 → Doc drift。** 修文件，並更新該 feature 檔的 `source_commit`／`last_verified_at`。
5. 產品有**刻意且被接受**的改進（例如命中率提升）導致 AC2 不一致：不是 regression，但也**不能由 agent 自行把新 `index/` 當 oracle**。由 human 重建並 commit `index/`（re-baseline），AC2 隨 HEAD 前進；AC1/AC4/AC5 的門檻只會由 human 以新版 `acceptance.yaml` 提高。

## 6. Cleanup

驗證不寫 repo。刪 scratch 即可：

```sh
rm -rf "${TMPDIR:-/tmp}"/koktai-verify.*
```

確認未誤改 repo：驗證前後各跑一次 `git status --short`，兩者必須完全相同（驗證只寫 repo 外 scratch）。

## 7. 相關控制面

- `flows/`：反切未命中分桶 triage（fan-out/fan-in，唯讀 agent）與命中率 fix loop（驗證閘門）。說明見 `flows/README.md`。
- `.agent/governance/`：四權分立、能力權杖、憲法路徑（`checks/`、`acceptance.yaml`、測試、`VERIFY.md`、`features/` 皆 worker 不可寫）。
- `.agent/delivery/`：governed-delivery 合約（intent、oracle manifest、envelope、evidence ledger、acceptance record）。
