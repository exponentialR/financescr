# Financescr

Financescr is a **FastAPI decisioning service** for:
1) **FinCrime screening + triage** (sanctions / PEP / adverse media), and  
2) **Credit decisioning** (personal loan underwriting),

with an **agentic front-door**.

**Design principle (strict):**
- **Deterministic engines decide** (scoring + explicit policy).
- The **LLM assists** (tool-calling orchestration, one follow‑up question, grounded explanation).
- Everything is **auditable, replayable, and evaluable**.

---

## What’s in the repo today

### Implemented
- `GET /health` (validates mounted data pack and exposes policy/data versions)
- `POST /agent/chat` (rule-based agent turn, persistent transcript, always returns tool trace)
- `GET /agent/conversations/{conversation_id}` (replay transcript + trace)
- Postgres persistence:
  - `conversations`
  - `conversation_messages`
- SQLAlchemy + Alembic migrations
- Docker Compose (API + Postgres)
- Provider layer (file-backed “data APIs”):
  - customers, watchlist, credit applications (JSONL under `/data/...`)
- Synthetic data generator:
  - `scripts/generate_data_v1.py` (seeded, deterministic)

### Planned (next)
- **FinCrime decision engine**
  - `POST /screen` (deterministic screening)
  - `GET /cases`, `GET /cases/{id}` (review workflow)
  - immutable audit log + case creation flow
  - offline fincrime eval harness + threshold tuning
- **Credit decision engine**
  - `POST /credit/apply` (deterministic PD + affordability + policy)
  - credit case flow (REFER queue)
  - offline credit eval harness + threshold tuning
- **LLM integration**
  - OpenAI tool-calling + grounded explanations (LLM never decides)
- **Tiny UI**
  - static HTML at `/ui` + scripted demo mode (curl + UI)

---

## Tech stack
- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Postgres (psycopg)
- Docker Compose

---

## Repo structure
```text
app/
  main.py
  api/
    routes.py
    schemas.py
  agent/
    intent.py
    trace.py
    orchestrator.py
  db/
    session.py
    models.py
    repo.py
  providers/
    jsonl.py
    customers.py
    watchlist.py
    credit.py
alembic/
scripts/
  generate_data_v1.py
tests/
docker-compose.yml
Dockerfile
```

---

## Local setup

### 1) Python deps (host)
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) External data pack (required)
Financescr reads **versioned data packs** from a host directory mounted into the container as `/data`.  
This keeps demo data **out of the repo** and makes runs reproducible.

Create the pack root (example):
```bash
mkdir -p ~/financescr_data/fincrime/v1
mkdir -p ~/financescr_data/credit/v1
mkdir -p ~/financescr_data/golden/v1
```

Generate synthetic v1 packs (seeded, deterministic):
```bash
python scripts/generate_data_v1.py --out_root ~/financescr_data --seed 42 \
  --n_customers 3000 --n_watchlist 3000 --n_credit_apps 3000 --n_fincrime_scenarios 1000
```

### 3) Configure the mount path for Docker
Create a local `.env` (not committed) with:
```bash
FINANCESCR_DATA_DIR=/Users/solua1/financescr_data
```

Docker Compose mounts:
- `${FINANCESCR_DATA_DIR}:/data:ro`

### 4) Start services
```bash
docker compose up --build -d
curl -s localhost:8000/health | python -m json.tool
```

---

# Data packs and schemas (FULL DETAIL)

Financescr uses **versioned data packs** under `/data`. A “version” is simply a folder label you control (e.g. `v1`).

## Data pack layout
```text
/data/
  fincrime/v1/
    policy.json
    customers.jsonl
    watchlist.jsonl
    labels.jsonl
  credit/v1/
    policy.json
    applications.jsonl
    labels.jsonl
  golden/v1/
    fincrime_golden.jsonl
    credit_golden.jsonl
```

### Why JSONL
JSON Lines (`.jsonl`) means:
- streaming-friendly
- easy batch processing
- stable line-by-line records (good for regression sets and eval harnesses)
- supports large packs without loading everything into memory

---

## FinCrime pack (`/data/fincrime/v1`)

### A) `customers.jsonl` — internal “KYC profile store”
**Purpose:** Mimics what a bank already knows about a customer (KYC/CRM).  
**Used by:** FinCrime screening (by `customer_id`), eval scenarios, agent follow-ups.

Each line is one customer profile.

**Schema (v1)**
- `customer_id` (string, required): stable ID (e.g. `C_002445`)
- `name` (string, required): full name as stored by the bank
- `dob` (string YYYY-MM-DD, nullable): date of birth
- `nationality` (string ISO2, nullable)
- `residence_country` (string ISO2, nullable)
- `id_hash` (string, nullable): **hashed** identifier (never raw ID number)
- `region` (enum string, required): `EU` or `ASIA` (for slice metrics)

**Example**
```json
{"customer_id":"C_002445","name":"Mariam Khan","dob":"1995-10-29","nationality":"SG","residence_country":"CZ","id_hash":null,"region":"ASIA"}
```

