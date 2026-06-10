#!/usr/bin/env python3
"""Initialize an isolated World Cup edition knowledge base."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import (  # noqa: E402
    default_match_ledger,
    default_teams,
    edition_data_root,
    ensure_base_wiki,
    ensure_edition_wiki,
    iso_now,
    raw_edition_root,
    source_registry_payload,
    wiki_edition_root,
    write_json,
)


def initialize_edition(*, root: Path, edition: str, now: str | None = None) -> dict:
    generated_at = iso_now(now)
    ensure_base_wiki(root)
    ensure_edition_wiki(root, edition)

    data_root = edition_data_root(root, edition)
    raw_root = raw_edition_root(root, edition)
    wiki_root = wiki_edition_root(root, edition)
    for path in [
        data_root / "reports" / "daily-predictions",
        data_root / "reports" / "posters",
        data_root / "reports" / "evaluations",
        data_root / "profiles",
        data_root / "snapshots",
        raw_root / "snapshots",
        raw_root / "evidence-packets",
        wiki_root / "reports" / "daily-predictions",
        wiki_root / "reports" / "posters",
        wiki_root / "reports" / "evaluations",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    registry = source_registry_payload(edition, generated_at)
    ledger = default_match_ledger(edition, generated_at)
    teams = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-team-placeholders",
        "teams": default_teams(),
        "summary": {
            "team_count": 48,
            "source_integrity": "partial",
            "status": "placeholder_until_official_roster_ingest",
        },
    }

    write_json(raw_root / "source-registry.json", registry)
    write_json(data_root / "source-registry.json", registry)
    write_json(data_root / "match-ledger.json", ledger)
    write_json(data_root / "teams.json", teams)

    db_path = data_root / f"worldcup_{edition}.db"
    from worldcup_db import init_database, get_db_connection, save_team, save_match
    init_database(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            for t in teams["teams"]:
                save_team(conn, t)
            for m in ledger["matches"]:
                save_match(conn, m)
    finally:
        conn.close()

    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "paths": {
            "raw": str(raw_root),
            "wiki": str(wiki_root),
            "data": str(data_root),
            "match_ledger": str(data_root / "match-ledger.json"),
            "source_registry": str(raw_root / "source-registry.json"),
            "database": str(db_path),
        },
        "summary": ledger["summary"],
        "safety_invariants": ledger["safety_invariants"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--edition", required=True)
    init.add_argument("--now")
    init.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        result = initialize_edition(root=Path(args.root).resolve(), edition=args.edition, now=args.now)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
