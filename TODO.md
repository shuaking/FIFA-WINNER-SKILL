# FIFA-WINNER-SKILL TODO

This list tracks the next work needed before the project is useful as a GitHub-ready, repeatable World Cup prediction toolkit.

## P0

- [x] Parse the official FIFA schedule and update the match ledger.
  - Goal: replace 104 placeholder matches with stable real fixtures, kickoff times, venues, stages and teams.
  - Acceptance: `match-ledger.json` still has 104 unique `match_id` values; group matches have official teams and kickoff times; unknown knockout teams keep placeholders.
  - Sources: FIFA official match schedule snapshot (via ESPN).
  - Script: `worldcup_fixture_parser.py`

- [x] Parse FIFA men's ranking into structured edition data.
  - Goal: generate a ranking table that can be joined to team dossiers and prediction evidence.
  - Acceptance: `rankings/fifa-men-ranking.json` records rank, team, points if available, source URL, tier and snapshot manifest.
  - Sources: FIFA men's ranking snapshot.
  - Script: `worldcup_ranking_parser.py`

- [x] Compile squad depth and position-balance features.
  - Goal: turn the 48 official squads and 1248 players into team-level features.
  - Acceptance: every team has GK/DF/MF/FW counts, average age when DOB is available, club-country distribution, missing-field summary and source refs.
  - Sources: FIFA official squad PDF parse output.
  - Script: `worldcup_squad_depth_compiler.py`

## P1

- [x] Design the first explainable prediction scoring model.
  - Goal: combine ranking, history, squad depth, schedule/rest and evidence gaps into an interpretable score.
  - Acceptance: every prediction reports data score, divination overlay score, confidence cap, evidence gaps and no betting language.
  - Constraint: data model weight remains 85%; 周易 entertainment layer remains at most 15%.
  - Script: `prediction_scoring_model.py`

- [x] Add daily evidence input for injuries, suspensions, probable lineups and late news.
  - Goal: allow manual or sourced daily updates without pretending uncertain news is complete.
  - Acceptance: missing daily evidence is `partial` or `blocked`; reports downgrade confidence when availability is unknown.
  - Sources: national FA sites first; T3 references only for cross-checks.
  - Script: `daily_evidence_input.py`

- [x] Restore OpenFootball historical data acquisition without GitHub API rate-limit failure.
  - Goal: use a stable raw URL, mirror, cached fixture, or authenticated GitHub token path.
  - Acceptance: historical World Cup results are snapshotted as source evidence and compiled into team/history features.
  - Resolution: switched from GitHub API to `raw.githubusercontent.com` direct URLs.
  - Script: `worldcup_history_fetcher.py`

## P2

- [x] Add GitHub packaging polish.
  - Goal: make the standalone export comfortable for outside users.
  - Acceptance: `LICENSE`, example `.env`, sample prediction report, sample poster manifest, and CI workflow are present.

- [x] Add example poster generation assets.
  - Goal: make `image2` configuration easier to understand.
  - Acceptance: sample manifest, blocked backend example, and successful backend provenance example are documented.

- [x] Add richer post-match review dashboards.
  - Goal: track hit rate for win/draw/loss, exact score, total-goal bucket and confidence calibration.
  - Acceptance: evaluator writes aggregate summaries without rewriting locked pre-match reports.

- [x] Add public README showcase and user-facing image2 prompt text files.
  - Goal: make the GitHub repo easy to scan, show the first two Friday posters, and give users `.txt` prompts when they ask for poster generation.
  - Acceptance: README includes prediction schedule, poster images, contact QR and safety boundary; poster builder writes `.txt` prompt files while keeping JSON manifests for provenance.

## Done

- [x] Initialize reusable edition structure for 2026.
- [x] Snapshot and parse FIFA official squad PDF.
- [x] Generate team/player dossiers from official roster data.
- [x] Add prediction evidence plan and source readiness guardrails.
- [x] Add GitHub readiness gate.
- [x] Add `play_card` for prediction playability.
- [x] Parse official FIFA schedule and update match ledger (104 matches).
- [x] Parse FIFA men's ranking (48 qualified teams, 211 total).
- [x] Compile squad depth and position-balance features (48 teams, 1248 players).
- [x] Design explainable prediction scoring model (5 components + 周易 overlay).
- [x] Add daily evidence input tool (injuries, suspensions, lineups, news).
- [x] Restore OpenFootball historical data (19 editions fetched, 37 teams with history).
- [x] Add GitHub packaging polish (`LICENSE`, `.env.example`, examples and CI).
- [x] Add poster generation examples for `image2` blocked/generated provenance.
- [x] Add aggregate post-match review dashboard with hit-rate and confidence calibration buckets.
- [x] Add first-day poster showcase, WeChat group entry and user-facing `image2` prompt `.txt` outputs.
