#!/usr/bin/env python3
"""Manual or sourced daily evidence input for injuries, suspensions, lineups and late news."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, load_json, write_json  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _daily_evidence_path(root: Path, edition: str, date: str) -> Path:
    return edition_data_root(root, edition) / "daily-evidence" / f"{date}.json"


def _load_daily_evidence(root: Path, edition: str, date: str) -> dict:
    path = _daily_evidence_path(root, edition, date)
    return load_json(path, default={})


def _save_daily_evidence(root: Path, edition: str, date: str, payload: dict) -> None:
    write_json(_daily_evidence_path(root, edition, date), payload)


def _severity_choices() -> list[str]:
    return ["doubtful", "questionable", "out", "ruled_out"]


def _source_choices() -> list[str]:
    return ["national_fa", "espn", "fbref", "other"]


def _reason_choices() -> list[str]:
    return ["yellow_cards", "red_card", "disciplinary"]


def _impact_choices() -> list[str]:
    return ["high", "medium", "low"]


def _section_status(count: int) -> str:
    return "complete" if count > 0 else "partial"


# ---------------------------------------------------------------------------
# subcommand implementations
# ---------------------------------------------------------------------------

def cmd_init(*, root: Path, edition: str, date: str, now: str | None = None) -> dict:
    """Initialize an empty daily evidence file for *date*."""
    generated_at = iso_now(now)
    path = _daily_evidence_path(root, edition, date)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing["status"] = "already_initialized"
        return existing

    payload = {
        "version": 1,
        "edition": edition,
        "date": date,
        "generated_at": generated_at,
        "mode": "daily-evidence",
        "status": "empty",
        "matches": [],
        "injuries": [],
        "suspensions": [],
        "probable_lineups": [],
        "late_news": [],
        "source_refs": [],
        "safety_invariants": [
            "missing_daily_evidence_is_marked_partial_or_blocked",
            "daily_evidence_does_not_overwrite_prediction_reports",
        ],
    }
    _save_daily_evidence(root, edition, date, payload)
    return payload


def cmd_add_injury(
    *,
    root: Path,
    edition: str,
    date: str,
    team_code: str,
    player_name: str,
    severity: str,
    source: str,
    source_url: str = "",
    notes: str = "",
    now: str | None = None,
) -> dict:
    """Append an injury entry to the daily evidence file."""
    generated_at = iso_now(now)
    evidence = _load_daily_evidence(root, edition, date)
    if not evidence:
        raise SystemExit(f"Error: no daily evidence file for {date}. Run 'init' first.")

    entry = {
        "team_code": team_code,
        "player_name": player_name,
        "severity": severity,
        "source": source,
        "source_url": source_url,
        "notes": notes,
        "recorded_at": generated_at,
    }
    evidence["injuries"].append(entry)
    evidence["generated_at"] = generated_at
    evidence["status"] = "updated"
    if source_url:
        evidence["source_refs"].append({"source": source, "url": source_url, "recorded_at": generated_at})
    _save_daily_evidence(root, edition, date, evidence)
    return evidence


def cmd_add_suspension(
    *,
    root: Path,
    edition: str,
    date: str,
    team_code: str,
    player_name: str,
    reason: str,
    matches_missed: int,
    source: str,
    source_url: str = "",
    notes: str = "",
    now: str | None = None,
) -> dict:
    """Append a suspension entry to the daily evidence file."""
    generated_at = iso_now(now)
    evidence = _load_daily_evidence(root, edition, date)
    if not evidence:
        raise SystemExit(f"Error: no daily evidence file for {date}. Run 'init' first.")

    entry = {
        "team_code": team_code,
        "player_name": player_name,
        "reason": reason,
        "matches_missed": matches_missed,
        "source": source,
        "source_url": source_url,
        "notes": notes,
        "recorded_at": generated_at,
    }
    evidence["suspensions"].append(entry)
    evidence["generated_at"] = generated_at
    evidence["status"] = "updated"
    if source_url:
        evidence["source_refs"].append({"source": source, "url": source_url, "recorded_at": generated_at})
    _save_daily_evidence(root, edition, date, evidence)
    return evidence


def cmd_add_lineup(
    *,
    root: Path,
    edition: str,
    date: str,
    team_code: str,
    formation: str,
    players: str,
    source: str,
    source_url: str = "",
    now: str | None = None,
) -> dict:
    """Append a probable lineup entry to the daily evidence file."""
    generated_at = iso_now(now)
    evidence = _load_daily_evidence(root, edition, date)
    if not evidence:
        raise SystemExit(f"Error: no daily evidence file for {date}. Run 'init' first.")

    player_list = [p.strip() for p in players.split(",") if p.strip()]
    entry = {
        "team_code": team_code,
        "formation": formation,
        "players": player_list,
        "source": source,
        "source_url": source_url,
        "recorded_at": generated_at,
    }
    evidence["probable_lineups"].append(entry)
    evidence["generated_at"] = generated_at
    evidence["status"] = "updated"
    if source_url:
        evidence["source_refs"].append({"source": source, "url": source_url, "recorded_at": generated_at})
    _save_daily_evidence(root, edition, date, evidence)
    return evidence


def cmd_add_news(
    *,
    root: Path,
    edition: str,
    date: str,
    headline: str,
    impact: str,
    source: str,
    detail: str = "",
    team_code: str = "",
    source_url: str = "",
    now: str | None = None,
) -> dict:
    """Append a late news entry to the daily evidence file."""
    generated_at = iso_now(now)
    evidence = _load_daily_evidence(root, edition, date)
    if not evidence:
        raise SystemExit(f"Error: no daily evidence file for {date}. Run 'init' first.")

    entry = {
        "headline": headline,
        "detail": detail,
        "impact": impact,
        "team_code": team_code,
        "source": source,
        "source_url": source_url,
        "recorded_at": generated_at,
    }
    evidence["late_news"].append(entry)
    evidence["generated_at"] = generated_at
    evidence["status"] = "updated"
    if source_url:
        evidence["source_refs"].append({"source": source, "url": source_url, "recorded_at": generated_at})
    _save_daily_evidence(root, edition, date, evidence)
    return evidence


def cmd_status(*, root: Path, edition: str, date: str) -> dict:
    """Show evidence completeness for *date*."""
    path = _daily_evidence_path(root, edition, date)
    if not path.exists():
        return {
            "date": date,
            "edition": edition,
            "evidence_file_exists": False,
            "overall_status": "blocked",
            "confidence_impact": "missing_daily_evidence_blocks_predictions_or_downgrades_confidence",
            "sections": {
                "injuries": {"count": 0, "status": "blocked"},
                "suspensions": {"count": 0, "status": "blocked"},
                "lineups": {"count": 0, "status": "blocked"},
                "news": {"count": 0, "status": "blocked"},
            },
            "safety_invariants": [
                "missing_daily_evidence_is_marked_partial_or_blocked",
                "daily_evidence_does_not_overwrite_prediction_reports",
            ],
        }

    evidence = json.loads(path.read_text(encoding="utf-8"))
    injuries = evidence.get("injuries", [])
    suspensions = evidence.get("suspensions", [])
    lineups = evidence.get("probable_lineups", [])
    news = evidence.get("late_news", [])

    sections = {
        "injuries": {"count": len(injuries), "status": _section_status(len(injuries))},
        "suspensions": {"count": len(suspensions), "status": _section_status(len(suspensions))},
        "lineups": {"count": len(lineups), "status": _section_status(len(lineups))},
        "news": {"count": len(news), "status": _section_status(len(news))},
    }

    total = len(injuries) + len(suspensions) + len(lineups) + len(news)
    if total == 0:
        overall = "blocked"
    else:
        any_partial = any(s["status"] == "partial" for s in sections.values())
        overall = "partial" if any_partial else "complete"

    confidence_impact = (
        "evidence_available_but_some_sections_missing_downgrades_prediction_confidence"
        if overall == "partial"
        else "all_sections_have_entries_confidence_not_capped_by_availability"
        if overall == "complete"
        else "missing_daily_evidence_blocks_predictions_or_downgrades_confidence"
    )

    return {
        "date": date,
        "edition": edition,
        "evidence_file_exists": True,
        "overall_status": overall,
        "confidence_impact": confidence_impact,
        "sections": sections,
        "total_entries": total,
        "safety_invariants": [
            "missing_daily_evidence_is_marked_partial_or_blocked",
            "daily_evidence_does_not_overwrite_prediction_reports",
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    # -- common args helper ------------------------------------------------
    def _add_common(p: argparse.ArgumentParser, *, require_date: bool = True) -> None:
        p.add_argument("--edition", required=True)
        p.add_argument("--root", default=".")
        p.add_argument("--now")
        if require_date:
            p.add_argument("--date", required=True)

    # init ----------------------------------------------------------------
    p_init = sub.add_parser("init", help="Initialize a daily evidence file for a given date.")
    _add_common(p_init)

    # add-injury ----------------------------------------------------------
    p_inj = sub.add_parser("add-injury", help="Add an injury report.")
    _add_common(p_inj)
    p_inj.add_argument("--team-code", required=True)
    p_inj.add_argument("--player-name", required=True)
    p_inj.add_argument("--severity", required=True, choices=_severity_choices())
    p_inj.add_argument("--source", required=True, choices=_source_choices())
    p_inj.add_argument("--source-url", default="")
    p_inj.add_argument("--notes", default="")

    # add-suspension ------------------------------------------------------
    p_sus = sub.add_parser("add-suspension", help="Add a suspension report.")
    _add_common(p_sus)
    p_sus.add_argument("--team-code", required=True)
    p_sus.add_argument("--player-name", required=True)
    p_sus.add_argument("--reason", required=True, choices=_reason_choices())
    p_sus.add_argument("--matches-missed", required=True, type=int)
    p_sus.add_argument("--source", required=True, choices=_source_choices())
    p_sus.add_argument("--source-url", default="")
    p_sus.add_argument("--notes", default="")

    # add-lineup ----------------------------------------------------------
    p_lin = sub.add_parser("add-lineup", help="Add a probable lineup.")
    _add_common(p_lin)
    p_lin.add_argument("--team-code", required=True)
    p_lin.add_argument("--formation", required=True)
    p_lin.add_argument("--players", required=True, help="Comma-separated player names.")
    p_lin.add_argument("--source", required=True, choices=_source_choices())
    p_lin.add_argument("--source-url", default="")

    # add-news ------------------------------------------------------------
    p_news = sub.add_parser("add-news", help="Add late news.")
    _add_common(p_news)
    p_news.add_argument("--headline", required=True)
    p_news.add_argument("--detail", default="")
    p_news.add_argument("--impact", required=True, choices=_impact_choices())
    p_news.add_argument("--team-code", default="")
    p_news.add_argument("--source", required=True, choices=_source_choices())
    p_news.add_argument("--source-url", default="")

    # status --------------------------------------------------------------
    p_stat = sub.add_parser("status", help="Show evidence completeness for a date.")
    _add_common(p_stat)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    edition = args.edition
    date = args.date
    now = args.now

    if args.command == "init":
        result = cmd_init(root=root, edition=edition, date=date, now=now)

    elif args.command == "add-injury":
        result = cmd_add_injury(
            root=root,
            edition=edition,
            date=date,
            team_code=args.team_code,
            player_name=args.player_name,
            severity=args.severity,
            source=args.source,
            source_url=args.source_url,
            notes=args.notes,
            now=now,
        )

    elif args.command == "add-suspension":
        result = cmd_add_suspension(
            root=root,
            edition=edition,
            date=date,
            team_code=args.team_code,
            player_name=args.player_name,
            reason=args.reason,
            matches_missed=args.matches_missed,
            source=args.source,
            source_url=args.source_url,
            notes=args.notes,
            now=now,
        )

    elif args.command == "add-lineup":
        result = cmd_add_lineup(
            root=root,
            edition=edition,
            date=date,
            team_code=args.team_code,
            formation=args.formation,
            players=args.players,
            source=args.source,
            source_url=args.source_url,
            now=now,
        )

    elif args.command == "add-news":
        result = cmd_add_news(
            root=root,
            edition=edition,
            date=date,
            headline=args.headline,
            detail=args.detail,
            impact=args.impact,
            team_code=args.team_code,
            source=args.source,
            source_url=args.source_url,
            now=now,
        )

    elif args.command == "status":
        result = cmd_status(root=root, edition=edition, date=date)

    else:
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
