#!/usr/bin/env python3
"""koktai 驗證檢核（VERIFY.md / acceptance.yaml / flows 共用）。

僅用標準庫；一律在 repo 根目錄執行：python3 checks/koktai_checks.py <子命令> …

結束碼（分類依據，見 VERIFY.md「失敗分類」）：
  0  PASS
  1  FAIL     —— 產物與 oracle 不符（product regression 或 spec/oracle error，需再判）
  2  HARNESS  —— 工具鏈、外部依賴、scratch 狀態缺失（harness failure）
"""

import argparse
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(ROOT, "a-tsioh_sandbox")
INDEX_FILES = ("unified_phonology.json", "han_to_tl.tsv", "tl_to_han.tsv",
               "chhoetaigi_gaps.tsv")
CONSTITUTION = os.path.join(ROOT, ".agent", "governance", "constitutional.yaml")
DIC_STATS_RE = re.compile(
    r"\[dic2json\] 章 (\d+) / 單字 (\d+) / 詞條 (\d+) / 反切 (\d+)")
VOLUMES = [f"{i:02d}" for i in range(1, 27)]


class Harness(Exception):
    """環境/工具失敗：不可歸因於產物。"""


def out(status, name, msg):
    print(f"[{status}] {name}: {msg}")


def need_dir(path, what):
    if not os.path.isdir(path):
        raise Harness(f"{what} 不存在：{path}")


# ------------------------------------------------------------ rebuild-json
def volume_dic(vol):
    hits = sorted(glob.glob(os.path.join(ROOT, f"beta{vol}k*.dic")))
    if len(hits) != 1:
        raise Harness(f"卷 {vol}：beta{vol}k*.dic 應恰一檔，得 {hits}")
    return hits[0]


def cmd_rebuild_json(a):
    jdir = os.path.join(a.scratch, "json")
    os.makedirs(jdir, exist_ok=True)
    totals = [0, 0, 0, 0]
    same = differ = 0
    for vol in VOLUMES:
        dic = volume_dic(vol)
        dst = os.path.join(jdir, f"{vol}.json")
        err = os.path.join(a.scratch, f"{vol}.stderr")
        with open(dst, "wb") as fo, open(err, "wb") as fe:
            p1 = subprocess.Popen(
                ["perl", os.path.join(SANDBOX, "recode_utf8.pl"), dic],
                stdout=subprocess.PIPE, stderr=fe, cwd=ROOT)
            p2 = subprocess.Popen(
                [sys.executable, os.path.join(SANDBOX, "dic2json.py")],
                stdin=p1.stdout, stdout=subprocess.PIPE, stderr=fe, cwd=ROOT)
            p1.stdout.close()
            p3 = subprocess.Popen(
                [sys.executable, os.path.join(SANDBOX, "rt2pronun.py")],
                stdin=p2.stdout, stdout=fo, stderr=fe, cwd=ROOT)
            p2.stdout.close()
            codes = (p3.wait(), p2.wait(), p1.wait())
        if any(codes):
            out("FAIL", "rebuild-json", f"卷 {vol} 管線結束碼 "
                f"recode={codes[2]} dic2json={codes[1]} rt2pronun={codes[0]}；見 {err}")
            return 1
        with open(err, encoding="utf-8", errors="replace") as f:
            m = DIC_STATS_RE.search(f.read())
        if not m:
            out("FAIL", "rebuild-json", f"卷 {vol} stderr 無 [dic2json] 統計行；見 {err}")
            return 1
        for i, v in enumerate(m.groups()):
            totals[i] += int(v)
        try:
            with open(dst, encoding="utf-8") as f:
                fmt = json.load(f).get("format")
        except (json.JSONDecodeError, AttributeError):
            fmt = None
        if fmt != "koktai-dic/2":
            out("FAIL", "rebuild-json", f"卷 {vol} 輸出非 koktai-dic/2 JSON：{dst}")
            return 1
        local = os.path.join(ROOT, "json", f"{vol}.json")
        if os.path.isfile(local):
            if filecmp_bytes(local, dst):
                same += 1
            else:
                differ += 1
                print(f"[info] rebuild-json: 卷 {vol} 與本機 json/{vol}.json 位元不同")
    got = ",".join(map(str, totals))
    print(f"[info] rebuild-json: 本機 json/ 位元相同 {same} 卷、不同 {differ} 卷"
          "（json/ 未入 git，僅診斷）")
    if a.expect_totals and got != a.expect_totals:
        out("FAIL", "rebuild-json",
            f"章,單字,詞條,反切 = {got}，預期 {a.expect_totals}")
        return 1
    out("PASS", "rebuild-json", f"26 卷；章,單字,詞條,反切 = {got}")
    return 0


