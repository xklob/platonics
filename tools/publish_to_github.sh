#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/../platonics-clone}"
if [[ -d "$DEST/.git" ]]; then
  echo "Using existing checkout: $DEST"
else
  git clone https://github.com/xklob/platonics.git "$DEST"
fi
# Copy only the files from this packaged collection, preserving unrelated repo files.
# tar is widely available on Windows/WSL/macOS/Linux and retains Unicode filenames.
(cd "$ROOT" && tar --exclude='__pycache__' --exclude='.git' --exclude='.DS_Store' -cf - .) | (cd "$DEST" && tar -xf -)
cd "$DEST"
python3 tools/verify_media.py
git add -A
if git diff --cached --quiet; then
  echo "No changes to push."
  exit 0
fi
git commit -m "Import all original geometry renders, reference stills and generator sources"
git push origin HEAD:master
echo "Published: https://github.com/xklob/platonics"
