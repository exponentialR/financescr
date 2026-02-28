"""
Financescr FinCrime screening service.

This module orchestrates the end-to-end deterministic screening flow:
- resolve subject (customer_id -> CustomerProvider) OR use provided subject
- load policy and apply it to produce a stable decision bundle

In Phase 1 (P1-1), this is a stub implementation that returns a stable contract.
Later phases will add:
- retrieval (top-K) against watchlist
- feature computation
- heuristic logistic scoring and reason codes
- threshold policy, case creation, and audit persistence

Author: Samuel Adebayo
"""
from __future__ import annotations

__author__ = "Samuel Adebayo"

import uuid
from typing import Any, Dict, List

from app.fincrime.schemas import ScreenRequest, ScreenResponse
from app.providers.customers import CustomerProvider
from app.settings import get_settings, load_json


def _missing_fields(subject: Dict[str, Any]) -> List[str]:
    """
    Determine which corroborating fields are missing for disambiguation.

    Returns a list of field names used by:
    - agent follow-up logic (ask one question when uncertain)
    - audit/eval slice metrics (missing DOB/country etc.)

    Note: in Phase 1 stub we allow either id_number or id_hash presence to mark "id present".
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


def screen(req: ScreenRequest) -> ScreenResponse:
    """
    Screen a subject against the watchlist (stub for P1-1).

    Args:
        req: ScreenRequest containing either customer_id or explicit subject fields.

    Returns:
        ScreenResponse with a stable contract. For P1-1, scoring is stubbed and
        match_probability is 0.0.

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

    # Stub outputs (until retrieval/scoring is implemented)
    request_id = str(uuid.uuid4())
    missing = _missing_fields(subject)

    return ScreenResponse(
        request_id=request_id,
        decision="CLEAR",
        match_probability=0.0,
        threshold_used=threshold,
        uncertainty_band=band,
        match_confidence_band="LOW",
        risk_severity="LOW",
        case_priority="P2",
        recommended_action="CLEAR",
        reason_codes=[],
        missing_fields=missing,
        top_match=None,
        matches=[],
        model={"name": "fincrime_heuristic_v1", "version": "v1_stub"},
        policy={"version": fincrime_policy.get("version", "fincrime/v1")},
    )