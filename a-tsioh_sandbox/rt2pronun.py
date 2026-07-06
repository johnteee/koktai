#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import re
import unicodedata


# --- 對照表定義 ---

# 臺灣閩南語羅馬字拼音對照吳守禮方音聲母表
initial_map_tl_to_bopo = {
    'p': 'ㄅ', 'ph': 'ㄆ', 'm': 'ㄇ', 'b': 'ㆠ',
    't': 'ㄉ', 'th': 'ㄊ', 'n': 'ㄋ', 'l': 'ㄌ',
    'k': 'ㄍ', 'kh': 'ㄎ', 'ng': 'ㄫ', 'g': 'ㆣ', 'h': 'ㄏ',
    'ts': 'ㄗ', 'tsh': 'ㄘ', 's': 'ㄙ', 'j': 'ㆡ',
    'tsi': 'ㄐ', 'tshi': 'ㄑ', 'si': 'ㄒ', 'ji': 'ㆢ',
    '': '',  # 代表無聲母
    
    # 非台語
    'f': 'ㄈ', 
    'zh': 'ㄓ', 'ch': 'ㄔ', 'sh': 'ㄕ', 'r': 'ㄖ',
}

# 臺灣閩南語羅馬字拼音對照吳守禮方音韻母表
final_map_tl_to_bopo = {
    'a': 'ㄚ', 'e': 'ㆤ', 'i': 'ㄧ', 'oo': 'ㆦ', 'o': 'ㄜ', 'u': 'ㄨ',
    'ai': 'ㄞ', 'au': 'ㄠ', 'ia': 'ㄧㄚ',
    'io': 'ㄧㄜ', 'iu': 'ㄧㄨ', 'ua': 'ㄨㄚ', 'ue': 'ㄨㆤ', 'ui': 'ㄨㄧ',
    'iau': 'ㄧㄠ', 'uai': 'ㄨㄞ',
    'ann': 'ㆩ', 'enn': 'ㆥ', 'inn': 'ㆪ', 'onn': 'ㆧ',
    'm': 'ㆬ', 'ng': 'ㆭ', 'ainn': 'ㆮ', 'iann': 'ㄧㆩ', 'iaunn': 'ㄧㆯ',
    'iunn': 'ㄧㆫ', 'uann': 'ㄨㆩ', 'uannh': 'ㄨㆩㆷ', 'uainn': 'ㄨㆮ',
    'am': 'ㆰ', 'an': 'ㄢ', 'ang': 'ㄤ',
    'im': 'ㄧㆬ', 'in': 'ㄧㄣ', 'ing': 'ㄧㄥ',
    'om': 'ㆱ', 'ong': 'ㆲ', 'iam': 'ㄧㆰ',
    'ian': 'ㄧㄢ', 'iang': 'ㄧㄤ', 'iong': 'ㄧㆲ',
    'un': 'ㄨㄣ', 'uan': 'ㄨㄢ',
    'ah': 'ㄚㆷ', 'eh': 'ㆤㆷ', 'ih': 'ㄧㆷ', 'oh': 'ㄜㆷ', 'uh': 'ㄨㆷ', 'auh': 'ㄠㆷ', 'iah': 'ㄧㄚㆷ',
    'ioh': 'ㄧㄜㆷ', 'iuh': 'ㄧㄨㆷ', 'iauh': 'ㄧㄠㆷ',
    'uah': 'ㄨㄚㆷ', 'ueh': 'ㄨㆤㆷ', 'ooh': 'ㆦㆷ',
    'annh': 'ㆩㆷ', 'ennh': 'ㆥㆷ', 'innh': 'ㆪㆷ', 'mh': 'ㆬㆷ', 'iannh': 'ㄧㆩㆷ', 'ngh': 'ㆭㆷ',
    'ap': 'ㄚㆴ', 'at': 'ㄚㆵ', 'ak': 'ㄚㆶ', 'op': 'ㆦㆴ', 'ok': 'ㆦㆶ', 'iok': 'ㄧㆦㆶ',
    'ip': 'ㄧㆴ', 'it': 'ㄧㆵ', 'ik': 'ㄧㆶ', 'iap': 'ㄧㄚㆴ', 'iat': 'ㄧㄚㆵ', 'iak': 'ㄧㄚㆶ',
    'ut': 'ㄨㆵ', 'uat': 'ㄨㄚㆵ',
    'ioo': 'ㄧㆦ', 'iooh': 'ㄧㆦㆷ',
    'ir': 'ㆨ', 'irh': 'ㆨㆷ', 'irp': 'ㆨㆴ', 'irt': 'ㆨㆵ', 'irk': 'ㆨㆶ',
    'irinn': 'ㆨㆪ', 'irm': 'ㆨㆬ', 'irn': 'ㆨㄣ', 'irng': 'ㆨㄥ',
    'er': 'ㄮ', 'ere': 'ㄮㆤ', 'erh': 'ㄮㆷ', 'ereh': 'ㄮㆤㆷ', 'erm': 'ㄮㆬ',
    'ee': 'ㄝ', 'uee': 'ㄨㄝ', 'eeh': 'ㄝㆷ', 'eng': 'ㄝㄥ',
    'or': 'ㄛ', 'orh': 'ㄛㆷ', 'ior': 'ㄧㄛ', 'iorh': 'ㄧㄛㆷ',
    'ie': 'ㄧㄝ',
    'uinn': 'ㄨㆪ', 'ionn': 'ㄧㆧ', 'uang': 'ㄨㄤ',
    'aih': 'ㄞㆷ', 'ainnh': 'ㆮㆷ', 'aunnh': 'ㆯㆷ', 'uih': 'ㄨㄧㆷ',
    'aunn': 'ㆯ', 'uenn': 'ㄨㆥ', 'uaih': 'ㄨㄞㆷ',
    'iunnh': 'ㄧㆫㆷ', 'iaunnh': 'ㄧㆯㆷ', 'uennh': 'ㄨㆥㆷ', 'uinnh': 'ㄨㆪㆷ', 'uainnh': 'ㄨㆮㆷ',
    'iut': 'ㄧㄨㆵ', 'uak': 'ㄨㄚㆶ', 'onnh': 'ㆧㆷ',
    'oi': 'ㆦㄧ', 'oih': 'ㆦㄧㆷ',

    # 注意：勿在此加入與台語鍵重複的「非台語」鍵（v1 的 'ong':'ㄥ'、'er':'ㄦ'
    # 曾覆蓋 'ong':'ㆲ'、'er':'ㄮ'，導致所有 ㆲ 韻被反查成 onn）。
    '': '',  # 代表無韻母
}

