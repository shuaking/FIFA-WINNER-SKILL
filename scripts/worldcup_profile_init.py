#!/usr/bin/env python3
"""Initialize team dossiers and player deep-profile tasks for an edition."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import (  # noqa: E402
    edition_data_root,
    iso_now,
    load_json,
    scope_list,
    slugify,
    wiki_edition_root,
    write_json,
    write_text,
)


def team_dossier_markdown(edition: str, team: dict, generated_at: str) -> str:
    return f"""---
type: entity
entity_type: national_team
edition: {edition}
status: {team.get('source_integrity', 'partial')}
updated: {generated_at[:10]}
---

# {team['name']}

## 档案状态

- Team ID：`{team['team_id']}`
- 小组：{team.get('group', '')}
- 来源完整性：{team.get('source_integrity', 'partial')}
- 当前状态：{team.get('status', 'partial')}

## 待补资料

- 官方阵容确认
- FIFA 排名
- 历史世界杯记录
- 近期状态和伤停
- 关键球员关系
"""


def player_dossier_markdown(edition: str, player: dict, team: dict, generated_at: str) -> str:
    return f"""---
type: entity
entity_type: player
edition: {edition}
status: partial
updated: {generated_at[:10]}
---

# {player.get('name', 'Unknown Player')}

## 基础信息

- Player ID：`{player.get('player_id', '')}`
- 国家队：{team.get('name', '')}
- 位置：{player.get('position', '')}
- 俱乐部：{player.get('club', '')}
- 来源完整性：partial

## 待补深档

- 国家队出场和进球
- 世界杯/洲际赛经历
- 近期状态、伤停和出场时间
- 预测相关标签
"""


def normalize_roster(path: Path | None) -> dict:
    if not path:
        return {"teams": []}
    payload = load_json(path, {"teams": []})
    return payload if isinstance(payload, dict) else {"teams": []}


def roster_players_for_team(roster: dict, team_id: str, team_name: str) -> list[dict]:
    for team in roster.get("teams", []):
        if not isinstance(team, dict):
            continue
        if team.get("team_id") == team_id or team.get("name") == team_name:
            return [player for player in team.get("players", []) if isinstance(player, dict)]
    return []


def initialize_profiles(
    *,
    root: Path,
    edition: str,
    scope: list[str] | str,
    roster_json: Path | None = None,
    now: str | None = None,
) -> dict:
    generated_at = iso_now(now)
    scopes = set(scope_list(scope))
    data_root = edition_data_root(root, edition)
    wiki_root = wiki_edition_root(root, edition)
    teams_payload = load_json(data_root / "teams.json", {"teams": []})
    teams = [team for team in teams_payload.get("teams", []) if isinstance(team, dict)]
    roster = normalize_roster(roster_json)
    tasks: list[dict] = []
    blockers: list[str] = []
    team_dossiers = 0
    player_dossiers = 0
    blocked_player_tasks = 0

    if "teams" in scopes:
        for team in teams:
            write_text(
                wiki_root / "entities" / "teams" / f"{slugify(team['team_id'])}.md",
                team_dossier_markdown(edition, team, generated_at),
            )
            tasks.append(
                {
                    "task_id": f"team-profile:{team['team_id']}",
                    "task_type": "team_profile",
                    "team_id": team["team_id"],
                    "status": "partial",
                    "required_sources": ["fifa-match-schedule", "fifa-squad-lists-pdf", "fifa-men-ranking", "wikidata-sparql"],
                }
            )
            team_dossiers += 1

    if "players" in scopes:
        roster_has_players = False
        for team in teams:
            players = roster_players_for_team(roster, team["team_id"], team["name"])
            if players:
                roster_has_players = True
            if not players:
                tasks.append(
                    {
                        "task_id": f"player-deep-profile:{team['team_id']}:roster-missing",
                        "task_type": "player_deep_profile_batch",
                        "team_id": team["team_id"],
                        "team_name": team["name"],
                        "status": "blocked",
                        "blockers": ["player_roster_source_missing"],
                        "required_sources": ["fifa-squad-lists-pdf", "wikidata-sparql", "national-fa-official-sites"],
                    }
                )
                blocked_player_tasks += 1
                continue
            for player in players:
                player_id = player.get("player_id") or f"{team['team_id']}:{slugify(str(player.get('name', 'unknown')))}"
                player = {**player, "player_id": player_id}
                write_text(
                    wiki_root / "entities" / "players" / f"{slugify(player_id)}.md",
                    player_dossier_markdown(edition, player, team, generated_at),
                )
                tasks.append(
                    {
                        "task_id": f"player-deep-profile:{player_id}",
                        "task_type": "player_deep_profile",
                        "player_id": player_id,
                        "team_id": team["team_id"],
                        "status": "partial",
                        "required_sources": ["fifa-squad-lists-pdf", "wikidata-sparql", "national-fa-official-sites"],
                    }
                )
                player_dossiers += 1
        if not roster_has_players:
            blockers.append("player_roster_source_missing")

    source_integrity = "partial" if blockers or blocked_player_tasks else "complete"
    result = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-profile-initialization",
        "scope": sorted(scopes),
        "summary": {
            "team_dossiers": team_dossiers,
            "player_dossiers": player_dossiers,
            "profile_tasks": len(tasks),
            "blocked_player_profile_tasks": blocked_player_tasks,
            "source_integrity": source_integrity,
        },
        "blockers": sorted(set(blockers)),
        "tasks": tasks,
        "safety_invariants": [
            "missing_player_rosters_are_blocked_not_complete",
            "player_deep_profiles_require_source_refs",
        ],
    }
    write_json(data_root / "profile-tasks.json", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--edition", required=True)
    init.add_argument("--scope", default="teams,players")
    init.add_argument("--roster-json")
    init.add_argument("--now")
    init.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    roster_json = Path(args.roster_json).resolve() if args.roster_json else None
    result = initialize_profiles(
        root=Path(args.root).resolve(),
        edition=args.edition,
        scope=args.scope,
        roster_json=roster_json,
        now=args.now,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
