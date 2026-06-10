# AI Octopus Paul Runtime Agent Runbook

Use this runbook when you are Codex, Claude Code, Cursor Agent, CI, or another runtime agent operating the repository.

## First Read Order

1. `AGENT_README.md`
2. `knowledge-base/agent/AGENT_CARD.json`
3. `knowledge-base/agent/TOOL_CATALOG.json`
4. `knowledge-base/agent/GUARDRAILS.md`
5. `schema/daily-prediction-report.schema.json`

## Preflight

```bash
python -m pytest -q
python scripts/worldcup_github_readiness_auditor.py write --edition 2026 --root .
```

If tests fail, report the failure before making prediction claims.

## Prediction Flow

```bash
python scripts/worldcup_edition_init.py init --edition 2026 --root .
python scripts/worldcup_prediction_evidence_planner.py write --edition 2026 --root .
python scripts/daily_evidence_input.py init --edition 2026 --date 2026-06-11 --root .
python scripts/daily_prediction_runner.py run --edition 2026 --date 2026-06-11 --root .
```

Use `prediction_scoring_model.py predict` or `octopus_paul_agent.py predict` for match/team/group/phase/all scoped work.

## Summary Flow

Read the generated prediction report JSON and summarize:

- status
- report path
- match count
- main pick and score
- confidence
- evidence gaps
- top analysis layers
- safety disclaimer

Do not paste the full report unless the user asks for raw JSON.

## Poster Flow

Only run this when the user asks for visual material:

```bash
python scripts/poster_prompt_builder.py build --edition 2026 --date 2026-06-11 --style showdown --match-id 2026-GA-01 --root .
python scripts/poster_generator.py generate --manifest <poster-manifest.json> --backend image2 --root .
```

If the backend is missing, the blocked result is correct.

## Evaluation Flow

After final scores are recorded:

```bash
python scripts/prediction_evaluator.py write --edition 2026 --date 2026-06-11 --root .
python scripts/prediction_evaluation_dashboard.py write --edition 2026 --root .
```

Use evaluation output for calibration and reflection. Never rewrite pre-match picks after kickoff.
