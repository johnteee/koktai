#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: Ytenx.join_fanqie 而鄰切·真韻 → 正韻反切（非·寬）。"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_unified_index import Pingshui, Ytenx  # noqa: E402

YTENX_ROOT = os.path.expanduser("~/dev/ytenx")


class JoinFanqieRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(YTENX_ROOT):
            raise unittest.SkipTest(f"ytenx data not found: {YTENX_ROOT}")
        cls.ytenx = Ytenx(YTENX_ROOT)
        cls.ps = Pingshui()

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


if __name__ == "__main__":
    unittest.main()