**Privacy rule (strict)**
- Never store raw ID numbers.
- Only `id_hash` is stored. Hashing is deterministic with a salt version.

---

### B) `watchlist.jsonl` — candidate universe (NOT training truth)
**Purpose:** The watchlist is the runtime **candidate set** (sanctions/PEP/adverse).  
**Used by:** retrieval + feature computation + evidence output.

Each line is one watchlist entity.

**Schema (v1)**
- `entity_id` (string, required): stable unique ID (e.g. `WL_000762`)
- `list_type` (enum string, required): `SANCTIONS|PEP|ADVERSE_MEDIA`
- `primary_name` (string, required): canonical watchlist name
- `aliases` (list[string], required but can be empty): alternate names/spellings/orderings/transliteration variants
- `dob` (list[string], optional): known DOB(s) (often missing in real lists)
- `nationalities` (list[string ISO2], optional)
- `residence_countries` (list[string ISO2], optional)
- `id_hashes` (list[string], optional): hashed identifiers if present (rare)
- `source` (string, optional): e.g. `OFAC`, `EU`, `HMT`, `UN`, `DEMO`
- `active` (bool, required): active/inactive record

**Example**
```json
{"entity_id":"WL_000762","list_type":"PEP","primary_name":"Walker Sarah","aliases":["Sarah Walker"],"dob":[],"nationalities":["HU"],"residence_countries":[],"id_hashes":[],"source":"DEMO","active":true}
```

**What list types mean**
- **SANCTIONS**: legally restricted parties (highest severity, typically P0 when confidence is MED/HIGH)
- **PEP**: politically exposed person (higher AML risk, triggers enhanced due diligence)
- **ADVERSE_MEDIA**: negative news / reputational risk (review policy varies)

---

### C) `labels.jsonl` — scenario truth for evaluation + training
**Purpose:** Defines “what should have happened” for an end-to-end screening scenario.  
This is your labelled ground truth for evaluation/training.

Each line is one **scenario** (a screening event for a customer).

**Schema (v1)**
- `scenario_id` (string, required): stable scenario ID (e.g. `SCN_000603`)
- `customer_id` (string, required): which customer was screened
- `label` (enum, required): `MATCH|NO_MATCH`
- `true_entity_id` (string, nullable): the correct `entity_id` if label is `MATCH`
- `notes` (string, optional): human note (synthetic / golden / edge case tags)

**Example**
```json
{"scenario_id":"SCN_000603","customer_id":"C_001469","label":"MATCH","true_entity_id":"WL_000338","notes":"synthetic_match"}
```

**How it’s used**
- **Retrieval evaluation:** `recall@k` = % of MATCH scenarios where `true_entity_id` appears in top-K retrieved candidates.
- **Decision evaluation:** precision/recall of REVIEW decision at a threshold.
- **Training (later):** expand each scenario into pairwise rows `(subject, candidate)` with target `y=1` for `true_entity_id`, else `y=0`.

---

### D) `policy.json` — deterministic decision policy (fincrime)
**Purpose:** Policy = operational decision rules (thresholds, severity/priority mapping).  
Policy is separate from the model so you can tune thresholds without retraining.

**Keys (v1)**
- `retrieval_top_k` (int): number of candidates retrieved for scoring
- `return_top_n` (int): number of matches returned as evidence
- `threshold` (float 0–1): cutoff for REVIEW decision
- `uncertainty_band` (float): ± band around threshold to trigger a single follow-up question
- `cost_fp` (float): false review cost (analyst load)
- `cost_fn` (float): missed match cost (high)
- `severity_by_list_type` (map): sanctions=HIGH etc.
- `priority_rules` (map): P0/P1/P2 routing based on severity + confidence band

---

## Credit pack (`/data/credit/v1`)

### A) `applications.jsonl` — loan applications
**Purpose:** Application-level signals (as if pulled from origination + internal risk systems).  
**Used by:** credit decisioning engine (PD + affordability + policy).

Each line is one application.

#### Required fields (v1)
- `application_id` (string): e.g. `A_002445`
- `customer_id` (string): links to fincrime customer record
- `product` (string): currently `PERSONAL_LOAN`
- `amount_gbp` (number)
- `term_months` (int)
- `income_monthly_gbp` (number)
- `outgoings_monthly_gbp` (number)
- `employment_status` (enum): `EMPLOYED|SELF_EMPLOYED|UNEMPLOYED`
- `employment_months` (int)
- `credit_utilisation` (float 0–1): derived if raw fields exist; otherwise treated as provided
- `missed_payments_12m` (int)
- `bank_balance_volatility` (float 0–1): derived if raw fields exist; otherwise treated as provided

#### Optional raw fields (recommended for realism)
These allow derived fields to be explained and recomputed deterministically.
- `revolving_balance_gbp` (number): total outstanding revolving balance (cards)
- `revolving_limit_gbp` (number): total revolving credit limit
- `balance_mean_gbp` (number): mean daily balance over lookback window (e.g. 90d)
- `balance_std_gbp` (number): std dev of daily balance over lookback window
- `days_overdraft_90d` (int): count of overdraft days in last 90 days