# 臺灣閩南語羅馬字拼音對照吳守禮方音聲調表
tone_map_tl_to_bopo = {
    '1': '', '2': 'ˋ', '3': '˪', '4': '',
    '5': 'ˊ', '6': '˫', '7': '˫', '8': '㆐', '9': '^',
    '0': '˙',  # 輕聲
    '10': '㆐' # 第8聲的另一種形式
}

教會系羅馬音標聲調符號表 = {
    'á': ('a', '2'), 'à': ('a', '3'), 'â': ('a', '5'), 'ǎ': ('a', '6'),
    'ā': ('a', '7'), 'a̍': ('a', '8'), 'a̋': ('a', '9'),
    'é': ('e', '2'), 'è': ('e', '3'), 'ê': ('e', '5'), 'ě': ('e', '6'),
    'ē': ('e', '7'), 'e̍': ('e', '8'), 'e̋': ('e', '9'),
    'í': ('i', '2'), 'ì': ('i', '3'), 'î': ('i', '5'), 'ǐ': ('i', '6'),
    'ī': ('i', '7'), 'ı̍': ('i', '8'), 'i̍': ('i', '8'), 'i̋': ('i', '9'),
    'ó': ('o', '2'), 'ò': ('o', '3'), 'ô': ('o', '5'), 'ǒ': ('o', '6'),
    'ō': ('o', '7'), 'o̍': ('o', '8'), 'ő': ('o', '9'),
    'ó͘': ('oo', '2'), 'ò͘': ('oo', '3'), 'ô͘': ('oo', '5'), 'ǒ͘': ('oo', '6'),
    'ō͘': ('oo', '7'), 'o̍͘': ('oo', '8'), 'ő͘': ('oo', '9'),
    'ú': ('u', '2'), 'ù': ('u', '3'), 'û': ('u', '5'), 'ǔ': ('u', '6'),
    'ū': ('u', '7'), 'u̍': ('u', '8'), 'ű': ('u', '9'),
    'ḿ': ('m', '2'), 'm̀': ('m', '3'), 'm̂': ('m', '5'), 'm̌': ('m', '6'),
    'm̄': ('m', '7'), 'm̍': ('m', '8'), 'm̋': ('m', '9'),
    'ń': ('n', '2'), 'ǹ': ('n', '3'), 'n̂': ('n', '5'), 'ň': ('n', '6'),
    'n̄': ('n', '7'), 'n̍': ('n', '8'), 'n̋': ('n', '9'), 'ň': ('n', '6'),
}

