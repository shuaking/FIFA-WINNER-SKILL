#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="fifa-winner-skill"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${CODEX_HOME:-$HOME/.codex}/skills/$SKILL_NAME"

mkdir -p "$(dirname "$TARGET_DIR")"
rm -rf "$TARGET_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude ".git" \
    --exclude ".env" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude ".DS_Store" \
    --exclude "artifacts" \
    --exclude "tmp" \
    "$SOURCE_DIR/" "$TARGET_DIR/"
else
  mkdir -p "$TARGET_DIR"
  tar -C "$SOURCE_DIR" \
    --exclude ".git" \
    --exclude ".env" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude ".DS_Store" \
    --exclude "artifacts" \
    --exclude "tmp" \
    -cf - . | tar -C "$TARGET_DIR" -xf -
fi

echo "Installed $SKILL_NAME to $TARGET_DIR"
