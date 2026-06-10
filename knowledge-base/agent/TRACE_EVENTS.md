# AI Octopus Paul Trace Events

This file defines a lightweight trace vocabulary for future runtime wrappers and for current CLI orchestrators that want consistent logs.

## Event Shape

```json
{
  "trace_id": "task-or-run-id",
  "event_id": "uuid-or-stable-counter",
  "event": "tool.started",
  "agent_id": "ai-octopus-paul-predictor",
  "edition": "2026",
  "match_id": "2026-GA-01",
  "timestamp": "2026-06-10T12:00:00+08:00",
  "status": "working",
  "message": "Running daily prediction",
  "data": {}
}
```

## Core Events

- `task.accepted`: A caller delegated a task to this agent.
- `task.blocked`: The task cannot continue without evidence, source access, backend, or user input.
- `tool.started`: A CLI tool started with sanitized arguments.
- `tool.finished`: A CLI tool finished with exit code, status, and artifact paths.
- `artifact.written`: A JSON, Markdown, SQLite, or media artifact was written.
- `guardrail.triggered`: A safety, source, copyright, or locked-report guardrail changed the response or blocked an action.
- `prediction.locked`: A pre-match prediction report became the canonical artifact.
- `handoff.created`: A downstream or upstream handoff payload was created.
- `handoff.completed`: A handoff produced an artifact or terminal status.

## Trace Data Rules

- Do not log API keys, cookies, tokens, or private user data.
- Log artifact paths, not entire large JSON reports.
- Log evidence gaps and blocker IDs.
- Log the safety disclaimer state for prediction-like outputs.

## Recommended Trace Sequence

For a daily prediction:

1. `task.accepted`
2. `tool.started` for source/evidence checks
3. `tool.finished`
4. `guardrail.triggered` if evidence is partial or blocked
5. `tool.started` for prediction
6. `artifact.written`
7. `prediction.locked`
8. `tool.finished`
9. `handoff.completed`
