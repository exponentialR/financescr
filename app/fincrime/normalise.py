"""
Fincrime text normalisation utilities.

These functions provide deterministic normalisation and tokenisation for:
- watchlist candidate retrieval (lexical scoring)
- similarity feature computation (token overlap/Jaccard)
- evidence/reason generation (consistent bahviour)
Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

import re 
from typing import List


_ASCII_FOLD_MAP = {
    # Common Latin diacritics we may emit in pools/variants
    "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a", "å": "a",
    "ç": "c",
    "é": "e", "è": "e", "ë": "e", "ê": "e",
    "í": "i", "ì": "i", "ï": "i", "î": "i",
    "ñ": "n",
    "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
    "ú": "u", "ù": "u", "ü": "u", "û": "u",
    "ý": "y", "ÿ": "y",

    # Central/Eastern Europe
    "ł": "l", "Ł": "l",
    "ś": "s", "Ś": "s",
    "ć": "c", "Ć": "c",
    "ń": "n", "Ń": "n",
    "ż": "z", "Ż": "z",
    "ź": "z", "Ź": "z",
    "ą": "a", "Ą": "a",
    "ę": "e", "Ę": "e",

    # Other common
    "š": "s", "Š": "s",
    "ž": "z", "Ž": "z",
}


_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9 ]+")
_MULTI_SPACE = re.compile(r"\s+")

def ascii_fold(text: str) -> str:
    """
    Replace a small set of diacritics with ASCII approximations.

    We intentionally keep this lightweight and deterministic (no external deps).
    """
    out_chars = []
    for ch in text:
        out_chars.append(_ASCII_FOLD_MAP.get(ch, ch))
    return "".join(out_chars)

def normalise_text(text: str) -> str:
    """
    Normalise a name-like string for deterministic matching.
    Steps:
    - ASCII fold (remove diacritics)
    - lowercase
    - apostrophes and hypens treated as spaces (O'Neill -> o neill, Jean-Luc -> jean luc)
    - remove remaining non-alphanumeric characters (keep spaces)
    - collapse whitepace
    """
    if text is None :
        return ""
    t = ascii_fold(text)
    t = t.lower()
    t = t.replace("-", " ").replace("'", " ")
    t = _NON_ALNUM_SPACE.sub(" ", t)
    t = _MULTI_SPACE.sub(" ", t)
    return t.strip()

def tokenise(text: str) -> List[str]:
    """
    Tokenise normalised text into tokens
    
    We do NOT remove stopwords because names are short and storpword removal can harm recall. 
    """
    t  = normalise_text(text)
    if not t:
        return []
    return t.split(" ")
