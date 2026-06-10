#!/usr/bin/env python3
"""Plan or write raw snapshots for registered World Cup sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import iso_now, load_json, raw_edition_root, write_json  # noqa: E402


def default_fetcher(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "fifa-winner-skill/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def extension_for_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".pdf", ".json", ".html", ".txt", ".csv"}:
        return suffix
    return ".bin"


def find_source(root: Path, edition: str, source_id: str) -> dict:
    registry = load_json(raw_edition_root(root, edition) / "source-registry.json", {"sources": []})
    for source in registry.get("sources", []):
        if source.get("source_id") == source_id:
            return source
    raise ValueError(f"unknown source_id: {source_id}")


def snapshot_source(
    *,
    root: Path,
    edition: str,
    source_id: str,
    mode: str,
    now: str | None = None,
    fetcher=default_fetcher,
) -> dict:
    generated_at = iso_now(now)
    source = find_source(root, edition, source_id)
    url = str(source.get("url", "")).strip()
    snapshot_dir = raw_edition_root(root, edition) / "snapshots"
    manifest_dir = raw_edition_root(root, edition) / "evidence-packets"
    date_slug = generated_at[:10]
    extension = extension_for_url(url)
    snapshot_path = snapshot_dir / f"{source_id}-{date_slug}{extension}"
    manifest_path = manifest_dir / f"{source_id}-{date_slug}-snapshot-manifest.json"

    if mode == "plan":
        result = {
            "version": 1,
            "edition": edition,
            "source_id": source_id,
            "mode": "source-snapshot-plan",
            "generated_at": generated_at,
            "status": "ready_for_apply" if url else "blocked_missing_url",
            "url": url,
            "snapshot_path": str(snapshot_path),
            "manifest_path": str(manifest_path),
            "summary": {"fetches_performed": 0, "raw_writes_performed": 0},
            "safety_invariants": ["plan_mode_does_not_fetch_or_write_raw_sources"],
        }
        return result

    if mode != "apply":
        raise ValueError(f"unsupported mode: {mode}")
    if not url:
        result = {
            "version": 1,
            "edition": edition,
            "source_id": source_id,
            "mode": "source-snapshot-apply",
            "generated_at": generated_at,
            "status": "blocked_missing_url",
            "url": url,
            "snapshot_path": str(snapshot_path),
            "manifest_path": str(manifest_path),
            "summary": {"fetches_performed": 0, "raw_writes_performed": 0},
            "blockers": ["source_url_missing"],
            "safety_invariants": [
                "blocked_missing_url_does_not_fetch_source",
                "missing_source_url_is_recorded_in_manifest",
            ],
        }
        write_json(manifest_path, result)
        return result

    try:
        payload = fetcher(url)
    except Exception as exc:  # noqa: BLE001 - source fetch failures must be recorded as evidence.
        result = {
            "version": 1,
            "edition": edition,
            "source_id": source_id,
            "source_name": source.get("name", ""),
            "source_tier": source.get("tier", ""),
            "url": url,
            "generated_at": generated_at,
            "mode": "source-snapshot-apply",
            "status": "blocked_fetch_failed",
            "snapshot_path": str(snapshot_path),
            "manifest_path": str(manifest_path),
            "allowed_use": source.get("allowed_use", ""),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "summary": {"fetches_performed": 1, "raw_writes_performed": 1},
            "blockers": ["source_fetch_failed"],
            "safety_invariants": [
                "failed_source_fetches_write_manifest_instead_of_silent_success",
                "blocked_fetch_failed_does_not_create_raw_snapshot_bytes",
            ],
        }
        write_json(manifest_path, result)
        return result

    digest = hashlib.sha256(payload).hexdigest()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(payload)
    manifest = {
        "version": 1,
        "edition": edition,
        "source_id": source_id,
        "source_name": source.get("name", ""),
        "source_tier": source.get("tier", ""),
        "url": url,
        "generated_at": generated_at,
        "mode": "source-snapshot-apply",
        "status": "snapshot_written",
        "snapshot_path": str(snapshot_path),
        "manifest_path": str(manifest_path),
        "bytes": len(payload),
        "sha256": digest,
        "allowed_use": source.get("allowed_use", ""),
        "summary": {"fetches_performed": 1, "raw_writes_performed": 2},
        "safety_invariants": [
            "raw_snapshot_preserves_original_source_bytes",
            "snapshot_manifest_records_source_url_tier_hash_and_allowed_use",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["plan", "apply"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--edition", required=True)
        cmd.add_argument("--source-id", required=True)
        cmd.add_argument("--now")
        cmd.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = snapshot_source(
        root=Path(args.root).resolve(),
        edition=args.edition,
        source_id=args.source_id,
        mode=args.command,
        now=args.now,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not str(result.get("status", "")).startswith("blocked") else 2


if __name__ == "__main__":
    raise SystemExit(main())
