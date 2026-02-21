# AGENTS.md — Financescr

Financescr is a production-lean FinCrime screening + triage service:
- API-first with a tiny analyst UI
- explicit decisioning policy (thresholding)
- auditability (immutable audit log)
- evaluation harness (PR/threshold + slice metrics)
- observability (structured logs + optional OTEL tracing)

This repo exists to demonstrate **Lead DS/ML + engineering** maturity. Do not build a toy CRUD app.

---

## 0) What “done” means (Weekend 1)
By end of Weekend 1, we must be able to demo:

### A) Screening flow (API + UI)
1) Analyst opens `/ui`
2) Submits an entity (name + optional DOB/country)
3) System returns:
   - decision: CLEAR or REVIEW
   - risk_score (0..1)
   - reasons (strings)
   - evidence (top matches, features, policy info)
4) If REVIEW: a case is created and appears in the review queue list

### B) Persistence + auditability
- Every /screen request produces an immutable audit_log row
- Every REVIEW decision creates a case row
- `/cases` shows latest cases
- `/cases/{id}` shows case + linked audit events

### C) Evaluation output
- `python -m eval.run` writes `eval/report.json` deterministically
- report schema is final even if metrics are placeholders in Weekend 1

### D) Production signals
- Structured JSON logs per request (decision, score, threshold, latency, version)
- CI runs offline (no web calls) and passes

---

## 1) Non-goals (explicit)
- No full UI or design system
- No authentication/SSO (demo only)
- No real PII or regulated datasets stored in the repo
- No compliance claims (we demonstrate engineering + evaluation discipline)

---

## 2) Hard constraints
- Python 3.11
- FastAPI + Pydantic models for every endpoint
- Postgres via psycopg (NO ORM)
- Minimal dependencies: add a new dep only if justified and documented
- CI must be fully offline
- Tests required for:
  - endpoint contracts
  - decision policy
  - persistence layer (mocked or testcontainers only if necessary)

---

## 3) Repository layout (expected)
```text
repo/
  app/
    main.py
    routes/
      screen.py
      cases.py
      health.py
      ui.py
    core/
      policy.py
      scoring.py
      versioning.py
      logging.py
    db/
      conn.py
      schema.py
      repo.py
      init.py
  static/
    index.html
  docs/
    architecture.md
    demo.md
    data.md
  data/
    watchlist.jsonl
    labels.jsonl
  eval/
    run.py
    metrics.py
    report_schema.py
  tests/
    test_contract_screen.py
    test_contract_cases.py
    test_policy.py
    test_repo.py
  RUNBOOK.md
  docker-compose.yml
  .env.example
```
Keep modules small. Prefer pure functions where possible.

---

## 4) API Contracts (must remain stable)
### GET /health
```
Response:
{ "status": "ok" }
```
### POST /screen
```
Request:
{
  "entity_id": "optional-string",
  "name": "string",
  "dob": "YYYY-MM-DD optional",
  "country": "optional-string",
  "attributes": { "optional": "json" }
}
```
```
Response:
{
  "request_id": "uuid",
  "version_stamp": "financescr:v0.1.0",
  "decision": "CLEAR|REVIEW",
  "risk_score": 0.0,
  "reasons": ["string"],
  "evidence": {
    "matches": [
      {
        "candidate_id": "string",
        "candidate_name": "string",
        "list_name": "string",
        "score": 0.0,
        "features": { "feature": 0.0 }
      }
    ],
    "adverse_media": {
      "signal": 0.0,
      "snippets": ["string"],
      "source": "fixture"
    },
    "policy": {
      "threshold": 0.7,
      "recall_target": 0.8,
      "cost_fp": 1.0,
      "cost_fn": 15.0
    },
    "model": {
      "name": "baseline_heuristic|match_lr",
      "version": "v0",
      "trained_at": "optional"
    },
    "case_id": "optional"
  }
}
```
### GET /cases
```
Response:
{
  "items": [
    {
      "case_id": "string",
      "created_at": "ISO-8601",
      "status": "OPEN|CLOSED",
      "entity_name": "string",
      "decision": "REVIEW",
      "risk_score": 0.0,
      "request_id": "uuid",
      "version_stamp": "string"
    }
  ]
}
```
### GET /cases/{case_id}
```
Response:
{
  "case": { ...same as list plus evidence... },
  "audit_events": [
    {
      "ts": "ISO-8601",
      "event": "screen_request|case_created|case_viewed",
      "request_id": "uuid",
      "payload": { "summary": "..." }
    }
  ]
}
```

Error handling (minimum):
- 422 validation errors handled by FastAPI
- 500 returns { "error": "internal_error", "request_id": "<uuid>" }

---

## 5) Data model (Postgres)
We keep schema minimal but credible.

Table: cases
- case_id TEXT PRIMARY KEY (uuid string)
- created_at TIMESTAMPTZ NOT NULL DEFAULT now()
- status TEXT NOT NULL  -- OPEN/CLOSED
- entity_name TEXT NOT NULL
- decision TEXT NOT NULL  -- REVIEW
- risk_score DOUBLE PRECISION NOT NULL
- evidence JSONB NOT NULL
- version_stamp TEXT NOT NULL
- request_id UUID NOT NULL

