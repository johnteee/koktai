# 統一聲韻索引（漢字 ↔ 台羅 雙向反查）

產生器：`a-tsioh_sandbox/build_unified_index.py`
輸入：`json/*.json`（koktai-dic/2）＋ ytenx 查表 ＋ `data/*.json` 兩張聲韻表
＋ ChhoeTaigi CSV（佐證層，選用）＋ 教育部詞彙比較/附錄 ods ＋ 千金譜 md
輸出：`index/unified_phonology.json`、`index/han_to_tl.tsv`、`index/tl_to_han.tsv`、
`index/chhoetaigi_gaps.tsv`

```sh
python3 a-tsioh_sandbox/build_unified_index.py \
    [--json 'json/*.json'] [--ytenx ~/dev/ytenx] [--out index] \
    [--chhoetaigi ExternalRef/ChhoeTaigiDatabase] \
    [--sutian ExternalRef/詞彙比較表.ods] \
    [--chhiankimpho ExternalRef/chhian-kim-pho2.md]
# 各外部源檔不存在時自動略過
```

## 資料匯流

| 來源 | 貢獻 |
|---|---|
| 單字讀音列（台甘/普閩 segments） | (漢字, 台羅) 對＋語域（文/語/白/漳/泉/廈…） |
| 單字讀音列（國音）＋字頭注音 | 漢字 → 國音注音集 |
| 詞條 tokens（`lang:"nan"`） | (漢字, 台羅) 對＋出現次數＋例源 |
| 詞條 tokens（`lang:"cmn"`） | 漢字 → 國音注音集 |
| 字頭反切引註 × ytenx | 中古音韻地位（聲母/韻母/韻目/等/呼/調） |
| `data/kuangx_pingshui.json` | 韻目 → 平水部/韻系 |
| `data/pingshui_tl.json` | 韻系 → 預期台羅文讀韻母 |
| ChhoeTaigi CSV × `chhoetaigi.py` | (漢字, 台羅) 佐證標籤＋權重（見下） |
| 詞彙比較表.ods × `sutian.py` | 佐證標籤 `比` ＋ 十腔別 `dialects`（見下） |
| 附錄 新詞/共同詞/俗諺 ×3 ods × `sutian.load_appendices` | 佐證標籤 `新`/`共`/`諺` |
| 千金譜 × `chhiankimpho.py` | 佐證標籤 `金`（POJ→台羅轉換；歷史文獻，權重 2） |

聚合鍵 `(漢字, 台羅音節)`；多音節台羅（詞讀）不入字級索引。每對記
`bopo / poj / registers / n（次數）/ w（權重）/ attest（佐證）/
dialects（腔別）/ sources（≤5 例源，格式「卷:字頭」或「卷:詞頭」）`。

## ChhoeTaigi 佐證層（方法仿 ch2taigi）

`chhoetaigi.load_attestation()` 把 ChhoeTaigi 開放辭典的「台文漢字 ↔ KipInput」
逐位對齊（漢字數＝音節數、全漢字才收，不猜），得 **27,290 組 (漢字, 台羅) 佐證對**；
單字辭典（甘字典、教育部 700 用字）直接收，甘字典「漢文音」另掛 `甘文` 標籤
（可對照我們的 `文` 語域）。

每個讀音對記 `attest`（佐證辭典標籤）與權重
`w = n + Σ 辭典權重`——辭典權重採 ch2taigi `calcWordWeightAndDeduplication`
的優先序 × 2 法（700用字 22 > 台語千詞 20 > 教典 18 > 台華線頂 16 > iTaigi 14 >
白話基礎語句 12 > 台日 10 > 甘典 8 > 植物名彙 6 > Embree 4 > Maryknoll 2）。
`taigi[]` 與 `tl` 反查均按 `w` 降冪（同 w 比 n），高頻＋多典佐證的讀音排前。

標籤字彙：`700`=教育部700用字、`教`=教育部台語辭典、`線`=台華線頂對照典、
`iT`=iTaigi、`基`=白話基礎語句集、`日`=台日大辭典、`甘`/`甘文`=甘字典（白/漢文音）、
`植`=台灣植物名彙、`Em`=Embree、`Mk`=Maryknoll；教育部附錄（權重同教典）：
`比`=詞彙比較、`新`=新詞120、`共`=臺華共同詞350、`諺`=俗諺40；
`金`=千金譜（歷史文獻，權重 2）。

