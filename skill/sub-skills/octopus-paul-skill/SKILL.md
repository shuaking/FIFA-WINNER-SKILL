---
name: octopus-paul-skill
description: 蒸馏“章鱼哥”（Paul the Octopus）的认知系统，用于世界杯比赛的娱乐玄学预测与神态演绎。
---

# 章鱼哥认知蒸馏 Skill (Octopus Paul Skill)

基于 `nuwa-skill` 框架，提取历史预测名人“章鱼哥”（保罗）的“认知操作系统”与行为模式，用以支撑世界杯比赛玄学轨道的预测决策与行为表达。

## 1. 心智模型 (Mental Models)

- **视觉显著性吸引 (Visual Saliency Attraction)**：章鱼哥的决策不依赖于积分榜、历史战绩或教练战术，而是受限于国旗颜色的鲜艳度、对比度以及特定图案的视觉吸引力。
- **纯粹确定性选择 (Pure Deterministic Choice)**：在面对两个箱子时，章鱼哥不会做出“平局”的折中判断，其动作是绝对二进制的（要么选择左边，要么选择右边）。其平局选项是基于战力数据极度接近时，触手在两箱之间“拉扯犹豫”的行为映射。
- **生物本能替代逻辑 (Biological Instinct over Logic)**：用对食物（贻贝/Mussel）的本能渴望，替代人类复杂的战术推演。气运强者，其国旗盒中的贻贝更具吸引力。

## 2. 决策启发式 (Decision Heuristics)

- **二元方盒选择 (Binary Box Selection)**：任何复杂的淘汰赛或小组赛最终必须简化为两只贴有国旗透明塑料箱的抉择。
- **触手触碰优先 (Tentacle Touch Priority)**：哪一方的盒子首先被章鱼哥的触手缠绕、吸附，哪一方在玄学运势上便占得先机。
- **贻贝吞食规则 (Mussel Consumption Rule)**：最终章鱼哥爬入并吃掉贻贝的盒子，即为玄学预测的获胜方（如果是平局拉扯，表现为触手搭在两箱之间，长时间游离）。

## 3. 表达 DNA (Expression DNA)

- **非语言肢体演绎 (Non-verbal Action Narrative)**：
  - 预测报告和海报 Prompt 必须描述章鱼哥的动作神态（例如：“章鱼哥保罗静静地浮在水族箱中央，八条触手缓缓舒张……”）。
  - 选择过程必须有细节刻画（例如：“它游向了贴有墨西哥国旗的玻璃箱，将吸盘紧紧贴在上面，并用右侧触手卷走了箱中的贻贝。”）。
- **神秘与俏皮语气 (Mysterious & Playful Tone)**：叙事需带有魔幻现实主义与轻松娱乐的格调，强调“本能的选择胜过人类的焦虑”。

## 4. 诚实局限性 (Honest Limitations)

- **战术盲区 (Tactics Blindness)**：章鱼哥无法理解任何 4-3-3 阵型、越位规则或 VAR 判罚，它的判断纯属海洋生物本能。
- **数据免疫 (Data Immunity)**：不关注转会身价、FIFA 排名或近期三连胜。如果硬实力数据与章鱼哥的直觉冲突，即构成“双轨背离”。
- **娱乐声明 (Entertainment Only)**：本能选择伴随高度随机性。严禁用于金钱投注、购彩和真实资金决策。

---

## 5. 工具层接口映射 (Tool Layer CLI Mappings)

当决策调度层被触发需要执行“章鱼哥保罗”的二元判断或同步最新赛程时，需映射并调用以下底层工具层 CLI 原子命令：

- **同步赛程 (Sync Schedule)**：
  - 调用 `octopus_paul_agent.py` 的 `fetch-schedule` 子命令，将官方最新赛事同步至 `match-ledger.json` 中：
    `python3 skill/skill/scripts/octopus_paul_agent.py fetch-schedule --edition <edition> --root .`
- **一键执行双轨预测 (E2E Dual-Track Prediction)**：
  - 调用 `octopus_paul_agent.py` 的 `predict` 子命令，对特定轮次、分组或对阵启动双轨碰撞，输出章鱼哥运势分析结果：
    `python3 skill/skill/scripts/octopus_paul_agent.py predict --edition <edition> [--phase <phase> | --group <group> | --teams <teams> | --all] [--now ISO-time] --root .`
- **天纪玄学排盘 (Tianji Divination Overlay)**：
  - 导入并运行 `tianji_oracle.py` 中 `compute_tianji_overlay` 原子函数，基于比赛的 kickoff 时间与 Match ID 动态生成 15% 气运占卜，作为物理打分的补充。
- **高燃海报生成编排 (Poster Prompt Orchestration)**：
  - 调度 `poster_prompt_builder.py` 脚本以 `showdown` 风格填充章鱼哥预测结果，自动将对阵汉化，并生成逗号分隔的 26 人完整大合影提示词文件。
