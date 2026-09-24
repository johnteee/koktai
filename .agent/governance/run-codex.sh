#!/usr/bin/env bash
# run-codex.sh：呼叫 codex worker 的共享 run 介面（governance 切片擁有）。
#
# 用法：
#   .agent/governance/run-codex.sh <read-only|workspace-write> <workdir> <prompt-file> [model] [effort]
#
# 語意（與各 flow 共用的合約）：
# - 以 `codex exec -s <mode> -C <workdir> [-m model] [-c model_reasoning_effort=<effort>] -o <tmpfile> -`
#   呼叫 codex，prompt 檔內容經 stdin 傳入（`-`）；codex 進度輸出保留在 stderr；
#   stdout 只印出最終 agent 訊息（tmpfile 內容）。
# - 未知的 mode 拒絕並以 exit 64 離開；codex 失敗或訊息為空時以非零值離開。
# - 空的選填參數（model / effort）沿用 codex 組態，不傳對應旗標。
#
# 誠實聲明：codex `-s workspace-write` 沙箱把寫入限制在 workdir+tmp，
# 但無法拒絕 workdir 內子路徑（如 checks/）；deny-write 只靠事後偵測
#（checks/koktai_checks.py guard + scope），此 script 不提供寫入前阻擋。
set -uo pipefail

MODE="${1:-}"
WORKDIR="${2:-}"
PROMPT_FILE="${3:-}"
MODEL="${4:-}"
EFFORT="${5:-}"

usage() {
  echo "usage: run-codex.sh <read-only|workspace-write> <workdir> <prompt-file> [model] [effort]" >&2
}

if [ "$MODE" != "read-only" ] && [ "$MODE" != "workspace-write" ]; then
  usage
  echo "run-codex.sh: unknown mode '$MODE' (want read-only|workspace-write)" >&2
  exit 64
fi

if [ -z "$WORKDIR" ] || [ ! -d "$WORKDIR" ]; then
  usage
  echo "run-codex.sh: workdir not found: '$WORKDIR'" >&2
  exit 66
fi

if [ -z "$PROMPT_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
  usage
  echo "run-codex.sh: prompt file not found: '$PROMPT_FILE'" >&2
  exit 66
fi

TMPFILE=""
cleanup() {
  if [ -n "$TMPFILE" ] && [ -f "$TMPFILE" ]; then
    rm -f "$TMPFILE"
  fi
}
trap cleanup EXIT

TMPFILE="$(mktemp "${TMPDIR:-/tmp}/koktai-run-codex.XXXXXX")" || exit 70
if [ ! -f "$TMPFILE" ]; then
  echo "run-codex.sh: cannot create temp file" >&2
  exit 70
fi

ARGS=(exec -s "$MODE" -C "$WORKDIR")
if [ -n "$MODEL" ]; then
  ARGS=("${ARGS[@]}" -m "$MODEL")
fi
if [ -n "$EFFORT" ]; then
  ARGS=("${ARGS[@]}" -c "model_reasoning_effort=$EFFORT")
fi
ARGS=("${ARGS[@]}" -o "$TMPFILE" -)

# codex 自身輸出（進度/事件）導向 stderr；stdout 只保留最終訊息。
CODE=0
codex "${ARGS[@]}" <"$PROMPT_FILE" >&2 || CODE=$?
if [ "$CODE" -ne 0 ]; then
  echo "run-codex.sh: codex failed with exit $CODE" >&2
  exit "$CODE"
fi

if [ ! -s "$TMPFILE" ]; then
  echo "run-codex.sh: codex returned an empty final message" >&2
  exit 71
fi

cat "$TMPFILE"
