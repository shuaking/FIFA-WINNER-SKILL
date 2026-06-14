# Handoff Contract

定义宿主 Agent 向本 Skill 委派任务时的交接载荷。当前为本地 CLI 模式，这些载荷是供 Codex、Claude Code、Cursor Agent、CI 或未来 A2A/MCP 包装器使用的静态契约。

## 通用信封

```json
{
  "task_id": "caller-generated-id",
  "handoff_type": "prediction_requested",
  "state": "submitted",
  "skill_id": "fifa-winner-skill",
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

## 状态

- `submitted`：调用方创建了任务
- `working`：运行时正在调用 CLI 工具
- `input_required`：缺少必要输入（edition、date、match_id、final_score 等）
- `blocked`：证据、源访问、后端或开球时间阻止任务继续
- `completed`：请求的产物已存在，调用方可以摘要
- `failed`：工具执行意外失败
- `canceled`：调用方停止了任务

## 交接类型

### `prediction_requested`

用于日期、比赛、球队、小组、阶段或全部比赛的预测请求。

必需输入：

```json
{
  "edition": "2026",
  "date": "2026-06-11",
  "match_id": "2026-GA-01",
  "teams": ["Mexico", "South Africa"],
  "scope": "date | match | teams | group | phase | all"
}
```

推荐工具：`plan_prediction_evidence` → `collect_daily_evidence` → `predict_daily` 或 `predict_scoped`

### `evidence_refresh_needed`

源就绪度或每日证据缺失或过时时使用。

推荐工具：`audit_source_readiness` → `plan_prediction_evidence` → `collect_daily_evidence`

### `poster_requested`

仅在用户要求视觉素材时使用。

推荐工具：`build_poster_prompt` → `generate_posters`（仅在后端已配置时）

### `evaluation_requested`

在 match ledger 中记录最终比分后使用。

必需输入：

```json
{
  "edition": "2026",
  "date": "2026-06-11",
  "final_scores_recorded": true
}
```

推荐工具：`evaluate_predictions` → `prediction_evaluation_dashboard.py write`

## 完成响应

宿主 Agent 应按以下格式摘要已完成任务：

```
Status: created | locked_existing_report | blocked | no_matches_found
Report: <path>
Matches: <count>
Main pick: <home/draw/away plus score>
Confidence: <low/medium/high>
Evidence gaps: <list or none>
Key layers: <2-3 analysis layer summaries>
Safety: 娱乐预测，非投注建议；不得作为投注、购彩或资金决策依据。
```
