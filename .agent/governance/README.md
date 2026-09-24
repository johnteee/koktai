# koktai 治理合約（governance slice）

本目錄是 fanqie 反切 `sim_tl` 命中率改進任務的治理面：提案、授權、效應、驗收四權
分立的靜態合約。這些檔案只描述「應該由誰把關」——真正執行把關的是 host
（codex 沙箱、git、checks/ 腳本、人類 control-owner），不是這些檔案本身。

## 四權分立（Four-Power Split）

| 權力 | 持有者 | 對應產物 |
| --- | --- | --- |
| 提案 Proposal | codex worker（`koktai-bounded-worker.md`） | 改 `a-tsioh_sandbox/build_unified_index.py` 的 diff 提案＋唯讀 triage 報告 |
| 授權 Authorization | 人類 control-owner：簽署 intent＋envelope | `capability-token.json`（lease 綁定）＋`.agent/delivery/envelope.yaml` |
| 效應 Effect | host（codex sandbox＋git）——沒有 broker | `effect-receipt.json`（模板；無 broker 簽發即自述） |
| 驗收 Acceptance | checks 驗證器＋具名 accepter | `acceptance-ladder.yaml`、`checks/verify.sh`、`checks/fanqie-target.sh` |

交接說明（handover）：worker 只准提案與受限執行（workspace 寫入僅
`a-tsioh_sandbox/build_unified_index.py`，其餘寫 repo 外 scratch）；任何寫入在發生
當下都不被阻擋，授權靠人類簽署的 intent＋envelope 事前框定，驗收靠每輪 loop 的
guard/scope/unittest/build-index/index-parity/hit-rate 事後驗證，具名 accepter
關閉驗收。`git` 歷史是唯一的 durable 記錄；沒有 append-only receipt store。

## 閘門厚度（Gate 2.0，按效應風險）

| 效應 | 厚度 | 理由 |
| --- | --- | --- |
| 改 `build_unified_index.py`（可逆、可 diff、可重建驗證） | 薄：loop 內自動，但每輪 guard＋scope＋測試驗證 | 低傳播、可 rollback、有機器證據 |
| `git commit/push` | 厚：must-approve（pause_actions） | 不可逆傳播（push 出去收不回） |
| 覆寫已入庫的 `index/` 或 `json/` | 厚：must-approve | 破壞 AC2 位元再現性基線 |
| 改 ExternalRef/ 或 `a-tsioh_sandbox/data/*.json` 先驗表 | 厚：must-approve | 改 oracle 地基，驗收即失效 |
| 新增依賴 / 網路存取 | 厚：must-approve | 外部傳播＋供應鏈風險 |
| 改憲法路徑（`.agent/**`、checks/、acceptance.yaml、tests） | 拒絕：worker 不得碰，guard 事後 FAIL＋escalate | 控制平面完整性 |

## Host 前提（preconditions）狀態

| 前提 | 狀態 | 證據 |
| --- | --- | --- |
| effect broker（簽發 receipt、阻擋越權寫入） | unmet | 不存在；codex `-s workspace-write` 擋不住 workdir 內子路徑 |
| policy engine（執行期強制 capability） | unmet | 只有靜態 token JSON，無執行期檢查 |
| verifier（guard/scope/verify.sh/fanqie-target.sh） | met | 已在 repo，可執行；mutation run 見 mutation-suite.yaml |
| approval gate（人類決策通道） | unknown | 等人類 control-owner 簽署 intent；通道存在但尚未行使 |
| budget enforcer | unmet | effect-budget.yaml 只是數字，loop 腳本（另一切片）才會讀它 |
| append-only receipt store | unmet | 只有 `git` 歷史是 durable 記錄 |

## 已知未接線的繞道（unwired bypasses）

- `direct_codex_exec_via_hook`：任何能直接呼叫 `codex exec`（或掛 hook 觸發）的路徑
  都繞過 `run-codex.sh` 與全部合約——本目錄沒有能力阻止，只能靠人類不這樣做。
- `worker_edits_checks_before_guard_snapshot`：若 worker 在 loop 第一輪 guard
  `--snapshot` 之前先改了 `checks/koktai_checks.py`（憲法路徑），快照會把「已污染」
  的 checks 當成基線，之後的 `--check` 全 PASS。緩解：快照必須由人類在乾淨樹上先取。
