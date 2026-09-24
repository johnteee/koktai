<!-- stub-marker: fanqie-fix -->
# 反切 sim_tl 命中率修復（單輪有界任務）

你是 bounded worker：本輪只准修改 `a-tsioh_sandbox/build_unified_index.py`
一個檔案，做完一個連貫修改就停。

## 目標

提升 `mc[].sim_tl` 對既有文讀（`taigi[].registers` 含「文」或 `attest` 含「甘文」）
的 any-hit 命中率，使其達到 `.agent/delivery/envelope.yaml` `loop_targets`：

- `min_hit_rate`：命中率須 ≥ 此值（當前基線 4173/5286 ≈ 0.7894）
- `max_avg_candidates`：平均候選數不得超過此值（基線 4.36）

## 硬性邊界

- 只編輯 `a-tsioh_sandbox/build_unified_index.py`；其他檔案一律不碰。
- 絕不修改：`checks/`、`acceptance.yaml`、`a-tsioh_sandbox/test_*.py`、
  `.agent/`、`flows/`、`index/`、`json/`、`docs/`。
- 不得放寬候選上限（`KEYPOINT_INITIAL_CAP=2` × `KEYPOINT_FINAL_CAP=3`）。
- 不得用擴張候選集換命中率（平均候選數有上限）。
- register alias 採保守原則：不得把「古文」「文語」「不分文白」映射成「文」。
- 非 mc 欄位（han、pingshui、taigi 等）的索引輸出必須保持位元一致
  （`index-parity --allow mc,pingshui` 只容忍 mc/pingshui 變動）。
- 一輪只做一個連貫修改；改完即停，由外部 verifier 判定。

## 參考

- 相關函式：`build_reading_profile`、`enrich_mc_with_reading_profile`、
  `derive_sim_tl`、`keypoint_compose`、`_profile_parts`。
- 下方附上 ledger 尾端（前幾輪的 verifier 結果與 signature）與本次
  verifier 輸出；若附 Triage 報告，優先採用其中假說。
