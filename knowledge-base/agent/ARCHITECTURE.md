# AI章鱼哥 世界杯预测 Agent 架构说明书 (Architecture Specifications)

“AI章鱼哥世界杯预测 Agent” 是一个面向 2026 世界杯（及后续届次）的多源智能预测与娱乐宣发 Agent。它不仅包含传统体育数据的建模计算，还集成了天纪紫微斗数开球时排盘与博彩市场双轨碰撞机制。

## 1. 五大核心功能模块 (Five Core Modules)

Agent 的整体逻辑由以下五个独立运行的模块拼装而成：

1.  **市场监测器 (Market Monitor)**：
    *   **脚本**：[worldcup_live_fetcher.py](../../scripts/worldcup_live_fetcher.py)
    *   **职责**：实时抓取 The Odds API 的最新盘口数据，换算无抽水隐含期望概率；订阅并解析 ESPN RSS 体育新闻 feed，执行情感词典扫描（如伤停、内讧等负向词，或复出、提气等正向词），计算球队每日舆情起伏分。
2.  **天纪神算 (Tianji Oracle)**：
    *   **脚本**：[tianji_oracle.py](../../scripts/tianji_oracle.py)
    *   **职责**：将开球的太阳时转换为北京时间及农历干支，基于简易紫微斗数排盘，对比主队（命宫）与客队（迁移宫）的星曜组合。通过紫府日月加权、化忌扣减、羊陀衝突判定，产生玄学轨道修正值与黄牌警告。
3.  **核心预测器 (Core Predictor)**：
    *   **脚本**：[prediction_scoring_model.py](../../scripts/prediction_scoring_model.py)
    *   **职责**：整合 FIFA 排名换算值（30%）、大名单深度（20%）、历史世界杯底蕴（20%）、休息天数与旅途负荷（15%）以及证据链完整度（15%），计算两支球队的硬实力基本面分。
4.  **双轨碰撞分析器 (Divergence Analyzer)**：
    *   **脚本**：在 [prediction_scoring_model.py](../../scripts/prediction_scoring_model.py) 中嵌入双轨对比模块。
    *   **职责**：对比基本面轨道（基本面 + 玄学分）与市场轨道（赔率期望分）。若指向一致输出“双轨共振（aligned）”报告；若反向冲突，则以“章鱼哥保罗”拟真神态输出“双轨背离（divergent）”的防诱盘或冷门警示。
5.  **宣发海报助手 (Creative Prompter)**：
    *   **脚本**：[poster_prompt_builder.py](../../scripts/poster_prompt_builder.py) 与 [poster_generator.py](../../scripts/poster_generator.py)
    *   **职责**：从预测报告中提炼高可玩性看点、胜负摘要、风险预警，自动合成针对 DALL-E/Midjourney 等海报生成的 Prompt 及负面提示词。

---

## 2. 知识库统一目录结构 (Knowledge-base Structure)

为了便于让 Codex、Claude Code 或其他大模型 Agent 快速加载和使用本 Skill，项目结构重构为单一知识库入口 `knowledge-base/`：

```
FIFA-WINNER-SKILL/
├── README.md                 # 重生章鱼哥介绍、快速开始与每日比赛日历
├── HISTORY.md                # 历史比赛预测、赛果命中复盘归档
├── pyproject.toml
├── scripts/                  # 核心运行器脚本
├── tests/                    # 18项自动化测试
└── knowledge-base/           # 统一知识库根目录
    ├── index.md              # 知识库主索引，指引届次
    ├── agent/                # Agent 设计规范与认知技能
    │   ├── ARCHITECTURE.md   # 本说明文档
    │   ├── SKILL.md          # 蒸馏得到的章鱼哥认知特征
    │   ├── AGENT_CARD.json   # A2A 风格能力卡
    │   ├── TOOL_CATALOG.json # MCP 风格 tools/resources/prompts 目录
    │   ├── RUNBOOK.md        # Codex/Claude Code 等 runtime agent 操作手册
    │   ├── GUARDRAILS.md     # 安全、证据、锁定报告护栏
    │   ├── HANDOFFS.md       # 任务交接状态与 payload 契约
    │   └── TRACE_EVENTS.md   # runtime wrapper 可复用追踪事件名
    └── 2026/                 # 2026 届世界杯独立隔离资料库
        ├── data/             # match-ledger, profiles 球队及球员档案、daily-evidence
        ├── raw/              # 原始 PDF 数据源、fixtures/rankings 的 snapshots
        └── wiki/             # 整理后的 MOC 主图谱与分析摘要
```

---

## 3. Agent-to-Agent 静态互操作层

runtime server 暂不实现，但项目已经提供可被其他 Agent 直接读取的静态契约：

1.  **能力发现**：`AGENT_CARD.json` 描述 agent identity、skills、capabilities、storage policy、safety boundary，以及 future A2A/MCP/OpenAI Agents SDK wrapper 的对齐点。
2.  **工具发现**：`TOOL_CATALOG.json` 把 Python CLI 映射成 tools，并列出 resources、prompts、guardrails、handoffs、trace events。
3.  **调用手册**：`RUNBOOK.md` 给 Codex、Claude Code、Cursor Agent、CI agent 提供最短可运行路径。
4.  **护栏与交接**：`GUARDRAILS.md` 固化娱乐预测边界；`HANDOFFS.md` 固化任务状态；`TRACE_EVENTS.md` 固化 wrapper 日志事件。

这层设计的目标是：不强迫外部 agent import Python 内部模块，只要求它们读卡片、跑 CLI、读 JSON artifact、按安全契约总结。

---

## 4. 未来升级规划 (Hermes & OpenHuman 机制规划)

我们规划在后续迭代中引入以下两个优秀 Agent 的核心设计，让“章鱼哥”从静态脚本流真正进化为**自适应、自成长的超级 Agent**：

### 🛠️ 规划一：借鉴 Hermes 风格的“自主 ReAct 规划循环” **[待实现 / Under Development]**
*   **当前痛点**：目前拉取盘口、拉取新闻、预测、更新 README 需按照命令行步骤手动触发。
*   **升级方案**：编写 `agent_brain.py` 运行时，使其常驻。用户输入自然语言如“*章鱼哥，分析下明天的法国 vs 巴西*”，Agent 会执行 ReAct 思考循环：
    1.  `Thought`：需要查阅明天日期法国与巴西的 kickoff 历史与账本。
    2.  `Action`：调用 ledger 提取 match_id。
    3.  `Thought`：需要实时赔率和最近 24 小时的媒体伤停。
    4.  `Action`：自主调起 `fetch-odds` 与 `fetch-news`。
    5.  `Thought`：数据有部分缺失，需调起 web search 补充。
    6.  `Action`：完成碰撞，渲染海报并直接推送至用户终端。

### 🔄 规划二：借鉴 OpenHuman 风格的“反思与自我微调 (Self-Reflection)” **[待实现 / Under Development]**
*   **当前痛点**：预测模型的超参数（基本面各分值权重、天纪气运修正权重）是静态的，若赛果发生爆冷或偏差，模型无法自动适应。
*   **升级方案**：
    1.  **赛后检讨日志**：每场比赛结束并录入比分后，Agent 自主比对差异，生成《章鱼哥的赛后反思日记》，存入 `HISTORY.md`。
    2.  **损失梯度自调整**：当连续几场高置信度预测出现方向性失误，Agent 读取复盘 dashboard，自我调小导致失误的因子权重（例如，发现伤停对弱队的影响被过分放大了，则在打分模型中微调该因子敏感度），使预测精度在世界杯期间滚雪球式自我进化。
