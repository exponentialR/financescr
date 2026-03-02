"""
Unit tests for fincrime string similarity.

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

import unittest

from app.fincrime.features import name_similarity_jw, jaro_winkler


class TestFincrimeSimilarity(unittest.TestCase):
    def test_exact_match(self):
        self.assertAlmostEqual(name_similarity_jw("Sarah Walker", "Sarah Walker"), 1.0, places=6)

    def test_token_order_difference(self):
        self.assertGreater(name_similarity_jw("Walker Sarah", "Sarah Walker"), 0.90)

    def test_small_typo(self):
        self.assertGreater(name_similarity_jw("Mohammed Khan", "Mohamad Khan"), 0.90)

    def test_diacritic_fold(self):
        self.assertGreater(name_similarity_jw("José Silva", "Jose Silva"), 0.95)

    def test_far_apart(self):
        self.assertLess(name_similarity_jw("Sarah Walker", "Ivan Petrov"), 0.30)

    def test_raw_jw_is_order_sensitive(self):
        self.assertLess(jaro_winkler("Walker Sarah", "Sarah Walker"), 0.80)