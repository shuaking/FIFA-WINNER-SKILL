#!/usr/bin/env python3
"""Build image-generation prompt manifests from daily prediction reports."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import DISCLAIMER, edition_data_root, iso_now, load_json, load_match_ledger, poster_manifest_path, write_json, write_text  # noqa: E402


NEGATIVE_PROMPT_SHOWDOWN = (
    "fictional players, generic footballers, fake faces, missing squad members, only 5 players, only 10 players, "
    "duplicate players, wrong team colors, wrong jersey numbers, wrong flag, fake logo, unreadable Chinese text, "
    "misspelled text, incorrect date, incorrect kickoff time, distorted faces, deformed hands, extra limbs, "
    "plastic skin, cartoon, anime, video game render, fantasy armor, low quality"
)


def _team_name(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("team_id") or "Unknown Team")
    return str(value or "Unknown Team")


def _team_id(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("team_id") or "").lower()
    return ""


def _prediction_team(value: object, match_team: object) -> object:
    if isinstance(value, dict) and value.get("team_id"):
        return value
    if isinstance(match_team, dict) and match_team.get("team_id"):
        return match_team
    return value


def _manifest_path(root: Path, edition: str, date: str, match_id: str | None = None) -> Path:
    if not match_id:
        return poster_manifest_path(root, edition, date)
    safe_match = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in match_id)
    return edition_data_root(root, edition) / "reports" / "posters" / f"{date}-{safe_match}-poster-manifest.json"


def _prompt_text_path(root: Path, edition: str, date: str, match_id: str | None = None) -> Path:
    if not match_id:
        return edition_data_root(root, edition) / "reports" / "posters" / f"{date}-poster-prompts.txt"
    safe_match = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in match_id)
    return edition_data_root(root, edition) / "reports" / "posters" / f"{date}-{safe_match}-poster-prompt.txt"


def _format_prompt_text(poster_items: list[dict]) -> str:
    if not poster_items:
        return "未找到可生成海报的预测项。\n"
    blocks = []
    for item in poster_items:
        header = f"# {item.get('match_id', '')} {item.get('home_team', '')} vs {item.get('away_team', '')}".strip()
        prompt = str(item.get("prompt", "")).strip()
        negative_prompt = str(item.get("negative_prompt", "")).strip()
        block = f"{header}\n\n{prompt}"
        if negative_prompt:
            block += f"\n\n负面提示词：\n{negative_prompt}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks) + "\n"


def _load_rosters_by_team_id(root: Path, edition: str) -> dict[str, dict]:
    roster_path = edition_data_root(root, edition) / "rosters" / "fifa-squad-lists.json"
    roster = load_json(roster_path, {})
    teams = roster.get("teams", []) if isinstance(roster, dict) else []
    result = {}
    for team in teams:
        if not isinstance(team, dict):
            continue
        team_id = str(team.get("team_id") or team.get("code") or "").lower()
        if team_id:
            result[team_id] = team
    return result


def _format_player(player: dict) -> str:
    shirt = player.get("shirt_number")
    position = str(player.get("position") or "").strip()
    name = str(player.get("player_name") or player.get("name_on_shirt") or "").strip()
    club = str(player.get("club") or "").strip()
    shirt_text = f"{shirt}号" if shirt not in (None, "") else "号码未知"
    main = " ".join(part for part in [shirt_text, position, name] if part)
    return f"{main} ({club})" if club else main


def _format_roster(team: dict | None) -> str:
    players = team.get("players", []) if isinstance(team, dict) else []
    if not players:
        return "官方阵容未找到，请生成前先补齐该队 roster。"
    return "\n".join(f"- {_format_player(player)}" for player in players if isinstance(player, dict))


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _kickoff_text(kickoff_at: str, timezone_name: str) -> str:
    kickoff = _parse_datetime(kickoff_at)
    if not kickoff:
        return "开赛时间待确认"
    local = kickoff.astimezone(ZoneInfo(timezone_name))
    return f"{local.month}月{local.day}日 {local:%H:%M} 开赛"


def prompt_for_prediction(item: dict) -> str:
    home = _team_name(item.get("home_team"))
    away = _team_name(item.get("away_team"))
    prediction = item["prediction"]
    score = prediction["score"]
    result = prediction.get("result") or prediction.get("predicted_outcome", "")
    return (
        "Create a polished Chinese editorial sports prediction poster. "
        f"Match: {home} vs {away}. "
        f"Prediction: {score['home']}-{score['away']}, result {result}, "
        f"total goals {prediction['total_goals']}, confidence {prediction['confidence']}. "
        "Use bold football matchday typography, clear score hierarchy, subtle pitch texture, "
        "national-team color accents, and a small visible disclaimer: 娱乐预测，非投注建议. "
        "Do not include betting odds, stake amounts, guaranteed-win wording, or sportsbook branding."
    )


def _showdown_copy(home: str, away: str, prediction_item: dict) -> tuple[str, str]:
    play_card = prediction_item.get("play_card", {}) if isinstance(prediction_item.get("play_card"), dict) else {}
    hook = str(play_card.get("match_hook") or "").strip()
    if hook:
        return "大战一触即发", hook
    return "大战一触即发", f"{home} 与 {away} 正面交锋，谁能抢下关键三分？"


def prompt_for_showdown_prediction(
    *,
    item: dict,
    home_roster: dict | None,
    away_roster: dict | None,
    timezone_name: str,
) -> tuple[str, str]:
    home = _team_name(item.get("home_team"))
    away = _team_name(item.get("away_team"))
    prediction = item["prediction"]
    score = prediction["score"]
    kickoff = _kickoff_text(str(item.get("kickoff_at") or ""), timezone_name)
    atmosphere, support = _showdown_copy(home, away, item)
    home_players = _format_roster(home_roster)
    away_players = _format_roster(away_roster)
    prompt = f"""为世界杯比赛「{home} vs {away}」制作一张高燃赛前预测宣传海报。

