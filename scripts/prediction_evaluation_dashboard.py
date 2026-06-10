#!/usr/bin/env python3
"""Aggregate post-match prediction evaluations into a review dashboard."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, load_json, wiki_edition_root, write_json, write_text  # noqa: E402


def _rate(hits: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return hits / total


def _confidence_level(value: object) -> str:
    level = str(value or "unknown").strip().lower()
    if level in {"low", "medium", "high"}:
        return level
    return "unknown"


def _empty_confidence_bucket() -> dict:
    return {"evaluated_matches": 0, "result_hits": 0}


def _merge_confidence_bucket(target: dict, source: dict) -> None:
    target["evaluated_matches"] += int(source.get("evaluated_matches", source.get("total", 0)) or 0)
    target["result_hits"] += int(source.get("result_hits", 0) or 0)


def _confidence_from_evaluations(evaluations: list[dict]) -> dict:
    buckets: dict[str, dict] = {}
    for item in evaluations:
        if item.get("status") != "evaluated":
            continue
        level = _confidence_level(
            item.get("prediction_confidence")
            or item.get("predicted_confidence")
            or item.get("confidence")
        )
        bucket = buckets.setdefault(level, _empty_confidence_bucket())
        bucket["evaluated_matches"] += 1
        if item.get("result_hit"):
            bucket["result_hits"] += 1
    return buckets


def _finalize_confidence_calibration(buckets: dict[str, dict]) -> dict:
    order = ["low", "medium", "high", "unknown"]
    result: dict[str, dict] = {}
    for level in order + sorted(level for level in buckets if level not in order):
        if level not in buckets:
            continue
        bucket = buckets[level]
        evaluated = int(bucket.get("evaluated_matches", 0) or 0)
        hits = int(bucket.get("result_hits", 0) or 0)
        result[level] = {
            "evaluated_matches": evaluated,
            "result_hits": hits,
            "result_hit_rate": _rate(hits, evaluated),
        }
    return result


def collect_evaluation_files(root: Path, edition: str) -> list[Path]:
    eval_dir = edition_data_root(root, edition) / "reports" / "evaluations"
    if not eval_dir.exists():
        return []
    return [
        path
        for path in sorted(eval_dir.glob("*.json"))
        if path.name not in {"aggregate-dashboard.json"} and not path.name.endswith("-dashboard.json")
    ]


def _dashboard_paths(root: Path, edition: str) -> tuple[Path, Path]:
    dashboard_path = edition_data_root(root, edition) / "reports" / "evaluations" / "aggregate-dashboard.json"
    markdown_path = wiki_edition_root(root, edition) / "reports" / "evaluations" / "aggregate-dashboard.md"
    return dashboard_path, markdown_path


def _empty_dashboard(*, root: Path, edition: str, generated_at: str) -> dict:
    dashboard_path, markdown_path = _dashboard_paths(root, edition)
    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-prediction-evaluation-dashboard",
        "status": "no_evaluations_yet",
        "dashboard_path": str(dashboard_path),
        "markdown_path": str(markdown_path),
        "summary": {
            "evaluation_days": 0,
            "evaluated_matches": 0,
            "blocked_missing_final_score": 0,
            "result_hits": 0,
            "score_hits": 0,
            "total_goals_hits": 0,
            "confidence_calibration": {},
        },
        "rates": {
            "result_hit_rate": 0.0,
            "score_hit_rate": 0.0,
            "total_goals_hit_rate": 0.0,
        },
        "days": [],
        "safety_invariants": [
            "evaluation_dashboard_reads_evaluations_without_rewriting_predictions",
            "locked_pre_match_reports_remain_unchanged",
        ],
    }


def _build_dashboard_from_evaluation_files(*, root: Path, edition: str, generated_at: str) -> dict:
    paths = collect_evaluation_files(root, edition)
    if not paths:
        return _empty_dashboard(root=root, edition=edition, generated_at=generated_at)

    totals = {
        "evaluated_matches": 0,
        "blocked_missing_final_score": 0,
        "result_hits": 0,
        "score_hits": 0,
        "total_goals_hits": 0,
    }
    days = []
    confidence_buckets: dict[str, dict] = {}

    for path in paths:
        payload = load_json(path, {})
        summary = payload.get("summary", {}) or {}
        evaluations = payload.get("evaluations", []) or []
        evaluated_from_items = sum(1 for item in evaluations if item.get("status") == "evaluated")
        blocked_from_items = sum(1 for item in evaluations if item.get("status") == "blocked_missing_final_score")

        evaluated = int(summary.get("evaluated_matches", evaluated_from_items) or 0)
        blocked = int(summary.get("blocked_missing_final_score", blocked_from_items) or 0)
        result_hits = int(summary.get("result_hits", sum(1 for item in evaluations if item.get("result_hit"))) or 0)
        score_hits = int(summary.get("score_hits", sum(1 for item in evaluations if item.get("score_hit"))) or 0)
        total_goals_hits = int(summary.get("total_goals_hits", sum(1 for item in evaluations if item.get("total_goals_hit"))) or 0)

        day = {
            "date": str(payload.get("date") or path.stem),
            "path": str(path),
            "evaluated_matches": evaluated,
            "blocked_missing_final_score": blocked,
            "result_hits": result_hits,
            "score_hits": score_hits,
            "total_goals_hits": total_goals_hits,
        }
        if evaluated or blocked or evaluations:
            days.append(day)

        totals["evaluated_matches"] += evaluated
        totals["blocked_missing_final_score"] += blocked
        totals["result_hits"] += result_hits
        totals["score_hits"] += score_hits
        totals["total_goals_hits"] += total_goals_hits

        file_buckets = _confidence_from_evaluations(evaluations)
        if file_buckets:
            for level, bucket in file_buckets.items():
                _merge_confidence_bucket(confidence_buckets.setdefault(level, _empty_confidence_bucket()), bucket)
        else:
            for level, bucket in (summary.get("confidence_calibration", {}) or {}).items():
                _merge_confidence_bucket(confidence_buckets.setdefault(level, _empty_confidence_bucket()), bucket)

    dashboard_path, markdown_path = _dashboard_paths(root, edition)
    evaluated_total = totals["evaluated_matches"]
    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-prediction-evaluation-dashboard",
        "status": "written" if days else "no_evaluations_yet",
        "dashboard_path": str(dashboard_path),
        "markdown_path": str(markdown_path),
        "summary": {
            "evaluation_days": len(days),
            **totals,
            "confidence_calibration": _finalize_confidence_calibration(confidence_buckets),
        },
        "rates": {
            "result_hit_rate": _rate(totals["result_hits"], evaluated_total),
            "score_hit_rate": _rate(totals["score_hits"], evaluated_total),
            "total_goals_hit_rate": _rate(totals["total_goals_hits"], evaluated_total),
        },
        "days": sorted(days, key=lambda item: item["date"]),
        "source": "evaluation_json_files",
        "safety_invariants": [
            "evaluation_dashboard_reads_evaluations_without_rewriting_predictions",
            "locked_pre_match_reports_remain_unchanged",
        ],
    }


def build_evaluation_dashboard(*, root: Path, edition: str, now: str | None = None) -> dict:
    generated_at = iso_now(now)
    db_path = edition_data_root(root, edition) / f"worldcup_{edition}.db"
    file_dashboard = _build_dashboard_from_evaluation_files(root=root, edition=edition, generated_at=generated_at)

    if not db_path.exists():
        return file_dashboard

    from worldcup_db import get_db_connection
    conn = get_db_connection(db_path)
    try:
        # 1. Fetch evaluated matches joined with predictions
        cursor = conn.execute("""
            SELECT
                e.match_id,
                e.actual_score_home,
                e.actual_score_away,
                p.predicted_score_home,
                p.predicted_score_away,
                p.confidence,
                p.prediction_date,
                e.is_result_correct,
                e.is_score_correct
            FROM evaluations e
            JOIN predictions p ON e.match_id = p.match_id
            ORDER BY p.prediction_date ASC, e.match_id ASC
        """)
        rows = cursor.fetchall()

        # 2. Fetch blocked / missing score count
        cursor_blocked = conn.execute("""
            SELECT COUNT(*)
            FROM predictions p
            LEFT JOIN evaluations e ON p.match_id = e.match_id
            WHERE e.match_id IS NULL
        """)
        blocked_count = cursor_blocked.fetchone()[0]
    except sqlite3.Error:
        return file_dashboard
    finally:
        conn.close()

    if not rows and file_dashboard.get("status") == "written":
        return file_dashboard

    # Process evaluated records
    totals = {
        "evaluated_matches": len(rows),
        "blocked_missing_final_score": blocked_count,
        "result_hits": 0,
        "score_hits": 0,
        "total_goals_hits": 0,
    }

    # Group by date
    days_map = {}
    confidence_buckets = {}

    for row in rows:
        m_id = row["match_id"]
        act_home = row["actual_score_home"]
        act_away = row["actual_score_away"]
        pred_home = row["predicted_score_home"]
        pred_away = row["predicted_score_away"]
        conf = _confidence_level(row["confidence"])
        p_date = row["prediction_date"] or "unknown-date"
        res_hit = bool(row["is_result_correct"])
        score_hit = bool(row["is_score_correct"])

        tg_hit = (act_home + act_away) == (pred_home + pred_away)

        if res_hit:
            totals["result_hits"] += 1
        if score_hit:
            totals["score_hits"] += 1
        if tg_hit:
            totals["total_goals_hits"] += 1

        # Day aggregation
        day_bucket = days_map.setdefault(p_date, {
            "date": p_date,
            "path": "",
            "evaluated_matches": 0,
            "blocked_missing_final_score": 0,
            "result_hits": 0,
            "score_hits": 0,
            "total_goals_hits": 0,
        })
        day_bucket["evaluated_matches"] += 1
        if res_hit:
            day_bucket["result_hits"] += 1
        if score_hit:
            day_bucket["score_hits"] += 1
        if tg_hit:
            day_bucket["total_goals_hits"] += 1

        # Confidence aggregation
        conf_bucket = confidence_buckets.setdefault(conf, _empty_confidence_bucket())
        conf_bucket["evaluated_matches"] += 1
        if res_hit:
            conf_bucket["result_hits"] += 1



    # Convert days_map to sorted list
    days = [days_map[d] for d in sorted(days_map.keys())]

    dashboard_path = edition_data_root(root, edition) / "reports" / "evaluations" / "aggregate-dashboard.json"
    markdown_path = wiki_edition_root(root, edition) / "reports" / "evaluations" / "aggregate-dashboard.md"
    evaluated = totals["evaluated_matches"]

    return {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-prediction-evaluation-dashboard",
        "status": "written" if days else "no_evaluations_yet",
        "dashboard_path": str(dashboard_path),
        "markdown_path": str(markdown_path),
        "summary": {
            "evaluation_days": len(days),
            **totals,
            "confidence_calibration": _finalize_confidence_calibration(confidence_buckets),
        },
        "rates": {
            "result_hit_rate": _rate(totals["result_hits"], evaluated),
            "score_hit_rate": _rate(totals["score_hits"], evaluated),
            "total_goals_hit_rate": _rate(totals["total_goals_hits"], evaluated),
        },
        "days": days,
        "safety_invariants": [
            "evaluation_dashboard_reads_evaluations_without_rewriting_predictions",
            "locked_pre_match_reports_remain_unchanged",
        ],
    }


def render_dashboard_markdown(dashboard: dict) -> str:
    summary = dashboard["summary"]
    rates = dashboard["rates"]
    lines = [
        "---",
        "type: report",
        f"edition: {dashboard['edition']}",
        "status: active",
        "---",
        "",
        f"# {dashboard['edition']} 世界杯预测复盘 Dashboard",
        "",
        "## 汇总",
        "",
        f"- 复盘日期数：{summary['evaluation_days']}",
        f"- 已评估比赛：{summary['evaluated_matches']}",
        f"- 缺赛果阻塞：{summary['blocked_missing_final_score']}",
        f"- 胜平负命中率：{rates['result_hit_rate']:.2%}",
        f"- 比分命中率：{rates['score_hit_rate']:.2%}",
        f"- 总进球命中率：{rates['total_goals_hit_rate']:.2%}",
        "",
        "## 每日",
        "",
    ]
    if not dashboard.get("days"):
        lines.append("- 暂无已评估比赛。")
    for day in dashboard.get("days", []):
        lines.append(
            f"- {day['date']}：评估 {day['evaluated_matches']} 场，胜平负 {day['result_hits']}，比分 {day['score_hits']}，总进球 {day['total_goals_hits']}"
        )
    lines.extend(["", "## 信心校准", ""])
    calibration = summary.get("confidence_calibration", {})
    if not calibration:
        lines.append("- 暂无可校准样本。")
    for level, bucket in calibration.items():
        lines.append(
            f"- {level}：评估 {bucket['evaluated_matches']} 场，胜平负命中 {bucket['result_hits']}，命中率 {bucket['result_hit_rate']:.2%}"
        )
    return "\n".join(lines).rstrip() + "\n"


def write_evaluation_dashboard(*, root: Path, edition: str, now: str | None = None) -> dict:
    dashboard = build_evaluation_dashboard(root=root, edition=edition, now=now)
    write_json(Path(dashboard["dashboard_path"]), dashboard)
    write_text(Path(dashboard["markdown_path"]), render_dashboard_markdown(dashboard))
    return dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--edition", required=True)
    write.add_argument("--now")
    write.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = write_evaluation_dashboard(root=Path(args.root).resolve(), edition=args.edition, now=args.now)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
