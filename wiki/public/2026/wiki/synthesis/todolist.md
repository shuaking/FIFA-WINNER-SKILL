---
type: synthesis
topic: 世界杯2026
status: active
created: 2026-06-10
updated: 2026-06-10
---

# 世界杯 2026 Todolist

这份清单记录 2026 世界杯预测工具接下来的路线。目标是让项目可以放到 GitHub，同时保持资料准确、来源可追溯、预测有可玩性。

## P0（已完成）

- [x] 解析 FIFA 官方赛程并回填比赛账本
  - 验收：104 场比赛保持唯一 `match_id`；小组赛有官方对阵和开球时间；淘汰赛未知对阵继续使用占位符。
  - 来源：FIFA 官方赛程快照（via ESPN）。
  - 脚本：`worldcup_fixture_parser.py`

- [x] 解析 FIFA 男足排名
  - 验收：生成结构化排名数据；每行保留来源 URL、tier 和 snapshot manifest。
  - 来源：FIFA 男足排名快照。
  - 脚本：`worldcup_ranking_parser.py`

- [x] 编译阵容深度和位置平衡特征
  - 验收：每队有 GK/DF/MF/FW 数量、平均年龄可用性、俱乐部分布、缺失字段摘要和 source refs。
  - 来源：FIFA 官方阵容 PDF 解析结果。
  - 脚本：`worldcup_squad_depth_compiler.py`

## P1（已完成）

- [x] 设计第一版可解释预测评分模型
  - 验收：每场预测输出 data score、divination overlay score、confidence cap 和 evidence gaps。
  - 约束：数据模型 85%，周易娱乐层最多 15%。
  - 脚本：`prediction_scoring_model.py`

- [x] 增加每日伤停、停赛、预计首发和临场新闻输入
  - 验收：缺资料时标记 `partial/blocked`；未知伤停会下调信心。
  - 来源：国家足协官网优先，T3 参考源只做交叉验证。
  - 脚本：`daily_evidence_input.py`

- [x] 恢复 OpenFootball 历史数据获取
  - 验收：历史世界杯结果能完成 raw 快照并编译为历史特征。
  - 解决方案：从 GitHub API 切换到 `raw.githubusercontent.com` 直链。
  - 脚本：`worldcup_history_fetcher.py`

## P2（已完成）

- [x] 补 GitHub 包装细节
  - 验收：LICENSE、示例 env、示例预测报告、示例 poster manifest 和 CI workflow 齐备。

- [x] 补海报生成示例
  - 验收：有 sample manifest、缺 backend 的 blocked 示例、成功生成时的 provenance 示例。

- [x] 增强赛后复盘 dashboard
  - 验收：统计胜平负、比分、总进球区间、信心校准命中情况；不改写赛前预测。

## 已完成

- [x] 初始化 2026 独立届次结构。
- [x] 快照并解析 FIFA 官方阵容 PDF。
- [x] 基于官方大名单生成球队和球员资料。
- [x] 增加预测证据计划和来源 readiness guardrails。
- [x] 增加 GitHub readiness gate。
- [x] 增加预测 `play_card`，提高报告可玩性。
- [x] 解析官方赛程（72场小组赛 + 32场淘汰赛占位）。
- [x] 解析 FIFA 排名（48队全部有排名和积分）。
- [x] 编译阵容深度特征（48队 1248人，位置/年龄/身高/俱乐部分布）。
- [x] 设计可解释预测模型（5个加权组件 + 周易六十四卦娱乐层）。
- [x] 每日证据输入工具（伤停/停赛/首发/新闻）。
- [x] 恢复 OpenFootball 历史数据（19届世界杯，37队有历史特征）。
- [x] GitHub 包装细节（LICENSE、示例、CI、README Examples）。
- [x] 海报生成示例（manifest、缺 backend blocked、成功 provenance）。
- [x] 赛后复盘聚合 dashboard（胜平负/比分/总进球命中率、信心校准分桶）。
