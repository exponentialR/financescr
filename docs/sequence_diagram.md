```mermaid

sequenceDiagram
  participant U as User (UI)
  participant A as /agent/chat (Orchestrator)
  participant S as /screen (Decision)
  participant D as DB (Postgres)

  U->>A: POST /agent/chat {message: "Screen John Smith"}
  A->>D: insert USER message
  A->>A: intent=SCREEN_SUBJECT (rules)
  A->>D: insert TOOL intent_update + trace[0]

  A->>S: POST /screen {subject:{name:"John Smith"}}
  S->>D: insert screening + audit (+case if REVIEW)
  S-->>A: screening_response {risk_score, threshold, matches...}

  A->>A: needs_followup? (band=0.05 / gap / missingness)
  alt needs_followup && followup_remaining
    A-->>U: "Do you have DOB (YYYY-MM-DD)?"
    A->>D: insert ASSISTANT question + trace
  else no follow-up
    A-->>U: "Model decision is CLEAR/REVIEW..." + evidence
    A->>D: insert ASSISTANT message + trace
  end

  U->>A: POST /agent/chat {message:"1980-01-02", context: active subject}
  A->>D: insert USER message
  A->>S: POST /screen {subject:{name:"John Smith", dob:"1980-01-02"}}
  S->>D: insert screening + audit (+case if REVIEW)
  S-->>A: updated screening_response

  A-->>U: "Model decision is ..." + evidence + case link
  A->>D: insert ASSISTANT message + trace (followup_remaining=false)
  ```