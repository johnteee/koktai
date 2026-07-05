# -*- coding: utf-8 -*-
"""koktai_dic — 《國臺對照活用辭典》 .dic 全結構解析庫（無資訊遺失）。

輸入：recode_utf8.pl 之後的 UTF-8 文本（造字已映射至 U+F0000+big5）。

.dic 結構（卷一實測 600 單字頭、67 章、~10600 詞條）：

  .章首
  ㄅㄚ ~t112fd0;[ba]                      ← 章節音節（國音注音 + 羅馬字）

  .本文                                   ← 單字條目開始
  ~fm7t168bb1;八~fm3t168bb1;<PUA>~fm3t84bb1;　布拔切，黠韻
      ↑字頭(明體)      ↑字頭注音字形       ↑反切引註（530/600 條含「切」）
  ~fkt168bb1;<PUA>...                     ← 楷體字頭變體（台語造字，76 條）
  ~fm7;國音~fm3t42;　~t84;...~bt315;∥~bt0; ← 讀音列（國音/台甘/普閩）
  ~t96;【~fb7bb1;八...】~t84;...           ← 詞條（歸屬於前一單字）

輸出 schema「koktai-dic/2」：
  {"format":"koktai-dic/2", "chapters":[
     {"zhuyin":…, "roman":…, "hanzi_entries":[
        {"head":{"display":…,"chars":[…],"ruby":[{glyph,bopo}…]},
         "annotation_raw":…, "fanqie":[{speller,yun,tone,source,derived,raw}…],
         "annotation_notes":[…],
         "readings":{"國音":{raw,segments},…},
         "word_entries":[v1 相容 entry + raw],
         "raw":[原始行（造字以 &#xf….; 逃逸，可逆）]}]}]}

保真原則：
  * 每層都保留 raw（造字字元以 &#xfXXXX; ASCII 逃逸 → 可逆、且不被後續
    文字階段誤改）。
  * 解不了的片段進 *_notes / unparsed，不丟棄。
"""

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 字形資源
def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

M3 = _load(os.path.join(_HERE, "..", "font", "m3.json"))      # hex -> 方音符號串（明體）
K = _load(os.path.join(_HERE, "..", "font", "k.json"))        # hex -> 方音符號串（楷體）
PRIVATE_TO_UNICODE = _load(os.path.join(_HERE, "mapping.json"))  # 造字字元 -> 罕用漢字

PUA_BASE = 0xF0000
PUA_RE = re.compile(r"[\U000F0000-\U000FFFFF]")
CIRCLED_RE = re.compile(r"[\U000FC6A1-\U000FC6A9]")           # ①..⑨ 造字


def pua_hex(ch):
    return "%04x" % (ord(ch) - PUA_BASE)


def escape_pua(s):
    """造字 → &#xfXXXX; ASCII 逃逸（raw 欄位用，可逆）。"""
    return PUA_RE.sub(lambda m: "&#xf%s;" % pua_hex(m.group(0)), s)


def decode_glyph(ch, kai=False):
    """單一造字字元 → dict(glyph, bopo|None, char|None)。

    bopo：方音符號串（m3/k 查表）；char：mapping.json 的罕用漢字。
    """
    code = ord(ch)
    if 0xFC6A1 <= code <= 0xFC6A9:  # 圈號 ①-⑨
        return {"glyph": pua_hex(ch), "char": chr(0x245F + code - 0xFC6A0)}
    hx = pua_hex(ch)
    out = {"glyph": hx}
    if kai and ch in PRIVATE_TO_UNICODE:
        out["char"] = PRIVATE_TO_UNICODE[ch]
        return out
    table = K if kai else M3
    if hx in table:
        out["bopo"] = table[hx]
    elif ch in PRIVATE_TO_UNICODE:
        out["char"] = PRIVATE_TO_UNICODE[ch]
    return out


