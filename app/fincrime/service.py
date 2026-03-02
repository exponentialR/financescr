"""
Financescr FinCrime screening service.

This module orchestrates the end-to-end deterministic screening flow:
- resolve subject (customer_id -> CustomerProvider) OR use provided subject
- load policy
- retrieve top-K candidates from watchlist (P1-3)
- return top-N retrieval evidence (debug) while scoring/policy decisioning is still stubbed

Later phases will add:
- similarity features (Jaro-Winkler) + frozen feature contract
- heuristic logistic scoring + reason codes
- threshold policy -> CLEAR vs REVIEW
- case creation + immutable audit log persistence

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

import uuid
from typing import Any, Dict, List

from app.fincrime.schemas import ScreenRequest, ScreenResponse, TopMatch
from app.fincrime.retrieval import retrieve_top_k
from app.providers.customers import CustomerProvider
from app.providers.watchlist import WatchlistProvider
from app.settings import get_settings, load_json


def _missing_fields(subject: Dict[str, Any]) -> List[str]:
    """
    Determine which corroborating fields are missing for disambiguation.

    Returns a list of field names used by:
    - agent follow-up logic (ask one question when uncertain)
    - audit/eval slice metrics (missing DOB/country etc.)

    Note: in Phase 1 we allow either id_number or id_hash presence to mark "id present".
    """
    missing: List[str] = []
    if not subject.get("dob"):
        missing.append("dob")
    if not subject.get("nationality"):
        missing.append("nationality")
    if not subject.get("residence_country"):
        missing.append("residence_country")
    if not subject.get("id_number") and not subject.get("id_hash"):
        missing.append("id_number")
    return missing


def _entity_to_dict(e: Any) -> Dict[str, Any]:
    """
    Convert WatchlistProvider entity objects into dicts expected by retrieval.

    WatchlistProvider returns WatchlistEntity dataclasses.
    """
    return {
        "entity_id": e.entity_id,
        "list_type": e.list_type,
        "primary_name": e.primary_name,
        "aliases": list(e.aliases or []),
        "active": bool(getattr(e, "active", True)),
    }


def screen(req: ScreenRequest) -> ScreenResponse:
    """
    Screen a subject against the watchlist.

    Current behaviour (P1-3):
    - resolves subject
    - retrieves top-K candidates deterministically
    - returns top-N retrieval evidence in `matches[]`
    - decision + match_probability remain stubbed until scoring is implemented

    Args:
        req: ScreenRequest containing either customer_id or explicit subject fields.

    Returns:
        ScreenResponse with stable contract and retrieval evidence.

    Raises:
        KeyError: If customer_id is provided and not found in the customer store.
        FileNotFoundError/ValueError: If policy JSON cannot be loaded.
    """
    s = get_settings()
    fincrime_policy = load_json(s.fincrime_policy_path)

    # Resolve subject (customer_id preferred)
    subject: Dict[str, Any]
    if req.customer_id:
        customers_path = getattr(s, "fincrime_customers_path", "/data/fincrime/v1/customers.jsonl")
        cp = CustomerProvider(customers_path)
        c = cp.get_customer(req.customer_id)
        subject = {
            "name": c.name,
            "dob": c.dob,
            "nationality": c.nationality,
            "residence_country": c.residence_country,
            "id_hash": c.id_hash,
        }
    else:
        # Provided subject mode
        subject = req.subject.model_dump()

    threshold = float(fincrime_policy["threshold"])
    band = float(fincrime_policy["uncertainty_band"])
    request_id = str(uuid.uuid4())
    missing = _missing_fields(subject)

    # --- P1-3: Retrieval top-K ---
    watchlist_path = getattr(s, "fincrime_watchlist_path", "/data/fincrime/v1/watchlist.jsonl")
    wp = WatchlistProvider(watchlist_path)
    entities = wp.all_entities()

    # Filter inactive (realistic)
    entity_dicts = [_entity_to_dict(e) for e in entities if getattr(e, "active", True)]
    top_k = int(req.options.top_k)
    hits = retrieve_top_k(subject["name"], entity_dicts, k=top_k)

    return_top_n = int(fincrime_policy.get("return_top_n", 5))
    matches: List[Dict[str, Any]] = []
    for h in hits[:return_top_n]:
        matches.append(
            {
                "candidate_id": h.entity_id,
                "candidate_name": h.best_name,
                "list_type": h.list_type,
                "score": float(h.retrieval_score),  # TEMP until scorer exists
                "reasons": ["RETRIEVAL_ONLY"],
                "features": {"used_alias": h.used_alias, "retrieval_score": float(h.retrieval_score)},
            }
        )

    top_match = None
    if hits:
        top_match = TopMatch(
            candidate_id=hits[0].entity_id,
            candidate_name=hits[0].best_name,
            list_type=hits[0].list_type,
            score=float(hits[0].retrieval_score),
        )

    # Stub decision until scoring/policy is implemented
    return ScreenResponse(
        request_id=request_id,
        decision="CLEAR",
        match_probability=0.0,  # will become top candidate p(match) after scorer lands
        threshold_used=threshold,
        uncertainty_band=band,
        match_confidence_band="LOW",
        risk_severity="LOW",
        case_priority="P2",
        recommended_action="CLEAR",
        reason_codes=[],
        missing_fields=missing,
        top_match=top_match,
        matches=matches,
        model={"name": "fincrime_heuristic_v1", "version": "v1_retrieval_debug"},
        policy={"version": fincrime_policy.get("version", "fincrime/v1")},
    )