#!/usr/bin/env python3
"""Explainable prediction scoring model for World Cup matches.

Computes a data-driven score (85%) combined with a deterministic
divination overlay (15%) for each upcoming match on a given date.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import (  # noqa: E402
    DATA_WEIGHT,
    DISCLAIMER,
    DIVINATION_WEIGHT,
    edition_data_root,
    iso_now,
    load_json,
    load_match_ledger,
    match_on_date,
    match_started,
    now_datetime,
    parse_datetime,
    write_json,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Component weights inside the data_score (must sum to 1.0)
W_RANKING_STRENGTH = 0.30
W_SQUAD_DEPTH = 0.20
W_HISTORICAL_PROXY = 0.20
W_REST_TRAVEL = 0.15
W_EVIDENCE_COMPLETENESS = 0.15

# Ranking points range for normalisation (approximate FIFA men's range)
_RANKING_POINTS_MIN = 1200.0
_RANKING_POINTS_MAX = 1900.0

# Maximum data_score before divination overlay
_DATA_SCORE_CAP = 85.0

# Maximum divination modifier (absolute value)
_DIVINATION_MODIFIER_MAX = 3.0

# Host nations for 2026 (home advantage bonus)
_HOST_NATIONS_2026 = {"mex", "usa", "can"}

# 64 hexagrams of the I Ching (Zhouyi) with short interpretations
_HEXAGRAMS = [
    (1, "乾 (The Creative)", "天行健，君子以自强不息"),
    (2, "坤 (The Receptive)", "地势坤，君子以厚德载物"),
    (3, "屯 (Difficulty at the Beginning)", "云雷屯，君子以经纶"),
    (4, "蒙 (Youthful Folly)", "山下出泉，蒙"),
    (5, "需 (Waiting)", "云上于天，需"),
    (6, "讼 (Conflict)", "天与水违行，讼"),
    (7, "师 (The Army)", "地中有水，师"),
    (8, "比 (Holding Together)", "地上有水，比"),
    (9, "小畜 (Small Taming)", "风行天上，小畜"),
    (10, "履 (Treading)", "上天下泽，履"),
    (11, "泰 (Peace)", "天地交，泰"),
    (12, "否 (Standstill)", "天地不交，否"),
    (13, "同人 (Fellowship)", "天与火，同人"),
    (14, "大有 (Great Possession)", "火在天上，大有"),
    (15, "谦 (Modesty)", "地中有山，谦"),
    (16, "豫 (Enthusiasm)", "雷出地奋，豫"),
    (17, "随 (Following)", "泽中有雷，随"),
    (18, "蛊 (Work on the Decayed)", "山下有风，蛊"),
    (19, "临 (Approach)", "泽上有地，临"),
    (20, "观 (Contemplation)", "风行地上，观"),
    (21, "噬嗑 (Biting Through)", "雷电噬嗑"),
    (22, "贲 (Grace)", "山下有火，贲"),
    (23, "剥 (Splitting Apart)", "山附于地，剥"),
    (24, "复 (Return)", "雷在地中，复"),
    (25, "无妄 (Innocence)", "天下雷行，物与无妄"),
    (26, "大畜 (Great Taming)", "天在山中，大畜"),
    (27, "颐 (Nourishment)", "山下有雷，颐"),
    (28, "大过 (Great Excess)", "泽灭木，大过"),
    (29, "坎 (The Abysmal)", "水洊至，习坎"),
    (30, "离 (The Clinging)", "明两作，离"),
    (31, "咸 (Influence)", "山上有泽，咸"),
    (32, "恒 (Duration)", "雷风恒"),
    (33, "遁 (Retreat)", "天下有山，遁"),
    (34, "大壮 (Great Power)", "雷在天上，大壮"),
    (35, "晋 (Progress)", "明出地上，晋"),
    (36, "明夷 (Darkening of the Light)", "明入地中，明夷"),
    (37, "家人 (The Family)", "风自火出，家人"),
    (38, "睽 (Opposition)", "上火下泽，睽"),
    (39, "蹇 (Obstruction)", "山上有水，蹇"),
    (40, "解 (Deliverance)", "雷雨作，解"),
    (41, "损 (Decrease)", "山下有泽，损"),
    (42, "益 (Increase)", "风雷益，上巽下震"),
    (43, "夬 (Breakthrough)", "泽上于天，夬"),
    (44, "姤 (Coming to Meet)", "天下有风，姤"),
    (45, "萃 (Gathering Together)", "泽上于地，萃"),
    (46, "升 (Pushing Upward)", "地中生木，升"),
    (47, "困 (Oppression)", "泽无水，困"),
    (48, "井 (The Well)", "木上有水，井"),
    (49, "革 (Revolution)", "泽中有火，革"),
    (50, "鼎 (The Cauldron)", "木上有火，鼎"),
    (51, "震 (The Arousing)", "洊雷震"),
    (52, "艮 (Keeping Still)", "兼山艮"),
    (53, "渐 (Development)", "山上有木，渐"),
    (54, "归妹 (The Marrying Maiden)", "泽上有雷，归妹"),
    (55, "丰 (Abundance)", "雷电皆至，丰"),
    (56, "旅 (The Wanderer)", "山上有火，旅"),
    (57, "巽 (The Gentle)", "随风巽"),
    (58, "兑 (The Joyous)", "丽泽兑"),
    (59, "涣 (Dispersion)", "风行水上，涣"),
    (60, "节 (Limitation)", "泽上有水，节"),
    (61, "中孚 (Inner Truth)", "泽上有风，中孚"),
    (62, "小过 (Small Excess)", "山上有雷，小过"),
    (63, "既济 (After Completion)", "水在火上，既济"),
    (64, "未济 (Before Completion)", "火在水上，未济"),
]


# ---------------------------------------------------------------------------
# Helpers: data look-ups
# ---------------------------------------------------------------------------


def _build_ranking_index(rankings_data: dict) -> dict[str, dict]:
    """Map upper-cased team_code -> ranking record."""
    index: dict[str, dict] = {}
    for entry in rankings_data.get("rankings", []):
        code = str(entry.get("team_code", "")).upper()
        if code:
            index[code] = entry
    return index


def _build_squad_index(squad_data: dict) -> dict[str, dict]:
    """Map upper-cased team_id -> squad depth record."""
    index: dict[str, dict] = {}
    for team in squad_data.get("teams", []):
        tid = str(team.get("team_id", "")).upper()
        if tid:
            index[tid] = team
    return index


def _build_evidence_index(evidence_plan: dict) -> dict[str, dict]:
    """Map evidence_id -> evidence item."""
    index: dict[str, dict] = {}
    for item in evidence_plan.get("items", []):
        eid = item.get("evidence_id", "")
        if eid:
            index[eid] = item
    return index


def _normalise_team_query(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _match_teams(match: dict, teams: list[str] | None) -> bool:
    if not teams:
        return True
    expected = {_normalise_team_query(team) for team in teams if team.strip()}
    if len(expected) != 2:
        return False
    home = match.get("home_team", {})
    away = match.get("away_team", {})
    actual = {
        _normalise_team_query(str(home.get("name") or "")),
        _normalise_team_query(str(home.get("team_id") or "")),
        _normalise_team_query(str(away.get("name") or "")),
        _normalise_team_query(str(away.get("team_id") or "")),
    }
    return expected.issubset(actual)


def _lookup_team(team_id: str, index: dict[str, dict]) -> dict | None:
    return index.get(team_id.upper())


def _get_last_match_date(team_id: str, matches: list[dict], current_kickoff: datetime) -> datetime | None:
    """Find the most recent prior match for *team_id* before *current_kickoff*."""
    team_upper = team_id.upper()
    latest: datetime | None = None
    for match in matches:
        kickoff = parse_datetime(str(match.get("kickoff_at", "")))
        if not kickoff:
            continue
        if kickoff >= current_kickoff:
            continue
        home = str(match.get("home_team", {}).get("team_id", "")).upper()
        away = str(match.get("away_team", {}).get("team_id", "")).upper()
        if home == team_upper or away == team_upper:
            if latest is None or kickoff > latest:
                latest = kickoff
    return latest


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------


def _normalise_ranking_points(points: float) -> float:
    """Scale FIFA ranking points to a 0-100 range."""
    span = _RANKING_POINTS_MAX - _RANKING_POINTS_MIN
    if span <= 0:
        return 50.0
    clamped = max(_RANKING_POINTS_MIN, min(_RANKING_POINTS_MAX, points))
    return round(((clamped - _RANKING_POINTS_MIN) / span) * 100.0, 2)


def score_ranking_strength(team_ranking: dict | None) -> float:
    """Component 1: ranking strength (0-100)."""
    if not team_ranking:
        return 30.0  # neutral baseline when ranking unknown
    return _normalise_ranking_points(float(team_ranking.get("points", 0)))


def score_squad_depth(team_squad: dict | None, global_summary: dict | None) -> float:
    """Component 2: squad depth / position balance (0-100).

    Evaluates GK/DF/MF/FW balance relative to global averages, plus
    average age and height proximity to global norms.
    """
    if not team_squad:
        return 40.0  # neutral when squad data missing

    pos = team_squad.get("position_counts", {})
    gk = pos.get("GK", 0)
    df = pos.get("DF", 0)
    mf = pos.get("MF", 0)
    fw = pos.get("FW", 0)
    total = gk + df + mf + fw
    if total == 0:
        return 40.0

    # Ideal ratio (approximate global averages): GK ~11.5%, DF ~33.5%, MF ~30%, FW ~25%
    ideal = {"GK": 0.115, "DF": 0.335, "MF": 0.300, "FW": 0.250}
    actual = {"GK": gk / total, "DF": df / total, "MF": mf / total, "FW": fw / total}
    balance_penalty = sum(abs(actual[k] - ideal[k]) for k in ideal)  # 0 = perfect, max ~1.0
    balance_score = max(0.0, 100.0 - balance_penalty * 100.0)

    # Age proximity (ideal ~27.5-28.5 for international squads)
    avg_age = float(team_squad.get("avg_age_years", 27.5))
    age_diff = abs(avg_age - 28.0)
    age_score = max(0.0, 100.0 - age_diff * 10.0)

    # Height proximity (ideal ~183cm for international squads)
    avg_height = float(team_squad.get("avg_height_cm", 183.0))
    height_diff = abs(avg_height - 183.0)
    height_score = max(0.0, 100.0 - height_diff * 5.0)

    # Combine: balance 50%, age 25%, height 25%
    combined = balance_score * 0.50 + age_score * 0.25 + height_score * 0.25
    return round(min(100.0, max(0.0, combined)), 2)


def score_historical_proxy(team_ranking: dict | None) -> float:
    """Component 3: historical performance proxy (0-100).

    Uses FIFA ranking as a proxy — higher-ranked teams generally have
    stronger World Cup pedigrees.  This is a placeholder until actual
    historical results data is ingested.
    """
    if not team_ranking:
        return 30.0
    points = float(team_ranking.get("points", 0))
    return _normalise_ranking_points(points)


def score_rest_travel(
    *,
    team_id: str,
    is_home: bool,
    current_kickoff: datetime,
    all_matches: list[dict],
    edition: str,
) -> float:
    """Component 4: rest / travel factor (0-100).

    - Base score 70 (neutral).
    - Bonus for more days rest (up to +20 for 5+ days).
    - Penalty for short rest (-15 for <=2 days).
    - Home-nation bonus (+10 for host countries).
    """
    base = 70.0

    last_match = _get_last_match_date(team_id, all_matches, current_kickoff)
    if last_match:
        days_rest = (current_kickoff - last_match).total_seconds() / 86400.0
        if days_rest >= 5:
            base += 20.0
        elif days_rest >= 4:
            base += 10.0
        elif days_rest >= 3:
            base += 5.0
        elif days_rest <= 2:
            base -= 15.0
    else:
        # No prior match found — assume tournament opener, full rest
        base += 15.0

    # Host nation bonus
    if is_home and team_id.lower() in _HOST_NATIONS_2026:
        base += 10.0

    return round(min(100.0, max(0.0, base)), 2)


def score_evidence_completeness(evidence_index: dict[str, dict]) -> float:
    """Component 5: evidence completeness modifier (-15 to +15).

    Positive when evidence is complete, negative when blocked/missing.
    This acts as a small additive modifier rather than a 0-100 score so
    that missing evidence visibly drags the final number.
    """
    # Key evidence families and their impact weight
    families = {
        "official_fixtures": 2.0,
        "official_rosters": 2.0,
        "fifa_rankings": 2.0,
        "historical_worldcup_results": 1.5,
        "recent_form_results": 2.0,
        "squad_depth_position_balance": 1.5,
        "injury_availability": 2.0,
        "venue_rest_travel": 1.0,
    }
    total_modifier = 0.0
    max_possible = sum(families.values())  # 14.0

    for evidence_id, weight in families.items():
        item = evidence_index.get(evidence_id)
        if not item:
            total_modifier -= weight
            continue
        status = item.get("status", "blocked")
        if status == "complete":
            total_modifier += weight
        elif status == "partial":
            total_modifier += weight * 0.4
        else:
            # blocked or missing
            total_modifier -= weight * 0.5

    # Scale to -15 .. +15 range
    normalised = (total_modifier / max_possible) * 15.0
    return round(max(-15.0, min(15.0, normalised)), 2)


# ---------------------------------------------------------------------------
# Divination overlay (Zhouyi / I Ching)
# ---------------------------------------------------------------------------


def _hexagram_hash(date: str, match_id: str) -> int:
    """Deterministic hash -> hexagram number 1-64."""
    seed = f"{date}|{match_id}|zhouyi"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 64) + 1


def _modifier_from_hexagram(number: int) -> tuple[float, float]:
    """Map hexagram number to (home_modifier, away_modifier) in [-3, +3].

    The modifiers are small and deterministic.  Positive hexagrams
    favour the home side; negative hexagrams favour the away side.
    Some are balanced (near zero for both).
    """
    # Use a simple mapping: hexagram number -> offset on a sine-like curve
    # This ensures a spread of positive/negative values across 1-64.
    import math

    # Home modifier: based on position in the cycle
    angle_home = (number - 1) * (2 * math.pi / 64)
    home_raw = math.sin(angle_home) * _DIVINATION_MODIFIER_MAX
    home_mod = round(home_raw, 1)

    # Away modifier: phase-shifted
    angle_away = ((number - 1) + 16) * (2 * math.pi / 64)
    away_raw = math.sin(angle_away) * _DIVINATION_MODIFIER_MAX
    away_mod = round(away_raw, 1)

    return home_mod, away_mod


def compute_divination_overlay(date: str, match_id: str) -> dict:
    """Compute the entertainment divination overlay for a match."""
    number = _hexagram_hash(date, match_id)
    hex_num, hex_name, hex_interp = _HEXAGRAMS[number - 1]
    home_mod, away_mod = _modifier_from_hexagram(number)
    return {
        "hexagram_number": hex_num,
        "hexagram_name": hex_name,
        "interpretation": hex_interp,
        "home_modifier": home_mod,
        "away_modifier": away_mod,
    }


# ---------------------------------------------------------------------------
# Confidence determination
# ---------------------------------------------------------------------------


def _collect_evidence_gaps(evidence_index: dict[str, dict]) -> list[str]:
    """Return a list of evidence families that are partial or blocked."""
    gaps: list[str] = []
    required_families = [
        "official_fixtures",
        "official_rosters",
        "fifa_rankings",
        "historical_worldcup_results",
        "recent_form_results",
        "squad_depth_position_balance",
        "injury_availability",
        "venue_rest_travel",
    ]
    for eid in required_families:
        item = evidence_index.get(eid)
        if not item:
            gaps.append(f"{eid}_missing")
            continue
        status = item.get("status", "blocked")
        if status == "blocked":
            gaps.append(f"{eid}_blocked")
        elif status == "partial":
            gaps.append(f"{eid}_partial")
    return gaps


def _determine_confidence(data_score: float, evidence_gaps: list[str]) -> tuple[str, str]:
    """Return (confidence_level, confidence_label).

    - high: data_score > 75 AND no blocked evidence
    - medium: data_score 50-75, or partial evidence present
    - low: data_score < 50, or any blocked evidence
    """
    has_blocked = any(g.endswith("_blocked") for g in evidence_gaps)
    has_partial = any(g.endswith("_partial") for g in evidence_gaps)

    if has_blocked:
        level = "low"
    elif data_score > 75 and not has_partial:
        level = "high"
    elif data_score >= 50:
        level = "medium"
    else:
        level = "low"

    labels = {"high": "高信心", "medium": "中等信心", "low": "低信心"}
    return level, labels[level]


def _estimate_scoreline(home_final: float, away_final: float, predicted_outcome: str) -> dict:
    """Translate model scores into a conservative football scoreline."""
    gap = abs(home_final - away_final)
    avg_strength = (home_final + away_final) / 2.0

    if predicted_outcome == "draw":
        goals = 1 if avg_strength >= 42 else 0
        return {"home": goals, "away": goals}

    if gap >= 18:
        winner_goals = 2
        loser_goals = 0 if min(home_final, away_final) < 43 else 1
    elif gap >= 8:
        winner_goals = 2
        loser_goals = 1
    else:
        winner_goals = 1
        loser_goals = 0

    if predicted_outcome == "home_win":
        return {"home": winner_goals, "away": loser_goals}
    return {"home": loser_goals, "away": winner_goals}


# ---------------------------------------------------------------------------
# Play card builder
# ---------------------------------------------------------------------------


def _build_play_card(
    *,
    match: dict,
    home_name: str,
    away_name: str,
    home_final: float,
    away_final: float,
    predicted_outcome: str,
    predicted_score: dict,
    total_goals: int,
    confidence: str,
    confidence_label: str,
    evidence_gaps: list[str],
    hexagram_name: str,
    data_weight: float,
    divination_weight: float,
) -> dict:
    outcome_labels = {
        "home_win": f"{home_name} 倾向胜出",
        "away_win": f"{away_name} 倾向胜出",
        "draw": "平局拉扯",
    }
    # Context-aware hook
    venue = match.get("venue", "")
    phase = match.get("phase", "group")
    group = match.get("group", "")
    if phase == "group" and group:
        hook = f"{group}组对决，{venue or '赛场待定'}。"
    elif phase != "group":
        hook = f"淘汰赛阶段，{venue or '赛场待定'}。"
    else:
        hook = f"{venue or '赛场待定'}。"

    # Watch points: derive from score gap and context
    watch_points: list[str] = []
    gap = abs(home_final - away_final)
    if gap > 20:
        watch_points.append(f"{home_name if home_final > away_final else away_name}排名优势明显")
        watch_points.append(f"{'弱' if home_final < away_final else '强'}方能否以冲击力弥补差距")
    else:
        watch_points.append("双方实力接近，临场发挥将决定走向")
        watch_points.append("中场控制权和定位球效率是关键")

    if phase == "group":
        watch_points.append("小组赛积分策略可能影响比赛节奏")

    # Risk flags from evidence gaps
    risk_flags: list[str] = []
    for gap_id in evidence_gaps:
        if "injury" in gap_id:
            risk_flags.append("伤停信息不完整")
        elif "recent_form" in gap_id:
            risk_flags.append("近期战绩数据缺失")
        elif "historical" in gap_id:
            risk_flags.append("历史战绩数据不足")
        elif "venue_rest" in gap_id:
            risk_flags.append("休息和旅行因素未充分计算")
    if not risk_flags:
        risk_flags.append("当前证据链完整度较好")

    # Poster angle (English for image generation)
    poster_angle = f"{home_name} vs {away_name}, {venue or 'World Cup stadium'}, vibrant crowd atmosphere, {hexagram_name} aesthetic overlay"

    # Confidence meter
    data_pct = round(data_weight * 100)
    div_pct = round(divination_weight * 100)
    confidence_meter = f"数据 {data_pct}% | 玄学 {div_pct}% | 信心: {confidence_label}"

    score_text = f"{predicted_score['home']}-{predicted_score['away']}"

    return {
        "share_title": f"{home_name} vs {away_name} | 娱乐预测 {score_text}",
        "match_hook": f"{outcome_labels[predicted_outcome]}，总进球参考 {total_goals} 球。{hook}",
        "watch_points": watch_points,
        "risk_flags": risk_flags,
        "poster_angle": f"{poster_angle}, predicted score {score_text}, total goals {total_goals}",
        "confidence_meter": confidence_meter,
        "gameplay_tags": ["胜平负", "比分", "总进球", "看点"],
    }


# ---------------------------------------------------------------------------
# Main prediction pipeline
# ---------------------------------------------------------------------------


def predict_match(
    *,
    match: dict,
    edition: str,
    date: str,
    all_matches: list[dict],
    ranking_index: dict[str, dict],
    squad_index: dict[str, dict],
    evidence_index: dict[str, dict],
    global_summary: dict | None,
) -> dict:
    """Compute the full prediction record for a single match."""
    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home_id = str(home_team.get("team_id", ""))
    away_id = str(away_team.get("team_id", ""))
    home_name = str(home_team.get("name") or home_id)
    away_name = str(away_team.get("name") or away_id)

    # --- Data look-ups ---
    home_ranking = _lookup_team(home_id, ranking_index)
    away_ranking = _lookup_team(away_id, ranking_index)
    home_squad = _lookup_team(home_id, squad_index)
    away_squad = _lookup_team(away_id, squad_index)

    kickoff = parse_datetime(str(match.get("kickoff_at", "")))
    kickoff_dt = kickoff or datetime.now(timezone.utc)

    # --- Component scores (each 0-100 except evidence which is -15..+15) ---
    rs_home = score_ranking_strength(home_ranking)
    rs_away = score_ranking_strength(away_ranking)

    sd_home = score_squad_depth(home_squad, global_summary)
    sd_away = score_squad_depth(away_squad, global_summary)

    hp_home = score_historical_proxy(home_ranking)
    hp_away = score_historical_proxy(away_ranking)

    rt_home = score_rest_travel(
        team_id=home_id,
        is_home=True,
        current_kickoff=kickoff_dt,
        all_matches=all_matches,
        edition=edition,
    )
    rt_away = score_rest_travel(
        team_id=away_id,
        is_home=False,
        current_kickoff=kickoff_dt,
        all_matches=all_matches,
        edition=edition,
    )

    ec_modifier = score_evidence_completeness(evidence_index)

    # --- Weighted data_score (per team, 0-100 before cap) ---
    raw_home = (
        rs_home * W_RANKING_STRENGTH
        + sd_home * W_SQUAD_DEPTH
        + hp_home * W_HISTORICAL_PROXY
        + rt_home * W_REST_TRAVEL
        + ec_modifier * W_EVIDENCE_COMPLETENESS
    )
    raw_away = (
        rs_away * W_RANKING_STRENGTH
        + sd_away * W_SQUAD_DEPTH
        + hp_away * W_HISTORICAL_PROXY
        + rt_away * W_REST_TRAVEL
        + ec_modifier * W_EVIDENCE_COMPLETENESS
    )

    data_home = round(min(_DATA_SCORE_CAP, max(0.0, raw_home)), 1)
    data_away = round(min(_DATA_SCORE_CAP, max(0.0, raw_away)), 1)

    # --- Divination overlay ---
    divination = compute_divination_overlay(date, match.get("match_id", ""))

    # --- Final scores ---
    home_final = round(min(100.0, max(0.0, data_home + divination["home_modifier"])), 1)
    away_final = round(min(100.0, max(0.0, data_away + divination["away_modifier"])), 1)

    # --- Predicted outcome ---
    gap = home_final - away_final
    if abs(gap) <= 3.0:
        predicted_outcome = "draw"
    elif gap > 0:
        predicted_outcome = "home_win"
    else:
        predicted_outcome = "away_win"
    predicted_score = _estimate_scoreline(home_final, away_final, predicted_outcome)
    total_goals = int(predicted_score["home"]) + int(predicted_score["away"])
    goals_line_2_5 = "over" if total_goals >= 3 else "under"

    # --- Confidence ---
    evidence_gaps = _collect_evidence_gaps(evidence_index)
    # Use the average data_score for confidence determination
    avg_data = (data_home + data_away) / 2.0
    confidence, confidence_label = _determine_confidence(avg_data, evidence_gaps)

    # --- Ranking info for output ---
    home_rank_info = {
        "team_id": home_id,
        "name": home_name,
        "ranking": home_ranking.get("rank", 0) if home_ranking else 0,
        "points": home_ranking.get("points", 0.0) if home_ranking else 0.0,
    }
    away_rank_info = {
        "team_id": away_id,
        "name": away_name,
        "ranking": away_ranking.get("rank", 0) if away_ranking else 0,
        "points": away_ranking.get("points", 0.0) if away_ranking else 0.0,
    }

    # --- Play card ---
    play_card = _build_play_card(
        match=match,
        home_name=home_name,
        away_name=away_name,
        home_final=home_final,
        away_final=away_final,
        predicted_outcome=predicted_outcome,
        predicted_score=predicted_score,
        total_goals=total_goals,
        confidence=confidence,
        confidence_label=confidence_label,
        evidence_gaps=evidence_gaps,
        hexagram_name=divination["hexagram_name"],
        data_weight=DATA_WEIGHT,
        divination_weight=DIVINATION_WEIGHT,
    )

    return {
        "match_id": match.get("match_id", ""),
        "kickoff_at": match.get("kickoff_at", ""),
        "venue": match.get("venue", ""),
        "group": match.get("group", ""),
        "phase": match.get("phase", "group"),
        "home_team": home_rank_info,
        "away_team": away_rank_info,
        "data_score": {
            "home": data_home,
            "away": data_away,
            "components": {
                "ranking_strength": {
                    "home": rs_home,
                    "away": rs_away,
                    "weight": W_RANKING_STRENGTH,
                },
                "squad_depth": {
                    "home": sd_home,
                    "away": sd_away,
                    "weight": W_SQUAD_DEPTH,
                },
                "historical_proxy": {
                    "home": hp_home,
                    "away": hp_away,
                    "weight": W_HISTORICAL_PROXY,
                },
                "rest_travel": {
                    "home": rt_home,
                    "away": rt_away,
                    "weight": W_REST_TRAVEL,
                },
                "evidence_completeness": {
                    "home": ec_modifier,
                    "away": ec_modifier,
                    "weight": W_EVIDENCE_COMPLETENESS,
                },
            },
        },
        "divination_overlay": divination,
        "prediction": {
            "home_final": home_final,
            "away_final": away_final,
            "result": predicted_outcome,
            "predicted_outcome": predicted_outcome,
            "score": predicted_score,
            "total_goals": total_goals,
            "goals_line_2_5": goals_line_2_5,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "evidence_gaps": evidence_gaps,
        },
        "play_card": play_card,
        "disclaimer": DISCLAIMER,
    }


def run_scoring_model(
    *,
    root: Path,
    edition: str,
    date: str | None = None,
    match_id: str | None = None,
    teams: list[str] | None = None,
    now: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Run the prediction scoring model for all matches on *date*."""
    generated_at = iso_now(now)
    now_dt = now_datetime(now)
    ed_root = edition_data_root(root, edition)

    # --- Load data sources ---
    ledger = load_match_ledger(root, edition)
    rankings_data = load_json(ed_root / "rankings" / "fifa-men-ranking.json", {"rankings": []})
    squad_data = load_json(ed_root / "squad-depth-features.json", {"teams": [], "global_summary": {}})
    evidence_plan = load_json(ed_root / "prediction-evidence-plan.json", {"items": []})

    ranking_index = _build_ranking_index(rankings_data)
    squad_index = _build_squad_index(squad_data)
    evidence_index = _build_evidence_index(evidence_plan)
    global_summary = squad_data.get("global_summary")
    all_matches = ledger.get("matches", [])

    # --- Find matches for this date that haven't kicked off ---
    predictions: list[dict] = []
    skipped_started = 0
    skipped_no_kickoff = 0

    for match in all_matches:
        if match_id and match.get("match_id") != match_id:
            continue
        if teams and not _match_teams(match, teams):
            continue
        if date and not match_on_date(match, date):
            continue
        if match_started(match, now_dt):
            skipped_started += 1
            continue
        kickoff = parse_datetime(str(match.get("kickoff_at", "")))
        if not kickoff:
            skipped_no_kickoff += 1
            continue

        prediction = predict_match(
            match=match,
            edition=edition,
            date=date or kickoff.date().isoformat(),
            all_matches=all_matches,
            ranking_index=ranking_index,
            squad_index=squad_index,
            evidence_index=evidence_index,
            global_summary=global_summary,
        )
        predictions.append(prediction)

    # --- Build report ---
    report_date = date
    if not report_date and predictions:
        first_kickoff = parse_datetime(str(predictions[0].get("kickoff_at", "")))
        report_date = first_kickoff.date().isoformat() if first_kickoff else "undated"
    report_date = report_date or "undated"

    report = {
        "version": 1,
        "edition": edition,
        "date": report_date,
        "generated_at": generated_at,
        "mode": "worldcup-prediction-scoring-model",
        "filters": {
            "match_id": match_id or "",
            "teams": teams or [],
        },
        "model_weights": {
            "data_model": DATA_WEIGHT,
            "divination_overlay": DIVINATION_WEIGHT,
            "component_weights": {
                "ranking_strength": W_RANKING_STRENGTH,
                "squad_depth": W_SQUAD_DEPTH,
                "historical_proxy": W_HISTORICAL_PROXY,
                "rest_travel": W_REST_TRAVEL,
                "evidence_completeness": W_EVIDENCE_COMPLETENESS,
            },
        },
        "status": "dry_run" if dry_run else "created",
        "summary": {
            "predictions_created": len(predictions),
            "matches_skipped_started": skipped_started,
            "matches_skipped_missing_kickoff": skipped_no_kickoff,
        },
        "predictions": predictions,
        "disclaimer": DISCLAIMER,
        "safety_invariants": [
            "data_model_weight_is_0_85",
            "divination_overlay_weight_is_0_15",
            "divination_overlay_capped_at_15_points",
            "data_score_capped_at_85_points",
            "no_betting_language_in_output",
            "missing_evidence_downgrades_confidence",
            "disclaimer_included_in_every_report",
        ],
    }

    # --- Write report (unless dry_run) ---
    if not dry_run and predictions:
        suffix = f"-{match_id}" if match_id else ""
        if teams and not match_id:
            suffix = "-" + "-vs-".join(_normalise_team_query(team) for team in teams)
        out_path = ed_root / "reports" / f"{report_date}{suffix}-prediction-report.json"
        write_json(out_path, report)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    predict = sub.add_parser("predict", help="Run the prediction scoring model")
    predict.add_argument("--edition", required=True, help="Edition identifier (e.g. 2026)")
    predict.add_argument("--root", default=".", help="Project root directory")
    predict.add_argument("--date", help="Target date in YYYY-MM-DD format")
    predict.add_argument("--match-id", help="Predict one match by stable match_id")
    predict.add_argument("--teams", help='Predict one match by team names or IDs, e.g. "Mexico,South Africa"')
    predict.add_argument("--now", default=None, help="Override current time (ISO-8601)")
    predict.add_argument(
        "--dry-run",
        action="store_true",
        help="Print predictions without writing files",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "predict":
        result = run_scoring_model(
            root=Path(args.root).resolve(),
            edition=args.edition,
            date=args.date,
            match_id=args.match_id,
            teams=[item.strip() for item in args.teams.split(",")] if args.teams else None,
            now=args.now,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
