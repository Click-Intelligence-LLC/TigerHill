#!/usr/bin/env bash
set -euo pipefail
MSG="${1:-chore: update}"
CUR=$(git rev-parse --abbrev-ref HEAD)

git pull --rebase
git add -A
git commit -m "$MSG" || echo "No changes to commit."
git push -u origin "$CUR"
echo "✅ Updated $CUR"
