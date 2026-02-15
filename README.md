# Financescr

Financescr is a FastAPI service for FinCrime screening workflows.

This repo currently includes:
- conversation persistence in Postgres
- a rule-based agent chat endpoint
- conversation replay endpoint
- Alembic migration scaffolding
- offline unit tests for API, orchestration, and repository behavior

## Current Scope

Implemented now:
- `GET /health`
- `POST /agent/chat`
- `GET /agent/conversations/{conversation_id}`
- Postgres tables for `conversations` and `conversation_messages`
- deterministic intent routing with trace capture

Planned but not yet implemented on this branch:
- `/screen`, `/cases`, `/cases/{id}`
- audit log and case creation flow
- eval harness output (`eval/report.json`)
- UI at `/ui`

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- Postgres (psycopg)

## Project Structure

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
alembic/
tests/
docker-compose.yml
Dockerfile
```

## Local Setup

### 1) Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Start Postgres

```bash
docker compose up -d db
```

Default DB config from this repo:
- user: `financescr`
- password: `financescr`
- db: `financescr`
- host: `localhost`
- port: `5432`

### 3) Run migrations

```bash
alembic upgrade head
```

### 4) Start API

```bash
uvicorn app.main:app --reload
```

API will be available at `http://127.0.0.1:8000`.

## API Usage

### Health

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{"status":"ok"}
```

### Agent Chat

`conversation_id` is client-generated UUID. If it does not exist yet, a conversation row is created.

```bash
CID=$(python -c "import uuid; print(uuid.uuid4())")
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CID\",\"message\":\"help\"}"
```

Example response shape:

```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "assistant_message": "You can say: 'Screen <name>', 'List cases', 'Open case <id>', or 'Explain last'.",
  "trace": [
    {"step": 0, "kind": "INTENT_UPDATE", "summary": "intent=HELP", "tool": "intent_update"},
    {"step": 1, "kind": "RESPONSE", "summary": "assistant_message_returned"}
  ],
  "final_state": {"intent": "HELP", "case_id": null}
}
```

### Conversation Replay

```bash
curl http://127.0.0.1:8000/agent/conversations/$CID
```

Returns ordered transcript messages with timestamp, role, content, and optional trace/tool metadata.

## Running Tests

Run all tests:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Current tests cover:
- health contract
- DB session behavior
- model metadata/index mapping
- intent detection
- trace serialization
- orchestrator transaction behavior
- agent route validation/mapping
- repository helper behavior

## Database Notes

The current Alembic migration creates:
- `conversations`
- `conversation_messages`

Indexes:
- `ix_conversation_updated_at`
- `ix_conversation_messages_conversation_id_created_at`

## Docs

Additional design docs are in:
- `docs/architecture.md`
- `docs/sequence_diagram.md`
- `docs/state_machine.md`
