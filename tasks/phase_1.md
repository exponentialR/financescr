# Phase 1: FinCrime `/screen` End-to-End

Phase 1 covers deterministic retrieval -> features -> scoring -> policy -> persistence hooks.  
Goal: keep it tight and shippable.

## Phase 1 Outcome (Definition of Done)

You can run:

```bash
curl -s localhost:8000/screen \
  -H "content-type: application/json" \
  -d '{"customer_id":"C_002445","options":{"top_k":20}}' | python -m json.tool
```

And get a stable response with:

- `decision` (`CLEAR`/`REVIEW`)
- `match_probability` (top match score)
- `matches[]` (top-N evidence with features + reasons)
- `policy` bundle (`threshold_used`, `uncertainty_band`, `risk_severity`, `case_priority`, `recommended_action`)
- `missing_fields[]` (if DOB/country/id is missing)
- `request_id`

Phase 1 does not require cases/audit tables yet (persistence can be stubbed or logged).  
Include minimal interfaces now so DB persistence can be added in Phase 2 without refactors.

## Phase 1 Architecture (End-to-End Flow)

1. `/screen` receives `{customer_id}` or `{subject}`.
2. Resolve subject:
   - If `customer_id`: `CustomerProvider.get_customer(customer_id)`
   - Else: use provided `subject`
3. Candidate retrieval:
   - Iterate watchlist entities from `WatchlistProvider.all_entities()`
   - Score candidate names (primary + aliases) by token overlap + prefix bonus
   - Return top-K candidates
4. Feature compute (frozen order):
   - Name similarity + token jaccard + length ratio
   - DOB exact/year match (or `-1` if missing)
   - Nationality/residence overlap (or `-1` if missing)
   - `id_hash` match (or `-1` if missing)
   - List-type one-hots + `alias_hit`
5. Score:
   - v1 heuristic logistic -> `p(match)` per candidate
   - Use top1/top2 for confidence band
6. Policy:
   - Threshold + uncertainty band
   - Severity by list type
   - Priority from severity + confidence
   - Recommended action
   - `missing_fields`
7. Response:
   - Top match summary + matches evidence + policy/model metadata + deterministic trace block (non-LLM)

## Key Design Choices (Locked)

### 1) Input Contract: `customer_id` vs `subject`

- A) `customer_id` only (realistic)
- B) `subject` only (simple)
- C) both (preferred) -> selected

Decision: pick C so demos work with either path and the agent can pass a filled subject after follow-up.

### 2) Retrieval Method

- A) lexical token overlap + prefix bonus (fast, deterministic, good for 3k) -> selected
- B) Postgres trigram search (better, more setup)
- C) embeddings (scope creep)

Decision: pick A.

### 3) Name Similarity

- A) Jaccard only (too weak)
- B) Jaro(-Winkler) + token Jaccard (robust and explainable) -> selected
- C) edit distance heavy (slower)

Decision: pick B.

### 4) Output Evidence Format

- A) return only top1 match
- B) return top-N with features + reasons -> selected

Decision: pick B for auditability.

## Phase 1 Module Layout (Exact)

Add:

```text
app/fincrime/
  __init__.py
  schemas.py        # request/response pydantic models
  normalize.py      # deterministic normalization + tokenization
  retrieval.py      # top-K candidate retrieval
  features.py       # frozen feature computation
  scorer.py         # heuristic logistic scoring + reason contributions
  policy.py         # decision bundle computation
  service.py        # orchestrates end-to-end screen()
```

Wire endpoint:

- `app/api/routes.py` -> `POST /screen` calls `fincrime.service.screen(...)`

## Phase 1 Response Contract (Canonical v1)

Freeze this now.

### `POST /screen` Request

```json
{
  "customer_id": "C_002445",
  "subject": null,
  "options": {"top_k": 20}
}
```

### Response

```json
{
  "request_id": "uuid",
  "decision": "CLEAR|REVIEW",
  "match_probability": 0.81,
  "threshold_used": 0.72,
  "uncertainty_band": 0.05,
  "match_confidence_band": "LOW|MED|HIGH",
  "risk_severity": "LOW|MED|HIGH",
  "case_priority": "P0|P1|P2",
  "recommended_action": "CLEAR|REVIEW_STANDARD|REVIEW_URGENT|REQUEST_INFO",
  "reason_codes": ["..."],
  "missing_fields": ["dob", "nationality"],
  "top_match": {
    "candidate_id": "WL_000762",
    "candidate_name": "Walker Sarah",
    "list_type": "PEP",
    "score": 0.81
  },
  "matches": [
    {
      "candidate_id": "WL_000762",
      "candidate_name": "Walker Sarah",
      "list_type": "PEP",
      "score": 0.81,
      "reasons": ["NAME_SIMILARITY_HIGH", "LIST_PEP"],
      "features": {
        "name_jw": 0.92,
        "name_token_jaccard": 0.67,
        "dob_exact": -1,
        "nationality_overlap": 0,
        "residence_overlap": -1,
        "id_number_match": -1,
        "alias_hit": 1
      }
    }
  ],
  "model": {"name": "fincrime_heuristic_v1", "version": "v1"},
  "policy": {"version": "fincrime/v2"}
}
```

## Phase 1 Metrics (After Endpoint Works)

- Latency (ms)
- Top1/top2 gap distribution
- Retrieval candidate count
- Missingness rate

## Phase 1 Work Breakdown (8 Tickets)

### Ticket P1-1: Fincrime Schemas + Endpoint Stub

- Add request/response Pydantic models
- Implement `/screen` placeholder response using policy values from file

### Ticket P1-2: Normalization + Tokenization

- Deterministic normalizer used by retrieval + similarity

### Ticket P1-3: Retrieval Top-K

- Implement token overlap + prefix bonus
- Return `CandidateHit` with `best_name_used` + `retrieval_score`

### Ticket P1-4: Name Similarity (Jaro-Winkler + Jaccard)

- Pure Python Jaro-Winkler
- Unit tests for known pairs

### Ticket P1-5: Feature Computation (Frozen Contract)

- Compute 12-13 features (including `alias_hit`)
- Missingness encoding `-1`

### Ticket P1-6: Heuristic Logistic Scorer + Reason Codes

- Weights + intercept
- Produce per-candidate `p(match)` + contribution-based reasons

### Ticket P1-7: Policy Bundle

- Confidence band + severity + priority + recommended action + `missing_fields`

### Ticket P1-8: Wire End-to-End + Curl Demo Script

- `/screen` runs full path
- Add `scripts/demo_screen.sh` for 3 sample customers

## Two Essential Questions

1. Should Phase 1 `/screen` accept raw `id_number` in `subject`, or only `id_hash`?
   - Recommendation: accept `id_number`, hash immediately, never persist raw.
2. Should Phase 1 point to v2 data pack paths now, or keep v1 until v2 is generated?
   - Recommendation: use v2.

If unanswered, default assumptions are:

- Accept raw `id_number` and hash it immediately
- Use v2 pack paths

## Final Output Requirement

### 1) What We Demo in 5 Minutes

`POST /screen` screens a real `customer_id` against a 3k watchlist and returns deterministic match probability, decision bundle, and top-N evidence with features + reasons.

### 2) Decisions Locked Today

- `/screen` supports both `customer_id` and `subject`
- Retrieval = lexical token overlap + prefix bonus
- Similarity = Jaro-Winkler + token Jaccard
- Evidence includes top-N + features + reasons (audit-ready)
