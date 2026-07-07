# -*- coding: utf-8 -*-
"""build_unified_index — 統一聲韻索引產生器（漢字 ↔ 台羅 雙向反查）。

輸入：
  * json/NN.json（koktai-dic/2 管線輸出：dic2json.py | rt2pronun.py）
  * ytenx 聲韻查表（--ytenx 指向 repo 根；用 kyonh=廣韻、tcenghyonhtsen=洪武正韻）
  * data/kuangx_pingshui.json（切韻系韻目 ↔ 平水部）
  * data/pingshui_tl.json（平水韻系 → 台羅文讀韻母；出處：ExternalRef 平水韻編碼 PDF）
  * data/literature_extra_chars.txt（可選；文學語料額外字頭 → ytenx 字頭歸小韻）

輸出（--out，預設 index/）：
  * unified_phonology.json  全量索引：han → {mandarin, taigi, mc, pingshui}、tl → [han…]
  * han_to_tl.tsv           漢字 → 台羅（含方音、白話字、語域、次數、例源）
  * tl_to_han.tsv           台羅音節 → 漢字（按出現次數排序）

用法：
  python3 a-tsioh_sandbox/build_unified_index.py \
      [--json 'json/*.json'] [--ytenx ~/dev/ytenx] [--out index] [--extra-chars PATH]
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chhoetaigi import DICT_WEIGHT, load_attestation, DEFAULT_DIR as CT_DIR
from sutian import load_sutsha, load_appendices, DEFAULT_ODS as SUTIAN_ODS
from chhiankimpho import load_attestation as load_chhiankimpho, DEFAULT_MD as CKP_MD
DEFAULT_EXTRA_CHARS = os.path.join(HERE, "data", "literature_extra_chars.txt")
HAN_RE = re.compile(r"[\u3400-\u9fff\U00020000-\U0002FFFF]")


# ---------------------------------------------------------------- ytenx 查表
def _rows(path, skip_hash=True):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if skip_hash and line.startswith("#"):
                continue
            yield line.split(" ")


def strip_ab(miuk):
    return re.sub(r"[AB]$", "", miuk)

# 中古聲母 → 台羅文讀聲母候選。清濁用於陰陽調推導；候選保留常見
# 文讀分支（如 日母 j/l、明母 b/m），不嘗試白話音或訓讀。
INITIAL_META = {
    "幫": ("全清", ["p"]), "滂": ("次清", ["ph"]),
    "並": ("全濁", ["p", "ph"]), "明": ("次濁", ["b", "m"]),
    "非": ("全清", ["h"]), "敷": ("次清", ["h"]),
    "奉": ("全濁", ["h"]), "微": ("次濁", ["b", "m"]),
    "端": ("全清", ["t"]), "透": ("次清", ["th"]),
    "定": ("全濁", ["t", "th"]), "泥": ("次濁", ["l", "n"]),
    "知": ("全清", ["t"]), "徹": ("次清", ["th"]),
    "澄": ("全濁", ["t", "th"]), "孃": ("次濁", ["l", "n"]),
    "精": ("全清", ["ts"]), "清": ("次清", ["tsh"]),
    "從": ("全濁", ["ts", "tsh"]), "心": ("全清", ["s"]),
    "邪": ("全濁", ["s", "ts"]),
    "莊": ("全清", ["ts"]), "初": ("次清", ["tsh"]),
    "崇": ("全濁", ["ts", "s"]), "生": ("全清", ["s"]),
    "俟": ("全濁", ["s"]),
    "章": ("全清", ["ts"]), "昌": ("次清", ["tsh"]),
    "船": ("全濁", ["s", "ts"]), "書": ("全清", ["s"]),
    "常": ("全濁", ["s", "ts"]),
    "見": ("全清", ["k"]), "溪": ("次清", ["kh"]),
    "羣": ("全濁", ["k", "kh"]), "疑": ("次濁", ["g", "ng"]),
    "曉": ("全清", ["h"]), "匣": ("全濁", ["h"]),
    "影": ("全清", [""]), "云": ("次濁", [""]),
    "以": ("次濁", [""]), "來": ("次濁", ["l"]),
    "日": ("次濁", ["j", "l"]),
}

# 洪武正韻牋 ytenx 聲母碼 → 切韻系聲母類。一般優先取反切上字；
# f/bf/mf/pf 只在正韻明示輕脣聲母時覆蓋反切上字。
ZHENGYUN_INITIAL = {
    "p": "幫", "ph": "滂", "b": "並", "m": "明",
    "f": "非", "pf": "非", "bf": "奉", "mf": "微",
    "t": "端", "th": "透", "d": "定", "n": "泥",
    "tr": "知", "thr": "徹", "dr": "澄", "nr": "孃",
    "ts": "精", "tsh": "清", "dz": "從", "s": "心", "z": "邪",
    "tsr": "莊", "tshr": "初", "dzr": "崇", "sr": "生",
    "tc": "章", "tch": "昌", "dc": "澄", "c": "書", "zc": "常",
    "k": "見", "kh": "溪", "g": "羣", "ng": "疑",
    "h": "曉", "gh": "匣", "q": "影", "y": "以", "j": "日",
    "l": "來", "ny": "日",
}
LIGHT_LABIAL_ZY = {"f", "pf", "bf", "mf"}


class Ytenx:
    """kyonh（廣韻）＋ tcenghyonhtsen（洪武正韻）小韻表。"""

    TONES = {1: "平", 2: "上", 3: "去", 4: "入"}

    def __init__(self, root):
        base = os.path.join(root, "ytenx", "sync")
        ky = os.path.join(base, "kyonh")

        self.yonh_mux = {}            # 韻母 -> {gheh, deng, ho}
        for c in _rows(os.path.join(ky, "YonhMux.txt")):
            if len(c) >= 4:
                self.yonh_mux[c[0]] = {
                    "gheh": c[1], "deng": int(c[2]), "ho": c[3]}

        self.miuk_tone = {}           # 韻目 -> 平上去入
        for c in _rows(os.path.join(ky, "YonhMiuk.txt")):
            if len(c) >= 3:
                self.miuk_tone[strip_ab(c[0])] = self.TONES.get(int(c[2]))

        self.ky_xy = {}               # 小韻序 -> record
        self.ky_fq = defaultdict(list)   # 反切 -> [小韻序]
        for c in _rows(os.path.join(ky, "SieuxYonh.txt")):
            if len(c) < 6:
                continue
            ziox, taj, cjeng, mux, miuk = c[0], c[1], c[2], c[3], c[4]
            fq = c[5]
            rec = {"xiaoyun": int(ziox), "taj": taj, "initial": cjeng,
                   "final": mux, "miuk": strip_ab(miuk), "fanqie": fq}
            rec.update(self.yonh_mux.get(mux, {}))
            rec["mc_tone"] = self.miuk_tone.get(strip_ab(miuk))
            self.ky_xy[int(ziox)] = rec
            self.ky_fq[fq].append(int(ziox))

        self.ky_dzih = defaultdict(list)  # 字 -> [小韻序]
        for c in _rows(os.path.join(ky, "Dzih.txt")):
            if len(c) >= 2 and c[0]:
                try:
                    self.ky_dzih[c[0]].append(int(c[1]))
                except ValueError:
                    pass

        self.zy_fq = defaultdict(list)   # 正韻 反切 -> [record]
        zy = os.path.join(base, "tcenghyonhtsen", "SieuxYonh.txt")
        for c in _rows(zy):
            if len(c) < 7:
                continue
            self.zy_fq[c[3] + c[4]].append({
                "xiaoyun": int(c[0]), "taj": c[1], "miuk": c[2],
                "initial": c[5], "final": c[6]})

    def join_fanqie(self, speller, yun, ps=None):
        """反切＋韻目 → (method, record)。

        優先序：廣韻精確 → 正韻精確 → 廣韻同平水部（辭典慣以平水目稱
        鄰韻，如 歌↔戈、職↔德、卦↔夬）→ 正韻反切唯一（正韻自有 22 目，
        引文韻目常仍作切韻系名）。方法名如實標注，供下游過濾。
        """
        def same_yun(a, b):
            if ps is None:
                return a == b
            return ps.normalize_yun(a) == ps.normalize_yun(b)

        for ziox in self.ky_fq.get(speller, ()):
            rec = self.ky_xy[ziox]
            if same_yun(rec["miuk"], yun):
                return "廣韻反切", rec
        for rec in self.zy_fq.get(speller, ()):
            if same_yun(rec["miuk"], yun):
                return "正韻反切", rec
        if ps is not None:
            want = ps.lookup(yun)
            if want:
                for ziox in self.ky_fq.get(speller, ()):
                    rec = self.ky_xy[ziox]
                    got = ps.lookup(rec["miuk"])
                    if got and got["bu"] == want["bu"]:
                        return "廣韻反切·平水寬", rec
        zys = self.zy_fq.get(speller, ())
        if len(zys) == 1:
            return "正韻反切·寬", zys[0]
        return None, None

    def join_char(self, ch, cap=6):
        ids = self.ky_dzih.get(ch)
        if not ids:
            return None
        return [self.ky_xy[z] for z in ids[:cap]]

    def char_initial(self, ch):
        ids = self.ky_dzih.get(ch)
        if not ids:
            return None
        counts = defaultdict(int)
        for z in ids:
            rec = self.ky_xy.get(z)
            if rec and rec.get("initial"):
                counts[rec["initial"]] += 1
        if not counts:
            return None
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


# ---------------------------------------------------------------- 平水層
class Pingshui:
    def __init__(self):
        with open(os.path.join(HERE, "data", "kuangx_pingshui.json"),
                  encoding="utf-8") as f:
            kp = json.load(f)
        with open(os.path.join(HERE, "data", "pingshui_tl.json"),
                  encoding="utf-8") as f:
            pt = json.load(f)
        self.variants = kp["variants"]
        self.by_kuangx = {}           # 切韻系韻目 -> (平水部, 系, 調)
        self.bu = {}                  # 平水部 -> {series, tone}
        for bu, rec in kp["pingshui"].items():
            self.bu[bu] = {"series": rec["series"], "tone": rec["tone"]}
            for k in rec["kuangx"]:
                self.by_kuangx.setdefault(k, (bu, rec["series"], rec["tone"]))
            self.by_kuangx.setdefault(bu, (bu, rec["series"], rec["tone"]))
        self.series_tl = pt["series"]

    def normalize_yun(self, yun):
        return self.variants.get(yun, yun)

    def lookup(self, yun):
        """韻目（切韻系或平水）→ {bu, series, tone, expected_tl} | None"""
        hit = self.by_kuangx.get(self.normalize_yun(yun))
        if not hit:
            return None
        bu, series, tone = hit
        tl = self.series_tl.get(series, {})
        expected = tl.get("tl_ru" if tone == "入" else "tl", [])
        return {"bu": bu, "series": series, "tone": tone,
                "expected_tl": expected}


# ---------------------------------------------------------------- 反切 → 台羅文讀模擬
def unique(seq):
    out, seen = [], set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def taigi_literary_tone(mc_tone, voicing):
    yin = voicing in ("全清", "次清")
    if mc_tone == "平":
        return 1 if yin else 5
    if mc_tone == "上":
        return 7 if voicing == "全濁" else 2
    if mc_tone == "去":
        return 3 if yin else 7
    if mc_tone == "入":
        return 4 if yin else 8
    return None


def initial_category(entry, ytenx):
    join = entry.get("join") or {}
    rec = (join.get("candidates") or [join])[0]
    initial = rec.get("initial")
    method = join.get("method", "")

    if method.startswith("正韻") and initial in LIGHT_LABIAL_ZY:
        return ZHENGYUN_INITIAL.get(initial), "正韻輕脣聲母"

    speller = (entry.get("fanqie") or "").removesuffix("切")
    if speller:
        cat = ytenx.char_initial(speller[0])
        if cat:
            return cat, "反切上字"

    if initial in INITIAL_META:
        return initial, "小韻聲母"
    if initial in ZHENGYUN_INITIAL:
        return ZHENGYUN_INITIAL[initial], "正韻聲母"
    return None, None


def sim_confidence(method):
    if method in ("廣韻反切", "正韻反切"):
        return "high"
    if method in ("廣韻反切·平水寬", "正韻反切·寬"):
        return "medium"
    return "low"


def derive_sim_tl(entry, ytenx):
    """反切/中古地位 → 台羅文讀候選；不預測白話音。"""
    psrec = entry.get("pingshui") or {}
    finals = psrec.get("expected_tl") or []
    if not finals:
        return None

    join = entry.get("join") or {}
    rec = (join.get("candidates") or [join])[0]
    mc_tone = rec.get("mc_tone") or psrec.get("tone")
    if not mc_tone:
        return None

    cat, source = initial_category(entry, ytenx)
    meta = INITIAL_META.get(cat)
    if not meta:
        return None
    voicing, initials = meta
    tone = taigi_literary_tone(mc_tone, voicing)
    if tone is None:
        return None

    syllables = unique(
        f"{initial}{final}{tone}" for initial in initials for final in finals)
    return {
        "syllables": syllables,
        "initials": initials,
        "finals": finals,
        "tone": tone,
        "initial_category": cat,
        "voicing": voicing,
        "source": source,
        "confidence": sim_confidence(join.get("method")),
    }


# ---------------------------------------------------------------- 語域
REG_SPLIT = re.compile(r"[、，,/]")
KNOWN_REGS = {"文", "語", "白", "漳", "泉", "廈", "俗", "又", "又音", "今",
              "舊", "訓", "替", "罕用", "文白"}


def norm_registers(reg):
    if not reg:
        return []
    out = []
    for part in REG_SPLIT.split(reg):
        part = part.strip("　 ")
        if part in KNOWN_REGS:
            out.append(part)
    return out


# ---------------------------------------------------------------- 收集
class Collector:
    def __init__(self):
        # (han, tl) -> {"bopo": set, "poj": set, "regs": set,
        #               "n": int, "src": []}
        self.pairs = defaultdict(
            lambda: {"bopo": set(), "poj": set(), "regs": set(),
                     "n": 0, "src": []})
        self.mandarin = defaultdict(set)      # han -> {注音}
        self.mc = defaultdict(list)           # han -> [mc records]
        self.stats = defaultdict(int)

    def add_pair(self, han, tl, bopo=None, poj=None, regs=(), src=None):
        if not han or not tl or "-" in tl:
            return
        p = self.pairs[(han, tl)]
        if bopo:
            p["bopo"].add(bopo)
        if poj:
            p["poj"].add(poj)
        p["regs"].update(regs)
        p["n"] += 1
        if src and len(p["src"]) < 5 and src not in p["src"]:
            p["src"].append(src)
        self.stats["taigi_pairs"] += 1

    def add_mandarin(self, han, zhuyin, ):
        if han and zhuyin:
            self.mandarin[han].add(zhuyin)


def head_chars(head):
    """單字頭 → 索引用漢字列表（標準字優先；楷體造字取 mapping 字）。"""
    if not head:
        return []
    out = []
    for c in head.get("chars", []):
        ch = c.get("char")
        if ch and HAN_RE.match(ch):
            out.append(ch)
    return out

def load_extra_chars(path):
    """額外字頭表：讀入需要 ytenx 字頭歸小韻補足的漢字。"""
    if not path or not os.path.isfile(path):
        return []
    chars, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0]
            for m in HAN_RE.finditer(line):
                ch = m.group(0)
                if ch not in seen:
                    seen.add(ch)
                    chars.append(ch)
    return chars


def add_ytenx_char_fallback(coll, ytenx, ps, ch):
    """For explicit extra chars, add an MC-only ytenx fallback if it yields TL."""
    if any((e.get("sim_tl") or {}).get("syllables")
           for e in coll.mc.get(ch, [])):
        coll.stats["extra_char_has_sim_tl"] += 1
        return False
    cands = ytenx.join_char(ch)
    if not cands:
        coll.stats["extra_char_no_ytenx"] += 1
        return False
    fb = {"join": {"method": "字頭歸小韻·外字",
                   "candidates": [
                       {k: v for k, v in c.items() if k != "fanqie"}
                       for c in cands]}}
    lookups = [b for b in (ps.lookup(c["miuk"]) for c in cands) if b]
    if lookups and len({b["bu"] for b in lookups}) == 1:
        fb["pingshui"] = lookups[0]
    sim = derive_sim_tl(fb, ytenx)
    if not sim:
        coll.stats["extra_char_no_sim_tl"] += 1
        return False
    fb["sim_tl"] = sim
    coll.mc[ch].append(fb)
    coll.stats["extra_char_fallback"] += 1
    coll.stats["sim_tl"] += 1
    return True

def collect_volume(vol_id, data, coll, ytenx, ps):
    for chap in data.get("chapters", []):
        for hz in chap.get("hanzi_entries", []):
            head = hz.get("head") or {}
            chars = head_chars(head)
            anchor = chars[0] if chars else None
            src = f"{vol_id}:{head.get('display', '?')}"

            # 字頭注音字形 = 國音
            for g in head.get("ruby", []):
                if anchor and g.get("bopo"):
                    coll.add_mandarin(anchor, g["bopo"])

            # 讀音列
            for label, recs in (hz.get("readings") or {}).items():
                for rec in recs:
                    for seg in rec.get("segments", []):
                        regs = norm_registers(seg.get("register"))
                        for g in seg.get("glyphs", []):
                            if not anchor:
                                continue
                            if label == "國音":
                                coll.add_mandarin(anchor, g.get("bopo"))
                            elif g.get("lang") == "nan" and g.get("tl"):
                                coll.add_pair(
                                    anchor, g["tl"], g.get("bopo"),
                                    g.get("poj"), regs, src + f"({label})")

            # 中古層：反切 join
            mc_seen = set()
            for cite in head.get("fanqie", []):
                yun = ps.normalize_yun(cite["yun"])
                method, rec = ytenx.join_fanqie(cite["speller"], yun, ps)
                entry = {"fanqie": cite["speller"] + "切",
                         "yun": cite["yun"], "source": cite.get("source")}
                if method:
                    entry["join"] = {"method": method, **{
                        k: v for k, v in rec.items() if k != "fanqie"}}
                    coll.stats[f"join_{method}"] += 1
                else:
                    coll.stats["join_none"] += 1
                psrec = ps.lookup(cite["yun"])
                if psrec:
                    entry["pingshui"] = psrec
                sim = derive_sim_tl(entry, ytenx)
                if sim:
                    entry["sim_tl"] = sim
                    coll.stats["sim_tl"] += 1
                key = (entry["fanqie"], entry["yun"])
                if anchor and key not in mc_seen:
                    mc_seen.add(key)
                    coll.mc[anchor].append(entry)

            # 未有精確 join → 字頭歸小韻（廣韻 Dzih fallback；含無引註字）
            if anchor and not any(
                    "join" in e for e in coll.mc.get(anchor, [])):
                cands = ytenx.join_char(anchor)
                if cands:
                    coll.stats["join_char_fallback"] += 1
                    fb = {"join": {"method": "字頭歸小韻",
                                   "candidates": [
                                       {k: v for k, v in c.items()
                                        if k != "fanqie"} for c in cands]}}
                    lookups = [b for b in
                               (ps.lookup(c["miuk"]) for c in cands) if b]
                    if lookups and len({b["bu"] for b in lookups}) == 1:
                        fb["pingshui"] = lookups[0]
                    sim = derive_sim_tl(fb, ytenx)
                    if sim:
                        fb["sim_tl"] = sim
                        coll.stats["sim_tl"] += 1
                    coll.mc[anchor].append(fb)

            # 詞條 tokens
            for w in hz.get("word_entries", []):
                wsrc = f"{vol_id}:{w.get('entry', '')[:12]}"
                for s in w.get("sentences", []):
                    for t in s.get("tokens", []):
                        if t.get("kind") != "han":
                            continue
                        for pron in t.get("pron", []):
                            if pron.get("lang") == "nan" and pron.get("tl"):
                                coll.add_pair(
                                    t["han"], pron["tl"], t["ruby"][0],
                                    pron.get("poj"), (), wsrc)
                            elif pron.get("lang") == "cmn":
                                coll.add_mandarin(t["han"], t["ruby"][0])


# ---------------------------------------------------------------- 輸出
def build_outputs(coll, out_dir, meta, attest=None, dialects=None):
    han = defaultdict(lambda: {"mandarin": [], "taigi": [], "mc": []})
    tl_index = defaultdict(list)

    att_pairs = att_tokens = tot_tokens = 0
    for (ch, tl), p in coll.pairs.items():
        tags = sorted(attest.get((ch, tl), ())) if attest else []
        w = p["n"] + sum(DICT_WEIGHT.get(t, 0) for t in tags)
        tot_tokens += p["n"]
        if tags:
            att_pairs += 1
            att_tokens += p["n"]
        rec = {
            "tl": tl,
            "bopo": sorted(p["bopo"]),
            "poj": sorted(p["poj"]),
            "registers": sorted(p["regs"]),
            "n": p["n"],
            "w": w,
            "sources": p["src"],
        }
        if tags:
            rec["attest"] = tags
        if dialects:
            dia = sorted(dialects.get((ch, tl), ()))
            if dia:
                rec["dialects"] = dia
        han[ch]["taigi"].append(rec)
    for ch, zy in coll.mandarin.items():
        han[ch]["mandarin"] = sorted(zy)
    for ch, mcs in coll.mc.items():
        seen, out = set(), []
        for e in mcs:
            key = json.dumps(
                {k: e.get(k) for k in ("fanqie", "yun", "source")},
                ensure_ascii=False, sort_keys=True) if e.get("fanqie") \
                else ("fb" if "join" in e else "x")
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
        han[ch]["mc"] = out

    for ch in han:
        han[ch]["taigi"].sort(key=lambda r: (-r["w"], -r["n"]))
        bu = sorted({e["pingshui"]["bu"] for e in han[ch]["mc"]
                     if "pingshui" in e})
        if bu:
            han[ch]["pingshui"] = bu
        for r in han[ch]["taigi"]:
            e = {"han": ch, "n": r["n"], "w": r["w"],
                 "registers": r["registers"]}
            if "attest" in r:
                e["attest"] = r["attest"]
            tl_index[r["tl"]].append(e)

    for syl in tl_index:
        tl_index[syl].sort(key=lambda r: (-r["w"], -r["n"]))

    if attest is not None:
        meta["stats"]["attest_pairs"] = att_pairs
        meta["stats"]["attest_pair_pct"] = round(
            att_pairs / max(len(coll.pairs), 1) * 100, 1)
        meta["stats"]["attest_token_pct"] = round(
            att_tokens / max(tot_tokens, 1) * 100, 1)

    os.makedirs(out_dir, exist_ok=True)
    uni = {
        "_meta": meta,
        "han": {ch: han[ch] for ch in sorted(han)},
        "tl": {s: tl_index[s] for s in sorted(tl_index)},
    }
    with open(os.path.join(out_dir, "unified_phonology.json"), "w",
              encoding="utf-8") as f:
        json.dump(uni, f, ensure_ascii=False, indent=1)

    with open(os.path.join(out_dir, "han_to_tl.tsv"), "w",
              encoding="utf-8") as f:
        f.write("#漢字\t台羅\t方音\t白話字\t語域\t次數\t權重\t佐證\t腔別\t例源\n")
        for ch in sorted(han):
            for r in han[ch]["taigi"]:
                f.write("\t".join([
                    ch, r["tl"], "/".join(r["bopo"]), "/".join(r["poj"]),
                    "/".join(r["registers"]), str(r["n"]), str(r["w"]),
                    ",".join(r.get("attest", [])),
                    ",".join(r.get("dialects", [])),
                    ";".join(r["sources"][:3])]) + "\n")

    with open(os.path.join(out_dir, "tl_to_han.tsv"), "w",
              encoding="utf-8") as f:
        f.write("#台羅\t漢字（按次數）\n")
        for syl in sorted(tl_index):
            f.write(syl + "\t" + " ".join(
                r["han"] for r in tl_index[syl]) + "\n")

    if attest is not None:
        gaps = [(ch, r) for ch, v in han.items() for r in v["taigi"]
                if "attest" not in r and r["n"] >= 10]
        gaps.sort(key=lambda x: -x[1]["n"])
        with open(os.path.join(out_dir, "chhoetaigi_gaps.tsv"), "w",
                  encoding="utf-8") as f:
            f.write("#高頻但無 ChhoeTaigi 佐證的讀音對（轉換問題或 koktai 特有讀）\n"
                    "#漢字\t台羅\t次數\t方音\t語域\t例源\n")
            for ch, r in gaps:
                f.write("\t".join([
                    ch, r["tl"], str(r["n"]), "/".join(r["bopo"]),
                    "/".join(r["registers"]),
                    ";".join(r["sources"][:3])]) + "\n")
        print(f"[index] ChhoeTaigi 佐證：{meta['stats']['attest_pairs']} 對 "
              f"（對 {meta['stats']['attest_pair_pct']}% / "
              f"token {meta['stats']['attest_token_pct']}%）；"
              f"高頻缺口 {len(gaps)} 筆 → chhoetaigi_gaps.tsv", file=sys.stderr)

    return uni


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="json/*.json")
    ap.add_argument("--ytenx", default=os.path.expanduser("~/dev/ytenx"))
    ap.add_argument("--out", default="index")
    ap.add_argument("--chhoetaigi", default=CT_DIR,
                    help="ChhoeTaigi CSV 目錄；不存在時自動略過佐證層")
    ap.add_argument("--sutian", default=SUTIAN_ODS,
                    help="教育部詞彙比較表 .ods；不存在時自動略過方言腔層")
    ap.add_argument("--moe-dir", default=None,
                    help="教育部附錄（新詞/共同詞/俗諺 *.ods）目錄；"
                         "預設同 --sutian 所在目錄")
    ap.add_argument("--chhiankimpho", default=CKP_MD,
                    help="千金譜 Markdown 檔路徑；不存在時自動略過")
    ap.add_argument("--extra-chars", default=DEFAULT_EXTRA_CHARS,
                    help="額外漢字清單；存在時以 ytenx 字頭歸小韻補 MC-only 文讀候選")
    args = ap.parse_args()

    ytenx = Ytenx(args.ytenx)
    ps = Pingshui()
    coll = Collector()

    attest = None
    if os.path.isdir(args.chhoetaigi):
        attest, att_stats = load_attestation(args.chhoetaigi)
        print(f"[index] ChhoeTaigi 佐證表：{att_stats['pairs']} (漢字,台羅) 對",
              file=sys.stderr)

    dialects = None
    if os.path.isfile(args.sutian):
        su_att, dialects, su_stats = load_sutsha(args.sutian)
        print(f"[index] 教育部詞彙比較：{su_stats['aligned']}/{su_stats['rows']} 列"
              f"對齊，{su_stats['pairs']} (漢字,台羅) 對", file=sys.stderr)
        if attest is None:
            attest = {}
        for k, v in su_att.items():
            attest.setdefault(k, set()).update(v)

    moe_dir = args.moe_dir or os.path.dirname(os.path.abspath(args.sutian))
    app_att, app_stats = load_appendices(moe_dir) \
        if os.path.isdir(moe_dir) else ({}, {})
    if app_att:
        if attest is None:
            attest = {}
        for k, v in app_att.items():
            attest.setdefault(k, set()).update(v)
        for tag, st in app_stats.items():
            print(f"[index] 教育部附錄 {tag}（{st['label']}）："
                  f"{st['aligned']}/{st['rows']} 列，{st['pairs']} 對"
                  f"（{st['file']}）", file=sys.stderr)

    if os.path.isfile(args.chhiankimpho):
        ckp_att, ckp_stats = load_chhiankimpho(args.chhiankimpho)
        print(f"[index] 千金譜：{ckp_stats['aligned']}/{ckp_stats['lines']} 行"
              f"對齊，{ckp_stats['pairs']} (漢字,台羅) 對", file=sys.stderr)
        if attest is None:
            attest = {}
        for k, v in ckp_att.items():
            attest.setdefault(k, set()).update(v)

    files = sorted(glob.glob(args.json))
    vols = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"[skip] {path}: 非 JSON", file=sys.stderr)
                continue
        if not isinstance(data, dict) or data.get("format") != "koktai-dic/2":
            print(f"[skip] {path}: 非 koktai-dic/2", file=sys.stderr)
            continue
        vol_id = os.path.splitext(os.path.basename(path))[0]
        vols.append(vol_id)
        collect_volume(vol_id, data, coll, ytenx, ps)

    extra_chars = load_extra_chars(args.extra_chars)
    if extra_chars:
        added = sum(1 for ch in extra_chars
                    if add_ytenx_char_fallback(coll, ytenx, ps, ch))
        print(f"[index] 額外字頭：{added}/{len(extra_chars)} 字加入 ytenx fallback",
              file=sys.stderr)

    meta = {
        "generator": "a-tsioh_sandbox/build_unified_index.py",
        "volumes": vols,
        "sources": {
            "koktai": "《國臺對照活用辭典》 koktai-dic/2 JSON",
            "ytenx_kyonh": "廣韻小韻/單字表（韻典網資料）",
            "ytenx_tcenghyonhtsen": "洪武正韻牋小韻表（韻典網資料）",
            "pingshui": "ExternalRef/平水韻注音符號編碼.pdf（王庚春）",
            "chhoetaigi": None if attest is None else
                "ExternalRef/ChhoeTaigiDatabase/（ChhoeTaigi 開放辭典 CSV；"
                "佐證標籤=辭典，權重法仿 ch2taigi）",
            "sutian_sutsha": None if dialects is None else
                "ExternalRef/詞彙比較表.ods（教育部台語辭典附錄「詞彙比較」；"
                "十腔別；佐證標籤=比）",
            "sutian_appendices": None if not app_att else {
                tag: f"{st['label']}（{st['file']}）"
                for tag, st in app_stats.items()},
            "chhiankimpho": None if not os.path.isfile(args.chhiankimpho) else
                "ExternalRef/chhian-kim-pho2.md（《千金譜》limkianhui 校訂版；"
                "POJ→台羅轉換；佐證標籤=金，權重=2）",
            "extra_chars": None if not os.path.isfile(args.extra_chars) else
                f"{os.path.relpath(args.extra_chars)}（文學語料額外字頭；"
                "ytenx 字頭歸小韻；MC-only 文讀候選）",
        },
        "stats": dict(coll.stats),
    }
    uni = build_outputs(coll, args.out, meta, attest=attest, dialects=dialects)

    n_han = len(uni["han"])
    n_tl = len(uni["tl"])
    print(f"[index] 漢字 {n_han} / 台羅音節 {n_tl} / "
          f"讀音對 {sum(len(v['taigi']) for v in uni['han'].values())}",
          file=sys.stderr)
    for k, v in sorted(coll.stats.items()):
        print(f"[index]   {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()
