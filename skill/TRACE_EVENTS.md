# Trace Events

为未来运行时包装器和当前 CLI 编排器定义轻量追踪词汇。

## 事件形状

```json
{
  "trace_id": "task-or-run-id",
  "event_id": "uuid-or-stable-counter",
  "event": "tool.started",
  "skill_id": "fifa-winner-skill",
  "edition": "2026",
  "match_id": "2026-GA-01",
  "timestamp": "2026-06-10T12:00:00+08:00",
  "status": "working",
  "message": "Running daily prediction",
  "data": {}
}
```

## 核心事件

- `task.accepted`：调用方向本 Skill 委派了任务
- `task.blocked`：任务因证据、源访问、后端或用户输入缺失而无法继续
- `tool.started`：CLI 工具以清理后的参数启动
- `tool.finished`：CLI 工具以退出码、状态和产物路径完成
- `artifact.written`：写入了 JSON、Markdown、SQLite 或媒体产物
- `guardrail.triggered`：安全、来源、版权或锁定报告护栏改变了响应或阻止了操作
- `prediction.locked`：赛前预测报告成为规范产物
- `handoff.created`：创建了下游或上游交接载荷
- `handoff.completed`：交接产生了产物或终态

## 追踪数据规则

- 不记录 API key、cookie、token 或私有用户数据
- 记录产物路径，不记录整个大型 JSON 报告
- 记录证据缺口和阻塞器 ID
- 记录预测类输出的安全声明状态