# --- 建立反向對照表 (方音 -> 羅馬拼音) ---

# 移除空值並反轉聲母表
bopo_to_initial_map = {v: k.replace('i', '') for k, v in initial_map_tl_to_bopo.items() if v}

# 移除空值並反轉韻母表
bopo_to_final_map = {v: k for k, v in final_map_tl_to_bopo.items() if v}

# 吳守禮寫法補充（僅反查方向）：ㄧㆤㆶ=ik、ㄮ=er(泉腔)、ㄦ 併入 er
bopo_to_final_map.update({'ㄧㆤㆶ': 'ik', 'ㄮ': 'er', 'ㄦ': 'er'})

# 處理聲調對照表的重複值，建立唯一的反向對照
bopo_to_tone_map = {
    'ˋ': '2', '˪': '3', 'ˊ': '5',
    '˫': '7',  # 6、7聲同符號，依慣例使用7
    '㆐': '8',  # 8、10聲同符號，依慣例使用8
    '^': '9', '˙': '0'
}

# 將方音韻母依長度降序排序，確保優先匹配最長的韻母
# 例如：優先匹配 "ㄨㆩㆷ" (uannh) 而不是 "ㄨ" (u)
sorted_bopo_finals = sorted(bopo_to_final_map.keys(), key=len, reverse=True)

# --- 轉換邏輯 ---

def 取得白話字韻母調符對照表():
    結果 = {
        ('a', '9'): 'ă', ('e', '9'): 'ĕ', ('i', '9'): 'ĭ',
        ('o', '9'): 'ŏ', ('o͘', '9'): 'ŏ͘', ('u', '9'): 'ŭ',
        ('m', '9'): 'm̆', ('n', '9'): 'n̆',
    }
    for 白話字傳統調, 臺羅組 in 教會系羅馬音標聲調符號表.items():
        if 白話字傳統調 == 'ı̍':
            # i8有兩種unicode，踢掉跟教典不同的。
            continue

        臺羅, 數字調 = 臺羅組
        新鍵值 = 臺羅組
        if 臺羅 == 'oo':
            新鍵值 = ('o͘', 數字調)
        if 數字調 != '9':
            結果.update({新鍵值: 白話字傳統調})
    return 結果