def filecmp_bytes(p, q):
    if os.path.getsize(p) != os.path.getsize(q):
        return False
    with open(p, "rb") as f, open(q, "rb") as g:
        while True:
            a, b = f.read(1 << 20), g.read(1 << 20)
            if a != b:
                return False
            if not a:
                return True


# ------------------------------------------------------------ build-index
def cmd_build_index(a):
    jglob = os.path.join(a.scratch, "json", "*.json")
    if len(glob.glob(jglob)) != 26:
        raise Harness(f"scratch JSON 不足 26 卷（先跑 rebuild-json）：{jglob}")
    ytenx = os.path.expanduser(a.ytenx)
    need_dir(os.path.join(ytenx, "ytenx", "sync", "kyonh"), "ytenx 資料")
    err = os.path.join(a.scratch, "index.stderr")
    with open(err, "wb") as fe:
        r = subprocess.run(
            [sys.executable, os.path.join(SANDBOX, "build_unified_index.py"),
             "--json", jglob, "--ytenx", ytenx,
             "--out", os.path.join(a.scratch, "index")],
            stderr=fe, cwd=ROOT)
    if r.returncode:
        out("FAIL", "build-index", f"結束碼 {r.returncode}；見 {err}")
        return 1
    missing = [f for f in INDEX_FILES
               if not os.path.isfile(os.path.join(a.scratch, "index", f))]
    if missing:
        out("FAIL", "build-index", f"缺輸出 {missing}")
        return 1
    out("PASS", "build-index", f"{a.scratch}/index（stderr：{err}）")
    return 0


# ------------------------------------------------------------ index-parity
def git_show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                       capture_output=True)
    if r.returncode:
        raise Harness(f"git show {ref}:{path} 失敗：{r.stderr.decode()[:200]}")
    return r.stdout


def strip_allowed(doc, allow):
    for rec in doc.get("han", {}).values():
        for k in allow:
            rec.pop(k, None)
    stats = doc.get("_meta", {}).get("stats", {})
    if "mc" in allow:
        for k in list(stats):
            if k.startswith(("sim_tl", "join_", "extra_char")):
                stats.pop(k)
    return doc


def cmd_index_parity(a):
    idx = os.path.join(a.scratch, "index")
    need_dir(idx, "scratch 索引（先跑 build-index）")
    allow = [k for k in (a.allow or "").split(",") if k]
    bad = []
    for f in INDEX_FILES:
        with open(os.path.join(idx, f), "rb") as fh:
            mine = fh.read()
        gold = git_show(a.ref, f"index/{f}")
        if mine == gold:
            continue
        if allow and f.endswith(".json"):
            if strip_allowed(json.loads(mine), allow) == \
                    strip_allowed(json.loads(gold), allow):
                print(f"[info] index-parity: {f} 僅允許欄位 {allow} 有差")
                continue
        bad.append(f)
    label = f"{a.ref}:index/" + (f"（允許變動：{','.join(allow)}）" if allow else "")
    if bad:
        out("FAIL", "index-parity", f"與 {label} 不同：{bad}")
        return 1
    out("PASS", "index-parity", f"4 檔與 {label} 一致")
    return 0


