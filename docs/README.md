# koktai 專案文件總覽

《國臺對照活用辭典》（吳守禮）數位化語料的解析管線、聲韻資料層、與統一聲韻索引。

## 文件地圖

| 文件 | 內容 |
|---|---|
| [dic-format.md](dic-format.md) | 原始 `.dic` 檔案格式規格（標記語法、造字編碼、排版變體） |
| [pipeline.md](pipeline.md) | 轉換管線 v2：階段、腳本、修復史、無損驗證 |
| [schema-koktai-dic-v2.md](schema-koktai-dic-v2.md) | `koktai-dic/2` JSON 輸出格式規格 |
| [bopo-tl-methodology.md](bopo-tl-methodology.md) | 方音符號 ↔ 台羅 ↔ 白話字轉換方法論（含 v1 bug 清單） |
| [unified-index.md](unified-index.md) | 統一聲韻索引（漢字↔台羅雙向反查）schema 與產生方式 |
| [ytenx-correspondence.md](ytenx-correspondence.md) | 與韻典網（ytenx）聲韻查表的對應分析與 join 方法論 |
| [data-tables.md](data-tables.md) | `a-tsioh_sandbox/data/*.json` 兩張聲韻資料表的內容與出處 |
| [external-references.md](external-references.md) | `ExternalRef/` 外部文件盤點、可用性、取用方式 |
| [scripts-inventory.md](scripts-inventory.md) | 腳本與資源全清單（現役管線＋legacy＋外部依賴） |
| [methodology.md](methodology.md) | 可複用方法論：無損原則、parity 驗證、join 設計、除錯教訓 |

## 快速上手

```sh
# 1. 全 26 卷 .dic → koktai-dic/2 JSON（約 40 秒）
perl gen_json.pl                     # 產出 json/01.json … json/26.json

# 2. 統一聲韻索引（約 10 秒；需本機有 ytenx repo；
#    ExternalRef/ChhoeTaigiDatabase 存在時自動加佐證層）
python3 a-tsioh_sandbox/build_unified_index.py \
    --json 'json/*.json' --ytenx ~/dev/ytenx --out index
# 產出 index/unified_phonology.json、han_to_tl.tsv、tl_to_han.tsv、
#      chhoetaigi_gaps.tsv

# 3.（選用）台羅→白話字轉換器黃金測試
python3 a-tsioh_sandbox/chhoetaigi.py --validate-poj
```

## 語料規模（2026-07 全量重建實測）

| 量 | 數字 |
|---|---|
| 卷 | 26（`beta01k.dic` … `beta26k.dic`，Big5＋EUDC 造字） |
| 章（`.章首` 音節） | 1,446 |
| 單字條目（`.本文`） | 12,857 |
| 詞條（`~t96;【…】`） | 43,913 |
| 反切引註（單字頭） | 11,002 |
| 索引漢字 | 10,026 |
| 索引台羅音節 | 3,272 |
| （漢字, 台羅）讀音對 | 28,758（聚合自 627,497 個對齊 token） |
| ChhoeTaigi 佐證 | 15,190 對（52.8%）；token 質量覆蓋 88.5% |

## 主要程式

| 檔案 | 角色 |
|---|---|
| `a-tsioh_sandbox/recode_utf8.pl` | Big5(CP950)→UTF-8；EUDC 造字 U+E000–F8FF → U+F0000＋Big5 碼位 |
| `a-tsioh_sandbox/koktai_dic.py` | `.dic` 全結構解析庫（章首／單字頭／讀音列／詞條／反切） |
| `a-tsioh_sandbox/dic2json.py` | stdin→stdout：`.dic`(UTF-8) → `koktai-dic/2` JSON |
| `a-tsioh_sandbox/rt2pronun.py` | 方音符號→台羅/白話字；逐字對齊 tokens；語言分類 |
| `a-tsioh_sandbox/build_unified_index.py` | 統一聲韻索引產生器（ytenx 中古層 join＋ChhoeTaigi 佐證/權重） |
| `a-tsioh_sandbox/chhoetaigi.py` | ChhoeTaigi CSV 載入庫＋佐證對齊＋POJ 黃金測試 |
| `gen_json.pl` | 全卷批次驅動 |
| `font/m3.json`, `font/k.json` | 造字 hex → 方音符號串（明體／楷體） |
| `a-tsioh_sandbox/mapping.json` | 造字字元 → 罕用漢字 |
| `a-tsioh_sandbox/data/pingshui_tl.json` | 平水韻系→台羅文讀韻母（源自 ExternalRef PDF） |
| `a-tsioh_sandbox/data/kuangx_pingshui.json` | 切韻系 206 韻目 ↔ 平水 106 部對照 |

## 已知界限

- **集韻缺表**：join_none 4,661 筆引註多為集韻反切；ytenx 無集韻資料集（見 [ytenx-correspondence.md](ytenx-correspondence.md)）。
- **卷 11 源檔截斷**：`beta11k.dic` 僅 2.2KB（5 單字），上游檔案問題，非管線問題。
- **`HanBunDatabase.accdb` 加密**：無密碼不可讀（見 [external-references.md](external-references.md)）。
- 圈號 ①–⑨ 會以低頻 token 進入索引（`n` 欄可濾）。
- 台／國語句切分與 v1 有 14 筆（0.6%）邊界差；雙方 ruby 皆全保留於 `sentence_ruby`。
