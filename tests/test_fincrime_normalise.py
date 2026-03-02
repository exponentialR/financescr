"""
Unit tests for fincrime normalisation/tokenisation.

Author: Samuel Adebayo
"""
from __future__ import annotations
__author__ = "Samuel Adebayo"
import unittest
from app.fincrime.normalise import ascii_fold, normalise_text, tokenise, ascii_fold

class TestFincrimeNormalise(unittest.TestCase):
    def test_ascii_fold(self):
        self.assertEqual(ascii_fold("José"), "Jose")
        self.assertEqual(ascii_fold("Łukasz"), "lukasz")
        self.assertEqual(ascii_fold("München"), "Munchen")

    def test_normalise_apostrophes_and_hyphens(self):
        self.assertEqual(normalise_text("O'Neill"), "o neill")
        self.assertEqual(normalise_text("Jean-Luc Picard"), "jean luc picard"
        )
    def test_normalise_whitespace_and_punc(self):
        self.assertEqual(normalise_text("  Sarah   Walker  "), "sarah walker")
        self.assertEqual(normalise_text("Walker, Sarah!!"), "walker sarah")

    def test_tokenize(self):
        self.assertEqual(tokenise("Walker Sarah"), ["walker", "sarah"])
        self.assertEqual(tokenise(""), [])
        self.assertEqual(tokenise(None), [])