# ------------------------------------------------------------ unittest
def cmd_unittest(a):
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_join_fanqie"],
        cwd=SANDBOX, capture_output=True, text=True)
    text = r.stderr + r.stdout
    m = re.search(r"^Ran (\d+) tests?", text, re.M)
    if not m:
        raise Harness(f"unittest 無 'Ran N tests' 輸出：{text[-400:]}")
    ran = int(m.group(1))
    skipped = re.search(r"skipped=(\d+)", text)
    if "SkipTest" in text or skipped or re.search(r"\bskipped\b", text):
        raise Harness("unittest 被略過（ytenx 缺席？）：" + text[-300:])
    if r.returncode:
        fails = re.findall(r"^(?:FAIL|ERROR): (\S+)", text, re.M)
        out("FAIL", "unittest", f"{ran} 測試，失敗 {fails}")
        return 1
    if ran < a.min_tests:
        out("FAIL", "unittest", f"只跑 {ran} 測試 < 最低 {a.min_tests}（測試被刪？）")
        return 1
    out("PASS", "unittest", f"{ran} 測試 OK")
    return 0


# ------------------------------------------------------------ poj-gold
def cmd_poj_gold(a):
    ct = os.path.join(ROOT, "ExternalRef", "ChhoeTaigiDatabase")
    need_dir(ct, "ChhoeTaigi CSV")
    sys.path.insert(0, SANDBOX)
    import chhoetaigi  # noqa: E402
    devnull = open(os.devnull, "w")
    saved, sys.stderr = sys.stderr, devnull
    try:
        ok, total, _ = chhoetaigi.validate_poj(ct)
    finally:
        sys.stderr = saved
        devnull.close()
    msg = f"{ok}/{total}（{ok / total:.2%}）"
    if a.total is not None and total != a.total:
        raise Harness(f"黃金對總數 {total} ≠ {a.total}（ChhoeTaigi CSV 版本變動？）")
    if ok < a.min_ok:
        out("FAIL", "poj-gold", f"{msg} < 最低 {a.min_ok}")
        return 1
    out("PASS", "poj-gold", msg)
    return 0


# ------------------------------------------------------------ hit-rate
def literary_gold(rec):
    return {t["tl"] for t in rec.get("taigi", [])
            if any("文" in r for r in t.get("registers", []))
            or "甘文" in t.get("attest", [])}


def measure(doc, dump=None):
    hits = total = cands = 0
    misses = {}
    for ch, rec in doc["han"].items():
        gold = literary_gold(rec)
        for mc in rec.get("mc", []):
            syl = (mc.get("sim_tl") or {}).get("syllables")
            if not syl or not gold:
                continue
            total += 1
            cands += len(syl)
            if gold & set(syl):
                hits += 1
            elif dump is not None:
                method = (mc.get("join") or {}).get("method", "未join")
                misses.setdefault(method, []).append(
                    (ch, mc.get("fanqie") or "", mc.get("yun") or "",
                     " ".join(syl), " ".join(sorted(gold))))
    if dump is not None:
        os.makedirs(dump, exist_ok=True)
        manifest = []
        for i, (method, rows) in enumerate(
                sorted(misses.items(), key=lambda kv: -len(kv[1])), 1):
            name = f"miss-{i:02d}.tsv"
            with open(os.path.join(dump, name), "w", encoding="utf-8") as f:
                f.write(f"# join.method={method}\trows={len(rows)}\n")
                f.write("#漢字\t反切\t韻\tsim_tl候選\t文讀gold\n")
                for row in rows:
                    f.write("\t".join(row) + "\n")
            manifest.append(f"{name}\t{method}\t{len(rows)}")
        with open(os.path.join(dump, "MANIFEST.tsv"), "w", encoding="utf-8") as f:
            f.write("#檔名\tjoin.method\t未命中數\n" + "\n".join(manifest) + "\n")
    return hits, total, (cands / total if total else 0.0)


def read_targets(path):
    """envelope.yaml 的 loop_targets 區塊（扁平 `key: number` 行）。"""
    targets, inside = {}, False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^loop_targets:\s*$", line):
                inside = True
                continue
            if inside:
                m = re.match(r"^\s+(\w+):\s*([0-9.]+)\s*(#.*)?$", line)
                if not m:
                    break
                targets[m.group(1)] = float(m.group(2))
    return targets