class 臺羅轉白話字():
    白話字韻母調符對照表 = 取得白話字韻母調符對照表()

    @classmethod
    def 轉白話字(cls, 聲, 韻, 調):
        白話字聲 = cls.轉白話字聲(聲)
        白話字韻 = cls.轉白話字韻(韻)
        白話字傳統調韻 = cls.白話字韻標傳統調(白話字韻, 調)
        return (
            白話字聲 +
            白話字傳統調韻
        )

    @classmethod
    def 轉白話字聲(cls, 聲):
        白話字聲 = None
        if 聲 == 'ts':
            白話字聲 = 'ch'
        elif 聲 == 'tsh':
            白話字聲 = 'chh'
        else:
            白話字聲 = 聲
        return 白話字聲

    @classmethod
    def 轉白話字韻(cls, 韻):
        白話字韻 = None
        # 母音
        if 'oo' in 韻:
            白話字韻 = 韻.replace('oo', 'o͘')
        elif 'ua' in 韻:
            白話字韻 = 韻.replace('ua', 'oa')
        elif 'ue' in 韻:
            白話字韻 = 韻.replace('ue', 'oe')
        elif 'ing' in 韻 or 'ik' in 韻:
            白話字韻 = 韻.replace('i', 'e')
        elif 'ir' in 韻:
            白話字韻 = 韻.replace('ir', 'ṳ')       # 泉腔（ChhoeTaigi 擴充白話字慣例）
        elif 'er' in 韻:
            白話字韻 = 韻.replace('er', 'o\u0324')  # 泉腔 o̤
        elif 'or' in 韻:
            白話字韻 = 韻.replace('or', 'o\u0324')  # ㄛ：ChhoeTaigi 同記 o̤
        else:
            # oo, au, ia, ai
            白話字韻 = 韻
        # 鼻化音
        if 'nnh' in 韻:
            白話字韻 = 白話字韻.replace('nnh', 'ⁿh')
        elif 'nn' in 韻:
            白話字韻 = 白話字韻.replace('nn', 'ⁿ')
        return 白話字韻

    母音字母 = set('aeiouṳ')
    調符組合符 = {'2': '\u0301', '3': '\u0300', '5': '\u0302', '6': '\u030c',
                  '7': '\u0304', '8': '\u030d', '9': '\u0306'}

    @staticmethod
    def _韻單位(白話字韻):
        """拆成標調單位：基底字母＋附著記號（o͘ 的 ͘、o̤ 的 ̤）。"""
        單位 = []
        for 字 in 白話字韻:
            if 單位 and 字 in ('\u0358', '\u0324'):
                單位[-1] += 字
            else:
                單位.append(字)
        return 單位

    @classmethod
    def _取標調位(cls, 單位):
        """標調位規則（以 ChhoeTaigi PojUnicode 黃金對驗證）：
        o͘ 最優先；三元音 iau/oai 標 a；i 開頭雙元音標第二母音；
        oa/oe 有子音韻尾（h/p/t/k/m/n/ng，鼻化 ⁿ 不算）標 a/e、無則標 o；
        其餘雙元音（ai/au/ui…）標第一母音；無母音 ng→n、m→m。"""
        母音位 = [i for i, u in enumerate(單位) if u[0] in cls.母音字母]
        if not 母音位:
            for i, u in enumerate(單位):
                if u == 'n':
                    return i
            for i, u in enumerate(單位):
                if u == 'm':
                    return i
            return None
        for i in 母音位:
            if 單位[i].endswith('\u0358'):
                return i
        母音 = ''.join(單位[i][0] for i in 母音位)
        有韻尾 = any(u[0] in 'hptkmn' for u in 單位[母音位[-1] + 1:])
        if 母音 in ('iau', 'oai'):
            return 母音位[1]
        if len(母音) >= 2:
            if 母音[0] == 'i':
                return 母音位[1]
            if 母音[:2] in ('oa', 'oe'):
                return 母音位[1] if 有韻尾 else 母音位[0]
            return 母音位[0]
        return 母音位[0]

    @classmethod
    def 白話字韻標傳統調(cls, 白話字韻無調, 調):
        if 調 in ('1', '4') or not 白話字韻無調:
            return 白話字韻無調
        單位 = cls._韻單位(白話字韻無調)
        位 = cls._取標調位(單位)
        if 位 is None:
            return 白話字韻無調
        單位[位] = cls.加上白話字調符(單位[位], 調)
        return ''.join(單位)

    @classmethod
    def 加上白話字調符(cls, 標調單位, 調):
        if (標調單位, 調) in cls.白話字韻母調符對照表:
            return cls.白話字韻母調符對照表[(標調單位, 調)]
        if 調 in cls.調符組合符:
            # 表外字母（ṳ、o̤…）：基底後接組合調符，NFC 正規重排
            return unicodedata.normalize('NFC', 標調單位 + cls.調符組合符[調])
        return 標調單位

tl2poj_converter = 臺羅轉白話字()

# 國語專用符號（台語方音不用）→ 用於分類 ruby 語言
MANDARIN_ONLY = set('ㄓㄔㄕㄖㄦㄩㄟㄡㄈ')
TONE8_DOT = '\u0358'   # ◌ ͘ 第8調（陽入）右上點