- `protected_file_copied_to_unprotected_path`：憲法檔複本外流到允許路徑時 guard
  看不見（實測 exit 0），只靠 scope 攔截；mutation-suite.yaml M3 有實測記錄。
- receipt 自簽：寫進 repo 的任何 receipt 都是 self-report（effect-receipt.json 頂層註記）。

## 十五不變量對照（Fifteen-Invariant Checklist）

使用正典不變量名稱；每列一個產出物。

| emitted_object | invariant(s) | host_enforcer | evidence_now | unwired_obligation |
| --- | --- | --- | --- | --- |
| `koktai-bounded-worker.md` | model-output≠effect、subagent-report-is-untrusted、escalation-not-absorbed | 人類審 wrapper＋codex 沙箱 | 檔案存在、三不條款＋prompt 防禦行齊 | 沙箱不擋子路徑；靠 guard/scope 事後偵測 |
| `run-codex.sh` | model-output≠effect、scope-string≠scope | host 以此 script 調 codex（`AGENT_CMD`） | `bash -n` 過；stub 成功路徑只印最終訊息；壞 mode exit 64 | hook 繞道（`direct_codex_exec_via_hook`）仍可能 |
| `escalate.yaml` | escalation-not-absorbed、新述詞 authorization-is-a-lease | loop 腳本每輪判讀（另一切片） | YAML 可解析；述詞含 ytenx pin 與 avg-cand 上限 | 本檔不執行；判讀接線在 flows 切片 |
| `capability-token.json` | authorization-is-a-lease、scope-string≠scope、authority-monotone-down-the-chain | 無（無 policy engine；state_predicate 靠 loop 比對） | JSON 可解析；flat 結構＋state_predicate 齊 | broker 正規化路徑＋執行期重驗不存在 |
| `effect-receipt.json` | model-output≠effect、approval≠evidence、exec-success≠goal-success、audit≠accountability | 無 broker（unmet） | 模板可解析；`issued_by: broker`＋自述警告齊 | broker-owned store 與完整性證據缺失 |
| `effect-budget.yaml` | new-session≠new-auth | loop 腳本計數（另一切片；host 尚無 enforcer） | YAML 可解析；lease 鍵＋cross-purpose 上限與 envelope 一致 | budget enforcer 未接線 |
| `approval.yaml` | approval≠evidence、authority-monotone-down-the-chain | 人類 control-owner 於流程外簽署 | 模板可解析；decision pending、approver 空白待填 | 人類決策通道尚未行使（unknown） |
| `acceptance-ladder.yaml` | exec-success≠goal-success、review≠evidence | checks/verify.sh＋fanqie-target.sh＋具名 accepter | YAML 可解析；L0–L5 對應具體 koktai 檢查 | L5 具名 accepter 尚未指派 |
| `mutation-suite.yaml` | control-effective-under-full-disclosure、role-sep≠failure-independence | `checks/koktai_checks.py` guard/scope（host 執行） | 三案實測 exit 碼已記錄（事後偵測，非寫入前阻擋） | 阻擋仍缺失；快照前污染缺口仍在 |
| `constitutional.yaml`（既有，引用） | authority-monotone-down-the-chain、risk-class-is-a-proposal | guard 事後雜湊比對（detection-only） | guard `--snapshot` 仍可解析本檔 | 寫入前阻擋需 host 權限模式 |

## 省略的條件產物（conditional artifacts omitted）

- `approver_canary`：觸發條件是需要量測「攔截率 vs 真實違規」的合規主張；缺 host
  canary runner（無合成違規注入器），故省略。
- `conformance_suite`：觸發條件是把 worker 當可替換商品（換模型/換 CLI）；目前只用
  codex 單一後端，缺多後端比對 runner，故省略。
- `checker_profile`：觸發條件是高風險驗收需要語義軸＋反操縱軸的低相關檢查器評分；
  無校準過的 benchmark 分數可填，故省略。
- experiment 檔（H1–H6 preregistration）：觸發條件是真的要跑治理實驗；本次只是
  first-task scaffold，故省略。

## 檔案清單

`README.md`（本檔）、`constitutional.yaml`（既有）、`koktai-bounded-worker.md`、
`run-codex.sh`、`escalate.yaml`、`capability-token.json`、`effect-receipt.json`、
`effect-budget.yaml`、`approval.yaml`、`acceptance-ladder.yaml`、`mutation-suite.yaml`。

**Governance status:** artifact-complete