def cmd_hit_rate(a):
    if not a.index and not a.scratch:
        raise Harness("需要 --index，或 --scratch／KOKTAI_SCRATCH")
    path = a.index or os.path.join(a.scratch, "index", "unified_phonology.json")
    if not os.path.isfile(path):
        raise Harness(f"索引不存在：{path}")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    hits, total, avg = measure(doc, a.dump_misses)
    if a.targets:
        t = read_targets(a.targets)
        for k in ("min_hit_rate", "max_avg_candidates"):
            if k not in t:
                raise Harness(f"{a.targets} 缺 loop_targets.{k}")
        a.min_rate, a.max_avg_cand = t["min_hit_rate"], t["max_avg_candidates"]
    rate = hits / total if total else 0.0
    msg = f"{hits}/{total}（{rate:.2%}），平均候選 {avg:.2f}"
    fails = []
    if a.min_hits is not None and hits < a.min_hits:
        fails.append(f"命中 {hits} < {a.min_hits}")
    if a.min_rate is not None and rate < a.min_rate:
        fails.append(f"命中率 {rate:.4f} < {a.min_rate}")
    if a.max_avg_cand is not None and avg > a.max_avg_cand:
        fails.append(f"平均候選 {avg:.4f} > {a.max_avg_cand}（候選膨脹）")
    if fails:
        out("FAIL", "hit-rate", f"{msg}；" + "；".join(fails))
        return 1
    out("PASS", "hit-rate", msg)
    return 0


# ------------------------------------------------------------ guard
def deny_globs():
    if not os.path.isfile(CONSTITUTION):
        raise Harness(f"憲法路徑清單不存在：{CONSTITUTION}")
    globs, inside = [], False
    with open(CONSTITUTION, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^\s*deny_write:\s*$", line):
                inside = True
                continue
            if inside:
                m = re.match(r'^\s+-\s+"([^"]+)"', line)
                if not m:
                    break
                globs.append(m.group(1))
    if not globs:
        raise Harness(f"{CONSTITUTION} 無 deny_write 清單")
    return globs


def constitutional_digest():
    globs = deny_globs()
    digests = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "json", "__pycache__")]
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            if any(fnmatch.fnmatch(rel, g) for g in globs):
                with open(os.path.join(ROOT, rel), "rb") as f:
                    digests[rel] = hashlib.sha256(f.read()).hexdigest()
    return digests


def cmd_guard(a):
    now = constitutional_digest()
    if a.snapshot:
        with open(a.snapshot, "w", encoding="utf-8") as f:
            json.dump(now, f, ensure_ascii=False, indent=1, sort_keys=True)
        out("PASS", "guard", f"快照 {len(now)} 檔 → {a.snapshot}")
        return 0
    if not os.path.isfile(a.check):
        raise Harness(f"快照不存在：{a.check}")
    with open(a.check, encoding="utf-8") as f:
        base = json.load(f)
    changed = sorted(k for k in set(base) | set(now) if base.get(k) != now.get(k))
    if changed:
        out("FAIL", "guard", f"憲法路徑被改動：{changed}")
        return 1
    out("PASS", "guard", f"{len(now)} 個憲法路徑檔未變")
    return 0


# ------------------------------------------------------------ scope
def dirty_paths():
    r = subprocess.run(["git", "status", "--porcelain=v1", "-z",
                        "--untracked-files=all"], cwd=ROOT, capture_output=True)
    if r.returncode:
        raise Harness("git status 失敗：" + r.stderr.decode()[:200])
    paths, parts = {}, r.stdout.decode("utf-8").split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:          # rename/copy：下一段是來源路徑
            i += 1
        full = os.path.join(ROOT, path)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                paths[path] = hashlib.sha256(f.read()).hexdigest()
        else:
            paths[path] = "absent"
    return paths