def analyze_bopo(bopo_string):
    """方音字串（可多音節）→ 分析結果 dict。

    回傳:
      {"lang": "nan",     "tl": …, "poj": …}            台語，全部轉出
      {"lang": "partial", "tl": …, "poj": …, "errors"}  部分轉出
      {"lang": "cmn"}                                    國語注音（不轉台羅）
      {"lang": "unknown", "errors": […]}                 無法解析
    """
    s = bopo_string.replace('〾', '')
    if 'ˇ' in s or any(c in MANDARIN_ONLY for c in s):
        return {'lang': 'cmn'}

    tls, pojs, errors = [], [], []
    i = 0
    pending_neutral = False
    while i < len(s):
        ch = s[i]
        if ch in ' \u3000\u00a0':
            i += 1
            continue
        if ch == '˙':                      # 前置輕聲點
            pending_neutral = True
            i += 1
            continue
        if ch == TONE8_DOT:                # 游離的第8調點
            i += 1
            continue

        roman_initial = ''
        if s[i] in bopo_to_initial_map:
            roman_initial = bopo_to_initial_map[s[i]]
            i += 1

        roman_final = ''
        found_final = False
        for final in sorted_bopo_finals:   # 最長匹配
            if s.startswith(final, i):
                roman_final = bopo_to_final_map[final]
                i += len(final)
                found_final = True
                break
        if not found_final:
            errors.append(f'{bopo_string}@{i}')
            i += 1
            continue

        # 聲調：容許「(空白)◌ ͘」= 第8調
        tone_number = ''
        j = i
        while j < len(s) and s[j] in ' \u3000\u00a0':
            j += 1
        if j < len(s) and s[j] == TONE8_DOT:
            tone_number = '8'
            i = j + 1
        elif i < len(s) and s[i] in bopo_to_tone_map:
            tone_number = bopo_to_tone_map[s[i]]
            i += 1
        elif roman_final.endswith(('p', 't', 'k', 'h')):
            tone_number = '4'
        else:
            tone_number = '1'
        if pending_neutral:
            tone_number = '0'
            pending_neutral = False

        tls.append(f'{roman_initial}{roman_final}{tone_number}')
        pojs.append(tl2poj_converter.轉白話字(
            roman_initial, roman_final, tone_number))

    if not tls:
        return {'lang': 'unknown', 'errors': errors or ['empty']}
    out = {'lang': 'partial' if errors else 'nan',
           'tl': '-'.join(tls), 'poj': '-'.join(pojs)}
    if errors:
        out['errors'] = errors
    return out


def convert_bopo_to_tl(bopo_string):
    """相容包裝：回傳 (tl, poj)；非台語/無法解析 → ('', '')。"""
    a = analyze_bopo(bopo_string)
    return a.get('tl', ''), a.get('poj', '')



RT_TOKEN_RE = re.compile(
    r"(?P<rt><rt>(?P<ruby>.*?)</rt>)"
    r"|(?P<glyph><glyph:(?P<gid>[^>]+)>)"
    r"|(?P<mark><mark>&#x(?P<mhex>[0-9a-fA-F]+);</mark>)"
    r"|(?P<char>.)",
    re.S)

HAN_RE = re.compile(r"[\u3400-\u9fff\U00020000-\U0002FFFF\u2460-\u2473\ufffd]")


def tokenize_ruby(text):
    """帶 <rt> 標記文字 → 對齊 tokens（漢字↔方音↔台羅↔白話字）。

    規則：
      * <rt> 附著於其前最近的基底單位（漢字／<mark>字形／<glyph:…>）。
      * 「／<rt>…」「/(替字)<rt>…」視為前一 token 的又讀。
      * 「·」（輕聲點）記於 token.neutral。
      * 無法對齊的 <rt> 進 token(han=None) —— 不丟。
    """
    tokens = []
    base = None          # 待附著基底：(kind, value)
    pending_alt = False  # 前一個非空白字元是「/」
    pending_neutral = False

    def new_token(ruby):
        t = {"han": base[1] if base else None,
             "kind": base[0] if base else None,
             "ruby": [ruby]}
        if pending_neutral:
            t["neutral"] = True
        tokens.append(t)

    for m in RT_TOKEN_RE.finditer(text):
        if m.group("rt"):
            ruby = m.group("ruby")
            if pending_alt and tokens and base is None:
                tokens[-1]["ruby"].append(ruby)      # 又讀
            elif base is None and tokens and tokens[-1]["kind"] is None:
                tokens[-1]["ruby"].append(ruby)
            else:
                new_token(ruby)
            base = None
            pending_alt = False
            pending_neutral = False
            continue
        if m.group("glyph"):
            base = ("glyph", m.group("gid"))
            pending_alt = False
            continue
        if m.group("mark"):
            base = ("pua", "&#x%s;" % m.group("mhex").lower())
            pending_alt = False
            continue
        ch = m.group("char")
        if ch == "/":
            pending_alt = True
            continue
        if ch == "·":
            pending_neutral = True
            continue
        if HAN_RE.match(ch):
            base = ("han", ch)
            pending_alt = False
            pending_neutral = False
        elif ch.strip() and ch not in "()（）":
            base = None
            pending_alt = False
    return tokens


