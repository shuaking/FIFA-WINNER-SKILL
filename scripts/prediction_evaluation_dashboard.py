#!/usr/bin/env python3
"""Aggregate post-match prediction evaluations into a review dashboard."""

from __future__ import annotations

import argparse
import json
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


def build_evaluation_dashboard(*, root: Path, edition: str, now: str | None = None) -> dict:
    generated_at = iso_now(now)
    days: list[dict] = []
    totals = {
        "evaluated_matches": 0,
        "blocked_missing_final_score": 0,
        "result_hits": 0,
        "score_hits": 0,
        "total_goals_hits": 0,
    }
    confidence_buckets: dict[str, dict] = {}

    for path in collect_evaluation_files(root, edition):
        payload = load_json(path)
        if payload.get("mode") != "worldcup-prediction-post-match-evaluation":
            continue
        summary = payload.get("summary", {})
        day = {
            "date": payload.get("date", path.stem),
            "path": str(path),
            "evaluated_matches": int(summary.get("evaluated_matches", 0) or 0),
            "blocked_missing_final_score": int(summary.get("blocked_missing_final_score", 0) or 0),
            "result_hits": int(summary.get("result_hits", 0) or 0),
            "score_hits": int(summary.get("score_hits", 0) or 0),
            "total_goals_hits": int(summary.get("total_goals_hits", 0) or 0),
        }
        days.append(day)
        for key in totals:
            totals[key] += day[key]
        summary_calibration = summary.get("confidence_calibration", {})
        if isinstance(summary_calibration, dict):
            for level, bucket in summary_calibration.items():
                if isinstance(bucket, dict):
                    _merge_confidence_bucket(
                        confidence_buckets.setdefault(_confidence_level(level), _empty_confidence_bucket()),
                        bucket,
                    )
        else:
            for level, bucket in _confidence_from_evaluations(payload.get("evaluations", [])).items():
                _merge_confidence_bucket(
                    confidence_buckets.setdefault(level, _empty_confidence_bucket()),
                    bucket,
                )
        if not summary_calibration:
            for level, bucket in _confidence_from_evaluations(payload.get("evaluations", [])).items():
                _merge_confidence_bucket(
                    confidence_buckets.setdefault(level, _empty_confidence_bucket()),
                    bucket,
                )

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
