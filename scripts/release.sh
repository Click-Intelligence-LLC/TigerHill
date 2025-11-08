#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <version> [title]"; exit 1
fi
VER="$1"             # e.g., v1.2.3
TITLE="${2:-TigerHill $VER}"

# Build (按需调整)
python -m pip install -U pip build >/dev/null
python -m build

# Changelog
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -z "$LAST_TAG" ]; then
  NOTES=$(git log --pretty=format:"* %s")
else
  NOTES=$(git log --pretty=format:"* %s" "${LAST_TAG}..HEAD")
fi

git pull --rebase
git add -A
git commit -m "chore: release $VER" || true
git tag -a "$VER" -m "Release $VER"
git push
git push origin "$VER"

# 需要 gh：brew install gh && gh auth login
gh release create "$VER" --title "$TITLE" --notes "$NOTES" dist/*
echo "✅ Released $VER"
