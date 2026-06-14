#!/usr/bin/env python3
"""Parse FIFA 2026 World Cup schedule and update the match ledger."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import (  # noqa: E402
    edition_data_root,
    worldcup_db_path,
    iso_now,
    load_json,
    write_json,
)

ET_OFFSET = timedelta(hours=4)

TEAM_NAME_TO_ID: dict[str, str] = {
    "Mexico": "mex",
    "South Africa": "rsa",
    "South Korea": "kor",
    "Czechia": "cze",
    "Canada": "can",
    "Bosnia and Herzegovina": "bih",
    "Qatar": "qat",
    "Switzerland": "sui",
    "Brazil": "bra",
    "Morocco": "mar",
    "Haiti": "hai",
    "Scotland": "sco",
    "United States": "usa",
    "Paraguay": "par",
    "Australia": "aus",
    "Türkiye": "tur",
    "Germany": "ger",
    "Curaçao": "cuw",
    "Ivory Coast": "civ",
    "Ecuador": "ecu",
    "Netherlands": "ned",
    "Japan": "jpn",
    "Sweden": "swe",
    "Tunisia": "tun",
    "Belgium": "bel",
    "Egypt": "egy",
    "Iran": "irn",
    "New Zealand": "nzl",
    "Spain": "esp",
    "Cape Verde": "cpv",
    "Saudi Arabia": "ksa",
    "Uruguay": "uru",
    "France": "fra",
    "Senegal": "sen",
    "Iraq": "irq",
    "Norway": "nor",
    "Argentina": "arg",
    "Algeria": "alg",
    "Austria": "aut",
    "Jordan": "jor",
    "Portugal": "por",
    "DR Congo": "cod",
    "Uzbekistan": "uzb",
    "Colombia": "col",
    "England": "eng",
    "Croatia": "cro",
    "Ghana": "gha",
    "Panama": "pan",
}

# Group stage pairings: (home_slot, away_slot) for matches 01-06 within a group.
# These mirror worldcup_core.default_group_matches.
GROUP_PAIRINGS: list[tuple[int, int]] = [
    (1, 2),
    (3, 4),
    (1, 3),
    (2, 4),
    (4, 1),
    (2, 3),
]

GROUPS: list[str] = [chr(ord("A") + i) for i in range(12)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_name_lookup() -> dict[str, str]:
    """Build a case-insensitive name -> team_id lookup from TEAM_NAME_TO_ID."""
    lookup: dict[str, str] = {}
    for name, tid in TEAM_NAME_TO_ID.items():
        lookup[name.lower()] = tid
    return lookup


_NAME_LOOKUP = _build_name_lookup()


def resolve_team_id(name: str) -> str | None:
    """Return the team_id for an ESPN team name, or None if unknown."""
    if not name:
        return None
    return _NAME_LOOKUP.get(name.strip().lower())


def et_to_utc_iso(date_str: str, time_str: str) -> str:
    """Convert a US-Eastern date + time pair to an ISO-8601 UTC string.

    *date_str* accepts ``YYYY-MM-DD`` or ``Month DD, YYYY``.
    *time_str* accepts ``H:MM AM/PM`` (12-hour) or ``HH:MM`` (24-hour).
    ET is assumed to be UTC-4 (EDT).
    """
    date_str = date_str.strip()
    time_str = time_str.strip()

    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            date_part = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue
    else:
        date_part = datetime.strptime(date_str, "%Y-%m-%d").date()

    time_lower = time_str.lower()
    if "am" in time_lower or "pm" in time_lower:
        clean = time_lower.replace("am", "").replace("pm", "").strip()
        hour_min = [int(p) for p in clean.split(":")]
        hour, minute = hour_min[0], hour_min[1] if len(hour_min) > 1 else 0
        if "pm" in time_lower and hour != 12:
            hour += 12
        elif "am" in time_lower and hour == 12:
            hour = 0
    else:
        hour_min = [int(p) for p in time_str.split(":")]
        hour, minute = hour_min[0], hour_min[1] if len(hour_min) > 1 else 0

    et_dt = datetime(
        date_part.year,
        date_part.month,
        date_part.day,
        hour,
        minute,
        tzinfo=timezone.utc,
    )
    utc_dt = et_dt + ET_OFFSET
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick(obj: dict, *keys: str, default: str = "") -> str:
    """Return the first non-empty value found among *keys* in *obj*."""
    for key in keys:
        val = obj.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------


def parse_fixtures(
    *,
    schedule: list[dict],
    ledger: dict,
    generated_at: str,
) -> dict:
    """Apply *schedule* data onto *ledger* matches and return the updated ledger."""

    matches: list[dict] = ledger["matches"]
    match_index: dict[str, dict] = {m["match_id"]: m for m in matches}
    match_number_index: dict[int, dict] = {m["match_number"]: m for m in matches}

    # -- separate group-stage from knockout --------------------------------
    group_matches_by_letter: dict[str, list[dict]] = defaultdict(list)
    knockout_entries: list[dict] = []

    for entry in schedule:
        match_num = entry.get("match_number") or entry.get("matchNumber") or entry.get("match")
        if match_num is not None:
            match_num = int(match_num)

        group = entry.get("group", "")
        is_group = False
        if 1 <= (match_num or 0) <= 72:
            is_group = True
        elif group and str(group).upper() in GROUPS:
            is_group = True

        if is_group and group:
            group_matches_by_letter[str(group).upper()].append(entry)
        else:
            knockout_entries.append(entry)

    # -- group stage: sort chronologically, map to ledger slots ------------
    group_updates = 0
    for group_letter in GROUPS:
        entries = group_matches_by_letter.get(group_letter, [])
        if not entries:
            continue

        def _sort_key(e: dict) -> tuple[str, str]:
            d = _pick(e, "date", "match_date", "date_str")
            t = _pick(e, "kickoff_et", "time", "kickoff_time", "kickoff", "time_et")
            return (d, t)

        entries.sort(key=_sort_key)

        for slot_idx, entry in enumerate(entries):
            if slot_idx >= len(GROUP_PAIRINGS):
                break

            match_id = f"2026-G{group_letter}-{slot_idx + 1:02d}"
            ledger_match = match_index.get(match_id)
            if not ledger_match:
                continue

            date_str = _pick(entry, "date", "match_date", "date_str")
            time_str = _pick(entry, "kickoff_et", "time", "kickoff_time", "kickoff", "time_et")
            if date_str and time_str:
                ledger_match["kickoff_at"] = et_to_utc_iso(date_str, time_str)

            venue = _pick(entry, "venue", "stadium")
            city = _pick(entry, "city", "location")
            if venue:
                ledger_match["venue"] = f"{venue}, {city}" if city else venue

            home_name = _pick(entry, "home_team", "home")
            away_name = _pick(entry, "away_team", "away")

            if home_name:
                home_id = resolve_team_id(home_name)
                ledger_match["home_team"] = {
                    "team_id": home_id or ledger_match["home_team"]["team_id"],
                    "name": home_name,
                    "slot": ledger_match["home_team"].get("slot", GROUP_PAIRINGS[slot_idx][0]),
                }
            if away_name:
                away_id = resolve_team_id(away_name)
                ledger_match["away_team"] = {
                    "team_id": away_id or ledger_match["away_team"]["team_id"],
                    "name": away_name,
                    "slot": ledger_match["away_team"].get("slot", GROUP_PAIRINGS[slot_idx][1]),
                }

            ledger_match["status"] = "fixture_official"
            group_updates += 1

    # -- knockout stage: update date/venue, keep placeholder teams ---------
    knockout_updates = 0
    for entry in knockout_entries:
        match_num = entry.get("match_number") or entry.get("matchNumber") or entry.get("match")
        if match_num is not None:
            match_num = int(match_num)

        ledger_match = match_number_index.get(match_num)
        if not ledger_match:
            continue

        date_str = _pick(entry, "date", "match_date", "date_str")
        time_str = _pick(entry, "kickoff_et", "time", "kickoff_time", "kickoff", "time_et")
        if date_str and time_str:
            ledger_match["kickoff_at"] = et_to_utc_iso(date_str, time_str)

        venue = _pick(entry, "venue", "stadium")
        city = _pick(entry, "city", "location")
        if venue:
            ledger_match["venue"] = f"{venue}, {city}" if city else venue

        # Knockout teams remain placeholders until results are known.
        # If the schedule provides descriptive labels, store them as names
        # but keep the original placeholder team_id.
        home_name = _pick(entry, "home_team", "home")
        away_name = _pick(entry, "away_team", "away")
        if home_name:
            ledger_match["home_team"]["name"] = home_name
        if away_name:
            ledger_match["away_team"]["name"] = away_name

        knockout_updates += 1

    # -- update ledger metadata -------------------------------------------
    ledger["generated_at"] = generated_at
    ledger["summary"]["fixture_status"] = "official_schedule_applied"
    ledger["summary"]["group_matches_updated"] = group_updates
    ledger["summary"]["knockout_matches_updated"] = knockout_updates
    ledger["safety_invariants"] = [
        "worldcup_match_ledger_records_all_104_matches",
        "all_104_match_ids_preserved_after_schedule_update",
        "group_matches_use_official_team_names_and_ids",
        "knockout_teams_remain_placeholders_until_officially_known",
        "kickoff_times_converted_from_et_to_utc_iso8601",
        "prediction_reports_append_to_matches_by_stable_match_id",
    ]

    return ledger


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_parse(args: argparse.Namespace) -> dict:
    schedule_path = Path(args.schedule_json)
    schedule: list[dict] = load_json(schedule_path, [])  # type: ignore[arg-type]
    if not isinstance(schedule, list):
        schedule = schedule.get("matches", [])  # type: ignore[union-attr]

    root = Path(args.root).resolve()
    edition = args.edition
    generated_at = iso_now(args.now)

    ledger_path = edition_data_root(root, edition) / "match-ledger.json"
    ledger: dict = load_json(ledger_path, {})  # type: ignore[arg-type]

    original_match_ids = sorted(m["match_id"] for m in ledger.get("matches", []))

    ledger = parse_fixtures(
        schedule=schedule,
        ledger=ledger,
        generated_at=generated_at,
    )

    updated_match_ids = sorted(m["match_id"] for m in ledger.get("matches", []))
    assert original_match_ids == updated_match_ids, (
        "match_id set changed after fixture parse"
    )
    assert len(updated_match_ids) == 104, (
        f"expected 104 matches, got {len(updated_match_ids)}"
    )

    write_json(ledger_path, ledger)

    db_path = worldcup_db_path(root, edition)
    from worldcup_db import get_db_connection, init_database, save_match
    init_database(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            for m in ledger["matches"]:
                save_match(conn, m)
    finally:
        conn.close()

    group_official = sum(
        1
        for m in ledger["matches"]
        if m.get("phase") == "group" and m.get("status") == "fixture_official"
    )
    group_placeholder = sum(
        1
        for m in ledger["matches"]
        if m.get("phase") == "group" and m.get("status") == "fixture_placeholder"
    )
    knockout_placeholder = sum(
        1
        for m in ledger["matches"]
        if m.get("phase") != "group"
        and m.get("status") == "knockout_placeholder_until_teams_known"
    )

    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "schedule_source": str(schedule_path),
        "match_ledger": str(ledger_path),
        "summary": {
            "total_matches": len(ledger["matches"]),
            "group_matches_official": group_official,
            "group_matches_placeholder": group_placeholder,
            "knockout_matches_placeholder": knockout_placeholder,
            "match_ids_preserved": len(updated_match_ids) == 104,
        },
        "safety_invariants": ledger.get("safety_invariants", []),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse schedule JSON and update match ledger")
    parse_cmd.add_argument("--edition", required=True, help="Edition year (e.g. 2026)")
    parse_cmd.add_argument("--schedule-json", required=True, help="Path to extracted ESPN schedule JSON")
    parse_cmd.add_argument("--root", default=".", help="Workspace root directory")
    parse_cmd.add_argument("--now", default=None, help="ISO-8601 timestamp override")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse":
        result = cmd_parse(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