## 教育部詞彙比較：方言腔層（`sutian.py`）

《臺灣台語常用詞辭典》附錄「詞彙比較」（`ExternalRef/詞彙比較表.ods`，
`--sutian` 可指路徑）給出**地點級**十腔別：偏泉 6（鹿泉/峽泉/北泉/竹泉/金泉/澎泉）、
偏漳 2（蘭漳/中漳）、混合 2（南混/高混）。同法逐位對齊（12,022/12,271 列，98%）
→ 2,976 佐證對＋腔別集合；**1,937 讀音對（6.7%）帶 `dialects` 欄**，十腔分佈均勻
（各約 1,000–1,160 對）。

- 陽上調 6（鹿港等腔保留）另掛調 7 摺疊鍵：koktai 方音 `˫` 不分 6/7 一律讀 7，
  摺疊後鹿港腔資料才可對接（徛 khia7 十腔全滿）。
- 與 koktai 語域互證：`書 tsir1` 語域「廈」× 腔別「峽泉,竹泉,金泉,鹿泉」；
  `書 si1` × 「蘭漳」——地點級資料可核對吳守禮的漳/泉/廈歸類。

### 佐證統計（全語料實測）

- 讀音對層：15,244 / 28,758（**53.0%**）獲至少一部外典佐證。
- token 質量層：**88.7%** 的出現次數落在有佐證的讀音對上——高頻讀音幾乎全數
  獲得獨立確認；無佐證者集中於低頻尾端。
- 高頻缺口（n ≥ 10 且無佐證）424 筆 → `chhoetaigi_gaps.tsv`。抽驗結果**多非
  轉換錯誤，而是 koktai 的訓用字/俗寫系統**：丌(=的 e)、𣍐(=袂 bē)、伓(=毋 m̄)、
  付(=予 hōo)、骹(=跤 kha)、讀(=濟 tsē)、載(=代 tāi)、或(=抑 ia̍h)——
  此檔即現成的「koktai↔教典正字」對照素材。

## 中古層 join 方法論（`Ytenx.join_fanqie`）

優先序（方法名如實寫入 `mc[].join.method`，下游可過濾）：

1. **廣韻反切**：反切二字＋韻目（剝 A/B 重紐尾）精確命中 kyonh 小韻。
2. **正韻反切**：同上命中洪武正韻牋小韻。
3. **廣韻反切·平水寬**：反切命中、韻目不同但**同平水部**——辭典慣以平水目稱
   鄰韻（歌↔戈、職↔德、陌↔麥、卦↔夬、黠↔鎋）。
4. **正韻反切·寬**：正韻中該反切唯一（正韻自有 76 目/22 系名，引文韻目常仍用
   切韻系名，如「莫葛切，末韻」實為正韻曷韻末小韻）。
5. **字頭歸小韻**（fallback）：字頭見於廣韻 `Dzih.txt` → 列候選小韻（上限 6）；
   候選同屬一平水部時附 `pingshui`。無引註的字（如「學」→覺韻匣母）也吃此路。

引文韻目先過異體正規化（`variants`：真→眞、皓→晧、號→号、寢→寑、艷→豔、
驗→釅、痲→麻）；「入屋韻」式調前綴在解析期已剝。

### 全語料 join 統計（11,002 筆引註）

| 方法 | 筆數 |
|---|---|
| 廣韻反切 | 2,778 |
| 正韻反切 | 1,884 |
| 廣韻反切·平水寬 | 233 |
| 正韻反切·寬 | 1,446 |
| **小韻 join 小計** | **6,341（57.6%）** |
| 未 join | 4,661（多為集韻反切；ytenx 無集韻表） |
| 字頭歸小韻（另計，含無引註字） | 3,414 |

### 反切關鍵點拼讀（`sim_tl.keypoint_composed`）

`derive_sim_tl()` 先用「中古聲母類 × 平水預期韻母 × 文讀調」產生規則候選；
索引完成收集現代讀音後，再由 `build_reading_profile()` 建立反切上下字關鍵點：

- 上字取台羅聲母、下字取台羅韻母，合成 `上字聲母 + 下字韻母 + 反切文讀調`。
- 關鍵點排序：文讀語域/`甘文` 佐證優先，其次非白/語/俗/訓讀音，最後全部讀音；
  同層按 `n + Σ外典權重` 排序。
