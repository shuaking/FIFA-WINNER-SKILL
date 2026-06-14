---
type: summary
topic: 世界杯2026
source_integrity: partial
raw_ref: raw/体育/世界杯/2026/evidence-packets/fifa-match-schedule-2026-06-09-snapshot-manifest.json
created: 2026-06-09
updated: 2026-06-09
---

# 2026-06-09 预测证据快照

## 来源边界

- FIFA 官方赛程页：T0，source_url: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums
- FIFA 男足排名页：T0，source_url: https://inside.fifa.com/fifa-world-ranking/men
- FIFA 官方阵容 PDF：T0，source_url: https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf
- OpenFootball World Cup JSON：T1，source_url: https://api.github.com/repos/openfootball/worldcup.json/contents

## Raw refs

- `raw/体育/世界杯/2026/evidence-packets/fifa-match-schedule-2026-06-09-snapshot-manifest.json`
- `raw/体育/世界杯/2026/evidence-packets/fifa-men-ranking-2026-06-09-snapshot-manifest.json`
- `raw/体育/世界杯/2026/evidence-packets/fifa-squad-lists-pdf-2026-06-09-snapshot-manifest.json`
- `raw/体育/世界杯/2026/evidence-packets/openfootball-worldcup-json-2026-06-09-snapshot-manifest.json`

## 核心事实

1. 官方阵容 PDF 已解析为 48 队、1248 名球员、48 名教练；1248 的原因是 FIFA 官方大名单按每队 26 人计算，即 48 * 26。
2. FIFA 赛程页已完成 raw 快照，但当前 match ledger 仍是 104 场占位账本，尚未导入真实开球时间、场馆和对阵。
3. FIFA 男足排名页已完成 raw 快照，但排名表尚未结构化解析，因此只能作为 partial evidence。
4. OpenFootball JSON 入口本次通过 GitHub API 抓取时遇到 403 rate limit，已写入 blocked manifest，不能算作可用历史数据。
5. 当前预测证据计划显示：阵容 complete；赛程、排名、阵容深度 partial；历史数据、近期状态、伤停、休息旅行等仍 blocked。

## 我的判断

现在可以确认“参赛名单资料库”已经有官方基础，但还不能做高置信赛前预测。下一步优先级应该是：先解析 FIFA 赛程并回填 `match-ledger.json`，再解析 FIFA 排名；历史战绩和近期状态可以稍后补，但伤停/首发必须每天赛前重新检查。

## 后续任务

- 写 FIFA 赛程 parser，将 104 场真实比赛回填到同一批永久 `match_id`。
- 写 FIFA ranking parser，生成 `data/editions/2026/rankings/fifa-men-ranking.json`。
- 增加 squad depth compiler，从 1248 人大名单生成各队位置结构。
- 为 OpenFootball JSON 配置 GitHub token、镜像或 raw 文件入口后重试。
- 建每日伤停/可用性人工或 API 输入格式，避免预测时假装知道伤停。
