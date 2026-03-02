"""
Fincrime feature utilities.

Phase 1:
- name-aware Jaro-Winkler similarity suitable for multi-token person names.

Why name-aware?
Raw Jaro-Winkler is character-order sensitive. For names, token order can be swapped
("Walker Sarah" vs "Sarah Walker") and should still score highly. Conversely, unrelated
names may share common characters and can otherwise score too high.

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

from typing import List

from app.fincrime.normalise import normalise_text, tokenise


def _jaro_distance(s1: str, s2: str) -> float:
    """Compute Jaro similarity between two strings. Returns a value in [0, 1]."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while k < len2 and not s2_matches[k]:
            k += 1
        if k < len2 and s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2

    return ((matches / len1) + (matches / len2) + ((matches - transpositions) / matches)) / 3.0


def _jaro_winkler_raw(s1: str, s2: str, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    """Jaro-Winkler on already-normalised strings."""
    j = _jaro_distance(s1, s2)

    prefix_len = 0
    for i in range(min(len(s1), len(s2), max_prefix)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break

    return min(1.0, j + prefix_len * prefix_scale * (1.0 - j))


def jaro_winkler(a: str, b: str, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    """Standard Jaro-Winkler similarity on normalised full strings (order-sensitive)."""
    s1 = normalise_text(a)
    s2 = normalise_text(b)
    return _jaro_winkler_raw(s1, s2, prefix_scale=prefix_scale, max_prefix=max_prefix)


def name_similarity_jw(a: str, b: str) -> float:
    """
    Name-aware similarity score in [0, 1].

    Strategy:
    - Tokenise both names.
    - Compute max token-to-token JW to capture last-name/first-name robustness.
    - Compute JW on sorted-token full strings to be order-invariant.
    - Blend the two for stability.
    """
    ta: List[str] = tokenise(a)
    tb: List[str] = tokenise(b)

    if not ta or not tb:
        return 0.0

    token_max = 0.0
    for x in ta:
        for y in tb:
            token_max = max(token_max, _jaro_winkler_raw(x, y))

    sa = " ".join(sorted(ta))
    sb = " ".join(sorted(tb))
    full_sorted = _jaro_winkler_raw(sa, sb)

    return 0.6 * full_sorted + 0.4 * token_max