海报必须准确出现这些中文文字：
主标题：{home} VS {away}
比赛时间：{kickoff}
氛围文案：{atmosphere}
副文案：AI 赛前预测｜胜负趋势分析
辅助文案：{support}
预测信息：娱乐预测 {score['home']}-{score['away']}，信心等级 {prediction['confidence']}

重要要求：
海报中必须出现 {home} 和 {away} 两支球队的完整阵容，不要只生成少数几个人。每队所有指定球员都要出现在画面中，采用完整球队大合影式战争海报构图：核心球员在前排，其他球员在中后排形成阵列。所有球员都必须是真实球员形象，根据公开比赛照片中的真实面部特征、发型、肤色、身材比例、球衣号码和比赛气质生成，不要生成虚构球员。

{home} 完整球员名单：
{home_players}

{away} 完整球员名单：
{away_players}

构图：
竖版 9:16。左侧是 {home} 完整阵容，右侧是 {away} 完整阵容。两队面对面站立，像开赛前最后一刻，前排球员身体前倾、眼神紧张，后排球员形成密集阵列。画面中央放置足球，足球附近有草屑、尘土、烟雾和强烈光影碰撞。

视觉氛围：
夜晚世界杯体育场，强烈探照灯，满场观众，草坪，国家队颜色的烟雾与光效。整体是电影级体育海报、真实足球摄影、商业赛事主视觉、高对比度、热血、紧张、压迫感、赛前大战氛围。

文字设计：
顶部放置大标题「{home} VS {away}」
标题下方放置「{kickoff}」
中部或底部放置「{atmosphere}」
底部放置「AI 赛前预测｜胜负趋势分析」
文字要清晰、简洁、像专业体育赛事海报，不要乱码，不要错字，不要出现错误时间。

风格关键词：
ultra realistic sports poster, cinematic football photography, official tournament atmosphere, dramatic stadium lighting, realistic faces, full squad lineup, intense face-off, high detail, professional commercial poster, epic matchday poster