def to_rt_markup(s, kai_regions=True):
    """整段文字之造字 → 行內標記（相容舊管線 jade-unescape.pl 的語意）：

      明體區：U+FC000-FCFFF 為「內文字元區」→ 裸放 m3 值（癶、ㄆㄚ 等）；
              其他區 m3 有 → <rt>注音</rt>；mapping 有 → 罕用漢字；
              否 → <glyph:m3/xxxx>
      <k>…</k> 楷體區：mapping 有 → 罕用漢字；k 有 → <rt>…</rt>；否 → <glyph:k/xxxx>
      ①-⑨ 圈號 → 直接還原
    """
    def _kai(m):
        body = m.group(1)
        parts = []
        for ch in body:
            if PUA_RE.match(ch):
                d = decode_glyph(ch, kai=True)
                if "char" in d:
                    parts.append(d["char"])
                elif "bopo" in d:
                    parts.append("<rt>%s</rt>" % d["bopo"])
                else:
                    parts.append("<glyph:k/%s>" % d["glyph"])
            else:
                parts.append(ch)
        return "".join(parts)

    if kai_regions:
        s = re.sub(r"<k>(.*?)</k>", _kai, s)

    def _ming(m):
        ch = m.group(0)
        d = decode_glyph(ch, kai=False)
        if "bopo" in d:
            if 0xFC000 <= ord(ch) <= 0xFCFFF:   # 內文字元區：裸放
                return d["bopo"]
            return "<rt>%s</rt>" % d["bopo"]
        if "char" in d:
            return d["char"]
        return "<glyph:m3/%s>" % d["glyph"]

    return PUA_RE.sub(_ming, s)


# ---------------------------------------------------------------- 行內格式碼
RE_FONT_KAI_SPAN = re.compile(r"~fk[a-z0-9]*;(.*?)~fm[37][a-z0-9]*;")
RE_CTRL = re.compile(r"~[a-z0-9]+;")


def mark_kai(s):
    """~fk;…~fm3; 楷體區 → <k>…</k>（先於格式碼剝除）。"""
    return RE_FONT_KAI_SPAN.sub(r"<k>\1</k>", s)


def strip_ctrl(s):
    return RE_CTRL.sub("", s)


# ---------------------------------------------------------------- 反切引註
_SRC = r"(?:[（(]\s*(?P<src>[^)）]{1,12})\s*[)）])?"
FANQIE_RE = re.compile(
    r"(?P<der>←)?"
    r"(?P<speller>[\u3400-\u9fff\U00020000-\U0002FFFF]{2})切，"
    r"(?P<tone>[平上去入])?"
    r"(?P<yun>[\u3400-\u9fff])韻"
    + _SRC
)
SRC_PREFIX_RE = re.compile(r"(?P<src>廣韻|集韻|正韻|唐韻|韻會|康典[^：:]{0,6})[：:]")


def parse_fanqie(text):
    """反切引註字串 → (citations, notes)。

    citations: [{speller, yun, tone, source, derived, raw}]
    notes: 無法解析成反切的剩餘片段（原文保留）。
    """
    citations, notes = [], []
    for seg in re.split(r"[。；;]", text):
        seg = seg.strip("　 \t")
        if not seg:
            continue
        pos = 0
        default_src = None
        mpre = SRC_PREFIX_RE.match(seg)
        if mpre:
            default_src = mpre.group("src")
            pos = mpre.end()
        found = False
        for m in FANQIE_RE.finditer(seg, pos):
            found = True
            citations.append({
                "speller": m.group("speller"),
                "yun": m.group("yun"),
                "tone": m.group("tone"),
                "source": m.group("src") or default_src,
                "derived": bool(m.group("der")),
                "raw": seg,
            })
        if not found:
            notes.append(seg)
    return citations, notes


# ---------------------------------------------------------------- 讀音列
# 標籤可出現在行首或 ∥ 之後（卷3等舊排版把多標籤擠在同一行）
READING_LABEL_RE = re.compile(r"~fm7[a-z0-9]*;(國音|台甘|普閩)")
REGISTER_RE = re.compile(r"[（(]([^)）]{1,8})[)）]")


def _parse_reading_body(body):
    body = mark_kai(body)
    body = strip_ctrl(body).replace("∥", "").strip("　 ")
    segments = []
    cur = {"register": None, "glyphs": [], "text": ""}

    def push():
        if cur["glyphs"] or cur["text"].strip("　 。="):
            seg = {k: v for k, v in cur.items() if v not in (None, [], "")}
            segments.append(seg)

    i = 0
    while i < len(body):
        mreg = REGISTER_RE.match(body, i)
        if mreg:
            push()
            cur = {"register": mreg.group(1), "glyphs": [], "text": ""}
            i = mreg.end()
            continue
        ch = body[i]
        if PUA_RE.match(ch):
            cur["glyphs"].append(decode_glyph(ch))
        else:
            cur["text"] += ch
        i += 1
    push()
    return segments


