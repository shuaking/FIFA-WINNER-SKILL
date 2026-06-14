---
type: report
edition: 2026
date: 2026-06-12
status: active
---

# 2026 World Cup Opening Predictions: Post-Match Model Review

## Conclusion

This round should not be counted as fully correct. Both reviewed matches hit the result direction, but both missed the exact score and the total-goals layer.

中文结论：这轮不能算预测完全正确。两场胜负方向都中了，但两场比分和总进球都没中。问题不在于方向判断完全失效，而在于比分层、总进球层和比赛状态树太薄。

| Match | Pre-match prediction | Actual result | Result | Score | Total goals |
|---|---:|---:|---|---|---|
| Mexico vs South Africa | 2-1 | 2-0 | hit | miss | miss |
| South Korea vs Czechia | 1-0 | 2-1 | hit | miss | miss |

The model was good enough to identify the stronger side, but too thin at explaining how the match could unfold. The score layer, total-goals layer, and match-state layer need to be thicker.

## Why It Missed

### Mexico 2-0 South Africa

The direction was right: Mexico were the better pre-match side and won. The miss was giving South Africa a default consolation goal. The model did not explicitly calculate `clean_sheet_probability`, so the 2-0 branch lost to a simpler 2-1 point estimate.

中文复盘：墨西哥胜出的方向判断对了，但模型没有显式计算零封概率，默认给南非一个安慰球，导致 2-0 分支输给了更粗糙的 2-1 点估计。

Referee and card volatility also stayed as narrative text. It should have moved the away-goal distribution once the match script pointed toward Mexico control and South Africa's attacking continuity dropping.

### South Korea 2-1 Czechia

The direction was also right: South Korea won. The miss was compressing the match into a low-event 1-0. The model underweighted Czechia's set-piece path to a goal and South Korea's second-half tempo/substitution response.

中文复盘：韩国胜出的方向判断对了，但模型把比赛压成低事件 1-0，低估了捷克定位球得分路径，也低估了韩国下半场提速和换人带来的二次进球。

The missing layer is `second_half_state_layer`: leading, level, and trailing states after halftime should change team-goal probabilities. A team chasing the match can raise both its own scoring chance and the opponent's transition chance.

## Root Causes

- `prediction.score` is too single-point. The model needs `scoreline_distribution` with at least three candidate scores and probabilities.
- Clean-sheet probability is missing. Strong-side control, weak-side attack limits, red cards, and pressure should feed `clean_sheet_probability`.
- Event risk is text-only. Cards, penalties, set pieces, and substitutions need to affect team goals and total goals.
- Match-state tree is too shallow. Current scenarios are base/upset/draw, but halftime leading/level/trailing branches are absent.
- Confidence is bundled. `medium confidence` currently reads like a single label, but result confidence, score confidence, and total-goals confidence should be separate.
- Evidence quality gates are not strict enough. Mock odds or weak evidence must not upgrade dual-track alignment or confidence.
- Prediction artifacts can drift. Evaluation must use the locked `daily-predictions` snapshot as the canonical accountable prediction; older parallel reports must be marked non-canonical or superseded.
- Public copy can overstate the round if it says "hit" without separating result direction, exact score, and total-goals performance.

## Corrective Actions

1. Add `scoreline_distribution`: output candidate scores such as 2-0, 2-1, 1-0 with probabilities and reasons.
2. Add `clean_sheet_probability`: explicitly raise clean-sheet branches when the stronger team controls the match and the weaker attack is limited.
3. Add `event_volatility_score`: connect referee strictness, red cards, penalties, set pieces, and substitutions to goal distributions.
4. Add `second_half_state_layer`: model leading, level, and trailing branches after halftime.
5. Split confidence fields: emit `result_confidence`, `score_confidence`, and `total_goals_confidence`.
6. Add a source-quality gate: mock odds and low-quality sources can appear as evidence but cannot upgrade confidence.
7. Add a prediction artifact registry: each match should point to one locked accountable report, while old parallel reports are labeled non-canonical.
8. Separate public hit labels: report `partial hit` and `full hit` separately so a direction hit is not presented as exact-score success.

## Stored Evidence

- Result evidence snapshot: `knowledge-base/2026/data/daily-evidence/2026-06-12-results.json`
- Daily evaluation: `knowledge-base/2026/data/reports/evaluations/2026-06-11.json`
- Daily evaluation: `knowledge-base/2026/data/reports/evaluations/2026-06-12.json`
- Machine-readable model review: `knowledge-base/2026/data/reports/evaluations/2026-06-12-model-review.json`

Safety note: this is entertainment prediction calibration only, not betting or financial advice.
