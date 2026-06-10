#!/usr/bin/env python3
"""Parse FIFA official squad-list PDFs into edition roster JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, slugify, wiki_edition_root, write_json, write_text  # noqa: E402

TEAM_RE = re.compile(r"^(.+?)\s+\(([A-Z]{3})\)\s*$")
DOB_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
HEIGHT_RE = re.compile(r"^\d{2,3}$")
POSITIONS = {"GK", "DF", "MF", "FW"}


def clean_cell(value: object) -> str:
    return str(value or "").replace("\x00", "").strip()


def compact_cells(row: list[object]) -> list[str]:
    return [clean_cell(cell) for cell in row]


def nonempty(values: list[str]) -> list[str]:
    return [value for value in values if value]


def parse_dob(value: str) -> str:
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


def parse_team_header(page_text: str) -> tuple[str, str]:
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        match = TEAM_RE.match(line)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    raise ValueError("team header not found")


def parse_player_row(row: list[object], *, team_code: str, edition: str) -> dict | None:
    cells = compact_cells(row)
    if len(cells) < 8 or not cells[0].isdigit() or cells[1] not in POSITIONS:
        return None
    dob_idx = next((index for index, value in enumerate(cells) if DOB_RE.match(value)), -1)
    if dob_idx == -1:
        return None
    height_candidates = [index for index, value in enumerate(cells[dob_idx + 1 :], start=dob_idx + 1) if HEIGHT_RE.match(value)]
    height_idx = height_candidates[-1] if height_candidates else -1
    club = ""
    if height_idx != -1:
        club_values = nonempty(cells[dob_idx + 1 : height_idx])
        club = " ".join(club_values).strip()
    pre_dob = nonempty(cells[3:dob_idx])
    first_names = pre_dob[0] if pre_dob else ""
    last_names = pre_dob[1] if len(pre_dob) > 1 else ""
    name_on_shirt = pre_dob[-1] if pre_dob else ""
    shirt_number = int(cells[0])
    player_id = f"{team_code.lower()}-{shirt_number:02d}"
    return {
        "player_id": player_id,
        "edition": edition,
        "team_code": team_code,
        "shirt_number": shirt_number,
        "position": cells[1],
        "player_name": cells[2],
        "first_names": first_names,
        "last_names": last_names,
        "name_on_shirt": name_on_shirt,
        "dob": parse_dob(cells[dob_idx]),
        "club": club,
        "height_cm": int(cells[height_idx]) if height_idx != -1 else None,
        "source_integrity": "official_squad_pdf",
        "source_refs": ["fifa-squad-lists-pdf"],
    }


def parse_coach_row(row: list[object]) -> dict | None:
    cells = compact_cells(row)
    values = nonempty(cells)
    if not values or values[0] != "Head coach":
        return None
    if len(values) < 4:
        return {"role": "Head coach", "coach_name": values[1] if len(values) > 1 else "", "nationality": ""}
    return {
        "role": "Head coach",
        "coach_name": values[1],
        "first_names": values[2] if len(values) > 2 else "",
        "last_names": values[3] if len(values) > 3 else "",
        "nationality": values[4] if len(values) > 4 else "",
    }


def parse_team_page(*, page_text: str, table_rows: list[list[object]], edition: str, page_number: int) -> dict:
    team_name, team_code = parse_team_header(page_text)
    players = []
    coach = None
    for row in table_rows:
        player = parse_player_row(row, team_code=team_code, edition=edition)
        if player:
            players.append(player)
            continue
        maybe_coach = parse_coach_row(row)
        if maybe_coach:
            coach = maybe_coach
    team_id = team_code.lower()
    return {
        "team": {
            "team_id": team_id,
            "name": team_name,
            "code": team_code,
            "source_integrity": "complete",
            "status": "official_squad_pdf_parsed",
            "source_refs": ["fifa-squad-lists-pdf"],
            "page_number": page_number,
        },
        "coach": coach or {},
        "players": players,
    }


def parse_squad_pdf(*, pdf_path: Path, edition: str, now: str | None = None) -> dict:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required to parse FIFA squad PDFs") from exc

    generated_at = iso_now(now)
    teams = []
    with pdfplumber.open(pdf_path) as doc:
        for index, page in enumerate(doc.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables()
            if not tables:
                continue
            teams.append(parse_team_page(page_text=text, table_rows=tables[0], edition=edition, page_number=index))

    player_count = sum(len(team["players"]) for team in teams)
    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "fifa-squad-pdf-parsed-roster",
        "source_pdf": str(pdf_path),
        "summary": {
            "teams": len(teams),
            "players": player_count,
            "coaches": sum(1 for team in teams if team.get("coach")),
            "source_integrity": "complete" if len(teams) == 48 and player_count == 1248 else "partial",
        },
        "teams": [
            {
                **team["team"],
                "coach": team["coach"],
                "players": team["players"],
            }
            for team in teams
        ],
        "safety_invariants": [
            "parsed_roster_preserves_fifa_source_pdf_reference",
            "player_rows_keep_official_pdf_fields",
        ],
    }


def write_roster_outputs(*, root: Path, edition: str, roster: dict, output: Path | None = None, update_edition_teams: bool = False) -> dict:
    data_root = edition_data_root(root, edition)
    output = output or (data_root / "rosters" / "fifa-squad-lists.json")
    write_json(output, roster)

    db_path = data_root / f"worldcup_{edition}.db"
    from worldcup_db import get_db_connection, init_database, save_team, save_player
    init_database(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            for team in roster["teams"]:
                save_team(conn, team)
                for p in team["players"]:
                    # Ensure team_id is set inside the player dict for foreign keys
                    p["team_id"] = team["team_id"]
                    save_player(conn, p)
    finally:
        conn.close()

    if update_edition_teams:
        teams = {
            "version": 1,
            "edition": edition,
            "generated_at": roster["generated_at"],
            "mode": "worldcup-teams-from-fifa-squad-pdf",
            "teams": [
                {key: value for key, value in team.items() if key not in {"players"}}
                for team in roster["teams"]
            ],
            "summary": {
                "team_count": len(roster["teams"]),
                "source_integrity": roster["summary"]["source_integrity"],
                "status": "official_squad_pdf_parsed",
            },
        }
        write_json(data_root / "teams.json", teams)
        write_roster_summary(root=root, edition=edition, roster=roster)
    return {"output": str(output), "update_edition_teams": update_edition_teams}


def write_roster_summary(*, root: Path, edition: str, roster: dict) -> None:
    path = wiki_edition_root(root, edition) / "summaries" / "fifa-squad-lists.md"
    write_text(
        path,
        f"""---
