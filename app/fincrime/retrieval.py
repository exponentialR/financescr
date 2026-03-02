"""
Fincrime watchlist candidate retrieval 

This module implements deterministic top-K retrieval over a watchlist using 
lexical heuristics. Simple, fast, and explainable

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

from dataclasses import dataclass
from typing import List, Tuple, Optional, Sequence, Iterable
from app.fincrime.normalise import tokenise, normalise_text

@dataclass(frozen=True)
class RetrievalHit:
    """
    A retreievd candidate with the best matching name variant and its retreival score.
    """
    entity_id: str
    list_type: str
    best_name: str
    retrieval_score: float
    used_alias: bool

def _token_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    """
    Compute token-level Jaccard similarity.
    """
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union else 0.0

def _last_token(tokens: Sequence[str]) -> Optional[str]:
    """
    Get the last token from a sequence of tokens, if it exists.
    """
    return tokens[-1] if tokens else None

def score_name_variant(subject_name: str, candidate_name: str) -> float:
    """
    Score a subject name against a single candidate name variant.

    Score = token_jaccard + last_name_bonus + prefix_bonus (capped at 1.0).
    """
    subj_tokens = tokenise(subject_name)
    cand_tokens = tokenise(candidate_name)

    tj = _token_jaccard(subj_tokens, cand_tokens)

    last_bonus = 0.0
    st_last = _last_token(subj_tokens)
    ct_last = _last_token(cand_tokens)
    if st_last and ct_last and st_last == ct_last:
        last_bonus = 0.15

    prefix_bonus = 0.0
    subj_norm = normalise_text(subject_name)
    cand_norm = normalise_text(candidate_name)
    if subj_tokens and cand_tokens:
        if cand_norm.startswith(subj_tokens[0]) or subj_norm.startswith(cand_tokens[0]):
            prefix_bonus = 0.05

    return min(1.0, tj + last_bonus + prefix_bonus)


def best_entity_hit(subject_name: str, entity: dict) -> RetrievalHit:
    """
    Choose the best-scoring name variant (primary or alias) for a watchlist entity.
    """
    primary = entity["primary_name"]
    aliases = entity.get("aliases", []) or []

    best_name = primary
    best_score = score_name_variant(subject_name, primary)
    used_alias = False

    for a in aliases:
        s = score_name_variant(subject_name, a)
        if s > best_score:
            best_score = s
            best_name = a
            used_alias = True

    return RetrievalHit(
        entity_id=entity["entity_id"],
        list_type=entity["list_type"],
        best_name=best_name,
        retrieval_score=best_score,
        used_alias=used_alias,
    )


def retrieve_top_k(subject_name: str, watchlist: Iterable[dict], k: int) -> List[RetrievalHit]:
    """
    Retrieve top-K candidate entities from a watchlist.

    Deterministic ordering:
    - sort by retrieval_score desc
    - then by entity_id asc (stable tie-break)
    """
    hits: List[RetrievalHit] = [best_entity_hit(subject_name, e) for e in watchlist]

    hits.sort(key=lambda h: (-h.retrieval_score, h.entity_id))
    return hits[:k]