**Derivation formulas (if raw fields present)**

**Credit utilisation**
\[
\text{credit\_utilisation} =
\text{clip}\left(\frac{\text{revolving\_balance\_gbp}}{\max(\text{revolving\_limit\_gbp}, \epsilon)}, 0, 1\right)
\]
with \(\epsilon\) small (e.g. 1.0) to avoid division by zero.

**Bank balance volatility**
\[
\text{bank\_balance\_volatility} =
\text{clip}\left(\frac{\text{balance\_std\_gbp}}{\max(\text{balance\_mean\_gbp}, \epsilon)}, 0, 1\right)
\]
Optionally, you can incorporate overdraft days as a separate feature or as a policy guardrail.

**Precedence rule**
- If raw fields exist and are valid, **Financescr derives** the feature deterministically.
- Otherwise it uses the provided `credit_utilisation` / `bank_balance_volatility`.

**Example (v1 minimal)**
```json
{"application_id":"A_002445","customer_id":"C_002445","product":"PERSONAL_LOAN","amount_gbp":300,"term_months":12,"income_monthly_gbp":600,"outgoings_monthly_gbp":325.5,"employment_status":"EMPLOYED","employment_months":23,"credit_utilisation":0.3094,"missed_payments_12m":0,"bank_balance_volatility":0.7115}
```

---

### B) `labels.jsonl` — credit outcomes
**Purpose:** supervised learning/evaluation truth for PD modelling.

Each line is one outcome label.

**Schema (v1)**
- `application_id` (string, required)
- `default_12m` (int 0/1, required): whether the borrower defaulted within 12 months
- `pd_12m` (float 0–1, optional/debug): synthetic underlying probability used during generation

**Example**
```json
{"application_id":"A_002445","pd_12m":0.2055,"default_12m":0}
```

**What is `default_12m`**
- Binary target: 1 if default event within 12 months, else 0.
- In real lending, “default” is defined by delinquency/charge-off rules (e.g., 90+ DPD). Here it is a consistent synthetic label.

---

### C) `policy.json` — deterministic decision policy (credit)
**Purpose:** converts PD + affordability into APPROVE/REFER/DECLINE and (optionally) APR pricing.

**Key behaviours**
- Compute features (including derived utilisation/volatility if raw fields exist)
- Score PD (heuristic logistic → trained LR later)
- Apply affordability stress test and PD thresholds
- Emit reason codes and a decision bundle

---

## Golden pack (`/data/golden/v1`)

Golden sets are **regression fixtures**: small curated subsets used to detect unintended changes in feature compute, scoring, or policy.

### A) `credit_golden.jsonl`
- `golden_id` (string)
- `application_id` (string)
- `notes` (string)

Example:
```json
{"golden_id":"GCRED_026","application_id":"A_002945","notes":"golden_credit_regression"}
```

### B) `fincrime_golden.jsonl`
Same idea, but for fincrime scenarios.

Example:
```json
{"scenario_id":"GSCN_012","customer_id":"C_000049","label":"MATCH","true_entity_id":"WL_000265","notes":"golden_match"}
```

---

## Required vs optional vs planned (summary)

### Credit `applications.jsonl`
- Required v1: the current fields in generator (amount/term/income/outgoings/employment/utilisation/missed/volatility)
- Optional v1 (recommended): raw balance/limit/stats fields to derive utilisation/volatility
- Planned v2: more realistic stability fields (months_at_address, housing_status, dependents) and richer bureau-like signals

### Fincrime data
- Required v1: customers + watchlist + scenario labels + policy
- Planned v2: list subtypes (e.g. terrorism/narcotics) and richer alias/transliteration coverage

---

## Contracts vs data vs policy (mental model)
- **Data** (`*.jsonl`): “world state” (customers, watchlist, applications)
- **Labels** (`labels.jsonl`): truth used for evaluation/training
- **Policy** (`policy.json`): operational decision thresholds + routing rules
- **Model** (later `model.json`): weights/coefficients used to score deterministically

---

## Existing API usage

### Health
```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

### Agent Chat
```bash
CID=$(python -c "import uuid; print(uuid.uuid4())")
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CID\",\"message\":\"help\"}" | python -m json.tool
```

### Conversation Replay
```bash
curl -s http://127.0.0.1:8000/agent/conversations/$CID | python -m json.tool
```

---

## Roadmap (high level)
1. Fincrime: implement `POST /screen` (retrieval → features → heuristic logistic → policy)
2. Credit: implement `POST /credit/apply` (PD → affordability → policy)
3. Persistence + audit + cases for both domains
4. Offline eval harness + threshold tuning + slice metrics
5. OpenAI tool-calling + grounded explanation generation
6. Tiny static UI + scripted demo mode (curl + UI)

---

## Notes on determinism & auditability
- Deterministic inference: same input + same data pack + same policy = same output.
- No raw secrets/PII in audit logs (no raw ID numbers).
- Model score is separate from policy decision.
- Traces and transcripts are persisted for replay.

