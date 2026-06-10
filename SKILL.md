---
name: fifa-winner-skill
description: Use when the user asks to initialize a FIFA World Cup knowledge base, collect team or player profiles, record matches, generate daily pre-match entertainment predictions, evaluate prediction accuracy, or create World Cup prediction posters. Not for betting or gambling advice.
---

# FIFA-WINNER-SKILL

FIFA-WINNER-SKILL is a reusable World Cup edition workflow. It keeps raw sources, compiled wiki notes, structured data, predictions, posters and post-match evaluations tied to the same edition and match ledger.

## Agent-to-Agent Entry

Runtime agents should read `AGENT_README.md` before invoking commands. The machine-readable capability card is `knowledge-base/agent/AGENT_CARD.json`; the tool/resource/prompt catalog is `knowledge-base/agent/TOOL_CATALOG.json`; the quick operator guide is `knowledge-base/agent/RUNBOOK.md`.

Use JSON reports as canonical audit artifacts. Use SQLite only as a query/index layer. If the two disagree, prefer the locked JSON report and report the mismatch.

## Safety First

Every prediction is entertainment only.

Required disclaimer:

```text
娱乐预测，非投注建议；不得作为投注、购彩或资金决策依据。
```

Never output stake sizing, odds advice, guaranteed wins, lottery advice, 稳赢, 稳胆, or similar gambling-oriented language.

## Command Roots

If running as a standalone GitHub repository, use commands from the repo root with `--root .`.

If running inside the `dxboy` knowledge base, use the project path `_meta/projects/世界杯预测/` and keep edition data isolated under:

- `raw/体育/世界杯/<edition>/`
- `wiki/体育/世界杯/<edition>/`
- `_meta/projects/世界杯预测/data/editions/<edition>/`

## Quick Routes

- Initialize edition:
  - `python3 scripts/worldcup_edition_init.py init --edition <edition> --root .`
- Source readiness:
  - `python3 scripts/worldcup_source_readiness_auditor.py write --edition <edition> --root .`
- Prediction evidence plan:
  - `python3 scripts/worldcup_prediction_evidence_planner.py write --edition <edition> --root .`
- Snapshot source:
  - `python3 scripts/worldcup_source_snapshot_tool.py plan --edition <edition> --source-id <source-id> --root .`
  - `python3 scripts/worldcup_source_snapshot_tool.py apply --edition <edition> --source-id <source-id> --root .`
- Parse FIFA official squad PDF:
  - `python3 scripts/fifa_squad_pdf_parser.py parse --edition <edition> --pdf <snapshot.pdf> --update-edition-teams --root .`
- Initialize teams and players:
  - `python3 scripts/worldcup_profile_init.py init --edition <edition> --scope teams,players --root .`
- Parse official FIFA schedule:
  - `python3 scripts/worldcup_fixture_parser.py parse --edition <edition> --schedule-json <schedule.json> --root .`
- Parse FIFA ranking:
  - `python3 scripts/worldcup_ranking_parser.py parse --edition <edition> --ranking-json <ranking.json> --snapshot-manifest <manifest.json> --root .`
- Compile squad depth:
  - `python3 scripts/worldcup_squad_depth_compiler.py build --edition <edition> --root .`
- Add daily evidence:
  - `python3 scripts/daily_evidence_input.py init --edition <edition> --date YYYY-MM-DD --root .`
  - `python3 scripts/daily_evidence_input.py status --edition <edition> --date YYYY-MM-DD --root .`
- Daily prediction:
  - `python3 scripts/prediction_scoring_model.py predict --edition <edition> --date YYYY-MM-DD --root .`
  - By teams: `python3 scripts/prediction_scoring_model.py predict --edition <edition> --teams "Team A,Team B" --root .`
  - By match id: `python3 scripts/prediction_scoring_model.py predict --edition <edition> --match-id <match_id> --root .`
- Report prompt:
  - `python3 scripts/prediction_report_prompt_builder.py build --edition <edition> --date YYYY-MM-DD --report-path <prediction-report.json> --match-id <match_id> --root .`
- Poster manifest and image generation:
  - Only when the user explicitly asks for a poster prompt: `python3 scripts/poster_prompt_builder.py build --edition <edition> --date YYYY-MM-DD --report-path <prediction-report.json> --match-id <match_id> --root .`
  - Give users the generated `.txt` prompt file for `image2`; keep JSON manifests for provenance only.
  - `python3 scripts/poster_generator.py generate --manifest <manifest.json> --backend image2 --root .`
- Post-match evaluation:
  - `python3 scripts/prediction_evaluator.py write --edition <edition> --date YYYY-MM-DD --root .`
  - `python3 scripts/prediction_evaluation_dashboard.py write --edition <edition> --root .`
- GitHub readiness:
  - `python3 scripts/worldcup_github_readiness_auditor.py write --edition <edition> --root .`

## Workflow

1. Initialize the edition if directories or match ledger are missing.
2. Run source readiness before claiming sources are usable.
3. Snapshot T0/T1 sources before parsing them; every snapshot needs URL, tier, hash and allowed-use metadata.
4. Parse official fixtures, rosters and rankings before stronger prediction claims.
5. Run prediction evidence planning before daily predictions.
6. Mark missing evidence as `partial` or `blocked`; never pretend it is complete.
7. Only predict matches that have not kicked off. Prefer `prediction_scoring_model.py` for official reports.
8. Lock pre-match reports. Do not overwrite them after kickoff.
9. Build report prompts from structured prediction reports, not memory. Build poster prompts only when requested by the user.
10. After matches, append evaluation and update the aggregate dashboard.

## Source Tiers

- T0: FIFA official schedule, FIFA official squad PDF, FIFA rankings, national FA official sites.
- T1: Wikidata, Wikipedia, OpenFootball and similar structured open sources.
- T2: football-data.org, API-Football, TheSportsDB; only after key, rate limit and license boundaries are recorded.
- T3: FBref, StatBunker, Transfermarkt, ESPN and similar references; cross-check only, no unauthorized bulk scraping.

## Prediction Evidence

Check these before daily predictions: official fixtures, official rosters, FIFA rankings, historical World Cup results, recent form, squad depth, injury availability, venue/rest/travel, head-to-head and player identity enrichment.

Statuses must be `complete`, `partial` or `blocked`.

## 玩法卡片

Every daily prediction should include `play_card` with share title, match hook, watch points, risk flags, poster angle, confidence meter and gameplay tags. Keep it fun and shareable, but never gambling-oriented.

## Prediction Rules

- Data model weight: 85%.
- Zhouyi entertainment overlay weight: max 15%.
- Missing roster, injury, lineup or recent-form evidence must downgrade confidence.
- Reports must keep the entertainment disclaimer.

## Poster Rules

- `image2` is a configurable backend alias.
- User-facing `image2` prompts must be plain `.txt`, not JSON.
- Do not build poster prompts unless the user explicitly asks for poster material.
- Missing backend must return `blocked_missing_backend`.
- Poster manifests must keep prompt, source report, backend, output path and provenance.
