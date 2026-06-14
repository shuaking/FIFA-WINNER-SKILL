#!/usr/bin/env python3
"""Compile squad depth and position-balance features from roster data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import raw_edition_root, edition_data_root, iso_now, load_json, write_json  # noqa: E402

CLUB_COUNTRY_RE = re.compile(r"\(([A-Z]{3})\)")
POSITIONS = ["GK", "DF", "MF", "FW"]


def parse_reference_date(value: str | None) -> date:
    """Parse a reference date string (YYYY-MM-DD) or return today."""
    if value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return date.today()


def compute_age_years(dob_str: str, reference: date) -> float | None:
    """Compute age in years from a YYYY-MM-DD DOB to the reference date."""
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    delta_days = (reference - dob).days
    return round(delta_days / 365.25, 2)


def extract_club_country(club: str) -> str | None:
    """Extract the 3-letter country code from a club string like 'Lille OSC (FRA)'."""
    if not club:
        return None
    match = CLUB_COUNTRY_RE.search(club)
    return match.group(1) if match else None


def compute_team_features(team: dict, reference: date) -> dict:
    """Compute squad-depth features for a single team."""
    players = team.get("players", [])
    total_players = len(players)

    # Position counts
    position_counts = {pos: 0 for pos in POSITIONS}
    for player in players:
        pos = player.get("position", "")
        if pos in position_counts:
            position_counts[pos] += 1

    # Age statistics
    ages = []
    for player in players:
        age = compute_age_years(player.get("dob", ""), reference)
        if age is not None:
            ages.append(age)
    avg_age_years = round(sum(ages) / len(ages), 2) if ages else None

    # Height statistics
    heights = []
    for player in players:
        h = player.get("height_cm")
        if h is not None:
            heights.append(h)
    avg_height_cm = round(sum(heights) / len(heights), 1) if heights else None

    # Club country distribution
    club_country_distribution: dict[str, int] = {}
    for player in players:
        country = extract_club_country(player.get("club", ""))
        if country:
            club_country_distribution[country] = club_country_distribution.get(country, 0) + 1

    # Missing fields detection
    missing_set: set[str] = set()
    for player in players:
        if not player.get("dob"):
            missing_set.add("dob")
        if not player.get("club"):
            missing_set.add("club")
        if player.get("height_cm") is None:
            missing_set.add("height_cm")
    missing_fields: str | list[str] = "none" if not missing_set else sorted(missing_set)

    return {
        "team_id": team.get("team_id", ""),
        "name": team.get("name", ""),
        "code": team.get("code", ""),
        "total_players": total_players,
        "position_counts": position_counts,
        "avg_age_years": avg_age_years,
        "avg_height_cm": avg_height_cm,
        "club_country_distribution": dict(sorted(club_country_distribution.items())),
        "missing_fields": missing_fields,
    }


def compile_squad_depth(
    *,
    root: Path,
    edition: str,
    now: str | None = None,
    reference_date: str | None = None,
) -> dict:
    """Build squad-depth features for all teams and write the output JSON."""
    generated_at = iso_now(now)
    data_root = edition_data_root(root, edition)
    roster = load_json(raw_edition_root(root, edition) / "rosters" / "fifa-squad-lists.json")
    ref_date = parse_reference_date(reference_date)

    teams_raw = roster.get("teams", [])
    team_features = [compute_team_features(team, ref_date) for team in teams_raw]

    # Global summary
    total_teams = len(team_features)
    total_players = sum(t["total_players"] for t in team_features)

    global_position_counts = {pos: 0 for pos in POSITIONS}
    for t in team_features:
        for pos in POSITIONS:
            global_position_counts[pos] += t["position_counts"].get(pos, 0)

    all_ages = [t["avg_age_years"] for t in team_features if t["avg_age_years"] is not None]
    global_avg_age = round(sum(all_ages) / len(all_ages), 2) if all_ages else None

    all_heights = [t["avg_height_cm"] for t in team_features if t["avg_height_cm"] is not None]
    global_avg_height_cm = round(sum(all_heights) / len(all_heights), 1) if all_heights else None

    payload = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-squad-depth-features",
        "global_summary": {
            "total_teams": total_teams,
            "total_players": total_players,
            "global_position_counts": global_position_counts,
            "global_avg_age": global_avg_age,
            "global_avg_height_cm": global_avg_height_cm,
        },
        "teams": team_features,
        "source_refs": ["fifa-squad-lists-pdf"],
        "safety_invariants": [
            "squad_depth_features_derived_from_fifa_official_roster_only",
            "missing_fields_reported_per_team_to_flag_incomplete_player_records",
            "age_computed_against_explicit_reference_date_for_reproducibility",
        ],
    }

    write_json(data_root / "squad-depth-features.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Compile squad depth features from roster data")
    build.add_argument("--edition", required=True, help="World Cup edition year (e.g. 2026)")
    build.add_argument("--root", default=".", help="Project root directory")
    build.add_argument("--now", default=None, help="Override generated_at timestamp (ISO-8601)")
    build.add_argument(
        "--reference-date",
        default=None,
        help="Reference date for age calculation in YYYY-MM-DD format (default: today)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compile_squad_depth(
        root=Path(args.root).resolve(),
        edition=args.edition,
        now=args.now,
        reference_date=args.reference_date,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
