#!/usr/bin/env bash
# clean-devin.sh
# Removes Devin / Cognition AI references from the local working tree.
# Dry-run by default. Run with --force to actually apply changes.
# This does NOT rewrite Git history (see instructions inside for history cleanup).

set -euo pipefail

DRY_RUN=1
if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
  DRY_RUN=0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "Devin/Cognition cleanup"
echo "Mode: $([[ $DRY_RUN -eq 1 ]] && echo 'DRY-RUN (no changes)' || echo 'FORCE (will modify files)')"
echo "Root: $ROOT"
echo ""

# Directories commonly created by Devin/Cognition tooling
DEVIN_DIRS=(
  ".devin"
  ".agents"
  ".cognition"
)

for d in "${DEVIN_DIRS[@]}"; do
  if [[ -d "$d" ]]; then
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[DRY-RUN] Would remove directory: $d"
    else
      echo "[DELETE] $d"
      rm -rf "$d"
    fi
  fi
done

# Search for Devin/Cognition strings in project files (excluding .git, deps, binaries)
PATTERNS=(
  "Devin"
  "devin"
  "Cognition"
  "cognition"
  "devin-ai"
  "devin-ai-integration"
  "Generated with \\[Devin\\]"
)

EXCLUDES="--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=dist"

if command -v rg >/dev/null 2>&1; then
  MATCHER=(rg -n --hidden $EXCLUDES -F "dummy")
  for p in "${PATTERNS[@]}"; do
    MATCHER+=("-e" "$p")
  done
else
  MATCHER=(grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=dist)
  for p in "${PATTERNS[@]}"; do
    MATCHER+=("-e" "$p")
  done
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "[DRY-RUN] Files matching Devin/Cognition references:"
  "${MATCHER[@]}" || true
  echo ""
  echo "Review the list above. Run again with:"
  echo "  bash clean-devin.sh --force"
else
  echo "[DELETE-LINES] Removing Devin/Cognition references from source files..."
  # Only edit plain-text files; use sed carefully.
  find . -type f \
    -not -path './.git/*' \
    -not -path './node_modules/*' \
    -not -path './venv/*' \
    -not -path './.venv/*' \
    -not -path './__pycache__/*' \
    -not -path './dist/*' \
    -not -path './.gitignore' \
    \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.md' -o -name '*.txt' -o -name '*.json' -o -name '*.py' -o -name '*.toml' -o -name '*.sh' -o -name '*.yml' -o -name '*.yaml' \) \
    -print0 | xargs -0 -I{} sed -i '/Devin\|Cognition\|devin-ai\|Generated with \[Devin\]/Id' "{}" 2>/dev/null || true

  # Remove the empty "Generated with Devin" lines that sed may leave behind
  find . -type f \
    -not -path './.git/*' \
    -not -path './node_modules/*' \
    \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.md' -o -name '*.txt' -o -name '*.py' -o -name '*.yml' -o -name '*.yaml' \) \
    -print0 | xargs -0 -I{} sed -i '/^Co-Authored-By: Devin/d' "{}" 2>/dev/null || true

  echo ""
  echo "Done. Check the result with:"
  echo "  git status"
fi

echo ""
echo "To clean Git history as well, install git-filter-repo and run:"
echo "  git filter-repo --replace-text <(echo 'Devin==>') --force"
echo "Or use git filter-branch. Be careful: this rewrites history."

# Self-destruct only when we really applied the cleanup
if [[ $DRY_RUN -eq 0 ]]; then
  SCRIPT_ABS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  if [[ -f "$SCRIPT_ABS" ]]; then
    echo ""
    echo "[DELETE] Self-destructing: $SCRIPT_ABS"
    rm -f "$SCRIPT_ABS"
  fi
fi