def enrich_tokens(tokens):
    for t in tokens:
        t["pron"] = [analyze_bopo(r) for r in t["ruby"]]
        langs = {p["lang"] for p in t["pron"]}
        t["lang"] = ("nan" if langs & {"nan", "partial"} else
                     "cmn" if "cmn" in langs else "unknown")
    return tokens


def annotate_text_field(data, key):
    """v1 相容欄位（pronun_*）＋ v2 保真欄位（*_ruby, tokens）。"""
    original = data[key]
    pronunciations = re.findall(r"<rt>(.*?)</rt>", original)
    # 所有 entry/sentence item 都保有成對 v1 欄位；無 ruby 時留空，避免下游缺鍵。
    data["pronun_tl"] = ""
    data["pronun_poj"] = ""
    if not pronunciations:
        return
    data[key + "_ruby"] = original                     # 保真：對齊原文
    data["pronun_bopo"] = "-".join(pronunciations)
    analyses = [analyze_bopo(p) for p in pronunciations]
    tl_flat = [a.get("tl", "") for a in analyses]
    poj_flat = [a.get("poj", "") for a in analyses]
    # v1 相容欄位必須成對存在：國音/未知注音不可硬轉台羅，留空字串保真。
    data["pronun_tl"] = "-".join(tl_flat)
    data["pronun_poj"] = "-".join(poj_flat)
    data["tokens"] = enrich_tokens(tokenize_ruby(original))
    data[key] = re.sub(r"<rt>.*?</rt>", "", original)


def annotate_reading_segments(readings):
    """單字讀音列之方音字形 → 台羅/白話字（國音列僅保留注音）。"""
    for label, recs in readings.items():
        for rec in recs:
            for seg in rec.get("segments", []):
                for g in seg.get("glyphs", []):
                    bopo = g.get("bopo")
                    if bopo and label != "國音":
                        a = analyze_bopo(bopo)
                        g["lang"] = a["lang"]
                        if "tl" in a:
                            g["tl"], g["poj"] = a["tl"], a["poj"]


def annotate_head(head):
    if not head:
        return
    for g in head.get("ruby", []):
        if g.get("bopo"):
            a = analyze_bopo(g["bopo"])
            g["lang"] = a["lang"]
            if "tl" in a:
                g["tl"], g["poj"] = a["tl"], a["poj"]


def process_entry(data):
    """遞迴處理：v2 樹（chapters/hanzi_entries）與 v1 list 皆可。"""
    if isinstance(data, list):
        for item in data:
            process_entry(item)
    elif isinstance(data, dict):
        if "readings" in data and isinstance(data["readings"], dict):
            annotate_reading_segments(data["readings"])
        if "head" in data and isinstance(data["head"], dict):
            annotate_head(data["head"])
        for key in ("entry", "sentence"):
            if key in data and isinstance(data[key], str):
                annotate_text_field(data, key)
        for value in data.values():
            if isinstance(value, (dict, list)):
                process_entry(value)


def main():
    raw_data = sys.stdin.buffer.read()
    decoded_data = raw_data.decode("utf-8")
    # 舊管線殘留的 <img> 造字圖 → 結構化 glyph 標記
    decoded_data = re.sub(r'<img src="img/(.*?)\.png"\s*>', r"<glyph:\1>",
                          decoded_data)
    data = json.loads(decoded_data)
    process_entry(data)
    print(json.dumps(data, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
