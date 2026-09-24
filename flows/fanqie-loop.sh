#!/usr/bin/env bash
# generated-by: flow-loop-harness / verify-gated-fix-loop / 2026-09-24 / dry-run-verified
# fanqie-loop.sh — 反切 sim_tl 命中率修復迴圈；loop body 只准改
# a-tsioh_sandbox/build_unified_index.py，直到 checks/fanqie-target.sh 通過。
#
# 結束碼：0 verifier 通過（目標達成）
#         2 MAX_ITER 用罄仍未達標（human 決定下一步，非軟成功）
#         3 kill 條件：guard/scope/HARNESS、同一 failure signature 達上限、或無進度
#         4 verifier 缺損/不可執行、缺 timeout(1)、bootstrap harness 失敗
#         5 intent gate：.agent/delivery/intent-record.yaml 未簽署（非 dry run）
#
# 用法：flows/fanqie-loop.sh
#   覆寫：STATE=... AGENT_CMD='...' VERIFY=... MAX_ITER=6 FAIL_SIG_LIMIT=2
#         CALL_TIMEOUT=1800 TRIAGE=/path/final.md DRY_RUN=1
#   dry run：DRY_RUN=1 且 AGENT_CMD 明示指向 stub → 略過 intent gate，ledger 記 DRY RUN。
set -euo pipefail
cd "$(dirname "$0")/.." || exit 4
REPO_ROOT="$(pwd -P)"

# ---- 1. Config header ----
# 權限邊界：loop body 走 workspace-write，但憲法路徑（checks/、.agent/、flows/、
# acceptance.yaml、test_*.py）由 host 權限模式排除寫入；guard/scope 為事後偵測。
AGENT_CMD_SET="${AGENT_CMD:+1}"
AGENT_CMD="${AGENT_CMD:-$REPO_ROOT/.agent/governance/run-codex.sh workspace-write $REPO_ROOT}"
VERIFY="${VERIFY:-$REPO_ROOT/checks/fanqie-target.sh}"   # 真值層：exit 0 = 達標
ENVELOPE="${ENVELOPE:-$REPO_ROOT/.agent/delivery/envelope.yaml}"
INTENT="${INTENT:-$REPO_ROOT/.agent/delivery/intent-record.yaml}"
TRIAGE="${TRIAGE:-}"                                    # 可選：triage final.md 餵入 prompt
tmp="${TMPDIR:-/tmp}"
STATE="${STATE:-${tmp%/}/koktai-fanqie-loop}"
export KOKTAI_SCRATCH="$STATE/scratch"                  # repo 外：重建 json/ 與 index/
export KOKTAI_GUARD="$STATE/guard.json"                 # 憲法路徑雜湊快照
export KOKTAI_SCOPE="$STATE/scope.json"                 # loop 開始時工作樹變動基線

env_val() { # $1=envelope 扁平 key $2=default
  local v
  v="$(awk -v k="$1" '$1 == k":" {print $2; exit}' "$ENVELOPE" 2>/dev/null || true)"
  printf '%s' "${v:-$2}"
}
MAX_ITER="${MAX_ITER:-$(env_val max_iterations 6)}"
CALL_TIMEOUT="${CALL_TIMEOUT:-$(env_val per_call_timeout_seconds 1800)}"
FAIL_SIG_LIMIT="${FAIL_SIG_LIMIT:-$(env_val failure_signature_limit 2)}"
# 總預算：至多 MAX_ITER 次 agent 呼叫 × CALL_TIMEOUT 秒 + 每輪一次 verifier。

# ---- 2. State directory / ledger ----
mkdir -p "$STATE"
LEDGER="$STATE/ledger.md"; touch "$LEDGER"
log() { printf '%s %s\n' "$(date +%T)" "$*" >> "$STATE/flow.log"; }

# ---- Intent gate（side-effectful flow；DRY_RUN 僅在 AGENT_CMD 明示時放行）----
if ! grep -q '^status: signed' "$INTENT" 2>/dev/null; then
  if [ "${DRY_RUN:-0}" = "1" ] && [ -n "$AGENT_CMD_SET" ]; then
    echo "- DRY RUN $(date -u +%Y-%m-%dT%H:%M:%SZ)（intent 未簽署，stub agent）" >> "$LEDGER"
  else
    echo "intent gate: $INTENT 未簽署（status: signed）；DRY_RUN=1 + 明示 AGENT_CMD 可略過" >&2
    exit 5
  fi
fi

# ---- Preflight（harness 級缺損 → 4）----
[ -f "$VERIFY" ] || { echo "verifier 不存在：$VERIFY" >&2; exit 4; }
[ -x "$VERIFY" ] || { echo "verifier 不可執行：$VERIFY" >&2; exit 4; }
[ -f "$ENVELOPE" ] || { echo "envelope 不存在：$ENVELOPE" >&2; exit 4; }
[ -f "$REPO_ROOT/flows/prompts/fanqie-fix.md" ] || { echo "缺 flows/prompts/fanqie-fix.md" >&2; exit 4; }
if [ -n "$TRIAGE" ] && [ ! -f "$TRIAGE" ]; then
  echo "TRIAGE 檔不存在：$TRIAGE" >&2; exit 4
fi
command -v timeout >/dev/null 2>&1 || {
  # stock macOS 無 timeout(1)：bash fallback（wall-clock watchdog）
  timeout() { local secs="$1"; shift
    "$@" & local pid=$!
    ( sleep "$secs"; kill "$pid" 2>/dev/null ) & local wd=$!
    wait "$pid" 2>/dev/null; local rc=$?
    kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
    return "$rc"; }
}

