#!/usr/bin/env bash
# koktai 驗證全掃：doctor → acceptance.yaml 每個 run: 行依序執行（約 35 秒）。
# 用法：checks/verify.sh            # 全部
#       ONLY=AC4 checks/verify.sh   # 只跑 id 前綴相符的 check（AC2 需先有 AC1 的 scratch）
#       KOKTAI_SCRATCH=/tmp/x checks/verify.sh   # 指定 scratch（須在 repo 外）
# 結束碼：0 全 PASS／1 有 FAIL（無 HARNESS）／2 有 HARNESS（環境不可信，先修 harness）。
# 證據：$KOKTAI_SCRATCH/summary.tsv、各 check 的 *.log、重建 JSON 與索引。
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
tmp="${TMPDIR:-/tmp}"
export KOKTAI_SCRATCH="${KOKTAI_SCRATCH:-$(mktemp -d "${tmp%/}/koktai-verify.XXXXXX")}"
mkdir -p "$KOKTAI_SCRATCH" || exit 2
SUMMARY="$KOKTAI_SCRATCH/summary.tsv"
printf 'id\tstatus\texit\tseconds\n' > "$SUMMARY"
echo "scratch: $KOKTAI_SCRATCH"

if ! checks/doctor.sh > "$KOKTAI_SCRATCH/doctor.log" 2>&1; then
  cat "$KOKTAI_SCRATCH/doctor.log"
  printf 'doctor\tHARNESS\t2\t-\n' >> "$SUMMARY"
  echo "verify: HARNESS (doctor failed)"; exit 2
fi
printf 'doctor\tPASS\t0\t-\n' >> "$SUMMARY"

any_fail=0; any_harness=0; ran=0; id=""
while IFS= read -r line; do
  case "$line" in
    *"- id: "*) id="${line#*- id: }" ;;
    *"run: "*)
      cmd="${line#*run: }"
      case "$id" in "${ONLY:-}"*) ;; *) continue ;; esac
      ran=$((ran+1)); t0=$(date +%s)
      bash -c "$cmd" > "$KOKTAI_SCRATCH/$id.log" 2>&1; ec=$?
      dt=$(( $(date +%s) - t0 ))
      case "$ec" in
        0) st=PASS ;;
        1) st=FAIL; any_fail=1 ;;
        *) st=HARNESS; any_harness=1 ;;
      esac
      printf '%s\t%s\t%s\t%s\n' "$id" "$st" "$ec" "$dt" >> "$SUMMARY"
      printf '%-30s %-8s (%ss)\n' "$id" "$st" "$dt"
      grep -E '^\[(PASS|FAIL|HARNESS)\]' "$KOKTAI_SCRATCH/$id.log" | sed 's/^/    /'
      ;;
  esac
done < acceptance.yaml

[ "$ran" -gt 0 ] || { echo "verify: HARNESS (no checks matched ONLY='${ONLY:-}')"; exit 2; }
if [ "$any_harness" = 1 ]; then echo "verify: HARNESS"; exit 2; fi
if [ "$any_fail" = 1 ]; then echo "verify: FAIL"; exit 1; fi
echo "verify: PASS ($ran checks)"; exit 0
