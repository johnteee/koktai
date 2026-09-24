#!/usr/bin/env bash
# koktai doctor：環境與快速冒煙（約 1 秒）。結束碼 0 健康／2 harness failure。
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
YTENX="${YTENX:-$HOME/dev/ytenx}"
PIN_YTENX="5f085b0cf4019b1dc10d120cfc62bbf6fcfd87fe"
bad=0
ok()   { printf '[ok]   %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*"; }
die()  { printf '[HARNESS] %s\n' "$*"; bad=1; }

command -v python3 >/dev/null && ok "python3 $(python3 -c 'import sys;print(sys.version.split()[0])')" || die "python3 不在 PATH"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null || die "需要 Python ≥ 3.8"
perl -MEncode -e1 2>/dev/null && ok "perl + Encode" || die "perl 或 Encode 模組缺席"
command -v git >/dev/null && git rev-parse --git-dir >/dev/null 2>&1 && ok "git repo $(git rev-parse --short HEAD)" || die "不在 git repo"

n_dic=$(ls beta??k*.dic 2>/dev/null | wc -l | tr -d ' ')
[ "$n_dic" = 26 ] && ok "26 卷 .dic" || die "beta??k*.dic 應 26 檔，得 $n_dic"

if [ -f "$YTENX/ytenx/sync/kyonh/SieuxYonh.txt" ] && [ -f "$YTENX/ytenx/sync/tcenghyonhtsen/SieuxYonh.txt" ]; then
  cur=$(git -C "$YTENX" rev-parse HEAD 2>/dev/null || echo unknown)
  [ "$cur" = "$PIN_YTENX" ] && ok "ytenx $YTENX @ ${cur:0:8}" \
    || warn "ytenx @ ${cur:0:8} ≠ 釘選 ${PIN_YTENX:0:8}；AC2 差異先當 harness 查"
else
  die "ytenx 資料缺席：$YTENX/ytenx/sync/{kyonh,tcenghyonhtsen}/SieuxYonh.txt（設 YTENX=路徑）"
fi
[ "${YTENX}" = "$HOME/dev/ytenx" ] || warn "test_join_fanqie.py 寫死 ~/dev/ytenx；YTENX 覆寫只影響 build-index"

n_csv=$(ls ExternalRef/ChhoeTaigiDatabase/*.csv 2>/dev/null | wc -l | tr -d ' ')
[ "$n_csv" = 11 ] && ok "ChhoeTaigi CSV 11 部" || die "ChhoeTaigi CSV 應 11 檔，得 $n_csv"
for f in "ExternalRef/詞彙比較表.ods" ExternalRef/chhian-kim-pho2.md a-tsioh_sandbox/data/literature_extra_chars.txt \
         a-tsioh_sandbox/data/pingshui_tl.json a-tsioh_sandbox/data/kuangx_pingshui.json font/m3.json font/k.json; do
  [ -f "$f" ] || die "缺 $f"
done
ls ExternalRef/sinsu120_*.ods ExternalRef/kiongtongsu350_*.ods ExternalRef/siokgan40_*.ods >/dev/null 2>&1 \
  && ok "外部源（詞彙比較/附錄/千金譜/資料表）齊" || die "教育部附錄 ods 缺席"

for f in unified_phonology.json han_to_tl.tsv tl_to_han.tsv chhoetaigi_gaps.tsv; do
  git cat-file -e "HEAD:index/$f" 2>/dev/null || die "HEAD 無 index/${f}（AC2 oracle 缺）"
done
git diff --quiet HEAD -- index/ 2>/dev/null && ok "index/ 與 HEAD 一致" \
  || warn "index/ 工作樹與 HEAD 不同；AC2 以 HEAD 為準"
n_json=$(ls json/??.json 2>/dev/null | wc -l | tr -d ' ')
[ "$n_json" = 26 ] && ok "json/ 26 卷（本機產物，未入 git）" || warn "json/ 只有 $n_json 卷；verify 會在 scratch 重建，不依賴 json/"
[ -w acceptance.yaml ] && warn "acceptance.yaml 可寫；應為 0444（chmod 444 acceptance.yaml）" || ok "acceptance.yaml 唯讀"

python3 checks/koktai_checks.py unittest --min-tests 13 || bad=1
[ "$bad" = 0 ] && { echo "doctor: healthy"; exit 0; } || { echo "doctor: HARNESS failure"; exit 2; }
