# Financescr synthetic data (v1)

Synthetic, non-PII fixtures for:
- candidate retrieval/matching against a watchlist corpus
- offline evaluation (precision/recall, threshold tuning, slice metrics)
- later training for a simple match-risk model (logistic regression) using derived pairwise examples

## watchlist.jsonl
Purpose: reference corpus the system screens against.

Schema:
- candidate_id: string, unique (e.g., "WL-000001")
- entity_type: "PERSON"
- names:
  - primary: string
  - aliases: string[]
  - name_parts: {given, family}
- attributes:
  - dob: "YYYY-MM-DD" | null
  - countries: string[] (ISO-3166-1 alpha-2) (may be empty)
  - gender: "M" | "F" | null
- identifiers: {national_id, passport} (null in v1)
- list:
  - list_name: string
  - list_type: "SANCTIONS" | "PEP" | "ADVERSE_MEDIA" | "INTERNAL_WATCH"
  - source: generator provenance
  - updated_at: date string

## labels.jsonl
Purpose: labelled evaluation scenarios; can be transformed into pairwise training examples.

Schema:
- scenario_id: string
- input: {entity_id, name, dob|null, country|null}
- candidates: [{candidate_id, label}]
- notes: {difficulty, reason}

Label semantics:
- Typically 0 or 1 positive candidate per scenario.
- A small fraction include multiple positives to simulate duplicates.

Regeneration:
Generated deterministically with seed=1337 (rules-based generator).
