# AI Octopus Paul Agent Guardrails

This document is for runtime agents that call this repository. It defines the non-negotiable safety and integrity boundaries.

## Required Framing

Every prediction-like answer must include:

```text
娱乐预测，非投注建议；不得作为投注、购彩或资金决策依据。
```

Allowed framing:

- Entertainment prediction.
- Evidence-based uncertainty.
- Scenario analysis.
- Watch points and risk flags.
- Post-match evaluation.

Forbidden framing:

- Betting advice.
- Stake sizing or bankroll management.
- Lottery or gambling calls.
- Guaranteed win language.
- "稳赢", "稳胆", "必赚", "梭哈", "lock bet", or similar terms.

## Evidence Guardrails

Before making a prediction summary, the caller should check:

1. `knowledge-base/<edition>/data/match-ledger.json` exists.
2. `knowledge-base/<edition>/data/prediction-evidence-plan.json` exists or can be generated.
3. `knowledge-base/<edition>/data/daily-evidence/<date>.json` exists when the task is date-specific.
4. The target match has not started.

If evidence is `partial` or `blocked`, keep that visible in the final answer. Do not upgrade confidence because a narrative sounds convincing.

## Storage Guardrails

JSON and Markdown artifacts under `knowledge-base/<edition>/` are canonical. SQLite is a query/index layer derived from those artifacts.

If JSON and SQLite disagree:

1. Prefer the locked JSON report.
2. Mention the mismatch.
3. Rebuild or refresh the SQLite index rather than editing locked predictions by hand.

## Locked Report Guardrails

Pre-match prediction reports are locked once written for a match/date. After kickoff:

- Do not regenerate a prediction to fit the match.
- Do not silently edit the pick, score, confidence, or analysis layers.
- Use post-match evaluation tools instead.

## Source And Copyright Guardrails

- Prefer T0 official sources for fixtures, squads, rankings, and match facts.
- Store URLs, metadata, structured values, and short summaries.
- Do not store large copyrighted article text.
- Respect source terms, rate limits, and API key boundaries.

## Poster Guardrails

Only build poster prompts or images when the user explicitly asks for poster, image, share card, or visual material.

If the image backend is missing, return the blocked result honestly. Do not claim an image was generated.