type: summary
edition: {edition}
source_url: https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf
source_integrity: {roster['summary']['source_integrity']}
status: active
---

# FIFA 官方阵容 PDF 摘要

- 队伍数：{roster['summary']['teams']}
- 球员数：{roster['summary']['players']}
- 教练数：{roster['summary']['coaches']}
- 原始 PDF：`{roster['source_pdf']}`

## 边界

本页只记录官方阵容 PDF 的结构化消化结果。球员国家队历史、伤停、近期状态和俱乐部深档仍需要后续来源补充。
""",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    parse = sub.add_parser("parse")
    parse.add_argument("--edition", required=True)
    parse.add_argument("--pdf", required=True)
    parse.add_argument("--output")
    parse.add_argument("--update-edition-teams", action="store_true")
    parse.add_argument("--now")
    parse.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    roster = parse_squad_pdf(pdf_path=Path(args.pdf).resolve(), edition=args.edition, now=args.now)
    output_info = write_roster_outputs(
        root=root,
        edition=args.edition,
        roster=roster,
        output=Path(args.output).resolve() if args.output else None,
        update_edition_teams=args.update_edition_teams,
    )
    result = {**roster, "output": output_info["output"], "update_edition_teams": output_info["update_edition_teams"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if roster["summary"]["source_integrity"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
