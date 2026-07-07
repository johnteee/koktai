# -*- coding: utf-8 -*-
"""chhiankimpho — 《千金譜》載入庫（ExternalRef/chhian-kim-pho2.md）。

來源：https://limkianhui.wordpress.com/2007/04/19/njhg/
檔案：ExternalRef/chhian-kim-pho2.md（HTML→Markdown 轉換版；CC BY-NC-ND 3.0 TW）

《千金譜》是閩南語啟蒙讀物，全文以「漢字＋白話字（POJ）」對照編排。
本模組逐行對齊漢字與 POJ 音節，將 POJ 轉為台羅（KipInput 數字調），
產出字級佐證對 {(漢字, 台羅): {'金'}}，併入統一索引。

POJ→台羅轉換規則：
- 聲母：ch→ts, chh→tsh
- 韻母：o͘→oo, oa→ua, oe→ue, ⁿ→nn, eng→ing, ek→ik
- 調符（NFD 組合符）：acute=2, grave=3, circumflex=5, caron=6,
  macron=7, vertical-line-above=8, breve/double-acute=9
- 原文以 ·（U+0387 GREEK ANO TELEIA）代替 o͘ 的 combining dot（U+0358），
  預先替換後再 NFD 正規化
- 無調號音節補預設調：入聲尾 p/t/k/h → 4，其餘 → 1
"""

import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MD = os.path.join(os.path.dirname(HERE), "ExternalRef", "chhian-kim-pho2.md")

HAN_RE = re.compile(r"[\u3400-\u9fff\U00020000-\U0002FFFF]")

# POJ 調符（NFD 組合符）→ 數字調
POJ_TONE_MARKS = {
    "\u0301": "2",  # acute  ´
    "\u0300": "3",  # grave  `
    "\u0302": "5",  # circumflex  ̂
    "\u030c": "6",  # caron  ˇ（泉腔陽上）
    "\u0304": "7",  # macron  ¯
    "\u030d": "8",  # vertical line above  ̍
    "\u030b": "9",  # double acute  ˝（調 9）
    "\u0306": "9",  # breve  ˘（調 9 異形）
}

# 羅馬字側標點（含引號、括號、CJK 標點）→ 空白
_LATIN_PUNCT = re.compile(
    r'[,;.!?:"\'()\[\]\u201c\u201d\u2018\u2019\u300c\u300d\u300e\u300f'
    r'\u3001\u3002\u300a\u300b\uff08\uff09\uff0c\uff1b\uff1a\uff01\uff1f]'
)


def _default_tone(body):
    return "4" if body and body[-1] in "ptkh" else "1"


def poj_to_tl_syl(poj_syl):
    """單一 POJ 音節（含調符）→ 台羅 KipInput（如 'pat4'）。失敗 → None。"""
    if not poj_syl:
        return None
    # 預處理：· (U+0387) → combining dot above right (U+0358)
    syl = poj_syl.replace("\u0387", "\u0358")
    syl = unicodedata.normalize("NFD", syl.lower())

    tone = ""
    base_chars = []
    for ch in syl:
        if ch in POJ_TONE_MARKS:
            tone = POJ_TONE_MARKS[ch]
        elif ch == "\u0358":          # combining dot above right → oo
            if base_chars and base_chars[-1] == "o":
                base_chars[-1] = "oo"
        elif ch == "\u207f":          # ⁿ superscript n → nn
            base_chars.append("nn")
        elif unicodedata.combining(ch):
            pass                       # 其他組合符，略過
        else:
            base_chars.append(ch)

    base = "".join(base_chars)
    if not base or not re.fullmatch(r"[a-z]+", base):
        return None

    # 聲母轉換（chh 先於 ch）
    base = base.replace("chh", "tsh").replace("ch", "ts")
    # 韻母轉換
    base = base.replace("oa", "ua").replace("oe", "ue")
    base = base.replace("eng", "ing").replace("ek", "ik")

    if not tone:
        tone = _default_tone(base)
    return base + tone


def _split_poj_syls(poj_text):
    raw = re.split(r"[\s\u002d\u2010-\u2015]+", poj_text)
    return [s for s in raw if s]


def _split_line(line):
    """將全文行拆成 (漢字列表, POJ 音節序列列表)。

    格式：漢字 漢字 漢字 ， POJ POJ POJ,
    分界：第一個拉丁字母出現處。
    斜線表示全詞或尾部變體：`lê-pē / lôe-pê` 兩讀都收。
    """
    m = re.search(r"[\u0041-\u005A\u0061-\u007A\u00C0-\u024F\u1E00-\u1EFF]", line)
    if not m:
        return None, None
    han_part, poj_part = line[:m.start()], line[m.start():]

    # 漢字側亦去括號註記（如「煙棰(煙仔)佮銀魚」中的 (煙仔)）
    han_part = re.sub(r"\([^)]*\)", "", han_part)
    han_chars = [c for c in han_part if HAN_RE.match(c)]

    # POJ 側：去括號註記 → 標點換空白 → 斜線變體 → 拆音節
    poj_part = re.sub(r"\([^)]*\)", " ", poj_part)
    poj_part = _LATIN_PUNCT.sub(" ", poj_part)
    parts = [_split_poj_syls(p) for p in re.split(r"\s*/\s*", poj_part) if p.strip()]
    if not parts:
        return han_chars, []
    base = parts[0]
    variants = []
    for part in parts:
        if len(part) == len(base):
            variants.append(part)
        elif len(part) < len(base):
            variants.append(base[:-len(part)] + part)
        else:
            variants.append(part)
    return han_chars, variants


def load_attestation(md_path=DEFAULT_MD):
    """→ (attest: {(漢字, tl): {'金'}}, stats: dict)"""
    if not os.path.exists(md_path):
        return {}, {"pairs": 0, "lines": 0, "aligned": 0, "skipped": 0}

    with open(md_path, encoding="utf-8") as f:
        lines = f.readlines()

    # 全文區間：【《千金譜》全文】…【《千金譜》注解】
    start = end = None
    for i, line in enumerate(lines):
        if "《千金譜》全文" in line:
            start = i + 1
        elif start and "《千金譜》注解" in line:
            end = i
            break
    if start is None:
        return {}, {"pairs": 0, "lines": 0, "aligned": 0, "skipped": 0}
    if end is None:
        end = len(lines)

    attest = {}
    stats = {"lines": 0, "aligned": 0, "skipped": 0}

    for line in lines[start:end]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        stats["lines"] += 1

        han_chars, poj_variants = _split_line(line)
        if not han_chars or not poj_variants:
            stats["skipped"] += 1
            continue

        got = False
        for poj_syls in poj_variants:
            if len(han_chars) != len(poj_syls):
                continue
            for han, poj in zip(han_chars, poj_syls):
                tl = poj_to_tl_syl(poj)
                if tl:
                    attest.setdefault((han, tl), set()).add("金")
                    got = True
        stats["aligned" if got else "skipped"] += 1

    stats["pairs"] = len(attest)
    return attest, stats


# ---------------------------------------------------------------- 註冊權重
try:
    from chhoetaigi import DICT_WEIGHT
    DICT_WEIGHT.setdefault("金", 2)       # 歷史文獻，權重同 Maryknoll（最低）
except ImportError:
    pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=DEFAULT_MD)
    args = ap.parse_args()
    attest, stats = load_attestation(args.md)
    print(f"[chhiankimpho] {stats}", file=sys.stderr)
    for (han, tl), tags in list(attest.items())[:24]:
        print(f"[chhiankimpho]   {han} {tl} {sorted(tags)}", file=sys.stderr)


if __name__ == "__main__":
    main()