Indexes:
- idx_cases_created_at on created_at desc
- idx_cases_request_id on request_id

Table: audit_log (immutable)
- id BIGSERIAL PRIMARY KEY
- ts TIMESTAMPTZ NOT NULL DEFAULT now()
- event TEXT NOT NULL
- payload JSONB NOT NULL
- version_stamp TEXT NOT NULL
- request_id UUID NOT NULL

Indexes:
- idx_audit_request_id on request_id
- idx_audit_ts on ts desc

Audit payload MUST include:
- decision, risk_score, threshold, reasons
- match summary (top-k candidate ids + scores)
Audit payload MUST NOT include:
- raw PII beyond what user typed (no extra enrichment)
- full documents/articles (store snippet hashes or short snippets only)

---

## 6) DS/ML spine (how we avoid “backend-only”)
Weekend 1 uses a deterministic baseline that is already “ML-ready”:
- compute matching features against a local watchlist fixture
- convert features -> risk_score via weighted heuristic
- apply explicit threshold policy
- store features in evidence for transparency

Weekend 2 upgrades scoring to a real model:
- train logistic regression on labelled pairs (match vs non-match)
- risk_score = P(match)
- keep same evidence format; only model fields change

We will not claim SOTA. We will show:
- feature engineering + threshold tuning + slice evaluation + feedback loop readiness

---

## 7) Feature set (match scoring)
For each candidate:
- f_token_sort (0..1)
- f_partial_ratio (0..1)
- f_jaro_like (0..1)  (approx or omit if not available)
- f_len_ratio (0..1)
- f_country_match (0/1)
- f_dob_match (0/1/unknown -> encode as 0/0.5/1)
- f_alias_hit (0/1) (optional)
Baseline risk_score (Weekend 1):
- weighted sum -> sigmoid -> [0..1]
Return features in evidence.

---

## 8) Decision policy (explicit + versioned)
Env vars:
- FINANCESCR_VERSION_STAMP="financescr:v0.1.0"
- FINANCESCR_THRESHOLD="0.70"
- FINANCESCR_RECALL_TARGET="0.80"
- FINANCESCR_COST_FP="1.0"
- FINANCESCR_COST_FN="15.0"

Logic:
- decision = REVIEW if risk_score >= threshold else CLEAR
- include threshold & costs in evidence.policy and logs

---

## 9) Evaluation requirements (mandatory)
```bash
`python -m eval.run` must:
- read `data/labels.jsonl`
- compute metrics deterministically
- write `eval/report.json` with stable schema (below)
```
```
`data/labels.jsonl` format (one per line):
{
  "name": "typed entity",
  "dob": "optional",
  "country": "optional",
  "candidates": [
    {"candidate_id":"X","candidate_name":"Y","label":1},
    {"candidate_id":"A","candidate_name":"B","label":0}
  ]
}
```

Weekend 1: allow placeholder metrics if needed, but keep schema final.

---

## 10) eval/report.json schema (final)
```
{
  "run": {
    "ts": "ISO-8601",
    "version_stamp": "financescr:v0.1.0",
    "model": {"name":"baseline_heuristic","version":"v0"},
    "threshold": 0.7,
    "recall_target": 0.8,
    "cost_fp": 1.0,
    "cost_fn": 15.0,
    "seed": 1337
  },
  "metrics": {
    "precision_at_recall_target": 0.0,
    "recall_at_threshold": 0.0,
    "false_review_rate": 0.0,
    "expected_cost": 0.0,
    "confusion_matrix": {"tp":0,"fp":0,"tn":0,"fn":0}
  },
  "slices": [
    {"slice":"name_len<=8","precision":0.0,"recall":0.0,"n":0},
    {"slice":"country_missing","precision":0.0,"recall":0.0,"n":0}
  ],
  "latency": {
    "p50_ms": 0,
    "p95_ms": 0
  }
}
```
---

## 11) Observability requirements
Structured JSON log per /screen request with:
- ts, request_id, version_stamp
- decision, risk_score, threshold
- reasons (list)
- latency_ms
- top_candidate_score
- error (if exception)

If OTEL enabled:
- spans: match_candidates, score_candidate, route_decision, persist_audit, create_case
- span attrs: request_id, use_case="screen", decision

---

## 12) Tiny UI requirements
UI must be single-file HTML + minimal CSS + vanilla JS fetch calls.
No build tool. No framework.

/ UI behaviour:
- form -> calls POST /screen
- renders response (decision, score, reasons, evidence.matches table)
- refreshes case list via GET /cases
- clicking a case calls GET /cases/{id} and displays evidence + audit events

---

## 13) Working rules for coding agents
- Make the smallest change that satisfies a milestone.
- Add tests for logic that could silently fail (policy, scoring, persistence).
- Prefer eval + observability over “features”.
- Keep CI offline.
- If you must choose: ship /screen + audit + eval report schema first.
