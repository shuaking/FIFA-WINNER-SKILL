# 架构说明书

FIFA-WINNER-SKILL 是一个面向世界杯娱乐预测的垂直领域 Skill，不是 Agent。

## 核心定位

```
宿主 Agent（Codex / Claude Code / 等）
  │
  ├─ 读 skill/SKILL.md          → "这个 Skill 是什么"
  ├─ 读 skill/TOOL_CATALOG.json → "有哪些工具可用"
  ├─ 读 skill/GUARDRAILS.md     → "安全边界是什么"
  ├─ 读 skill/ORCHESTRATION.md  → "最佳工作流是什么"
  │
  └─ 自主决定调用哪个工具、什么顺序
```

**Skill = 工具 + 契约 + 领域知识。** 推理、编排、决策由宿主 Agent 负责。

## 五大核心模块

1. **市场监测器 (Market Monitor)** — `worldcup_live_fetcher.py`
   实时抓取赔率数据，换算隐含期望概率；解析 ESPN RSS 新闻，计算舆情起伏分。

2. **天纪神算 (Tianji Oracle)** — `tianji_oracle.py`
   开球时辰 → 干支 → 紫微命盘 → 星曜组合 → 玄学轨道修正值。

3. **核心预测器 (Core Predictor)** — `prediction_scoring_model.py`
   整合 FIFA 排名(30%)、大名单深度(20%)、历史底蕴(20%)、休息/旅途(15%)、证据完整度(15%)。

4. **三轨碰撞分析器 (Tri-Track Analyzer)** — 嵌入核心预测器
   基本面轨道 vs 市场轨道 → 共振/背离判定 → 玄学修正叠加。

5. **宣发海报助手 (Creative Prompter)** — `poster_prompt_builder.py` + `poster_generator.py`
   从预测报告提炼看点，自动合成 DALL-E/Midjourney 海报 Prompt。

## 目录结构

```
FIFA-WINNER-SKILL/
├── skill/                    ← Skill 声明层（轻量，安装时复制）
│   ├── SKILL.md              ← 入口声明
│   ├── AGENT_CARD.json       ← 能力卡
│   ├── TOOL_CATALOG.json     ← 工具目录
│   ├── ORCHESTRATION.md      ← 编排建议
│   ├── GUARDRAILS.md          ← 护栏
│   ├── HANDOFFS.md            ← 交接契约
│   ├── TRACE_EVENTS.md        ← 追踪事件
│   ├── RUNBOOK.md             ← 操作手册
│   ├── ARCHITECTURE.md        ← 本文件
│   ├── scripts/               ← 工具实现（34个 CLI 脚本）
│   ├── schema/                ← 输入输出契约
│   └── tests/                 ← 测试套件
├── wiki/                     ← 知识库（公共知识，可独立增长）
│   ├── 2026/                 ← 2026 届数据
│   └── public/               ← 公共默认预测
├── docs/                     ← 文档
├── AGENT_README.md           ← 宿主 Agent 入口指南
└── README.md                 ← 项目介绍
```

## 为什么是 Skill 而不是 Agent

- 世界杯预测是**确定性流水线**：采集 → 预测 → 报告 → 看板 → 复盘
- 每一步都是确定的，不需要"自主决定下一步做什么"
- 没有 runtime、没有自主循环、没有持续运行实例
- **宿主 Agent 负责编排和推理，Skill 负责领域封装和工具执行**

## 数据分层

| 数据 | 性质 | 位置 |
|------|------|------|
| 赛程/排名/阵容/历史 | 公共事实 | `wiki/2026/` |
| AI 章鱼哥默认预测 | 公共基线 | `wiki/public/` |
| 用户预测/证据/覆盖 | 私有数据 | `wiki/public/2026/` |
| SQLite 缓存 | 派生索引 | `wiki/public/2026/` |
