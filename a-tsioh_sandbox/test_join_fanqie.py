#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: Ytenx.join_fanqie 而鄰切·真韻 → 正韻反切（非·寬）。"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_unified_index import Pingshui, Ytenx, derive_sim_tl  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
