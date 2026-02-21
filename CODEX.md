# CODEX_TASKS — Financescr (copy/paste into Codex)

Use ONE task per Codex run. Follow AGENTS.md strictly.
Each task must include: plan, files touched, tests added, docs updated, commands to run.

---

## Task 1 — Stable API contract + request_id/version_stamp
Implement:
- Pydantic models for ScreenRequest/ScreenResponse
- /health endpoint
- /screen endpoint stub (no DB yet), returns deterministic placeholder decision/score/evidence
Add contract tests for /health and /screen schema.

Acceptance:
- response includes request_id + version_stamp
- tests pass (pytest)
- docs/demo.md contains curl example for /screen

---

## Task 2 — Postgres schema + init script
Implement:
- schema definitions for cases + audit_log (+ indexes)
- `python -m app.db.init` idempotent init
Add unit test for schema init logic (mock psycopg connect).

Acceptance:
- running init twice works
- docs/architecture.md updated with table descriptions

---

## Task 3 — DB connection + repository layer (no ORM)
Implement:
- app/db/conn.py: build DSN from env
- app/db/repo.py: functions:
  - insert_audit(event, payload, version_stamp, request_id)
  - create_case(case_fields) -> case_id
  - list_cases(limit=50)
  - get_case(case_id)
  - get_audit_by_request_id(request_id)
Add unit tests using mocked cursor/connection objects.

Acceptance:
- functions exist, covered by tests
- errors raise clear exceptions

---

## Task 4 — Decision policy module + baseline scoring features
Implement:
- app/core/policy.py: loads threshold/costs/recall_target from env
- app/core/scoring.py: computes matching features + heuristic score
- app/core/versioning.py: resolves version_stamp from env default
Add unit tests for:
- thresholding logic
- score determinism given same inputs
- feature bounds in [0,1]

Acceptance:
- scoring returns {risk_score, reasons, evidence.matches with features}
- deterministic behaviour under fixed seed/order

---

## Task 5 — Wire /screen to persistence (audit always, case on REVIEW)
Update /screen to:
- generate request_id
- compute score/decision using policy
- insert audit_log row always
- if REVIEW: create case row and return case_id in evidence
Add integration-ish tests by mocking repo layer:
- CLEAR does not create case
- REVIEW creates case
- audit always written

Acceptance:
- logs include decision/score/threshold
- contract tests updated accordingly

---

## Task 6 — Cases endpoints
Implement:
- GET /cases
- GET /cases/{id} returning case + audit events (by request_id)
Add contract tests for both.

Acceptance:
- listing returns at most 50
- detail returns audit events sorted by ts desc

---

## Task 7 — Structured JSON logging (+ latency_ms)
Implement:
- app/core/logging.py helper to emit JSON logs consistently
- /screen logs must include:
  request_id, version_stamp, decision, risk_score, threshold_used, latency_ms, top_candidate_score
Add tests using caplog to ensure fields present.

Acceptance:
- logs are JSON (stringified dict)
- caplog tests pass

---

## Task 8 — Offline eval harness (final schema)
Implement:
- eval/report_schema.py defining report schema builder
- eval/metrics.py with precision/recall/confusion/cost + slice metrics
- eval/run.py reads data/labels.jsonl, runs scoring, writes eval/report.json deterministically
Include tiny fixtures under data/ and tests verifying:
- report.json schema
- determinism (two runs identical)

Acceptance:
- `python -m eval.run` produces report.json
- CI runs offline

---

## Task 9 — Tiny UI (single file, no build)
Implement:
- static/index.html with:
  - screening form
  - results panel
  - cases list + case detail
- app/routes/ui.py: GET /ui serves the HTML
- JS fetch calls to /screen, /cases, /cases/{id}
Add a basic smoke test: GET /ui returns 200 and contains expected marker text.

Acceptance:
- manual demo works
- no frontend deps added

---

## Task 10 — Docs and runbook
Update:
- docs/demo.md with exact demo steps
- docs/architecture.md with full data flow
- docs/data.md describing fixture formats and label semantics
- RUNBOOK.md with failure modes + rollback

Acceptance:
- demo.md can be followed verbatim
