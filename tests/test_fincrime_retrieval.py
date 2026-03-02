"""
Unit tests for fincrime retrieval.

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

import unittest

from app.fincrime.retrieval import retrieve_top_k, score_name_variant


class TestFincrimeRetrieval(unittest.TestCase):
    def test_score_variant_basic(self):
        self.assertGreater(score_name_variant("Sarah Walker", "Walker Sarah"), 0.5)
        self.assertGreater(score_name_variant("O'Neill Sean", "Sean O Neill"), 0.5)
        self.assertLess(score_name_variant("Sarah Walker", "Ivan Petrov"), 0.2)

    def test_retrieve_top_k_deterministic(self):
        watchlist = [
            {"entity_id": "WL_000002", "list_type": "PEP", "primary_name": "Ivan Petrov", "aliases": []},
            {"entity_id": "WL_000001", "list_type": "PEP", "primary_name": "Walker Sarah", "aliases": ["Sarah Walker"]},
            {"entity_id": "WL_000003", "list_type": "SANCTIONS", "primary_name": "Sarah J Walker", "aliases": []},
        ]
        hits = retrieve_top_k("Sarah Walker", watchlist, k=2)
        self.assertEqual(len(hits), 2)
        # Best should be WL_000001 because it has exact alias match
        self.assertEqual(hits[0].entity_id, "WL_000001")
        # Second should be WL_000003 (still shares tokens)
        self.assertEqual(hits[1].entity_id, "WL_000003")

    def test_tie_break_on_entity_id(self):
        watchlist = [
            {"entity_id": "WL_000002", "list_type": "PEP", "primary_name": "John Smith", "aliases": []},
            {"entity_id": "WL_000001", "list_type": "PEP", "primary_name": "John Smith", "aliases": []},
        ]
        hits = retrieve_top_k("John Smith", watchlist, k=2)
        # same score, entity_id ascending should decide
        self.assertEqual(hits[0].entity_id, "WL_000001")
        self.assertEqual(hits[1].entity_id, "WL_000002")