# -*- coding: utf-8 -*-
"""chhoetaigi — ChhoeTaigi 開放辭典 CSV 載入庫（ExternalRef/ChhoeTaigiDatabase/）。

提供三種產物：
1. 字級佐證 load_attestation()：(漢字, 台羅) -> {辭典標籤}
   方法：詞條「台文漢字 ↔ KipInput 音節」逐位對齊（漢字數 == 音節數才對齊，
   全漢字才收），同 koktai tokenize_ruby 的對齊思路；單字辭典（甘字典/700用字）
   直接收，甘字典「漢文音」另掛『甘文』標籤。
2. POJ 黃金對 iter_poj_gold()：(KipInput 音節, PojUnicode 音節) 對，
   供驗證 rt2pronun 的 台羅→白話字 轉換。
3. 權重 DICT_WEIGHT：仿 ch2taigi calcWordWeightAndDeduplication 的
   辭典優先序權重（優先序 × 2），供索引排序。

台羅正規化慣例（ChhoeTaigi Input 欄 → koktai TL）：
- 去括號註記（「(替)」等）、「--」輕聲連字符視同「-」、全小寫。
- 無調號音節補預設調：入聲尾 p/t/k/h → 4，其餘 → 1（koktai TL 一律帶調號）。
"""

import csv
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(os.path.dirname(HERE), "ExternalRef", "ChhoeTaigiDatabase")

HAN_RE = re.compile(r"^[\u3400-\u9fff\U00020000-\U0002FFFF]$")
KIP_SYL_RE = re.compile(r"^[a-z]+[0-9]$")
PAREN_RE = re.compile(r"\([^)]*\)|（[^）]*）")

# ch2taigi dictList 優先序（前者權威）；weight = 排序權重 × 2（仿 ch2taigi）。
# align: 台文漢字欄（可逐位對齊）；kip: 數字調台羅欄；poj: POJ Unicode 欄。
DICTS = [
    # tag,  檔名,                                        align 欄,           kip 欄,      poj 欄
    ("700", "ChhoeTaigi_700iongji.csv",                  "HanLoTaibunPoj",  None,        None),
    ("千",  "ChhoeTaigi_taigi1000.csv",                  None,              None,        None),
    ("教",  "ChhoeTaigi_KauiokpooTaigiSutian.csv",       "HanLoTaibunKip",  "KipInput",  "PojUnicode"),
    ("線",  "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv","HanLoTaibunKip",  "KipInput",  "PojUnicode"),
    ("iT",  "ChhoeTaigi_iTaigiHoataiTuichiautian.csv",   "HanLoTaibunKip",  "KipInput",  "PojUnicode"),
    ("基",  "ChhoeTaigi_TaioanPehoeKichhooGiku.csv",     None,              "KipInput",  "PojUnicode"),
    ("日",  "ChhoeTaigi_TaijitToaSutian.csv",            "HanLoTaibunKip",  "KipInput",  "PojUnicode"),
    ("甘",  "ChhoeTaigi_KamJitian.csv",                  "HanLoTaibunPoj",  "KipInput",  "PojUnicode"),
    ("植",  "ChhoeTaigi_TaioanSitbutMialui.csv",         "HanLoTaibunPoj",  "KipInput",  "PojUnicode"),
    ("Em",  "ChhoeTaigi_EmbreeTaiengSutian.csv",         None,              "KipInput",  "PojUnicode"),
    ("Mk",  "ChhoeTaigi_MaryknollTaiengSutian.csv",      None,              "KipInput",  "PojUnicode"),
]
# 註：taigi1000 表頭殘缺（讀音三欄無欄名）不取；Embree/Maryknoll/基礎語句集
# 無台文漢字欄（HoaBun 是華文，絕不可拿來對齊音節），僅供 POJ 黃金對。

DICT_WEIGHT = {tag: (len(DICTS) - i) * 2 for i, (tag, *_rest) in enumerate(DICTS)}
DICT_WEIGHT["甘文"] = DICT_WEIGHT["甘"]
# 教育部附錄標籤（比/新/共/諺）由 sutian.py 註冊，權重同「教」。

