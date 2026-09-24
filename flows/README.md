# flows/ — agent 治理下的驗證與交付流程

本目錄收錄兩個 host 端流程腳本（bash 3.2 相容），依 `flow-control-generator`
與 `flow-loop-harness` 技能模板生成。腳本只負責控制流；模型只負責步驟內容。
所有 agent 呼叫一律經 `AGENT_CMD`（預設 `.agent/governance/run-codex.sh`），
以 `timeout "$CALL_TIMEOUT"` 包裹；state 一律放 repo 外（`$TMPDIR/koktai-*`）。

## flows/fanqie-miss-triage.sh — 未命中分桶診斷（唯讀）

拓撲：parallel fan-out/fan-in。選此拓撲是因為各 `join.method` 桶的診斷彼此
獨立、結果只需合併一次；不需要迭代（迭代屬於 fanqie-loop）。

- Stage 0（決定性）：`hit-rate --dump-misses` 把未命中按 `join.method` 分桶
  寫到 `$STATE/buckets/`（`MANIFEST.tsv` + `miss-NN.tsv`）。
  閘門：manifest 至少 1 桶，否則 exit 2。
- Fan-out：前 `MAX_BRANCHES`（預設 8，envelope `max_triage_branches`）桶，
  每桶一個 read-only agent，並行上限 `MAX_JOBS`（預設 4，
  envelope `max_parallel_agents`），每分支 prompt = `prompts/triage-branch.md`
  + 桶標頭 + 前 `ROWS`（預設 150）列。閘門：strict（任一分支失敗即 exit 2）；
  設 `MIN_OK=N` 可改為明示 quorum。
- Fan-in：`prompts/triage-synthesize.md` + 全部分支輸出 → 單一合成 agent →
  `$STATE/final.md`。合併閘門：`checks/verify-triage.sh`（決定性：非空、
  四個標題、引用 manifest 中存在的 miss-NN、無 TODO/TBD/PLACEHOLDER、
  含「平均候選」影響說明）。

結束碼：0 完成／2 閘門失敗／4 harness（缺 index、envelope、prompt、timeout）。

```bash
# dry run（stub agent，見下方證據）
STATE=/tmp/ks-triage AGENT_CMD=/tmp/stub-triage.sh flows/fanqie-miss-triage.sh
# 正式 run（read-only，不需 intent 簽署——不寫 repo）
flows/fanqie-miss-triage.sh
# resume：STATE 保留即可重跑；fan-*.md 會先清除再重跑
```

State：`${TMPDIR}/koktai-fanqie-miss-triage/`（`buckets/`、`bprompt-*.md`、
`fan-*.md`、`synth-prompt.md`、`final.md`、`flow.log`）。
預算：至多 `MAX_BRANCHES`+1 次 agent 呼叫，各 ≤ `CALL_TIMEOUT`（預設 1800 s，
envelope `per_call_timeout_seconds`）。

## flows/fanqie-loop.sh — verify-gated 修復迴圈

拓撲：verify-gated fix loop（flow-loop-harness）。唯一的成功訊號是外部
verifier `checks/fanqie-target.sh`（guard→scope→unittest→build-index→
index-parity→hit-rate）；模型自報不算數。

- Intent gate：`.agent/delivery/intent-record.yaml` 須有 `status: signed`，
  否則 exit 5。`DRY_RUN=1` 且 `AGENT_CMD` 明示（stub）時放行並在 ledger 記
  `DRY RUN`。
- Bootstrap（首次）：`rebuild-json --expect-totals 1446,12857,43913,11002`
  → `guard --snapshot` → `scope --snapshot`，產物在 `$STATE`（repo 外）。
  Resume：基線已存在即沿用，ledger 追加 `RESUMED`。
- 每輪：prompt = `prompts/fanqie-fix.md` + ledger 尾 20 行 + verifier 輸出
  （+ 可選 `TRIAGE=` 檔）→ agent（workspace-write，僅應改
  `a-tsioh_sandbox/build_unified_index.py`）→ verifier。
- Kill 條件（exit 3）：verifier 輸出含 `[FAIL] guard`、`[FAIL] scope` 或
  `[HARNESS]`；同一 failure signature（首個 `[FAIL] <name>:` 行原文，含數字——命中率有進步即不同 signature）
  連續達 `FAIL_SIG_LIMIT`（預設 2，envelope `failure_signature_limit`）；
  或工作樹無可觀察變動（git diff stat + untracked count 不變）。
