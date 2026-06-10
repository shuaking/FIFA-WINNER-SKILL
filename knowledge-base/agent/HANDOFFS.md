# AI Octopus Paul Agent Handoff Contract

This document defines the handoff payloads that other runtime agents can use when delegating work to AI Octopus Paul.

Runtime implementation is intentionally local CLI for now. These payloads are static contracts for Codex, Claude Code, Cursor agents, CI agents, or future A2A/MCP wrappers.

## Common Envelope

```json
{
  "task_id": "caller-generated-id",
  "handoff_type": "prediction_requested",
  "state": "submitted",
  "agent_id": "ai-octopus-paul-predictor",
  "edition": "2026",
  "root": ".",
  "requested_at": "2026-06-10T12:00:00+08:00",
  "input": {},
  "artifacts": [],
  "safety": {
    "disclaimer_required": true,
    "betting_advice_allowed": false
  }
}
```

## States

- `submitted`: Caller has created the task.
- `working`: A runtime is invoking CLI tools.
- `input_required`: Required inputs such as edition, date, match id, or final score are missing.
- `blocked`: The agent cannot continue because evidence, source access, backend, or kickoff timing blocks the task.
- `completed`: The requested artifact exists and the caller can summarize it.
- `failed`: Tool execution failed unexpectedly.
- `canceled`: Caller stopped the task.

## Handoff Types

### `prediction_requested`

Use for date, match, teams, group, phase, or all-match prediction requests.

Required input:

```json
{
  "edition": "2026",
  "date": "2026-06-11",
  "match_id": "2026-GA-01",
  "teams": ["Mexico", "South Africa"],
  "scope": "date | match | teams | group | phase | all"
}
```

Recommended tools:

1. `plan_prediction_evidence`
2. `collect_daily_evidence` when date-specific evidence is missing
3. `predict_daily` or `predict_scoped`

### `evidence_refresh_needed`

Use when source readiness or daily evidence is missing or stale.

Recommended tools:

1. `audit_source_readiness`
2. `plan_prediction_evidence`
3. `collect_daily_evidence`

### `poster_requested`

Use only after the user asks for visual material.

Recommended tools:

1. `build_poster_prompt`
2. `generate_posters` only when a backend is configured

### `evaluation_requested`

Use after final scores are recorded in the match ledger.

Required input:

```json
{
  "edition": "2026",
  "date": "2026-06-11",
  "final_scores_recorded": true
}
```

Recommended tools:

1. `evaluate_predictions`
2. `prediction_evaluation_dashboard.py write`

## Completion Response

Runtime agents should summarize completed tasks with:

```text
Status: created | locked_existing_report | blocked | no_matches_found
Report: <path>
Matches: <count>
Main pick: <home/draw/away plus score>
Confidence: <low/medium/high>
Evidence gaps: <list or none>
Key layers: <2-3 analysis layer summaries>
Safety: 娱乐预测，非投注建议；不得作为投注、购彩或资金决策依据。
```
