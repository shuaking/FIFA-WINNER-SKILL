#!/usr/bin/env python3
"""Parse FIFA men's ranking data and generate structured ranking output for qualified World Cup teams."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, load_json, raw_edition_root, write_json  # noqa: E402

QUALIFIED_TEAM_CODES: list[str] = sorted([
    "ALG", "ARG", "AUS", "AUT", "BEL", "BIH", "BRA", "CAN", "CPV", "CIV",
    "COD", "COL", "CRO", "CUW", "CZE", "ECU", "EGY", "ENG", "ESP", "FRA",
    "GER", "GHA", "HAI", "IRN", "IRQ", "JPN", "JOR", "KOR", "KSA", "MAR", "MEX",
    "NED", "NOR", "NZL", "PAN", "PAR", "POR", "QAT", "RSA", "SCO", "SEN",
    "SUI", "SWE", "TUN", "TUR", "URU", "USA", "UZB",
])


def parse_ranking(
    *,
    root: Path,
    edition: str,
    ranking_json: str,
    snapshot_manifest: str,
    now: str | None = None,
) -> dict:
    generated_at = iso_now(now)
    data_root = edition_data_root(root, edition)

    rankings_raw = load_json(Path(ranking_json))
    if not isinstance(rankings_raw, list):
        raise ValueError(f"ranking JSON must be an array, got {type(rankings_raw).__name__}")

    manifest = load_json(Path(snapshot_manifest))
    if not isinstance(manifest, dict):
        raise ValueError(f"snapshot manifest must be an object, got {type(manifest).__name__}")

    qualified_set = set(QUALIFIED_TEAM_CODES)
    qualified_rankings: list[dict] = []
    for entry in rankings_raw:
        code = str(entry.get("team_code", "")).strip().upper()
        if code not in qualified_set:
            continue
        qualified_rankings.append({
            "rank": entry.get("rank"),
            "team_name": entry.get("team_name", ""),
            "team_code": code,
            "points": entry.get("points"),
            "world_rank": entry.get("rank"),
        })

    qualified_rankings.sort(key=lambda item: (item["world_rank"] is None, item["world_rank"]))

    missing_codes = qualified_set - {item["team_code"] for item in qualified_rankings}

    source_url = str(manifest.get("url", "")).strip()
    source_tier = str(manifest.get("source_tier", manifest.get("tier", ""))).strip()

    ranking_date = ""
    if qualified_rankings:
        ranking_date = generated_at[:10]

    source_integrity = "complete" if not missing_codes else "partial"

    report = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "fifa-men-ranking",
        "source_url": source_url,
        "source_tier": source_tier,
        "snapshot_manifest": snapshot_manifest,
        "rankings": qualified_rankings,
        "summary": {
            "total_teams": len(rankings_raw),
            "qualified_teams": len(qualified_rankings),
            "ranking_date": ranking_date,
            "source_integrity": source_integrity,
        },
        "safety_invariants": [
            "ranking_output_contains_only_qualified_teams",
            "rankings_sorted_by_world_rank_ascending",
            "missing_qualified_teams_recorded_in_source_integrity",
        ],
    }

    if missing_codes:
        report["missing_qualified_teams"] = sorted(missing_codes)

    out_path = raw_edition_root(root, edition) / "rankings" / "fifa-men-ranking.json"
    write_json(out_path, report)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    parse_cmd = sub.add_parser("parse")
    parse_cmd.add_argument("--edition", required=True)
    parse_cmd.add_argument("--ranking-json", required=True)
    parse_cmd.add_argument("--snapshot-manifest", required=True)
    parse_cmd.add_argument("--now")
    parse_cmd.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = parse_ranking(
        root=Path(args.root).resolve(),
        edition=args.edition,
        ranking_json=args.ranking_json,
        snapshot_manifest=args.snapshot_manifest,
        now=args.now,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