- 候選上限為上字聲母 2 類 × 下字韻母 3 型，避免為了命中率過度擴張候選集。
- 補強結果寫入 `mc[].sim_tl.keypoint_composed`，並併入 `mc[].sim_tl.syllables`。

全語料實測：`sim_tl_keypoint_enriched = 9,153` 筆 mc、
`sim_tl_keypoint_added = 25,824` 個候選。以既有文讀（`registers` 含文或 `attest`
含 `甘文`）為 gold，`sim_tl.syllables` 任一命中率由 3,893/5,284（73.68%）提升到
4,173/5,286（78.94%）；平均候選數由 2.33 增至 4.36。

## 輸出 schema

### `unified_phonology.json`

```jsonc
{
  "_meta": { "generator", "volumes": ["01"…"26"], "sources": {…}, "stats": {…} },
  "han": {
    "八": {
      "mandarin": ["ㄅㄚ", "ㄅㄚˊ"],
      "taigi": [ { "tl": "peh4", "bopo": ["ㄅㆤㆷ"], "poj": ["peh"],
                   "registers": ["語"], "n": 104, "w": 162,
                   "attest": ["iT","教","日","線"],          // 無佐證則省略此欄
                   "dialects": ["南混","蘭漳"],              // 無腔別資料則省略
                   "sources": ["01:八(台甘)", "01:八個…"] } ],  // 按 w 降冪
      "mc": [ { "fanqie": "布拔切", "yun": "黠", "source": null,
                "join": { "method": "正韻反切·寬", "xiaoyun": 2017, "taj": "八",
                          "miuk": "轄", "initial": "p", "final": "at" },
                "pingshui": { "bu": "黠", "series": "刪", "tone": "入",
                               "expected_tl": ["at", "uat"] },
                "sim_tl": { "syllables": ["pat4", "puat4", "peh4", "buat4", "bat4", "beh4"],
                            "initials": ["p"], "finals": ["at", "uat"], "tone": 4,
                            "initial_category": "幫", "voicing": "全清", "source": "反切上字",
                            "confidence": "medium",
                            "keypoint_composed": ["puat4", "pat4", "peh4", "buat4", "bat4", "beh4"] } } ],
      "pingshui": ["黠"]
    }
  },
  "tl": {
    "pat4": [ { "han": "識", "n": 104, "w": 104, "registers": ["語"] },
              { "han": "八", "n": 36, "w": 116,
                "attest": ["iT","教","日","植","甘","甘文","線"], … }, … ]
  }
}
```

### TSV

```
han_to_tl.tsv：#漢字	台羅	方音	白話字	語域	次數	權重	佐證	腔別	例源
tl_to_han.tsv：#台羅	漢字（按權重）
chhoetaigi_gaps.tsv：#漢字	台羅	次數	方音	語域	例源   （n≥10 且無佐證）
```

## 規模與品質抽樣

- **10,185 漢字 / 3,272 台羅音節 / 28,758 讀音對**（自 627,497 個對齊 token 聚合）。
- 文白層次自然浮現：`方 hong1(文)×649 / hng1(白)×104 / pang1(白)×11`；
  `東 tang1(語)×143 / tong1(文白)×17`；`食 tsiah8(白)×1306 / sit8(文)×202`。
- 反查韻類完整：`hong5 → 皇防黃妨紅縫逢凰惶癀蓬航鴻馮…`（54 字）。
- 平水預期韻母可作一致性檢核：八(黠部刪系→at/uat) ⇔ pat4 ✓；
  例外即真異讀（食：職韻→預期 ik，實讀 sit8 收 -t，屬已知不規則）。

## 已知雜訊與過濾建議

- 圈號 ①–⑨ 作基底的低頻 token（`n` 小）→ 以 `n ≥ 2` 或字元白名單過濾。
- 嚴格應用建議：取 `attest` 非空（外典確認）或 `n ≥ 10` 的讀音對；
  兩者皆無者多為排版雜訊或極罕見讀。
- `mandarin` 聚合自國語句 ruby，破音字會收到多讀（含罕見文讀），屬來源如實。
- 「正韻反切·寬」存在跨韻書反切碰撞的理論風險；嚴格應用請只取
  `廣韻反切`/`正韻反切` 兩種方法。
- 訓讀現象如實保留（`pat4 → 識/別/曾`：台語 bat「識得」之用字），語域欄可辨；
  koktai 訓用字與教典正字的系統差見 `chhoetaigi_gaps.tsv`。