避免：
不要生成虚构球员，不要只出现几个人，不要遗漏完整阵容，不要重复同一个球员，不要错误球衣颜色，不要错误国旗，不要乱码文字，不要卡通风，不要游戏渲染风，不要塑料皮肤，不要脸部畸形，不要多手多脚，不要把 {home} 球员放到 {away} 阵容里，不要把 {away} 球员放到 {home} 阵容里。"""
    return prompt, NEGATIVE_PROMPT_SHOWDOWN


def build_poster_manifest(
    *,
    root: Path,
    edition: str,
    date: str,
    report_path: Path | None = None,
    match_id: str | None = None,
    now: str | None = None,
    style: str = "prediction",
    timezone_name: str = "Asia/Shanghai",
) -> dict:
    generated_at = iso_now(now)
    prompt_text_path = _prompt_text_path(root, edition, date, match_id)
    report_path = report_path or (edition_data_root(root, edition) / "reports" / "daily-predictions" / f"{date}.json")
    report = load_json(report_path, {})
    rosters_by_team_id = _load_rosters_by_team_id(root, edition) if style == "showdown" else {}
    ledger = load_match_ledger(root, edition) if style == "showdown" else {"matches": []}
    matches_by_id = {match.get("match_id"): match for match in ledger.get("matches", []) if isinstance(match, dict)}
    poster_items = []
    for prediction in report.get("predictions", []):
        if match_id and prediction.get("match_id") != match_id:
            continue
        match = matches_by_id.get(prediction.get("match_id"), {})
        home_team = _prediction_team(prediction.get("home_team"), match.get("home_team") if isinstance(match, dict) else {})
        away_team = _prediction_team(prediction.get("away_team"), match.get("away_team") if isinstance(match, dict) else {})
        home = _team_name(home_team)
        away = _team_name(away_team)
        score = prediction["prediction"]["score"]
        home_team_id = _team_id(home_team)
        away_team_id = _team_id(away_team)
        prompt = prompt_for_prediction(prediction)
        negative_prompt = ""
        kickoff_text = ""
        roster_counts = {}
        if style == "showdown":
            home_roster = rosters_by_team_id.get(home_team_id)
            away_roster = rosters_by_team_id.get(away_team_id)
            prompt, negative_prompt = prompt_for_showdown_prediction(
                item=prediction,
                home_roster=home_roster,
                away_roster=away_roster,
                timezone_name=timezone_name,
            )
            kickoff_text = _kickoff_text(str(prediction.get("kickoff_at") or ""), timezone_name)
            roster_counts = {
                home_team_id or home: len(home_roster.get("players", [])) if isinstance(home_roster, dict) else 0,
                away_team_id or away: len(away_roster.get("players", [])) if isinstance(away_roster, dict) else 0,
            }
        poster_items.append(
            {
                "poster_id": f"{prediction['match_id']}:prediction-poster",
                "match_id": prediction["match_id"],
                "style": style,
                "home_team": home,
                "away_team": away,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "prediction": prediction["prediction"],
                "kickoff_at": prediction.get("kickoff_at", ""),
                "kickoff_text": kickoff_text,
                "roster_counts": roster_counts,
                "disclaimer": DISCLAIMER,
                "prompt": prompt,
                "prompt_text_path": str(prompt_text_path),
                "negative_prompt": negative_prompt,
                "required_text": [
                    home,
                    away,
                    f"{score['home']}-{score['away']}",
                    "娱乐预测，非投注建议",
                ]
                + ([kickoff_text, "AI 赛前预测｜胜负趋势分析"] if kickoff_text else []),
                "forbidden_text": ["投注金额", "稳赢", "稳胆", "下注", "odds", "sportsbook"],
            }
        )
    manifest = {
        "version": 1,
        "edition": edition,
        "date": date,
        "generated_at": generated_at,
        "mode": "worldcup-prediction-poster-prompt-manifest",
        "source_report": str(report_path),
        "manifest_path": str(_manifest_path(root, edition, date, match_id)),
        "prompt_text_path": str(prompt_text_path),
        "match_id_filter": match_id or "",
        "style": style,
        "timezone": timezone_name,
        "poster_items": poster_items,
        "summary": {"poster_items": len(poster_items)},
        "safety_invariants": [
            "poster_prompt_derived_from_structured_prediction_report",
            "poster_disclaimer_required",
            "poster_must_not_include_betting_language",
            "user_facing_image2_prompt_is_plain_text",
        ],
    }
    write_text(prompt_text_path, _format_prompt_text(poster_items))
    write_json(Path(manifest["manifest_path"]), manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--edition", required=True)
    build.add_argument("--date", required=True)
    build.add_argument("--report-path")
    build.add_argument("--match-id")
    build.add_argument("--now")
    build.add_argument("--style", choices=["prediction", "showdown"], default="prediction")
    build.add_argument("--timezone", dest="timezone_name", default="Asia/Shanghai")
    build.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_poster_manifest(
        root=Path(args.root).resolve(),
        edition=args.edition,
        date=args.date,
        report_path=Path(args.report_path).resolve() if args.report_path else None,
        match_id=args.match_id,
        now=args.now,
        style=args.style,
        timezone_name=args.timezone_name,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
