#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: Ytenx.join_fanqie 而鄰切·真韻 → 正韻反切（非·寬）。"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_unified_index import (  # noqa: E402
    Collector,
    Pingshui,
    Ytenx,
    add_ytenx_char_fallback,
    build_reading_profile,
    derive_sim_tl,
    enrich_mc_with_reading_profile,
    load_extra_chars,
    norm_registers,
)

YTENX_ROOT = os.path.expanduser("~/dev/ytenx")


class JoinFanqieRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(YTENX_ROOT):
            raise unittest.SkipTest(f"ytenx data not found: {YTENX_ROOT}")
        cls.ytenx = Ytenx(YTENX_ROOT)
        cls.ps = Pingshui()

    def _mc_entry(self, speller, yun):
        """Build mc-layer entry like collect_volume."""
        yun_norm = self.ps.normalize_yun(yun)
        method, rec = self.ytenx.join_fanqie(speller, yun_norm, self.ps)
        entry = {"fanqie": speller + "切", "yun": yun}
        if method:
            entry["join"] = {"method": method, **{
                k: v for k, v in rec.items() if k != "fanqie"}}
        psrec = self.ps.lookup(yun)
        if psrec:
            entry["pingshui"] = psrec
        return entry

    def test_erlin_zhen_is_zhengyun_exact(self):
        yun = self.ps.normalize_yun("真")
        method, rec = self.ytenx.join_fanqie("而鄰", yun, self.ps)

        self.assertEqual(method, "正韻反切")
        self.assertNotEqual(method, "正韻反切·寬")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["xiaoyun"], 180)
        self.assertEqual(rec["taj"], "人")
        self.assertEqual(rec["miuk"], "真")
        self.assertEqual(rec["final"], "jeon")

    def test_pingshui_zhen_expected_tl(self):
        psrec = self.ps.lookup("真")
        self.assertIsNotNone(psrec)
        self.assertIn("in", psrec["expected_tl"])
        self.assertIn("un", psrec["expected_tl"])

    def test_derive_sim_tl_ren_erlin_zhen(self):
        """而鄰切·真 → 人：反切上字 而→日母，平聲次濁 → jin5/lin5。"""
        entry = self._mc_entry("而鄰", "真")
        sim = derive_sim_tl(entry, self.ytenx)
        self.assertIsNotNone(sim)

        self.assertIn("jin5", sim["syllables"])
        self.assertIn("lin5", sim["syllables"])
        self.assertEqual(sim["tone"], 5)
        self.assertEqual(sim["initial_category"], "日")
        self.assertEqual(sim["voicing"], "次濁")
        self.assertIn("in", sim["finals"])
        self.assertIn("un", sim["finals"])
        self.assertEqual(sim["confidence"], "high")

    def test_derive_sim_tl_zhong_fanqie_overrides_zhengyun_initial(self):
        """陟隆切：反切上字 陟→知母 應含 tiong1，非僅正韻 tc→章母 tsong1。"""
        entry = self._mc_entry("陟隆", "東")
        sim = derive_sim_tl(entry, self.ytenx)
        self.assertIsNotNone(sim)
        self.assertIn("tiong1", sim["syllables"])
        self.assertNotIn("tsong1", sim["syllables"])
        self.assertEqual(sim["initial_category"], "知")
        self.assertEqual(sim["source"], "反切上字")

        zy_only = {
            "join": {
                "method": "正韻反切",
                "xiaoyun": 22,
                "taj": "中",
                "miuk": "東",
                "initial": "tc",
                "final": "jong",
            },
            "pingshui": self.ps.lookup("東"),
        }
        sim_zy = derive_sim_tl(zy_only, self.ytenx)
        self.assertIsNotNone(sim_zy)
        self.assertIn("tsong1", sim_zy["syllables"])
        self.assertNotIn("tiong1", sim_zy["syllables"])
        self.assertEqual(sim_zy["initial_category"], "章")
        self.assertEqual(sim_zy["source"], "正韻聲母")

    def test_add_ytenx_char_fallback_xiao(self):
        """嘯：字頭歸小韻·外字 → 嘯部、siau3。"""
        coll = Collector()
        self.assertTrue(add_ytenx_char_fallback(coll, self.ytenx, self.ps, "嘯"))
        rec = coll.mc["嘯"][0]
        self.assertEqual(rec["join"]["method"], "字頭歸小韻·外字")
        self.assertEqual(rec["pingshui"]["bu"], "嘯")
        self.assertIn("siau3", rec["sim_tl"]["syllables"])

    def test_load_extra_chars_comments_and_dedup(self):
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
            f.write("# comment with 嘯\n")
            f.write("嘯 蕭\n")
            f.write("嘯\n")
            path = f.name
        try:
            self.assertEqual(load_extra_chars(path), ["嘯", "蕭"])
        finally:
            os.unlink(path)

    def test_norm_registers_wenyin_wendu_jiewenyin_map_to_wen(self):
        """文音、文讀、皆文音 → 文；可與其他已知語域並列。"""
        self.assertEqual(norm_registers("文音"), ["文"])
        self.assertEqual(norm_registers("文讀"), ["文"])
        self.assertEqual(norm_registers("皆文音"), ["文"])
        self.assertEqual(norm_registers("文音、白"), ["文", "白"])
        self.assertEqual(norm_registers("皆文音，俗"), ["文", "俗"])

    def test_norm_registers_wenbai_preserved(self):
        """既有 文白 標籤仍整體保留，不拆成 文+白。"""
        self.assertEqual(norm_registers("文白"), ["文白"])
        self.assertEqual(norm_registers("文白、漳"), ["文白", "漳"])

    def test_derive_sim_tl_keypoint_composed_from_reading_profile(self):
        """反切上下字 reading_profile → 關鍵點拼讀候選，保留規則候選。"""
        entry = self._mc_entry("而鄰", "真")
        entry["reading_profile"] = {
            "而": {"keypoints": [{"initial": "j", "tone": 5}]},
            "鄰": {"keypoints": [{"final": "in", "tone": 5}]},
        }
        sim = derive_sim_tl(entry, self.ytenx)
        self.assertIsNotNone(sim)

        self.assertIn("jin5", sim["syllables"])
        self.assertIn("lin5", sim["syllables"])
        self.assertEqual(sim["tone"], 5)
        self.assertEqual(sim["initial_category"], "日")

        composed = sim.get("keypoint_composed") or []
        self.assertIn("jin5", composed)

    def test_build_reading_profile_splits_tl_into_initial_final_tone(self):
        coll = Collector()
        coll.add_pair("林", "lim5", regs=("文",), src="test")
        kp = build_reading_profile(coll)["林"]["keypoints"][0]
        self.assertEqual(kp["tl"], "lim5")
        self.assertEqual(kp["initial"], "l")
        self.assertEqual(kp["final"], "im")
        self.assertEqual(kp["tone"], 5)

    def test_build_reading_profile_ranks_wen_before_colloquial(self):
        """文讀關鍵點優先於高頻白話讀。"""
        coll = Collector()
        for _ in range(10):
            coll.add_pair("車", "tshia1", regs=("白",), src="test")
        coll.add_pair("車", "tshiu1", regs=("文",), src="test")
        kps = build_reading_profile(coll)["車"]["keypoints"]
        self.assertEqual([k["tl"] for k in kps], ["tshiu1", "tshia1"])
        self.assertTrue(kps[0]["literary"])
        self.assertFalse(kps[1]["literary"])

    def test_build_reading_profile_ranks_ganwen_before_colloquial(self):
        """甘文佐證關鍵點優先於高頻白話讀。"""
        coll = Collector()
        for _ in range(5):
            coll.add_pair("行", "hiann5", regs=("白",), src="test")
        coll.add_pair("行", "hing5", regs=(), src="test")
        attest = {("行", "hing5"): ("甘文",)}
        kps = build_reading_profile(coll, attest=attest)["行"]["keypoints"]
        self.assertEqual([k["tl"] for k in kps], ["hing5", "hiann5"])
        self.assertTrue(kps[0]["literary"])

    def test_enrich_mc_with_reading_profile_adds_keypoint_composed(self):
        """既有 mc.sim_tl 以反切上下字關鍵點補強，且不殘留 reading_profile。"""
        entry = self._mc_entry("而鄰", "真")
        sim = derive_sim_tl(entry, self.ytenx)
        self.assertIsNotNone(sim)
        entry["sim_tl"] = {**sim, "syllables": ["lin1"]}

        coll = Collector()
        coll.add_pair("而", "jin5", regs=("文",), src="test")
        coll.add_pair("鄰", "lin5", regs=("文",), src="test")
        profile = build_reading_profile(coll)
        coll.mc["人"] = [entry]

        enriched, added = enrich_mc_with_reading_profile(
            coll, self.ytenx, profile)
        self.assertEqual(enriched, 1)
        self.assertGreater(added, 0)
        self.assertIn("keypoint_composed", entry["sim_tl"])
        self.assertIn("jin5", entry["sim_tl"]["keypoint_composed"])
        self.assertNotIn("reading_profile", entry)


if __name__ == "__main__":
    unittest.main()
