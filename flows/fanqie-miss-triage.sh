#!/usr/bin/env bash
# generated-by: flow-control-generator / parallel-fan-out-fan-in / 2026-09-24 / dry-run-verified
# fanqie-miss-triage.sh — 反切未命中分桶診斷（唯讀 agents，不修改 repo）。
#
# 拓撲：Stage0 決定性分桶（hit-rate --dump-misses）
#       → fan-out：前 MAX_BRANCHES 個 join.method 桶各一個唯讀診斷 agent（並行上限 MAX_JOBS）
#       → fan-in：單一合成 agent → flows/checks/verify-triage.sh 合併閘門。
#
# 結束碼：0 完成（final.md 通過合併閘門）
#         2 閘門失敗（無 bucket、分支失敗/未達 quorum、合成失敗、合併閘門未過）
#         4 harness（缺 index/envelope/prompt/timeout、stage0 harness 失敗）
#
# 用法：flows/fanqie-miss-triage.sh
#   覆寫：STATE=... AGENT_CMD='...' MAX_BRANCHES=8 MAX_JOBS=4 ROWS=150 MIN_OK= INDEX=...
set -euo pipefail
cd "$(dirname "$0")/.." || exit 4
REPO_ROOT="$(pwd -P)"

# ---- 1. Config header ----
# 唯讀權限邊界：agents 一律走 read-only 模式（run-codex.sh read-only）。
AGENT_CMD="${AGENT_CMD:-$REPO_ROOT/.agent/governance/run-codex.sh read-only $REPO_ROOT}"
ENVELOPE="${ENVELOPE:-$REPO_ROOT/.agent/delivery/envelope.yaml}"
INDEX="${INDEX:-$REPO_ROOT/index/unified_phonology.json}"
tmp="${TMPDIR:-/tmp}"
STATE="${STATE:-${tmp%/}/koktai-fanqie-miss-triage}"
MIN_OK="${MIN_OK:-}"          # quorum：空 = strict（任一分支失敗即中止）
ROWS="${ROWS:-150}"           # 每桶餵給 agent 的未命中列數上限

env_val() { # $1=envelope 扁平 key $2=default
  local v
  v="$(awk -v k="$1" '$1 == k":" {print $2; exit}' "$ENVELOPE" 2>/dev/null || true)"
  printf '%s' "${v:-$2}"
}
MAX_BRANCHES="${MAX_BRANCHES:-$(env_val max_triage_branches 8)}"
MAX_JOBS="${MAX_JOBS:-$(env_val max_parallel_agents 4)}"
CALL_TIMEOUT="${CALL_TIMEOUT:-$(env_val per_call_timeout_seconds 1800)}"
# 總預算：MAX_BRANCHES 分支 + 1 合成，各 ≤ CALL_TIMEOUT 秒（並行所以牆鐘上限約
# ceil(MAX_BRANCHES/MAX_JOBS+1) × CALL_TIMEOUT）。

# ---- 2. State directory ----
mkdir -p "$STATE"
log() { printf '%s %s\n' "$(date +%T)" "$*" >> "$STATE/flow.log"; }
log "triage start state=$STATE branches=$MAX_BRANCHES jobs=$MAX_JOBS rows=$ROWS"

# ---- preflight（harness 級缺損 → 4）----
[ -f "$INDEX" ]    || { echo "index 不存在：$INDEX" >&2; exit 4; }
command -v timeout >/dev/null 2>&1 || {
  # stock macOS 無 timeout(1)：bash fallback（wall-clock watchdog）
  timeout() { local secs="$1"; shift
    "$@" & local pid=$!
    ( sleep "$secs"; kill "$pid" 2>/dev/null ) & local wd=$!
    wait "$pid" 2>/dev/null; local rc=$?
    kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
    return "$rc"; }
}
for f in flows/prompts/triage-branch.md flows/prompts/triage-synthesize.md \
         flows/checks/verify-triage.sh; do
  [ -f "$REPO_ROOT/$f" ] || { echo "缺少 $f" >&2; exit 4; }
done