def parse_reading_line(line):
    """讀音列（可含多個標籤）→ [{label, raw, segments}, …]。

    新式：~fm7;台甘~fm3t42;　~t84;(文)…(語)…∥
    舊式：~fm7;國音…∥~fm7bt0;台甘…∥…（多標籤同一行）
    """
    hits = list(READING_LABEL_RE.finditer(line))
    if not hits:
        return []
    out = []
    for k, m in enumerate(hits):
        end = hits[k + 1].start() if k + 1 < len(hits) else len(line)
        out.append({
            "label": m.group(1),
            "raw": escape_pua(line[m.start():end]),
            "segments": _parse_reading_body(line[m.end():end]),
        })
    return out


# ---------------------------------------------------------------- 單字頭
# 任意格式碼段：code 形如 fm7 / fm3t168bb1 / fk / t84 / t112fd0 …
SEG_RE = re.compile(r"~(?P<code>[a-z0-9]+);(?P<body>[^~]*)")
HEAD_START_RE = re.compile(r"^~f[a-z0-9]*t168")


def parse_hanzi_head(line):
    """單字頭行 → {display, chars, ruby, annotation_raw, fanqie, annotation_notes}。

    支援兩式：
      新（卷1）：~fm7t168bb1;字~fm3t168bb1;<注音字形>~fm3t84bb1;　<引註>
      舊（卷3）：~fm7t168;字~fm3;<注音字形>~t84;　<引註>
    字頭段與注音字形段交錯；t84 段起為引註尾。
    """
    chars, ruby, display = [], [], []
    tail_parts = []
    in_tail = False
    font = "fm7"
    for m in SEG_RE.finditer(line):
        code, body = m.group("code"), m.group("body")
        if not in_tail and "t84" in code:
            in_tail = True
        if in_tail:
            tail_parts.append(body)
            continue
        if code.startswith("f"):
            font = ("fk" if code.startswith("fk")
                    else code[:3] if code.startswith(("fm7", "fm3", "fb7"))
                    else font)
        for ch in body:
            if PUA_RE.match(ch):
                d = decode_glyph(ch, kai=font == "fk")
                if "bopo" in d:                      # 注音字形
                    ruby.append(d)
                else:                                # 造字字頭
                    chars.append({"glyph": d["glyph"], "char": d.get("char")})
                    display.append(d.get("char") or "\ufffd")
            elif ch not in "　 ":
                if ch == "/":
                    display.append("/")
                else:
                    chars.append({"char": ch})
                    display.append(ch)
    tail = strip_ctrl("".join(tail_parts)).strip("　 ")

    fanqie, notes = parse_fanqie(tail) if tail else ([], [])
    return {
        "display": "".join(display),
        "chars": chars,
        "ruby": ruby,
        "annotation_raw": escape_pua(tail) if tail else None,
        "fanqie": fanqie,
        "annotation_notes": notes,
    }


# ---------------------------------------------------------------- 詞條（v1 相容 + 保真）
RE_WORD = re.compile(r"^~t96;【(?P<entry>[^】]+)】~(fd6)?t84;(?P<definition>.*)$")
RE_DEF = re.compile(r"^(?P<nh>[0-9]+ )?(?P<POS>\[[^\]]+\])?(?P<body>.*)$")
RE_BOPO = re.compile(r"[\u3105-\u31ba\u31c0-\u31ff˪˫˙ˊˇˋ㆐^]")


def _is_taigi(sentence):
    """漢字後有注音（造字或 <rt>）→ 台文句。沿用 v1 判斷法。"""
    for i, ch in enumerate(sentence[:-1]):
        o = ord(ch)
        if 0x3400 <= o <= 0x9FFF or 0x20000 <= o <= 0x2FFFF:
            nxt = sentence[i + 1]
            if PUA_RE.match(nxt):
                continue
            if RE_BOPO.match(nxt) or nxt in ("<", ")", "/", "·"):
                continue
            return False
    return True


def split_by_language(definition):
    sentences = []
    current = "國語"
    chunks = definition.split("。")
    for i, sentence in enumerate(chunks):
        if not sentence:
            continue
        if i < len(chunks) - 1:
            sentence += "。"
        if "(台)" in sentence[:5]:
            sentence = sentence.replace("(台)", "", 1)
            current = "台"
        if "(國語)" in sentence[:6]:
            sentence = sentence.replace("(國語)", "", 1)
            current = "國語"
        if current == "台" and not _is_taigi(sentence):
            current = "國語"
        if sentences and sentences[-1]["lang"] == current:
            sentences[-1]["sentence"] += sentence
        else:
            sentences.append({"lang": current, "sentence": sentence})
    return sentences


