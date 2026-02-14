```mermaid
stateDiagram-v2
  [*] --> IDLE

  IDLE --> SCREENED_DONE: user provides name \n screen_subject runs\nno follow-up needed
  IDLE --> SCREENED_NEEDS_FOLLOWUP: user provides name\nscreen_subject runs\nneeds_followup=true

  SCREENED_NEEDS_FOLLOWUP --> SCREENED_DONE: user answers follow-up\nre-screen\nfollowup_remaining=false
  SCREENED_NEEDS_FOLLOWUP --> SCREENED_DONE: user refuses/skip\nno more follow-ups\nuse current result

  SCREENED_DONE --> CASE_CONTEXT: user opens case\nget_case
  CASE_CONTEXT --> SCREENED_DONE: user screens new subject\n(intent SCREEN_SUBJECT)

  SCREENED_DONE --> IDLE: reset conversation\n(new conversation_id)
  CASE_CONTEXT --> IDLE: reset conversation\n(new conversation_id)
  ```