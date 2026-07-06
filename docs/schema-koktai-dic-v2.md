# `koktai-dic/2` JSON 格式規格

`dic2json.py`（結構）＋`rt2pronun.py`（讀音註記）兩階段後的最終形態，即 `json/NN.json`。

## 頂層

```jsonc
{
  "format": "koktai-dic/2",
  "chapters": [ Chapter… ],
  "unassigned": [ … ],          // 檔頭雜項、無法歸屬的散行（保真）
  "stats": { "chapters": n, "hanzi_entries": n, "word_entries": n, "fanqie_citations": n }
}
```

## Chapter（`.章首`）

```jsonc
{
  "zhuyin": "ㄅㄚ",             // 國音注音（章節音節）
  "roman": "ba",                // 原書羅馬字
  "raw_head": "ㄅㄚ ~t112fd0;[ba]",
  "hanzi_entries": [ HanziEntry… ],
  "orphan_word_entries": [ WordEntry… ]   // 章首後、.本文 前的詞條（選現）
}
```

## HanziEntry（`.本文` 單字條目）

```jsonc
{
  "head": {
    "display": "八",                     // 字頭顯示形（造字無對映時 U+FFFD）
    "chars": [ {"char": "八"} | {"glyph": "fb49", "char": "罕用字|null"} ],
    "ruby":  [ {"glyph": "fab6", "bopo": "ㄅㄚ",     // 字頭注音（國音）
                "lang": "nan|cmn|…", "tl": "pa1", "poj": "pa"} ],
    "annotation_raw": "布拔切，黠韻",     // 引註尾原文（&#x 逃逸）
    "fanqie": [ {
      "speller": "布拔",                 // 反切二字
      "yun": "黠",                       // 韻目（單字；調前綴已剝）
      "tone": "入|null",                 // 「入屋韻」式的調前綴
      "source": "廣韻|集韻|正韻|唐韻|康典…|null",
      "derived": false,                  // ←（由他音導出）
      "raw": "布拔切，黠韻"
    } ],
    "annotation_notes": [ "康典未收字" ]  // 非反切引註（不丟）
  },
  "readings": {
    "國音": [ {"raw": "…", "segments": [ Segment… ]} ],
    "台甘": [ … ],
    "普閩": [ … ]
  },
  "word_entries": [ WordEntry… ],
  "raw": [ "~fm7t168bb1;八…" ]           // 條目全部原始行（&#x 逃逸，可逆）
}
```

### Segment（讀音列語域段）

```jsonc
{
  "register": "文|語|白|漳|泉|廈|俗|…|null",
  "glyphs": [ {"glyph": "fb49", "bopo": "ㄅㄚㆵ",
               "lang": "nan", "tl": "pat4", "poj": "pat"} ],   // 國音列不轉台羅
  "text": "＝…。"                        // 段內非造字文字
}
```

## WordEntry（`~t96;` 詞條；v1 欄位全相容＋保真欄位）

```jsonc
{
  "entry": "八方",                       // 詞頭（<rt> 已剝）
  "entry_ruby": "八<rt>ㄅㄚ</rt>方<rt>ㄈㄤ</rt>",   // 保真：剝除前原文
  "nh": "1",                             // 同形詞條編號
  "POS": "[名]|None",
  "body": "…",
  "sentences": [ {
    "lang": "台|國語",
    "sentence": "…",                     // <rt> 已剝
    "sentence_ruby": "…<rt>…</rt>…",     // 保真
    "pronun_bopo": "ㄅㄚ-ㄏㆲ",           // v1 相容：ruby 扁平串接；無 ruby 時省略
    "pronun_tl":   "pa1-hong1",          // v1 相容：entry/sentence item 必有；無 ruby 或不可硬轉時為 ""
    "pronun_poj":  "pa-hong",            // 與 pronun_tl 成對，由同一 bopo→TL→POJ 轉換器產生
    "tokens": [ Token… ]                 // v2 逐字對齊
  } ],
  "raw": [ 原始行… ]
}
```

### Token（逐字對齊單位）

```jsonc
{
  "han": "方",                 // 基底：漢字｜&#xf….;（未知造字）｜glyph id｜null
  "kind": "han|pua|glyph|null",
  "ruby": [ "ㄏㆲ", "ㄏㆭ" ],   // 一至多個讀音（「/」又讀歸同 token）
  "pron": [ {"lang": "nan", "tl": "hong1", "poj": "hong"},
            {"lang": "cmn"},                       // 國語注音：不轉台羅
            {"lang": "partial|unknown", "errors": ["…@i"]} ],
  "lang": "nan|cmn|unknown",   // token 層綜合分類
  "neutral": true              // 選現：輕聲點「·」
}
```

## 標記字彙（字串欄位內）

| 標記 | 意義 |
|---|---|
| `<rt>…</rt>` | 方音符號注音（ruby） |
| `<k>…</k>` | 楷體區（台語字層）——dic2json 內部已展開，殘留即原文如此 |
| `<glyph:m3/xxxx>` / `<glyph:k/xxxx>` | 無對映表的造字（xxxx = Big5 hex） |
| `<mark>&#xfxxxx;</mark>` | 未知楷體造字（v1 相容記法） |
| `&#xfxxxx;` | raw 欄位中的造字逃逸（可逆還原 U+F0000+xxxx） |

## 與 v1 的相容性

- v1 消費欄位 `entry / nh / POS / body / sentences[].{lang,sentence,pronun_*}` 名稱、語意不變。
- v1 頂層是 list、同名詞條聚成 `heteronyms`；v2 改為章→單字→詞條樹，`nh` 保留
  原書編號，聚合請在消費端做（`build_unified_index.py` 即如此）。
