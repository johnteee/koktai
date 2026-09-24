#!/usr/bin/env bash
# fanqie-loop 真值層（flows/fanqie-loop.sh 的 VERIFY）：結束碼 0 = 目標達成且未越界。
# 需要環境變數（由 fanqie-loop.sh 在 loop 開始時建立）：
#   KOKTAI_SCRATCH   repo 外 scratch，內含已重建的 json/（26 卷）
#   KOKTAI_GUARD     guard 快照（憲法路徑雜湊）
#   KOKTAI_SCOPE     scope 基線（loop 開始時既有的工作樹變動）
# 門檻只從 .agent/delivery/envelope.yaml loop_targets 讀；此檔與 envelope 皆為憲法路徑。
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
: "${KOKTAI_SCRATCH:?}" "${KOKTAI_GUARD:?}" "${KOKTAI_SCOPE:?}"
ALLOW="a-tsioh_sandbox/build_unified_index.py,a-tsioh_sandbox/__pycache__/*"
C="python3 checks/koktai_checks.py"

$C guard --check "$KOKTAI_GUARD"                           || exit $?
$C scope --check "$KOKTAI_SCOPE" --allow "$ALLOW"          || exit $?
$C unittest --min-tests 13                                 || exit $?
rm -rf "$KOKTAI_SCRATCH/index"
$C build-index                                             || exit $?
$C index-parity --ref HEAD --allow mc,pingshui             || exit $?
$C hit-rate --targets .agent/delivery/envelope.yaml        || exit $?
