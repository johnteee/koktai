# 腳本與資源全清單

## 現役管線（v2）

| 檔案 | 語言 | 角色 |
|---|---|---|
| `gen_json.pl` | Perl | 批次驅動：對 26 卷執行 recode→dic2json→rt2pronun |
| `a-tsioh_sandbox/recode_utf8.pl` | Perl | CP950→UTF-8；EUDC PUA→U+F0000+Big5；格式碼小寫化 |
| `a-tsioh_sandbox/koktai_dic.py` | Py3 | 解析庫：章首/單字頭（新舊兩式）/讀音列（單/多標籤）/詞條/反切；造字解碼 `to_rt_markup`（含 Fc 內文字元區語意）；raw 逃逸 `escape_pua` |
| `a-tsioh_sandbox/dic2json.py` | Py3 | stdin→stdout 包裝：`parse_volume` ＋ 統計 stderr |
| `a-tsioh_sandbox/rt2pronun.py` | Py3 | 三張對照表；`analyze_bopo`（音節切分/調/國語分類）；`tokenize_ruby` 逐字對齊；台羅→白話字 |
| `a-tsioh_sandbox/build_unified_index.py` | Py3 | 統一索引：讀音聚合＋ytenx join＋平水層＋ChhoeTaigi 佐證/權重＋TSV/JSON 輸出 |
| `a-tsioh_sandbox/chhoetaigi.py` | Py3 | ChhoeTaigi CSV 載入庫：KipInput 正規化、漢字↔音節逐位對齊（佐證表）、POJ 黃金對；`--validate-poj`（轉換器黃金測試）、`--attest-stats` |
| `a-tsioh_sandbox/sutian.py` | Py3 | 教育部辭典附錄載入庫：詞彙比較（十腔別、佐證 `比`、陽上 6→7 摺疊）＋新詞/共同詞/俗諺（佐證 `新`/`共`/`諺`、「/」變體、俗諺句級對齊） |

## 資料資源

| 檔案 | 內容 |
|---|---|
| `font/m3.json` | 明體造字 hex→方音串/內文字元（`fab6→ㄅㄚ`；Fc 區為內文字元） |
| `font/k.json` | 楷體造字 hex→方音串 |
| `a-tsioh_sandbox/mapping.json` | 造字字元→罕用漢字（Unicode 有碼位者） |
| `a-tsioh_sandbox/data/pingshui_tl.json` | 平水韻系→台羅文讀（源：ExternalRef PDF） |
| `a-tsioh_sandbox/data/kuangx_pingshui.json` | 切韻 206 目↔平水 106 部＋異體正規化 |
| `beta01k.dic`–`beta26k.dic` | 原始排版檔（Big5+EUDC；卷 11 源檔截斷僅 2.2KB） |
| `01.dic.utf8.txt` | 卷 1 的 recode 輸出快照（開發便利品，可由 recode 重生） |
| `json/01.json`–`26.json` | koktai-dic/2 輸出 |
| `index/` | 統一聲韻索引輸出（含 `chhoetaigi_gaps.tsv` 高頻無佐證缺口報告） |
| `ExternalRef/ChhoeTaigiDatabase/*.csv` | ChhoeTaigi 開放辭典 11 部（甘字典/台日/教典/線頂/iTaigi/Embree/Maryknoll…）；佐證層與 POJ 黃金對來源 |
| `ExternalRef/詞彙比較表.ods` | 教育部台語辭典附錄「詞彙比較」（sutian.moe.edu.tw）；十腔別方言層來源 |
| `ExternalRef/sinsu120_*.ods`、`kiongtongsu350_*.ods`、`siokgan40_*.ods` | 教育部附錄：新詞 120／臺華共同詞 350／俗諺 40（佐證 `新`/`共`/`諺`；glob 取最新版本） |

## Legacy／周邊（未動，供考古）

| 檔案 | 狀態 | 備註 |
|---|---|---|
| `font/jade-unescape.pl` | legacy（jade 路徑用） | 造字→`<rt>`/`<img>`/`<mark>`；其 Fc 區「裸放」語意已移植入 `koktai_dic.to_rt_markup`；JSON 管線不再經過 |
| `a-tsioh_sandbox/analyse_word_entry.py` | legacy | v1 詞條解析（僅 `~t96;`；`.本文` 丟棄的源頭）；邏輯已由 `koktai_dic` 取代並擴充 |
| `jade/*.jade` | 舊文本層（34 個月前） | 26 卷 HTML 預覽源；**無字頭反切**；勿當權威文本 |
| `gen.pl` / `gen_tai.pl` / `gen_ji.pl` | legacy | 舊批次殼 |
| `a-tsioh_sandbox/rt2pronun.py` 以外的 sandbox 腳本（`dic2json.py` 舊版邏輯、`wsl_to_kaulo.py`、`phash_guess_mapping.py`、`recode_utf8.pl` 同目錄其他實驗） | 實驗品 | 造字圖形辨識、格式實驗等 |
| `parse_to_neo4j/`（`parse_dic.py`、`build_graph.py`、`mapping.json`、`m3.json`） | 實驗品 | 圖資料庫實驗；其 `mapping.json`/`m3.json` 與 font/ 同源 |
| `han2edu/`（分漢字注音、臺文格式正規化） | 實驗品 | 依 `tai.jade`（已不在 repo）運作 |
| `scripts/`（`finderr.pl`、`neutral.pl`、`sortphr.pl`） | legacy | 校對輔助 |
| `font/tai.c`、`usrfont.lst`、`*.xfn`、`hfn/` | 字型工程 | `tai.c` 定義方音鍵盤與 **15 聲**編碼（README 亦述） |
| `big5-mapping/`（`EUDC___0.tte`、`BIG5-Original.xls`） | 字型工程 | 造字檔與 Big5 對照原始材料 |
| `img/`、`html/` | 展示 | 造字 PNG（`img/m3/`、`img/k/`）與 demo |
| `phsource.txt`、`phsource`、`ph-comp.txt` | 文獻 | 方音符號源流解說（含各符篆文出處） |
| `mytaiin8.txt`、`preface1.dic`、`dic-cont.txt`、`missings.sorted` | 文獻/雜項 | 序文、缺字清單等 |

## 外部依賴

| 依賴 | 用途 | 必要性 |
|---|---|---|
| Perl（core `Encode`） | recode | 必要（或以 Python 重寫 recode 即可移除） |
| Python 3（標準庫） | 其餘全部 | 必要；無第三方套件 |
| `~/dev/ytenx` repo | 中古層 join | 建索引時必要（`--ytenx` 可指路徑）；缺席時可跳過 mc 層（未實作 no-ytenx 模式） |
| ~~CPAN JSON / File::Slurp~~ | ~~jade-unescape~~ | v2 已移除此依賴 |
| `ExternalRef/ChhoeTaigiDatabase/` | 索引佐證層＋POJ 黃金測試 | 選用；目錄缺席時 `--chhoetaigi` 自動略過，索引仍可建（無 attest/w 加成） |
| `ExternalRef/詞彙比較表.ods` | 索引方言腔層 | 選用；檔案缺席時 `--sutian` 自動略過（無 dialects 欄） |
| `ExternalRef/{sinsu,kiongtongsu,siokgan}*.ods` | 索引佐證標籤 新/共/諺 | 選用；缺席自動略過（`--moe-dir` 可另指目錄） |