# 台羅調符（NFD 組合符）→ 數字調；KIP Unicode（700用字音讀欄）轉數字用。
_TONE_MARKS = {"\u0301": "2", "\u0300": "3", "\u0302": "5", "\u030c": "6",
               "\u0304": "7", "\u030d": "8", "\u030b": "9"}


def _default_tone(body):
    return "4" if body and body[-1] in "ptkh" else "1"


def norm_kip_word(word):
    """KipInput 詞 → 正規化台羅音節列表；含非法音節 → None（整詞棄）。"""
    if not word:
        return None
    word = PAREN_RE.sub("", word).strip().lower().replace("--", "-")
    if not word:
        return None
    syls = []
    for syl in word.split("-"):
        syl = syl.strip()
        if not syl:
            continue
        if not re.fullmatch(r"[a-z]+[0-9]?", syl):
            return None
        if not syl[-1].isdigit():
            syl += _default_tone(syl)
        if not KIP_SYL_RE.fullmatch(syl):
            return None
        syls.append(syl)
    return syls or None


def kip_unicode_to_input(word):
    """KIP Unicode（調符式）→ 數字調 KipInput 形。ⁿ→nn 順手容錯。"""
    if not word:
        return None
    out = []
    for syl in word.replace("--", "-").split("-"):
        syl = unicodedata.normalize("NFD", syl.strip().lower())
        tone = ""
        body = []
        for ch in syl:
            if ch in _TONE_MARKS:
                tone = _TONE_MARKS[ch]
            elif ch == "\u207f":          # ⁿ
                body.append("nn")
            elif unicodedata.combining(ch):
                return None               # 其他組合符（非 KIP）
            else:
                body.append(ch)
        b = "".join(body)
        if not b:
            continue
        out.append(b + (tone or _default_tone(b)))
    return "-".join(out) if out else None


def _split_variants(cell):
    """欄值 → 詞形變體列表（「/」分隔；先去括號）。"""
    if not cell:
        return []
    return [v for v in PAREN_RE.sub("", cell).split("/") if v.strip()]


def _rows(csv_dir, fname):
    path = os.path.join(csv_dir, fname)
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def _align(han_word, syls, add):
    """全漢字詞 × 音節列表逐位對齊；不合即棄（不猜）。"""
    if not han_word or not syls:
        return False
    chars = list(han_word.strip())
    if len(chars) != len(syls):
        return False
    if not all(HAN_RE.match(c) for c in chars):
        return False
    for c, s in zip(chars, syls):
        add(c, s)
    return True


def load_attestation(csv_dir=DEFAULT_DIR, tags=None):
    """→ (attest: {(漢字, tl): set(tag)}, stats: dict)"""
    attest = {}
    stats = {}

    def mk_add(tag):
        def add(han, tl):
            attest.setdefault((han, tl), set()).add(tag)
        return add

    for tag, fname, align_col, kip_col, _poj in DICTS:
        if tags and tag not in tags:
            continue
        if align_col is None:
            continue
        add, n_ok, n_skip = mk_add(tag), 0, 0
        for row in _rows(csv_dir, fname):
            if tag == "700":                       # 單字：音讀/又音為 KIP Unicode
                han = (row.get("HanLoTaibunPoj") or "").strip()
                if len(han) != 1 or not HAN_RE.match(han):
                    n_skip += 1
                    continue
                got = False
                for col in ("音讀", "又音"):
                    for v in _split_variants(row.get(col) or ""):
                        num = kip_unicode_to_input(v)
                        syls = norm_kip_word(num) if num else None
                        if syls and len(syls) == 1:
                            add(han, syls[0])
                            got = True
                n_ok += got
                continue

            han_cell = (row.get(align_col) or "").strip()
            variants = _split_variants(row.get(kip_col) or "")
            others = _split_variants(row.get(kip_col + "Others") or "") \
                if kip_col and kip_col + "Others" in row else []
            got = False
            for v in variants + others:
                syls = norm_kip_word(v)
                if syls and _align(han_cell, syls, add):
                    got = True
            if tag == "甘":                        # 漢文音（文讀）另掛標籤
                for v in _split_variants(row.get("HanbunImKipInput") or ""):
                    syls = norm_kip_word(v)
                    if syls and _align(han_cell, syls, mk_add("甘文")):
                        got = True
            n_ok += got
            n_skip += not got
        stats[tag] = {"aligned_rows": n_ok, "skipped_rows": n_skip}

    stats["pairs"] = len(attest)
    return attest, stats