- 上限：`MAX_ITER`（預設 6，envelope `max_iterations`）用罄 → exit 2。

結束碼：0 達標／2 cap 用罄／3 kill（guard/scope/HARNESS、signature 重複、
無進度）／4 verifier 缺損或 bootstrap 失敗／5 intent 未簽署。

```bash
# dry run（stub agent；在 repo 副本中執行，勿動真 repo）
DRY_RUN=1 STATE=/tmp/ks1 AGENT_CMD=/tmp/stub.sh flows/fanqie-loop.sh
# 正式 run（需先簽署 intent-record.yaml）
flows/fanqie-loop.sh
# resume：同一 STATE 重跑即續（沿用 scratch/guard/scope 基線）
STATE=/tmp/ks1 flows/fanqie-loop.sh
```

State：`${TMPDIR}/koktai-fanqie-loop/`（`scratch/`、`guard.json`、`scope.json`、
`ledger.md`、`verify-out.txt`、`iter-N-{prompt,out}.md`、`flow.log`、
`bootstrap.log`）。

## Human-approval boundary

首次無人值守 run 前，human 必須核定：verifier（fanqie-target.sh 的檢查鏈與
envelope 門檻）、caps（MAX_ITER／CALL_TIMEOUT／FAIL_SIG_LIMIT／MAX_BRANCHES）、
權限旗標（read-only vs workspace-write、host 須以權限模式排除憲法路徑寫入）、
blast radius（loop 只准動 `build_unified_index.py`；triage 唯讀）。核定紀錄
寫入 `.agent/delivery/evidence-ledger.yaml`（該檔由 governance slice 維護，
本目錄不建立）。envelope `pause_actions`（git commit/push、覆寫 index//json/、
改先驗表、新增外部依賴）逐次需 human 決定，loop 內不得自行執行。

## Dry-run 證據（2026-09-24，stub agents，repo 副本 /tmp/koktai-flowtest）

| 案例 | 指令 | 結束碼 |
| --- | --- | --- |
| triage 正常 | `STATE=/tmp/ks-triage AGENT_CMD=/tmp/stub-triage.sh flows/fanqie-miss-triage.sh` | 0（final.md 產出、verify-triage PASS） |
| triage 分支空輸出 | `STATE=/tmp/ks-triage2 AGENT_CMD=/tmp/stub-triage-empty.sh flows/fanqie-miss-triage.sh` | 2（strict gate：branch failures 1） |
| loop 已達標 | `DRY_RUN=1 STATE=/tmp/ks1 AGENT_CMD=/tmp/stub-noop.sh flows/fanqie-loop.sh`（副本 envelope min_hit_rate 0.78） | 0（already verified） |
| loop cap | `DRY_RUN=1 STATE=/tmp/ks2 AGENT_CMD=/tmp/stub-comment.sh MAX_ITER=2 FAIL_SIG_LIMIT=99 flows/fanqie-loop.sh` | 2 |
| loop 無進度 | `DRY_RUN=1 STATE=/tmp/ks2 AGENT_CMD=/tmp/stub-noop.sh flows/fanqie-loop.sh`（resume） | 3（NO PROGRESS） |
| loop guard KILL | `DRY_RUN=1 STATE=/tmp/ks2 AGENT_CMD=/tmp/stub-guardkill.sh flows/fanqie-loop.sh` | 3（[FAIL] guard） |
| loop 同 signature 重現 | `DRY_RUN=1 STATE=/tmp/ks-sig AGENT_CMD=/tmp/stub-comment.sh flows/fanqie-loop.sh`（每輪加註解、命中不變；副本 /tmp/koktai-sigtest） | 3（iter 2：同一 failure signature 第 2 次） |
| loop verifier 缺損 | `DRY_RUN=1 STATE=/tmp/ks4 AGENT_CMD=/tmp/stub-noop.sh VERIFY=/nonexistent flows/fanqie-loop.sh` | 4 |
| loop intent 未簽 | `STATE=/tmp/ks5 AGENT_CMD=/tmp/stub-noop.sh flows/fanqie-loop.sh`（無 DRY_RUN） | 5 |

備註：macOS 無 `timeout(1)` 時腳本內建 bash watchdog fallback；host 有
timeout(1) 則優先用之。
