# 功能分區（verification map）

每檔一個功能區：入口、驅動命令、可觀察結果、失敗路徑、證據。全掃入口與失敗分類見 [../VERIFY.md](../VERIFY.md)。

| 檔案 | 功能區 | 對應驗收 | 覆蓋原始碼（變動即需重驗） |
|---|---|---|---|
| [dic-to-json.md](dic-to-json.md) | `.dic` → koktai-dic/2 JSON（recode＋結構解析＋造字解碼） | AC1 | `beta*.dic`、`a-tsioh_sandbox/recode_utf8.pl`、`koktai_dic.py`、`dic2json.py`、`font/m3.json`、`font/k.json`、`a-tsioh_sandbox/mapping.json`、`gen_json.pl` |
| [bopo-tl-poj.md](bopo-tl-poj.md) | 方音符號 → 台羅／白話字、逐字對齊 tokens | AC1、AC2、AC4 | `a-tsioh_sandbox/rt2pronun.py`、`chhoetaigi.py`（`iter_poj_gold`/`validate_poj`） |
| [unified-index.md](unified-index.md) | 統一聲韻索引聚合與四檔輸出 | AC2 | `a-tsioh_sandbox/build_unified_index.py`（`Collector`、`collect_volume`、`build_outputs`、`main`） |
| [fanqie-sim-tl.md](fanqie-sim-tl.md) | 反切 × ytenx 中古層 join、`sim_tl` 模擬文讀、關鍵點拼讀 | AC2、AC3、AC5 | `build_unified_index.py`（`Ytenx`、`Pingshui`、`derive_sim_tl`、`build_reading_profile`、`enrich_mc_with_reading_profile`、`add_ytenx_char_fallback`、`norm_registers`）、`a-tsioh_sandbox/data/*`、`test_join_fanqie.py`、`~/dev/ytenx` |
| [attestation-layers.md](attestation-layers.md) | 外典佐證（ChhoeTaigi、教育部詞彙比較／附錄、千金譜）與權重 | AC2 | `a-tsioh_sandbox/chhoetaigi.py`（`load_attestation`）、`sutian.py`、`chhiankimpho.py`、`ExternalRef/` |

## 維護規則

- **事件驅動，非定期**：覆蓋原始碼一有變動，重跑該檔驅動命令，更新 `source_commit`／`last_verified_at`。
- `verification_status: failed` 代表產品變了——**先依 VERIFY.md 分類，再決定改不改地圖**。地圖永不為了配合壞掉的產品而改寫。
- 數字以本檔 metadata 的 `source_commit` 為準；`docs/` 的敘述性數字若與此不同，以實測為準並修 `docs/`（doc drift）。