def iter_poj_gold(csv_dir=DEFAULT_DIR):
    """yield (kip 音節, poj Unicode 音節, tag)——去重後的黃金對。"""
    seen = set()
    for tag, fname, _align_col, kip_col, poj_col in DICTS:
        if not kip_col or not poj_col:
            continue
        for row in _rows(csv_dir, fname):
            kips = _split_variants(row.get(kip_col) or "")
            pojs = _split_variants(row.get(poj_col) or "")
            for kw, pw in zip(kips, pojs):        # 變體逐位配對，數量不齊自然截斷
                ks = norm_kip_word(kw)
                pw = pw.strip().lower().replace("--", "-")
                psyls = [p for p in pw.split("-") if p]
                if not ks or len(ks) != len(psyls):
                    continue
                for k, p in zip(ks, psyls):
                    if re.search(r"[^a-z\u0300-\u036f\u207f\u0358·̍]",
                                 unicodedata.normalize("NFD", p)):
                        continue
                    key = (k, p)
                    if key not in seen:
                        seen.add(key)
                        yield k, p, tag


# ---------------------------------------------------------------- 驗證模式
def parse_tl(syl):
    """數字調台羅音節 → (聲, 韻, 調)；壞形 → None。"""
    if not syl or not syl[-1].isdigit():
        return None
    body, tone = syl[:-1], syl[-1]
    if body in ("m", "mh", "hm", "hmh", "ng", "ngh", "hng", "hngh"):
        return "", body, tone
    for ini in ("tsh", "ts", "chh", "ch", "ph", "th", "kh", "ng",
                "p", "b", "m", "t", "n", "l", "k", "g", "h", "s", "j"):
        if body.startswith(ini):
            rest = body[len(ini):]
            if rest and (ini != "n" or not rest.startswith("g")):
                return ini, rest, tone
    return "", body, tone


def validate_poj(csv_dir=DEFAULT_DIR, limit_examples=12):
    sys.path.insert(0, HERE)
    from rt2pronun import 臺羅轉白話字 as conv

    total = ok = 0
    misses = {}
    for k, gold, tag in iter_poj_gold(csv_dir):
        parsed = parse_tl(k)
        if not parsed:
            continue
        ini, fin, tone = parsed
        mine = conv.轉白話字(ini, fin, tone)
        a = unicodedata.normalize("NFD", mine)
        b = unicodedata.normalize("NFD", gold)
        total += 1
        if a == b:
            ok += 1
        else:
            bucket = (fin, tone)
            misses.setdefault(bucket, []).append((k, gold, mine, tag))
    print(f"[poj-gold] 音節對 {total}，符合 {ok}（{ok/total:.2%}）",
          file=sys.stderr)
    for bucket, items in sorted(misses.items(), key=lambda kv: -len(kv[1]))[:limit_examples]:
        k, gold, mine, tag = items[0]
        print(f"[poj-gold]  韻 {bucket[0]} 調 {bucket[1]}: ×{len(items)}  "
              f"例 {k} 應 {gold} 得 {mine} ({tag})", file=sys.stderr)
    return ok, total, misses


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--validate-poj", action="store_true")
    ap.add_argument("--attest-stats", action="store_true")
    args = ap.parse_args()
    if args.validate_poj:
        validate_poj(args.dir)
    if args.attest_stats:
        _att, stats = load_attestation(args.dir)
        for k, v in stats.items():
            print(f"[attest] {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()
