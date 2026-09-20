#!/usr/bin/env bash
# Apply auto-model-router: install user skills, copy demo, open savings dashboard.
# Running this script is how the dashboard auto-starts. Dropping SKILL.md alone does not.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$ROOT/skills/auto-model-router/SKILL.md"
DEMO_SRC="$ROOT/demo"

if [[ ! -f "$SKILL_SRC" ]]; then
  echo "error: missing skill at $SKILL_SRC" >&2
  exit 1
fi

HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
  echo "error: HOME is not set" >&2
  exit 1
fi

AMR_HOME="$HOME_DIR/.auto-model-router"
DEMO_DEST="$AMR_HOME/demo"
LOGS_DEST="$AMR_HOME/logs"

install_skill() {
  local dest_dir="$1"
  mkdir -p "$dest_dir"
  cp "$SKILL_SRC" "$dest_dir/SKILL.md"
  echo "  installed skill → $dest_dir/SKILL.md"
}

echo "Applying auto-model-router..."

# User-wide skills for common hosts (create dirs when reasonable).
install_skill "$HOME_DIR/.cursor/skills/auto-model-router"
install_skill "$HOME_DIR/.claude/skills/auto-model-router"
install_skill "$HOME_DIR/.codex/skills/auto-model-router"

# Demo + estimator + sample log under ~/.auto-model-router/demo
mkdir -p "$DEMO_DEST" "$LOGS_DEST"
cp "$DEMO_SRC/dashboard.html" "$DEMO_DEST/dashboard.html"
cp "$DEMO_SRC/savings_estimator.py" "$DEMO_DEST/savings_estimator.py"
cp "$DEMO_SRC/sample_usage_log.json" "$DEMO_DEST/sample_usage_log.json"
echo "  demo → $DEMO_DEST"

# Empty usage log if missing (do not wipe an existing log).
USAGE_LOG="$LOGS_DEST/usage.jsonl"
if [[ ! -f "$USAGE_LOG" ]]; then
  : > "$USAGE_LOG"
  echo "  created empty log → $USAGE_LOG"
else
  echo "  kept existing log → $USAGE_LOG"
fi

DASHBOARD="$DEMO_DEST/dashboard.html"
opened=0
case "$(uname -s)" in
  Darwin)
    if open "$DASHBOARD" 2>/dev/null; then opened=1; fi
    ;;
  *)
    if command -v xdg-open >/dev/null 2>&1; then
      if xdg-open "$DASHBOARD" >/dev/null 2>&1; then opened=1; fi
    elif command -v sensible-browser >/dev/null 2>&1; then
      if sensible-browser "$DASHBOARD" >/dev/null 2>&1; then opened=1; fi
    fi
    ;;
esac

echo
echo "Success: auto-model-router applied."
echo "  Skills: ~/.cursor, ~/.claude, ~/.codex (under skills/auto-model-router/)"
echo "  Dashboard: $DASHBOARD"
if [[ "$opened" -eq 1 ]]; then
  echo "  Opened the savings dashboard in your default browser."
else
  echo "  Could not auto-open a browser. Open the dashboard path above manually,"
  echo "  then click \"Load sample log\"."
fi
echo
echo "Note: Cursor/Claude loading SKILL.md alone cannot open a GUI."
echo "      \"Apply\" means running this script so the dashboard auto-starts."
