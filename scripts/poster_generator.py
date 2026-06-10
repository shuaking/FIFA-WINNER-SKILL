#!/usr/bin/env python3
"""Generate prediction posters from a poster manifest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import backend_command_env, load_json, poster_result_path, project_root, write_json  # noqa: E402


def generate_posters(*, root: Path, manifest_path: Path, backend: str) -> dict:
    manifest = load_json(manifest_path, {})
    date = str(manifest.get("date", "unknown-date"))
    edition = str(manifest.get("edition", "unknown-edition"))
    env_name = backend_command_env(backend)
    command_template = os.environ.get(env_name, "").strip()
    result_path = poster_result_path(root, edition, date, backend)

    if not command_template:
        result = {
            "version": 1,
            "edition": edition,
            "date": date,
            "backend": backend,
            "status": "blocked_missing_backend",
            "generated_at": manifest.get("generated_at", ""),
            "manifest_path": str(manifest_path),
            "result_path": str(result_path),
            "summary": {
                "poster_items": len(manifest.get("poster_items", [])),
                "images_generated": 0,
                "images_blocked": len(manifest.get("poster_items", [])),
            },
            "blockers": [f"missing_backend_command_env:{env_name}"],
            "outputs": [],
            "safety_invariants": [
                "missing_image_backend_blocks_generation_instead_of_faking_success",
                "poster_outputs_must_keep_manifest_provenance",
            ],
        }
        write_json(result_path, result)
        return result

    outputs = []
    output_dir = project_root(root) / "artifacts" / "editions" / edition / "posters" / date
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest.get("poster_items", []):
        out_path = output_dir / f"{item['match_id']}-{backend}.png"
        command = command_template.format(prompt=item["prompt"], output=str(out_path), poster_id=item["poster_id"])
        completed = subprocess.run(command, shell=True, text=True, capture_output=True, check=False)
        outputs.append(
            {
                "poster_id": item["poster_id"],
                "match_id": item["match_id"],
                "output_path": str(out_path) if completed.returncode == 0 and out_path.exists() else "",
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )

    images_generated = sum(1 for output in outputs if output.get("output_path"))
    result = {
        "version": 1,
        "edition": edition,
        "date": date,
        "backend": backend,
        "status": "generated" if images_generated == len(outputs) else "partial",
        "manifest_path": str(manifest_path),
        "result_path": str(result_path),
        "summary": {
            "poster_items": len(outputs),
            "images_generated": images_generated,
            "images_blocked": len(outputs) - images_generated,
        },
        "outputs": outputs,
        "safety_invariants": ["poster_outputs_keep_manifest_provenance"],
    }
    write_json(result_path, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--manifest", required=True)
    generate.add_argument("--backend", default="image2")
    generate.add_argument("--root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = generate_posters(root=Path(args.root).resolve(), manifest_path=Path(args.manifest).resolve(), backend=args.backend)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "blocked_missing_backend" else 2


if __name__ == "__main__":
    raise SystemExit(main())
