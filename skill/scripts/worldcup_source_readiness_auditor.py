#!/usr/bin/env python3
"""Audit source readiness for a World Cup edition without fetching data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import edition_data_root, iso_now, load_json, raw_edition_root, write_json  # noqa: E402


def audit_source_readiness(*, root: Path, edition: str, now: str | None = None) -> dict:
    generated_at = iso_now(now)
    registry = load_json(raw_edition_root(root, edition) / "source-registry.json", {"sources": []})
    items = []
    for source in registry.get("sources", []):
        url = str(source.get("url", "")).strip()
        tier = str(source.get("tier", "")).strip()
        status = "ready_for_manual_or_adapter_check" if url or source.get("source_id") == "national-fa-official-sites" else "limited_missing_url"
        warnings = []
        if tier == "T3":
            warnings.append("reference_only_no_unauthorized_bulk_scrape")
        if tier == "T2":
            warnings.append("api_requires_key_limit_license_record_before_use")
        items.append(
            {
                "source_id": source.get("source_id", ""),
                "tier": tier,
                "url": url,
                "role": source.get("role", ""),
                "status": status,
                "warnings": warnings,
                "fetch_performed": False,
                "write_performed": False,
            }
        )
    report = {
        "version": 1,
        "edition": edition,
        "generated_at": generated_at,
        "mode": "worldcup-source-readiness-no-fetch",
        "summary": {
            "sources": len(items),
            "t0_sources": sum(1 for item in items if item["tier"] == "T0"),
            "fetches_performed": 0,
            "writes_performed": 0,
        },
        "items": items,
        "safety_invariants": ["source_readiness_audit_does_not_fetch_or_snapshot_sources"],
    }
    write_json(edition_data_root(root, edition) / "source-readiness.json", report)
    return report


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
    result = audit_source_readiness(root=Path(args.root).resolve(), edition=args.edition, now=args.now)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