# ---- 3. Runner abstraction：所有 agent 呼叫只走這裡 ----
run_agent() { # $1=prompt-file $2=out-file；失敗或空輸出 → 刪檔回傳 1
  log "start $1"
  if timeout "$CALL_TIMEOUT" $AGENT_CMD "$1" > "$2" && [ -s "$2" ]; then
    log "done  $1 -> $2"
    return 0
  fi
  rm -f "$2"
  log "fail  $1"
  return 1
}

# ---- Stage 0：決定性分桶 ----
mkdir -p "$STATE/buckets"
ec=0
python3 checks/koktai_checks.py hit-rate --index "$INDEX" \
  --dump-misses "$STATE/buckets" > "$STATE/stage0-hit-rate.txt" 2>&1 || ec=$?
cat "$STATE/stage0-hit-rate.txt"
log "stage0 hit-rate exit=$ec"
if [ "$ec" -eq 2 ]; then echo "stage0 harness failure" >&2; exit 4; fi

MANIFEST="$STATE/buckets/MANIFEST.tsv"
buckets="$(awk -F'\t' 'NR>1 && NF>=3 {print $1}' "$MANIFEST" 2>/dev/null || true)"
# gate：manifest 至少 1 桶（0 桶 = 無未命中，無分診標的，以閘門失敗回報）
if [ -z "$buckets" ]; then
  echo "gate: manifest 無 bucket（無未命中可診斷）" >&2; exit 2
fi

# ---- Fan-out：每桶一個唯讀診斷 agent ----
rm -f "$STATE"/fan-*.md        # 清掉上一輪殘留，避免舊輸出滿足閘門
FAILED=0
wave_wait() { local pid; for pid in "$@"; do wait "$pid" || FAILED=$((FAILED+1)); done; }
pids=(); i=0; n=0
for b in $buckets; do
  n=$((n+1))
  if [ "$n" -gt "$MAX_BRANCHES" ]; then break; fi
  bfile="$STATE/buckets/$b"
  if [ ! -f "$bfile" ]; then echo "manifest 列出但缺檔：$b" >&2; exit 4; fi
  prompt="$STATE/bprompt-${b%.tsv}.md"
  {
    cat flows/prompts/triage-branch.md
    echo; echo "## Bucket"
    head -n 2 "$bfile"
    echo; echo "## 未命中列（前 $ROWS 列）"
    tail -n +3 "$bfile" | head -n "$ROWS"
  } > "$prompt"
  run_agent "$prompt" "$STATE/fan-${b%.tsv}.md" &
  pids+=($!); i=$((i+1))
  if [ $((i % MAX_JOBS)) -eq 0 ]; then wave_wait "${pids[@]}"; pids=(); fi
done
if [ "${#pids[@]}" -gt 0 ]; then wave_wait "${pids[@]}"; fi   # fan-in barrier（尾波）

# Gate：strict 預設；MIN_OK=N 為明示的部分失敗 quorum，絕不靜默略過
ok=0
for f in "$STATE"/fan-*.md; do
  if [ -e "$f" ] && [ -s "$f" ]; then ok=$((ok+1)); fi
done
log "fan-out done ok=$ok failed=$FAILED"
if [ -n "$MIN_OK" ]; then
  if [ "$ok" -lt "$MIN_OK" ]; then
    echo "quorum not met: $ok < $MIN_OK" >&2; exit 2
  fi
else
  if [ "$FAILED" -ne 0 ] || [ "$ok" -eq 0 ]; then
    echo "branch failures: $FAILED, successful outputs: $ok" >&2; exit 2
  fi
fi

# ---- Fan-in：單一合成 agent + 合併閘門 ----
{
  cat flows/prompts/triage-synthesize.md
  echo; echo "## MANIFEST"; cat "$MANIFEST"
  echo; echo "## 分支診斷"
  for f in "$STATE"/fan-*.md; do
    if [ -e "$f" ]; then echo; echo "### $(basename "$f")"; cat "$f"; fi
  done
} > "$STATE/synth-prompt.md"
if ! run_agent "$STATE/synth-prompt.md" "$STATE/final.md"; then
  echo "synthesis failed" >&2; exit 2
fi
# gate：合併結果的決定性檢核（非只看分支 tally）
if ! flows/checks/verify-triage.sh "$STATE/final.md" "$MANIFEST"; then
  echo "merged gate failed" >&2; exit 2
fi
log "triage complete -> $STATE/final.md"
echo "final: $STATE/final.md"