def parse_word_entry(joined, raw_lines):
    m = RE_WORD.match(joined)
    if not m:
        return None
    entry = strip_ctrl(mark_kai(m.group("entry")))
    definition = strip_ctrl(mark_kai(m.group("definition")))
    dm = RE_DEF.match(definition)
    body = dm.group("body")
    sentences = split_by_language(body)
    for s in sentences:
        s["sentence"] = to_rt_markup(s["sentence"])
    return {
        "entry": to_rt_markup(entry),
        "nh": (dm.group("nh") or "1").strip(),
        "POS": dm.group("POS") or "None",
        "body": to_rt_markup(body),
        "sentences": sentences,
        "raw": [escape_pua(l) for l in raw_lines],
    }


# ---------------------------------------------------------------- 整卷解析
CHAPTER_HEAD_RE = re.compile(
    r"^(?P<zhuyin>[^~\[]+?)\s*~t112fd0;\[(?P<roman>[^\]]+)\]")


def parse_volume(lines):
    """UTF-8 行序列 → koktai-dic/2 結構。"""
    chapters = []
    chapter = None
    hz = None            # 進行中單字條目
    word_buf = []        # 進行中詞條行
    expect = None        # 'chapter-head' | 'hanzi-head' | None
    unassigned = []      # 檔頭雜項

    def ensure_chapter():
        nonlocal chapter
        if chapter is None:
            chapter = {"zhuyin": None, "roman": None, "hanzi_entries": []}
            chapters.append(chapter)

    def flush_word():
        nonlocal word_buf
        if not word_buf:
            return
        joined = "".join(l.strip() for l in word_buf)
        parsed = parse_word_entry(joined, word_buf)
        if hz is not None:
            target = hz["word_entries"]
        elif chapter is not None:      # 章首後、.本文 前的孤兒詞條
            target = chapter.setdefault("orphan_word_entries", [])
        else:
            target = unassigned
        if parsed is None:
            target.append({"unparsed": [escape_pua(l) for l in word_buf]})
        else:
            target.append(parsed)
        word_buf = []

    def flush_hanzi():
        nonlocal hz
        flush_word()
        if hz is not None:
            headless = not hz["head"] and not hz["readings"]
            prev = (chapter["hanzi_entries"][-1]
                    if chapter and chapter["hanzi_entries"] else None)
            if headless and hz["word_entries"] and prev is not None:
                # 舊排版以 .本文 分段：無頭詞條塊併回前一單字
                prev["word_entries"].extend(hz["word_entries"])
                prev["raw"].extend(hz["raw"])
            elif hz["head"] or hz["word_entries"] or hz["readings"]:
                ensure_chapter()
                chapter["hanzi_entries"].append(hz)
            elif hz["raw"]:
                unassigned.append({"stray": hz["raw"]})
        hz = None

    for raw in lines:
        line = raw.rstrip("\r\n")
        s = line.strip()

        if s == ".章首":
            flush_hanzi()
            chapter = None
            expect = "chapter-head"
            continue
        if s == ".本文":
            flush_hanzi()
            hz = {"head": None, "readings": {}, "word_entries": [], "raw": []}
            expect = "hanzi-head"
            continue

        if expect == "chapter-head" and s:
            ensure_chapter()
            m = CHAPTER_HEAD_RE.match(s)
            if m:
                chapter["zhuyin"] = strip_ctrl(m.group("zhuyin")).strip()
                chapter["roman"] = m.group("roman")
            else:
                chapter["zhuyin"] = strip_ctrl(s)
            chapter["raw_head"] = escape_pua(line)
            expect = None
            continue

        if hz is not None and s:
            hz["raw"].append(escape_pua(line))

        if expect == "hanzi-head" and re.match(r"^~f[a-z0-9]+t168", s):
            hz["head"] = parse_hanzi_head(s)
            expect = None
            continue

        if (hz is not None and not word_buf
                and READING_LABEL_RE.search(s)
                and not s.startswith("~t96;")):
            flush_word()
            for r in parse_reading_line(s):
                hz["readings"].setdefault(r["label"], []).append(
                    {k: r[k] for k in ("raw", "segments")})
            continue

        if s.startswith("~t96;"):
            flush_word()
            word_buf = [line]
            continue

        if s and word_buf:
            word_buf.append(line)   # 詞條續行（含 ~fk;類語… 等）
        elif s and hz is None and not s.startswith("."):
            unassigned.append({"stray": escape_pua(line)})

    flush_hanzi()
    return {
        "format": "koktai-dic/2",
        "chapters": chapters,
        "unassigned": unassigned,
    }
