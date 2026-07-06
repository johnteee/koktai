# -*- coding: utf-8 -*-
"""sutian — 教育部《臺灣台語常用詞辭典》附錄「詞彙比較」表載入庫。

來源：https://sutian.moe.edu.tw/zh-hant/huliok/sutsha/
檔案：ExternalRef/詞彙比較表.ods（單工作表；欄＝華語詞目id/華語詞目/腔/漢字/羅馬字）

十腔別（偏泉 6：鹿港/三峽/臺北/新竹/金門/馬公；偏漳 2：宜蘭/臺中；混合 2：臺南/高雄），
羅馬字為教育部台羅調符式（含泉腔 ir/er 與陽上調 6）。

產物（同 chhoetaigi 介面，可直接併入統一索引）：
- attest: {(漢字, 台羅數字調): {'比'}} —— 字級佐證（逐位對齊，寧缺勿猜）
- dialects: {(漢字, 台羅): {腔別短名}} —— 方言腔層（koktai 漳/泉語域的官方對照）

對齊規則沿用 chhoetaigi：全漢字、漢字數＝音節數才收；括號註記兩側同步剝除；
羅馬字空白視同連字符（「予醫生看 hōo i-sing khuànn」→ 4:4）；「--」輕聲視同「-」。
"""

import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chhoetaigi import (HAN_RE, PAREN_RE, DICT_WEIGHT,
                        kip_unicode_to_input, norm_kip_word)

EXTREF_DIR = os.path.join(os.path.dirname(HERE), "ExternalRef")
DEFAULT_ODS = os.path.join(EXTREF_DIR, "詞彙比較表.ods")

# 教育部附錄標籤 → 權重（同屬教典家族）
for _t in ("比", "新", "共", "諺"):
    DICT_WEIGHT.setdefault(_t, DICT_WEIGHT["教"])

# 其餘三種附錄（序號/詞目|俗諺/音讀 簡單綱要；檔名帶版本日期，glob 取最新）
APPENDICES = [
    ("新", "sinsu*.ods",       "新詞"),
    ("共", "kiongtongsu*.ods", "臺華共同詞"),
    ("諺", "siokgan*.ods",     "俗諺"),
]

_PUNCT_RE = re.compile(r"[。，、！？；：．…‧,.!?;:'\"“”‘’「」『』()（）\u2010-\u2015]")

TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"

KHIUNN_SHORT = {
    "鹿港偏泉腔": "鹿泉", "三峽偏泉腔": "峽泉", "臺北偏泉腔": "北泉",
    "新竹偏泉腔": "竹泉", "金門偏泉腔": "金泉", "馬公偏泉腔": "澎泉",
    "宜蘭偏漳腔": "蘭漳", "臺中偏漳腔": "中漳",
    "臺南混合腔": "南混", "高雄混合腔": "高混",
}


def _iter_rows(ods_path):
    """yield [cell 文字…]（honor number-columns-repeated，上限 20 欄）。"""
    with zipfile.ZipFile(ods_path) as z:
        root = ET.fromstring(z.read("content.xml"))
    for row in root.iter(f"{{{TABLE_NS}}}table-row"):
        cells = []
        for cell in row.iter(f"{{{TABLE_NS}}}table-cell"):
            texts = [
                "".join(p.itertext())
                for p in cell.iter(f"{{{TEXT_NS}}}p")
            ]
            v = " ".join(t for t in texts if t)
            rep = int(cell.get(f"{{{TABLE_NS}}}number-columns-repeated", 1))
            cells.extend([v] * min(rep, 20))
            if len(cells) > 20:
                break
        yield cells