def cmd_scope(a):
    now = dirty_paths()
    if a.snapshot:
        with open(a.snapshot, "w", encoding="utf-8") as f:
            json.dump(now, f, ensure_ascii=False, indent=1, sort_keys=True)
        out("PASS", "scope", f"基線 {len(now)} 個既有變動路徑 → {a.snapshot}")
        return 0
    if not os.path.isfile(a.check):
        raise Harness(f"基線不存在：{a.check}")
    with open(a.check, encoding="utf-8") as f:
        base = json.load(f)
    allow = [g for g in (a.allow or "").split(",") if g]
    outside = sorted(p for p in set(base) | set(now)
                     if base.get(p) != now.get(p)
                     and not any(fnmatch.fnmatch(p, g) for g in allow))
    if outside:
        out("FAIL", "scope", f"變動超出允許範圍 {allow}：{outside[:20]}")
        return 1
    out("PASS", "scope", f"變動皆在允許範圍 {allow}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    scratch_default = os.environ.get("KOKTAI_SCRATCH")

    p = sub.add_parser("rebuild-json", help="26 卷 .dic → scratch/json（不碰 repo json/）")
    p.add_argument("--scratch", default=scratch_default)
    p.add_argument("--expect-totals", help="章,單字,詞條,反切 總數")
    p.set_defaults(fn=cmd_rebuild_json, needs_scratch=True)

    p = sub.add_parser("build-index", help="scratch/json → scratch/index")
    p.add_argument("--scratch", default=scratch_default)
    p.add_argument("--ytenx", default=os.environ.get("YTENX", "~/dev/ytenx"))
    p.set_defaults(fn=cmd_build_index, needs_scratch=True)

    p = sub.add_parser("index-parity", help="scratch/index 對 git REF:index/ 位元比對")
    p.add_argument("--scratch", default=scratch_default)
    p.add_argument("--ref", default="HEAD")
    p.add_argument("--allow", help="JSON 允許變動的 han[] 欄位，逗號分隔（如 mc,pingshui）")
    p.set_defaults(fn=cmd_index_parity, needs_scratch=True)

    p = sub.add_parser("unittest", help="a-tsioh_sandbox/test_join_fanqie.py")
    p.add_argument("--min-tests", type=int, default=0)
    p.set_defaults(fn=cmd_unittest, needs_scratch=False)

    p = sub.add_parser("poj-gold", help="台羅→白話字 對 ChhoeTaigi 黃金對")
    p.add_argument("--min-ok", type=int, required=True)
    p.add_argument("--total", type=int)
    p.set_defaults(fn=cmd_poj_gold, needs_scratch=False)

    p = sub.add_parser("hit-rate", help="mc[].sim_tl 對既有文讀 any-hit 命中率")
    p.add_argument("--scratch", default=scratch_default)
    p.add_argument("--index", help="直接指定 unified_phonology.json（預設 scratch/index/）")
    p.add_argument("--min-hits", type=int)
    p.add_argument("--min-rate", type=float)
    p.add_argument("--max-avg-cand", type=float)
    p.add_argument("--targets", help="從 envelope.yaml 的 loop_targets 讀門檻")
    p.add_argument("--dump-misses", help="未命中依 join.method 分桶寫出到此目錄")
    p.set_defaults(fn=cmd_hit_rate, needs_scratch=False)

    p = sub.add_parser("guard", help="憲法路徑（constitutional.yaml deny_write）雜湊快照/比對")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", help="寫出快照")
    g.add_argument("--check", help="與快照比對")
    p.set_defaults(fn=cmd_guard, needs_scratch=False)

    p = sub.add_parser("scope", help="工作樹變動範圍：基線快照／比對（允許 glob 以逗號分隔）")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", help="寫出基線（既有 dirty/untracked 路徑與雜湊）")
    g.add_argument("--check", help="與基線比對")
    p.add_argument("--allow", help="允許變動的路徑 glob，逗號分隔")
    p.set_defaults(fn=cmd_scope, needs_scratch=False)

    a = ap.parse_args()
    try:
        if a.needs_scratch and not a.scratch:
            raise Harness("需要 --scratch 或環境變數 KOKTAI_SCRATCH")
        if getattr(a, "scratch", None):
            a.scratch = os.path.abspath(a.scratch)
            if a.scratch == ROOT or a.scratch.startswith(ROOT + os.sep):
                raise Harness(f"scratch 必須在 repo 外：{a.scratch}")
        sys.exit(a.fn(a))
    except Harness as e:
        out("HARNESS", a.cmd, str(e))
        sys.exit(2)


if __name__ == "__main__":
    main()
