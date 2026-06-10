# FIFA-WINNER-SKILL

FIFA-WINNER-SKILL 是一个可复用的世界杯娱乐预测 Skill。它按届次独立保存赛程、球队、球员、来源证据、预测报告、海报 prompt 和赛后复盘。第一版先落地 2026 FIFA World Cup。

> 娱乐预测，非投注建议；不得作为投注、购彩或资金决策依据。

## Safety / 安全声明

这个项目只用于娱乐参考、AI Skill 设计学习和技术交流。禁止用于下注、跟单、购彩、赔率交易、资金决策或任何赌博相关场景。

项目输出不得包含投注金额、赔率建议、稳赚/稳赢/稳胆/必中/保证命中等表达。周易部分只是娱乐叙事，最多影响 15%，不能覆盖数据证据。

## 首日海报展示

北京时间 2026-06-12 周五前两场已经生成宣传海报：

海报玩法代号暂定：章鱼哥。

![Mexico vs South Africa](assets/posters/2026-06-12-mexico-vs-south-africa.png)

![South Korea vs Czechia](assets/posters/2026-06-12-south-korea-vs-czechia.png)

## Prediction Schedule / 预测日历

比赛日按北京时间展示；命令里的 `--date` 默认跟随 FIFA/UTC 赛程日期，不确定时优先用 `--match-id`。

| 节奏 | 比赛 | 预测摘要 | 状态 |
|---|---|---|---|
| 周四预测周五 | `2026-GA-01` Mexico vs South Africa | Mexico 2-1 South Africa，总进球 3，信心低 | 已生成报告与海报 |
| 周四预测周五 | `2026-GA-02` South Korea vs Czechia | South Korea 1-1 Czechia，总进球 2，信心低 | 已生成报告与海报 |
| 周五预测周六 | 后续赛程 | 比赛日前刷新资料后生成 | 待追加 |
| 每个比赛日 | 当天未开球比赛 | 预测锁定后只追加复盘 | 持续更新 |

## Quick Start / 快速开始

```bash
python3 scripts/worldcup_edition_init.py init --edition 2026 --root .
python3 scripts/worldcup_prediction_evidence_planner.py write --edition 2026 --root .
python3 scripts/prediction_scoring_model.py predict --edition 2026 --match-id 2026-GA-01 --root .
```

安装成 Codex Skill：

```bash
bash install_as_skill.sh
```

## Daily Prediction / 每日预测

按日期预测：

```bash
python3 scripts/prediction_scoring_model.py predict --edition 2026 --date YYYY-MM-DD --root .
```

按单场预测：

```bash
python3 scripts/prediction_scoring_model.py predict --edition 2026 --match-id 2026-GA-01 --root .
python3 scripts/prediction_scoring_model.py predict --edition 2026 --teams "Mexico,South Africa" --root .
```

输出包含胜平负、比分、总进球数、大小球倾向、信心等级、关键证据、证据缺口和周易娱乐解读。比赛开球后不覆盖赛前预测，只追加赛后复盘。

## Poster Prompt / 海报 Prompt

只有用户明确要做宣传海报时，才生成 `image2` prompt：

```bash
python3 scripts/poster_prompt_builder.py build \
  --edition 2026 \
  --date 2026-06-11 \
  --report-path data/editions/2026/reports/2026-06-11-prediction-report.json \
  --match-id 2026-GA-01 \
  --style showdown \
  --root .
```

给人复制到 `image2` 的文件是 `.txt`，不是 JSON。JSON manifest 只用于 provenance 和自动化追踪。

## Prediction Evidence / 预测证据

预测前优先看这些资料：FIFA 官方赛程、官方阵容 PDF、FIFA 排名、历史世界杯战绩、近期状态、阵容深度、伤停停赛、预计首发、场馆、休息间隔和旅行因素。

每条关键资料都要有 source URL、source tier、更新时间和状态。缺资料就标 `partial` 或 `blocked`，不能假装完整。

## Playability / 可玩性

每场预测会生成适合分享的玩法卡片：一句话标题、比赛钩子、观赛看点、风险提示、海报角度、信心说明和赛后复盘入口。可玩性只服务娱乐表达，不服务下注决策。

## Examples / 示例

- 首场海报 prompt：`data/editions/2026/reports/posters/2026-06-11-2026-GA-01-poster-prompt.txt`
- 第二场海报 prompt：`data/editions/2026/reports/posters/2026-06-12-2026-GA-02-poster-prompt.txt`
- 样例报告和生成结果：`examples/`

当前 2026 数据状态：104 场比赛账本、48 支球队、1248 名官方阵容球员、FIFA 排名、OpenFootball 历史数据已接入。临场伤停、预计首发和最新新闻需要比赛日前继续刷新。

## GitHub Readiness / 发布检查

```bash
python3 scripts/worldcup_github_readiness_auditor.py write --edition 2026 --root .
python3 -m unittest tests/test_worldcup_predictor_system.py
```

`ready_with_known_data_gaps` 表示仓库格式、来源边界和玩法链路可以发布，但仍有明确数据缺口。

## Roadmap / 路线

- 每个比赛日前刷新伤停、预计首发和临场新闻。
- 持续追加每日预测、海报、赛果和复盘。
- 累积命中率、比分偏差和信心校准。
- 适配更多图片生成后端，但 `image2` 仍作为默认别名。
- 2030、2034 等后续届次沿用独立资料库结构。

## 加群交流

想一起讨论世界杯娱乐预测、AI Skill、数据源和海报玩法，可以扫码加我微信，我建群同步每日预测和共建进度。

![WeChat](assets/contact/wechat-qr.jpg)

## Credits / 致谢

感谢 [Nuwa skill](https://github.com/alchaincyf/nuwa-skill) 的设计思路、[open-source football data](https://github.com/openfootball) 生态，以及 [LINUX DO / L站](https://linux.do/) 社区对 AI Skill 可玩性的启发。