def load_sutsha(ods_path=DEFAULT_ODS):
    """→ (attest {(漢字,tl):{'比'}}, dialects {(漢字,tl):{短腔名}}, stats)"""
    attest, dialects = {}, {}
    stats = {"rows": 0, "aligned": 0, "skipped": 0}
    for cells in _iter_rows(ods_path):
        if len(cells) < 5:
            continue
        _id, hoa, khiunn, han, lo = cells[:5]
        if khiunn not in KHIUNN_SHORT:      # 表頭或雜列
            continue
        stats["rows"] += 1
        han = PAREN_RE.sub("", han or "").replace(" ", "")
        lo = PAREN_RE.sub("", lo or "").strip()
        chars = list(han)
        if not chars or not all(HAN_RE.match(c) for c in chars):
            stats["skipped"] += 1           # 借詞（bàng-gà）或非漢字
            continue
        # 空白視同連字符；逐段轉數字調再正規化
        syls = []
        bad = False
        for chunk in re.split(r"\s+", lo):
            if not chunk:
                continue
            num = kip_unicode_to_input(chunk)
            norm = norm_kip_word(num) if num else None
            if not norm:
                bad = True
                break
            syls.extend(norm)
        if bad or len(chars) != len(syls):
            stats["skipped"] += 1
            continue
        short = KHIUNN_SHORT[khiunn]
        for c, s in zip(chars, syls):
            keys = [(c, s)]
            if s.endswith("6"):
                # koktai 方音 ˫ 不分 6/7（一律讀 7）：陽上另掛 7 摺疊鍵才可對接
                keys.append((c, s[:-1] + "7"))
            for k in keys:
                attest.setdefault(k, set()).add("比")
                dialects.setdefault(k, set()).add(short)
        stats["aligned"] += 1
    stats["pairs"] = len(attest)
    return attest, dialects, stats


def _load_simple(ods_path, tag):
    """序號/詞目/音讀 三欄附錄 → attest {(漢字,tl):{tag}}, stats。
    俗諺為句級：標點換空白後逐字對齊；「/」為全讀變體（漳泉又音），逐一對齊。"""
    attest = {}
    stats = {"rows": 0, "aligned": 0, "skipped": 0}
    for cells in _iter_rows(ods_path):
        if len(cells) < 3:
            continue
        _no, han, lo = cells[0], cells[1], cells[2]
        if not han or not lo or han in ("詞目", "俗諺"):
            continue
        stats["rows"] += 1
        han = _PUNCT_RE.sub("", PAREN_RE.sub("", han)).replace(" ", "")
        # 羅馬字側標點換空白（逗號常黏字：bīn,m̄-thang）
        lo = _PUNCT_RE.sub(" ", PAREN_RE.sub("", lo)).strip()
        chars = list(han)
        if not chars or not all(HAN_RE.match(c) for c in chars):
            stats["skipped"] += 1
            continue
        got = False
        for variant in lo.split("/"):
            syls = []
            bad = False
            for chunk in re.split(r"\s+", variant):
                if not chunk:
                    continue
                num = kip_unicode_to_input(chunk)
                norm = norm_kip_word(num) if num else None
                if not norm:
                    bad = True
                    break
                syls.extend(norm)
            if bad or len(chars) != len(syls):
                continue
            for c, s in zip(chars, syls):
                attest.setdefault((c, s), set()).add(tag)
            got = True
        stats["aligned" if got else "skipped"] += 1
    stats["pairs"] = len(attest)
    return attest, stats


def load_appendices(extref_dir=EXTREF_DIR):
    """三種簡單附錄合併 → (attest, stats per tag)；無檔案時回空。"""
    import glob as _glob
    attest = {}
    stats = {}
    for tag, pat, label in APPENDICES:
        hits = sorted(_glob.glob(os.path.join(extref_dir, pat)))
        if not hits:
            continue
        att, st = _load_simple(hits[-1], tag)     # 版本日期序，取最新
        st["file"] = os.path.basename(hits[-1])
        st["label"] = label
        stats[tag] = st
        for k, v in att.items():
            attest.setdefault(k, set()).update(v)
    return attest, stats


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ods", default=DEFAULT_ODS)
    args = ap.parse_args()
    attest, dialects, stats = load_sutsha(args.ods)
    print(f"[sutian] {stats}", file=sys.stderr)
    # 抽樣：泉腔特有形
    hits = [(h, t, sorted(d)) for (h, t), d in dialects.items()
            if re.search(r"(ir|er)", t) or t.endswith("6")]
    for h, t, d in hits[:12]:
        print(f"[sutian]   {h} {t} {','.join(d)}", file=sys.stderr)
    print(f"[sutian] 泉腔形（ir/er/調6）共 {len(hits)} 對", file=sys.stderr)
    app_att, app_stats = load_appendices()
    for tag, st in app_stats.items():
        print(f"[sutian] 附錄 {tag}（{st['label']}，{st['file']}）：{st}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
