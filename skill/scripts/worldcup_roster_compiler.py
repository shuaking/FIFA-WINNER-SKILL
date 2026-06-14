#!/usr/bin/env python3
"""Compile edition teams and player profile tasks into a roster status file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, load_json, write_json  # noqa: E402


def compile_roster(*, root: Path, edition: str, now: str | None = None) -> dict:
    generated_at = iso_now(now)
    data_root = edition_data_root(root, edition)
    teams_payload = load_json(data_root / "teams.json", {"teams": []})
    tasks_payload = load_json(data_root / "profile-tasks.json", {"tasks": []})
    player_tasks = [task for task in tasks_payload.get("tasks", []) if task.get("task_type") in {"player_deep_profile", "player_deep_profile_batch"}]
    report = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-roster-compiled-status",
        "summary": {
            "teams": len(teams_payload.get("teams", [])),
            "player_profile_tasks": len(player_tasks),
            "blocked_player_profile_tasks": sum(1 for task in player_tasks if task.get("status") == "blocked"),
            "compiled_players": sum(1 for task in player_tasks if task.get("task_type") == "player_deep_profile"),
            "source_integrity": tasks_payload.get("summary", {}).get("source_integrity", "partial"),
        },
        "teams": teams_payload.get("teams", []),
        "player_profile_tasks": player_tasks,
        "safety_invariants": ["compiled_roster_reports_missing_players_as_blocked_or_partial"],
    }
    write_json(data_root / "roster-compiled.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--edition", required=True)
    build.add_argument("--now")
    build.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compile_roster(root=Path(args.root).resolve(), edition=args.edition, now=args.now)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
