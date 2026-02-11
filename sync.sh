#!/usr/bin/env bash
set -euo pipefail

BRANCH=$(git branch --show-current)
MSG="${1:-sync $(date '+%Y-%m-%d %H:%M:%S')}"

git add -A

if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi

git commit -m "$MSG"

if git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null 2>&1; then
  git push origin "$BRANCH"
else
  git push -u origin "$BRANCH"
fi

echo "Pushed to origin/$BRANCH"
