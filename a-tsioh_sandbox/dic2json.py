# -*- coding: utf-8 -*-
"""dic2json — .dic(UTF-8) → koktai-dic/2 JSON（stdin→stdout）。

用法（gen_json.pl 管線）：
    perl a-tsioh_sandbox/recode_utf8.pl betaNNk.dic \
      | python3 a-tsioh_sandbox/dic2json.py \
      | python3 a-tsioh_sandbox/rt2pronun.py > json/NN.json

相對 v1 的差異：
  * .本文 單字條目（字頭／注音字形／反切引註／國音·台甘·普閩讀音列）
    全部結構化保留 —— v1 直接丟棄。
  * .章首（章節音節：注音＋羅馬字）保留。
  * 造字字形就地解碼（併入舊 jade-unescape.pl 職責，去除 CPAN 依賴）：
    m3/k.json → <rt>方音</rt>、mapping.json → 罕用漢字、無表 → <glyph:…>。
  * 每層保留 raw（造字以 &#xfXXXX; 逃逸，可逆）；解析失敗片段進
    unparsed/stray，不再靜默流失，也不再把診斷印進 stdout 汙染 JSON。
"""

import json
import sys

import koktai_dic


def main():
    data = sys.stdin.buffer.read().decode("utf-8")
    volume = koktai_dic.parse_volume(data.splitlines())

    n_hz = sum(len(c["hanzi_entries"]) for c in volume["chapters"])
    n_word = sum(len(h["word_entries"])
                 for c in volume["chapters"] for h in c["hanzi_entries"])
    n_fq = sum(len(h["head"]["fanqie"])
               for c in volume["chapters"] for h in c["hanzi_entries"]
               if h.get("head"))
    volume["stats"] = {
        "chapters": len(volume["chapters"]),
        "hanzi_entries": n_hz,
        "word_entries": n_word,
        "fanqie_citations": n_fq,
    }
    print(f"[dic2json] 章 {volume['stats']['chapters']} / 單字 {n_hz} / "
          f"詞條 {n_word} / 反切 {n_fq}", file=sys.stderr)

    json.dump(volume, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
