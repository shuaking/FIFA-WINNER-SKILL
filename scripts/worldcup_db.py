#!/usr/bin/env python3
"""SQLite database helper interface for World Cup predictor."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def get_db_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get sqlite3 connection with foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str | Path) -> None:
    """Initialize SQLite tables and indexes."""
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection(db_path)
    try:
        with conn:
            # Create Teams table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    team_id TEXT PRIMARY KEY,
                    code TEXT,
                    name_en TEXT,
                    name_zh TEXT,
                    colors TEXT,
                    glow_color TEXT,
                    stars TEXT,
                    adjective TEXT
                )
            """)

            # Create Players table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    player_id TEXT PRIMARY KEY,
                    team_id TEXT,
                    shirt_number INTEGER,
                    position TEXT,
                    player_name TEXT,
                    name_on_shirt TEXT,
                    club TEXT,
                    dob TEXT,
                    height_cm INTEGER,
                    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);")

            # Create Matches table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    edition TEXT,
                    phase TEXT,
                    group_name TEXT,
                    kickoff_at TEXT,
                    home_team_id TEXT,
                    away_team_id TEXT,
                    venue TEXT,
                    status TEXT,
                    final_score_home INTEGER,
                    final_score_away INTEGER,
                    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
                    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_kickoff ON matches(kickoff_at);")

            # Create Predictions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    match_id TEXT PRIMARY KEY,
                    prediction_date TEXT,
                    prediction_status TEXT,
                    predicted_result TEXT,
                    predicted_score_home INTEGER,
                    predicted_score_away INTEGER,
                    confidence TEXT,
                    divination_hexagram TEXT,
                    generated_at TEXT,
                    FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_analysis_layers (
                    match_id TEXT,
                    layer_id TEXT,
                    title TEXT,
                    verdict TEXT,
                    confidence TEXT,
                    payload_json TEXT NOT NULL,
                    generated_at TEXT,
                    PRIMARY KEY (match_id, layer_id),
                    FOREIGN KEY (match_id) REFERENCES predictions(match_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prediction_analysis_layer_id ON prediction_analysis_layers(layer_id);")

            # Create Evaluations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    match_id TEXT PRIMARY KEY,
                    actual_score_home INTEGER,
                    actual_score_away INTEGER,
                    is_result_correct INTEGER CHECK(is_result_correct IN (0, 1)),
                    is_score_correct INTEGER CHECK(is_score_correct IN (0, 1)),
                    evaluated_at TEXT,
                    FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
                )
            """)
            conn.commit()
    finally:
        conn.close()


def save_team(conn: sqlite3.Connection, team: dict) -> None:
    """Upsert a team record."""
    conn.execute("""
        INSERT INTO teams (team_id, code, name_en, name_zh, colors, glow_color, stars, adjective)
        VALUES (:team_id, :code, :name_en, :name_zh, :colors, :glow_color, :stars, :adjective)
        ON CONFLICT(team_id) DO UPDATE SET
            code = excluded.code,
            name_en = excluded.name_en,
            name_zh = excluded.name_zh,
            colors = COALESCE(excluded.colors, colors),
            glow_color = COALESCE(excluded.glow_color, glow_color),
            stars = COALESCE(excluded.stars, stars),
            adjective = COALESCE(excluded.adjective, adjective)
    """, {
        "team_id": str(team["team_id"]).lower(),
        "code": team.get("code") or team.get("team_id", "").upper(),
        "name_en": team.get("name_en") or team.get("name") or "Unknown Team",
        "name_zh": team.get("name_zh") or team.get("name") or "Unknown Team",
        "colors": team.get("colors"),
        "glow_color": team.get("glow_color"),
        "stars": team.get("stars"),
        "adjective": team.get("adjective")
    })


def save_player(conn: sqlite3.Connection, player: dict) -> None:
    """Upsert a player record."""
    conn.execute("""
        INSERT INTO players (player_id, team_id, shirt_number, position, player_name, name_on_shirt, club, dob, height_cm)
        VALUES (:player_id, :team_id, :shirt_number, :position, :player_name, :name_on_shirt, :club, :dob, :height_cm)
        ON CONFLICT(player_id) DO UPDATE SET
            team_id = excluded.team_id,
            shirt_number = excluded.shirt_number,
            position = excluded.position,
            player_name = excluded.player_name,
            name_on_shirt = excluded.name_on_shirt,
            club = excluded.club,
            dob = excluded.dob,
            height_cm = excluded.height_cm
    """, {
        "player_id": str(player["player_id"]).lower(),
        "team_id": str(player["team_id"]).lower(),
        "shirt_number": player.get("shirt_number"),
        "position": player.get("position"),
        "player_name": player.get("player_name"),
        "name_on_shirt": player.get("name_on_shirt"),
        "club": player.get("club"),
        "dob": player.get("dob"),
        "height_cm": player.get("height_cm")
    })


def save_match(conn: sqlite3.Connection, match: dict) -> None:
    """Upsert a match record."""
    home_id = match.get("home_team_id") or ""
    away_id = match.get("away_team_id") or ""

    # Try to extract from home_team dict
    if not home_id and isinstance(match.get("home_team"), dict):
        home_id = match["home_team"].get("team_id") or ""
    if not away_id and isinstance(match.get("away_team"), dict):
        away_id = match["away_team"].get("team_id") or ""

    home_id = str(home_id).lower()
    away_id = str(away_id).lower()

    # Pre-check if team records exist to satisfy FK constraints, if not create dummy ones
    for tid, tname in [(home_id, match.get("home_team")), (away_id, match.get("away_team"))]:
        if not tid:
            continue
        cur = conn.execute("SELECT 1 FROM teams WHERE team_id = ?", (tid,))
        if not cur.fetchone():
            name_str = tname if isinstance(tname, str) else (tname.get("name") if isinstance(tname, dict) else tid.upper())
            save_team(conn, {"team_id": tid, "name_en": name_str, "name_zh": name_str})

    final_score = match.get("final_score") or {}
    fs_home = final_score.get("home") if final_score else None
    fs_away = final_score.get("away") if final_score else None

    conn.execute("""
        INSERT INTO matches (match_id, edition, phase, group_name, kickoff_at, home_team_id, away_team_id, venue, status, final_score_home, final_score_away)
        VALUES (:match_id, :edition, :phase, :group_name, :kickoff_at, :home_team_id, :away_team_id, :venue, :status, :final_score_home, :final_score_away)
        ON CONFLICT(match_id) DO UPDATE SET
            edition = excluded.edition,
            phase = excluded.phase,
            group_name = excluded.group_name,
            kickoff_at = excluded.kickoff_at,
            home_team_id = excluded.home_team_id,
            away_team_id = excluded.away_team_id,
            venue = excluded.venue,
            status = excluded.status,
            final_score_home = COALESCE(excluded.final_score_home, final_score_home),
            final_score_away = COALESCE(excluded.final_score_away, final_score_away)
    """, {
        "match_id": match["match_id"],
        "edition": match.get("edition") or "2026",
        "phase": match.get("phase") or "group",
        "group_name": match.get("group") or match.get("group_name") or "",
        "kickoff_at": match.get("kickoff_at"),
        "home_team_id": home_id or None,
        "away_team_id": away_id or None,
        "venue": match.get("venue"),
        "status": match.get("status") or "fixture_official",
        "final_score_home": fs_home,
        "final_score_away": fs_away
    })


def save_prediction(conn: sqlite3.Connection, prediction: dict) -> None:
    """Upsert a prediction record."""
    pred_info = prediction.get("prediction") or {}
    score = pred_info.get("score") or {}
    divination = prediction.get("divination_overlay") or {}

    conn.execute("""
        INSERT INTO predictions (match_id, prediction_date, prediction_status, predicted_result, predicted_score_home, predicted_score_away, confidence, divination_hexagram, generated_at)
        VALUES (:match_id, :prediction_date, :prediction_status, :predicted_result, :predicted_score_home, :predicted_score_away, :confidence, :divination_hexagram, :generated_at)
        ON CONFLICT(match_id) DO UPDATE SET
            prediction_date = excluded.prediction_date,
            prediction_status = excluded.prediction_status,
            predicted_result = excluded.predicted_result,
            predicted_score_home = excluded.predicted_score_home,
            predicted_score_away = excluded.predicted_score_away,
            confidence = excluded.confidence,
            divination_hexagram = excluded.divination_hexagram,
            generated_at = excluded.generated_at
    """, {
        "match_id": prediction["match_id"],
        "prediction_date": prediction.get("prediction_date") or prediction.get("generated_at", "")[:10],
        "prediction_status": prediction.get("status") or "locked_pre_match_prediction",
        "predicted_result": pred_info.get("result") or pred_info.get("predicted_outcome"),
        "predicted_score_home": score.get("home"),
        "predicted_score_away": score.get("away"),
        "confidence": pred_info.get("confidence"),
        "divination_hexagram": divination.get("hexagram"),
        "generated_at": prediction.get("generated_at")
    })


def save_prediction_analysis_layers(conn: sqlite3.Connection, prediction: dict) -> None:
    """Store explainability layers as a query index while keeping JSON reports canonical."""
    match_id = prediction["match_id"]
    generated_at = prediction.get("generated_at")
    for layer in prediction.get("analysis_layers", []) or []:
        layer_id = str(layer.get("layer_id") or "")
        if not layer_id:
            continue
        conn.execute("""
            INSERT INTO prediction_analysis_layers
                (match_id, layer_id, title, verdict, confidence, payload_json, generated_at)
            VALUES
                (:match_id, :layer_id, :title, :verdict, :confidence, :payload_json, :generated_at)
            ON CONFLICT(match_id, layer_id) DO UPDATE SET
                title = excluded.title,
                verdict = excluded.verdict,
                confidence = excluded.confidence,
                payload_json = excluded.payload_json,
                generated_at = excluded.generated_at
        """, {
            "match_id": match_id,
            "layer_id": layer_id,
            "title": layer.get("title"),
            "verdict": layer.get("verdict"),
            "confidence": layer.get("confidence"),
            "payload_json": json.dumps(layer, ensure_ascii=False, sort_keys=True),
            "generated_at": generated_at,
        })


def save_evaluation(conn: sqlite3.Connection, evaluation: dict) -> None:
    """Upsert an evaluation record."""
    conn.execute("""
        INSERT INTO evaluations (match_id, actual_score_home, actual_score_away, is_result_correct, is_score_correct, evaluated_at)
        VALUES (:match_id, :actual_score_home, :actual_score_away, :is_result_correct, :is_score_correct, :evaluated_at)
        ON CONFLICT(match_id) DO UPDATE SET
            actual_score_home = excluded.actual_score_home,
            actual_score_away = excluded.actual_score_away,
            is_result_correct = excluded.is_result_correct,
            is_score_correct = excluded.is_score_correct,
            evaluated_at = excluded.evaluated_at
    """, {
        "match_id": evaluation["match_id"],
        "actual_score_home": evaluation["actual_score_home"],
        "actual_score_away": evaluation["actual_score_away"],
        "is_result_correct": 1 if evaluation["is_result_correct"] else 0,
        "is_score_correct": 1 if evaluation["is_score_correct"] else 0,
        "evaluated_at": evaluation.get("evaluated_at")
    })
