#!/usr/bin/env bash
# verify-triage.sh — fanqie-miss-triage 合併閘門（決定性，無模型判斷）。
# 用法：verify-triage.sh <final.md> <MANIFEST.tsv>
# 結束碼：0 通過／1 閘門未過／4 用法或檔案缺損。
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <final.md> <MANIFEST.tsv>" >&2; exit 4
fi
FINAL="$1"; MANIFEST="$2"
[ -f "$MANIFEST" ] || { echo "manifest 不存在：$MANIFEST" >&2; exit 4; }

fail() { echo "verify-triage: $1" >&2; exit 1; }

# 非空
[ -s "$FINAL" ] || fail "final.md 為空或不存在"

# 必備章節標題
for h in '## 假說' '## 證據' '## 建議修改' '## 風險'; do
  grep -qF "$h" "$FINAL" || fail "缺少標題 $h"
done

# 無佔位文字
if grep -qiE 'TODO|TBD|PLACEHOLDER' "$FINAL"; then
  fail "含 TODO/TBD/PLACEHOLDER"
fi

# 至少引用一個 manifest 中實際存在的 miss-NN 檔名
cited="$(grep -oE 'miss-[0-9]+' "$FINAL" | sort -u || true)"
[ -n "$cited" ] || fail "未引用任何 miss-NN"
found=0
for m in $cited; do
  if grep -qF "$m" "$MANIFEST"; then found=1; break; fi
done
[ "$found" -eq 1 ] || fail "引用的 miss-NN 皆不在 manifest：$cited"

# 每個建議須交代候選數影響：決定性近似 = 全文須出現「平均候選」
grep -qF '平均候選' "$FINAL" || fail "未交代候選數影響（缺「平均候選」）"

echo "verify-triage: PASS"
exit 0