# ---- Bootstrap：首次啟動重建 scratch json/ 並拍 guard/scope 基線；resume 沿用 ----
if [ ! -f "$KOKTAI_GUARD" ] || [ ! -f "$KOKTAI_SCOPE" ] || [ ! -d "$KOKTAI_SCRATCH/json" ]; then
  log "bootstrap: rebuild-json + guard/scope snapshot"
  python3 checks/koktai_checks.py rebuild-json \
    --expect-totals 1446,12857,43913,11002 > "$STATE/bootstrap.log" 2>&1 || {
      cat "$STATE/bootstrap.log" >&2; echo "bootstrap rebuild-json 失敗" >&2; exit 4; }
  python3 checks/koktai_checks.py guard --snapshot "$KOKTAI_GUARD" >> "$STATE/bootstrap.log" 2>&1 || {
    echo "bootstrap guard snapshot 失敗" >&2; exit 4; }
  python3 checks/koktai_checks.py scope --snapshot "$KOKTAI_SCOPE" >> "$STATE/bootstrap.log" 2>&1 || {
    echo "bootstrap scope snapshot 失敗" >&2; exit 4; }
else
  echo "- RESUMED $(date -u +%Y-%m-%dT%H:%M:%SZ)（沿用既有 scratch/guard/scope 基線）" >> "$LEDGER"
fi

# ---- Verifier wrapper：保留輸出供 prompt 與 kill 分類 ----
VERIFY_EC=0
check() {
  VERIFY_EC=0
  "$VERIFY" > "$STATE/verify-out.txt" 2>&1 || VERIFY_EC=$?
  return "$VERIFY_EC"
}

# kill 分類：guard/scope FAIL 或任何 HARNESS 行 → 憲法/harness 層問題，立即停
classify_kill() {
  grep -qE '^\[FAIL\] (guard|scope):' "$STATE/verify-out.txt" && return 0
  grep -qE '^\[HARNESS\]' "$STATE/verify-out.txt" && return 0
  return 1
}

# failure signature：第一個 [FAIL] <name>: 行原文（含數字）。數字不遮罩：命中率未達標是
# 每輪都會出現的同類失敗，遮罩後會把「有進步但仍未達標」誤判成重複；保留數字時，
# 只有「改了程式、結果一字不差」（同測試同失敗、同命中數）才算重複 signature。
signature() {
  grep -m1 -E '^\[FAIL\] [^:]+:' "$STATE/verify-out.txt" || true
}

# 進度偵測：git 追蹤 diff stat + 未追蹤檔數（STATE 在 repo 外，不需排除）
snapshot() {
  if git rev-parse --git-dir >/dev/null 2>&1; then
    printf '%s +u%s' "$(git diff HEAD --stat | tail -n1)" \
      "$(git ls-files -o --exclude-standard | wc -l | tr -d ' ')"
  else
    if [ -s "$STATE/verify-out.txt" ]; then cksum < "$STATE/verify-out.txt"; else echo "no-signal-$RANDOM"; fi
  fi
}

# ---- 第 0 次驗證：可能已達標 ----
if check; then echo "already verified"; exit 0; fi
if classify_kill; then
  cat "$STATE/verify-out.txt" >&2
  echo "- preflight: KILL（guard/scope/HARNESS）" >> "$LEDGER"; exit 3
fi

prev="$(snapshot)"
prev_sig=""        # 只與「上一輪 iteration」的 signature 比對；preflight 不算一輪
sig_count=0

for i in $(seq 1 "$MAX_ITER"); do
  {
    cat flows/prompts/fanqie-fix.md
    echo; echo "## Ledger tail"; tail -n 20 "$LEDGER"
    echo; echo "## Verifier output"; cat "$STATE/verify-out.txt"
    if [ -n "$TRIAGE" ]; then echo; echo "## Triage"; cat "$TRIAGE"; fi
  } > "$STATE/iter-$i-prompt.md"

  log "iter $i agent call"
  timeout "$CALL_TIMEOUT" $AGENT_CMD "$STATE/iter-$i-prompt.md" \
    > "$STATE/iter-$i-out.md" || true

  if check; then
    echo "- iter $i: VERIFIED" >> "$LEDGER"; exit 0
  fi

  if classify_kill; then
    cat "$STATE/verify-out.txt" >&2
    echo "- iter $i: KILL（guard/scope/HARNESS）" >> "$LEDGER"; exit 3
  fi

  cur="$(snapshot)"
  sig="$(signature)"
  if [ "$sig" = "$prev_sig" ]; then
    sig_count=$((sig_count+1))
  else
    sig_count=1; prev_sig="$sig"
  fi
  echo "- iter $i: not verified; sig: ${sig:-none} (x$sig_count); progress: ${cur:-none}" >> "$LEDGER"

  if [ "$sig_count" -ge "$FAIL_SIG_LIMIT" ]; then
    echo "- iter $i: 同一 failure signature 第 ${sig_count} 次（≥${FAIL_SIG_LIMIT}），停止" >> "$LEDGER"
    exit 3
  fi
  if [ "$cur" = "$prev" ]; then
    echo "- iter $i: NO PROGRESS, aborting" >> "$LEDGER"; exit 3
  fi
  prev="$cur"
done
echo "- cap $MAX_ITER exhausted" >> "$LEDGER"; exit 2
