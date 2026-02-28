"""
Financescr FinCrime screening API schemas.

These pydantic models define the stable request/response contracts for the
deterministic FinCrime screening engine.

Author: Samuel Adebayo
"""
from __future__ import annotations
__author__ = "Samuel Adebayo"
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, model_validator

class ScreenOptions(BaseModel):
    """ Options controlling screening behaviour and evidence payload size."""
    top_k: int = Field(default=20, ge=1, le=200, description="number of candidates to retrieve before scoring")

class SubjectInput(BaseModel):
    """
    Explicit subject information for screenning.

    Notes:
    - `id_number` is accepted as raw input for convienience, but must be hashed immediately
        and MUST NOT be persisted in DB, logs, or audit events.
    """
    name: str = Field(..., description="Full name of the subject to be screened")
    dob : Optional[str] = Field(default=None, description="Date of birth of the subject in YYYY-MM-DD format")
    nationality: Optional[str] = Field(default=None, description="Nationality as ISO2 country code.")
    residence_country: Optional[str] = Field(default=None, description="Residence country as ISO2 country code.")
    id_number: Optional[str] = Field(default=None, description="Raw ID number (never stored; hashed immediately).")

class ScreenRequest(BaseModel):
    """
    Screening request.
    Provide either: 
    - customer_id (preferred): the service loads subject fields via CustomerProvider, OR
    - subject: explicitly provided subject information (used when customer_id is absent).

    if both are provided, customer_id wins (subject is ignored) for v1 determinism
    """
    customer_id: Optional[str] = Field(default=None, description="Bank-internal customer identifier.")
    subject: Optional[SubjectInput] = Field(default=None, description="Explicit subject fields (if no customer_id).")
    options: ScreenOptions = Field(default_factory=ScreenOptions)

    @model_validator(mode="after")
    def _validate_one_of(self) -> "ScreenRequest":
        """Validate that at least one of (customer_id, subject) is provided."""
        if not self.customer_id and not self.subject:
            raise ValueError("Provide either customer_id or subject")
        return self

class MatchEvidence(BaseModel):
    """
    Evidence for a single candidate match.
    
    This is designed to be audit-friendly:
    - score is a deterministic probability-like value (heuristic logistic in v1)
    - reasons are human-readable reason codes derived from feature contributions/policy
    - features may be included for top-N candidates (not necessarily all top-K)
    """
    candidate_id: str
    candidate_name: str
    list_type: str
    score: float
    reasons: List[str] = Field(default_factory=list)
    features: Dict[str, Any] = Field(default_factory=dict)

class TopMatch(BaseModel):
    """Summary of the best-scoring candidate match."""
    candidate_id: str
    candidate_name: str
    list_type: str
    score: float

Decision = Literal["CLEAR", "REVIEW"]
Confidence = Literal["LOW", "MED", "HIGH"]
Severity = Literal["LOW", "MED", "HIGH"]
Priority = Literal["P0", "P1", "P2"]
Action = Literal["CLEAR", "REVIEW_STANDARD", "REVIEW_URGENT", "REQUEST_INFO"]

class ScreenResponse(BaseModel):
    """
    Screening response.

    v1 returns a stable decision bundle plus evidence. As we implement later phases:
    - matches will include computed features and reason codes
    - decision will be derived from the model score + policy thresholds
    - cases/audit will be persisted in Postgres
    """
    request_id: str
    decision: Decision
    match_probability: float
    threshold_used: float
    uncertainty_band: float
    match_confidence_band: Confidence
    risk_severity: Severity
    case_priority: Priority
    recommended_action: Action
    reason_codes: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    top_match: Optional[TopMatch] = None
    matches: List[MatchEvidence] = Field(default_factory=list)
    model: Dict[str, Any] = Field(default_factory=dict)
    policy: Dict[str, Any] = Field(default_factory=dict)