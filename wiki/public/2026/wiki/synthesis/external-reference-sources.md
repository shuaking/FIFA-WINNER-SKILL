---
type: synthesis
edition: 2026
status: active
---

# External Reference Source Alignment 2026

This report records which external agent projects were checked and which source leads were adopted.
The reference projects are not official data authorities.

## Projects

### zhangcraigxg-work-cup-2026

- Repo: https://github.com/ZhangCraigXG/work-cup-2026
- Status: checked
- HEAD: 3560ef2c64055a15554c7a1bee66344242359c31
- Kind: reference_skill
- Usable for: coach-view analysis workflow, Chinese source lead for worldcup2026cn schedule, groups, team pages and player status checks, A2A skill file layout inspiration
- Not usable for: T0 match facts, direct structured prediction features without separate source verification, bulk scraping instructions

### crain99-worldcut-2026

- Repo: https://github.com/Crain99/worldcut-2026
- Status: checked
- HEAD: d7e05173cf9bf7413cf2f121f30285b0dc58a0f7
- Kind: reference_app
- Usable for: Sporttery fixed-bonus source lead, SQLite cache pattern for prediction history, odds snapshots and simulated account state, match intelligence tool-chain pattern combining official schedule, rankings, openfootball, APIs and search, static prediction snapshot fields for cross-checking score/probability presentation
- Not usable for: betting advice, unverified final match facts, copying UI or server code into this agent

## Adopted Source Leads

- worldcup2026cn from zhangcraigxg-work-cup-2026: https://worldcup2026cn.com/
- sporttery-cn-fixed-bonus from crain99-worldcut-2026: https://webapi.sporttery.cn/gateway/uniform/football/getMatchListV1.qry?clientCode=3001
- worldcup26-api from crain99-worldcut-2026: https://worldcup26.ir/
- international-results-csv from crain99-worldcut-2026: https://github.com/martj42/international_results

## Decisions

- keep_json_markdown_canonical: Reference SQLite patterns are useful for query/cache layers, but audit artifacts stay portable JSON/Markdown.
- register_reference_projects_as_t3: They are design and source-lead references, not official match-fact authorities.
- add_market_signal_as_optional_evidence: Market snapshots can explain divergence but must not become betting advice or override verified football evidence.
