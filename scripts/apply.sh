#!/usr/bin/env bash
# Apply auto-model-router: install user skills, copy demo, open savings dashboard.
# Running this script is how the dashboard auto-starts. Dropping SKILL.md alone does not.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$ROOT/skills/auto-model-router/SKILL.md"
DEMO_SRC="$ROOT/demo"
WEEKLY_SRC="$ROOT/scripts/weekly_review.py"

usage() {
  cat <<'USAGE'
Usage: ./scripts/apply.sh [options]

Dashboard:
  (default)              Open dashboard unless preference says no
  --no-open              Do not open browser; set openDashboardOnApply=false
  --open                 Open browser; set openDashboardOnApply=true

Weekly review (opt-in; local usage log only — not vendor billing):
  --enable-weekly-review   Set weeklyReview=true
  --disable-weekly-review  Set weeklyReview=false
  --install-schedule       Install a user cron/launchd-style weekly job (explicit opt-in)
  --uninstall-schedule     Remove the weekly schedule installed by this script

Preference file: ~/.auto-model-router/config.json
  { "openDashboardOnApply": true, "weeklyReview": false }

Run a review anytime:
  python3 ~/.auto-model-router/weekly_review.py --force
USAGE
}

FLAG_OPEN=""
FLAG_WEEKLY=""
INSTALL_SCHEDULE=0
UNINSTALL_SCHEDULE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-open)
      FLAG_OPEN=0
      shift
      ;;
    --open)
      FLAG_OPEN=1
      shift
      ;;
    --enable-weekly-review)
      FLAG_WEEKLY=1
      shift
      ;;
    --disable-weekly-review)
      FLAG_WEEKLY=0
      shift
      ;;
    --install-schedule)
      INSTALL_SCHEDULE=1
      shift
      ;;
    --uninstall-schedule)
      UNINSTALL_SCHEDULE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

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
CONFIG_FILE="$AMR_HOME/config.json"
WEEKLY_DEST="$AMR_HOME/weekly_review.py"
CRON_MARKER="# auto-model-router-weekly-review"

# Merge one boolean key into config.json without wiping sibling keys.
set_config_bool() {
  local key="$1"
  local value="$2" # true | false
  mkdir -p "$AMR_HOME"
  python3 - "$CONFIG_FILE" "$key" "$value" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3].lower() == "true"
cfg = {"openDashboardOnApply": True, "weeklyReview": False}
if path.is_file():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            cfg.update(data)
    except (OSError, json.JSONDecodeError):
        pass
cfg[key] = val
# Normalize known keys to bools when present
for k in ("openDashboardOnApply", "weeklyReview"):
    if k in cfg:
        cfg[k] = bool(cfg[k])
path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
print(f"  preference → {path} ({key}={'true' if val else 'false'})")
PY
}

read_config_bool() {
  # Args: key default(true|false). Prints 1 or 0.
  local key="$1"
  local default="$2"
  python3 - "$CONFIG_FILE" "$key" "$default" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
default = sys.argv[3].lower() == "true"
val = default
if path.is_file():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and key in data:
            val = bool(data[key])
    except (OSError, json.JSONDecodeError):
        pass
print(1 if val else 0)
PY
}

install_skill() {
  local dest_dir="$1"
  mkdir -p "$dest_dir"
  cp "$SKILL_SRC" "$dest_dir/SKILL.md"
  echo "  installed skill → $dest_dir/SKILL.md"
}

cron_command() {
  local py
  py="$(command -v python3 || command -v python || true)"
  if [[ -z "$py" ]]; then
    echo "error: python3 not found; cannot install schedule" >&2
    return 1
  fi
  # Mondays 09:00 local — --force so the job runs even if preference later flips;
  # preference still gates interactive "should I remind" behavior.
  printf '%s' "0 9 * * 1 $py $WEEKLY_DEST --force"
}

install_schedule() {
  if [[ ! -f "$WEEKLY_DEST" ]]; then
    echo "error: missing $WEEKLY_DEST (apply install first)" >&2
    return 1
  fi
  local line
  line="$(cron_command)" || return 1
  local tmp
  tmp="$(mktemp)"
  crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | grep -v "weekly_review.py" >"$tmp" || true
  printf '%s %s\n' "$line" "$CRON_MARKER" >>"$tmp"
  crontab "$tmp"
  rm -f "$tmp"
  echo "  installed weekly cron → Mondays 09:00 ($WEEKLY_DEST --force)"
  echo "  remove with: ./scripts/apply.sh --uninstall-schedule"
}

uninstall_schedule() {
  local tmp
  tmp="$(mktemp)"
  if crontab -l 2>/dev/null | grep -q "$CRON_MARKER\|weekly_review.py"; then
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | grep -v "weekly_review.py" >"$tmp" || true
    if [[ -s "$tmp" ]]; then
      crontab "$tmp"
    else
      crontab -r 2>/dev/null || true
    fi
    echo "  removed weekly cron entry"
  else
    echo "  no auto-model-router cron entry found"
  fi
  rm -f "$tmp"
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

if [[ -f "$WEEKLY_SRC" ]]; then
  cp "$WEEKLY_SRC" "$WEEKLY_DEST"
  chmod +x "$WEEKLY_DEST"
  echo "  weekly review → $WEEKLY_DEST"
fi

# Ensure config exists with defaults (do not wipe user values).
if [[ ! -f "$CONFIG_FILE" ]]; then
  mkdir -p "$AMR_HOME"
  printf '%s\n' '{
  "openDashboardOnApply": true,
  "weeklyReview": false
}' > "$CONFIG_FILE"
  echo "  created config → $CONFIG_FILE"
fi

# Empty usage log if missing (do not wipe an existing log).
USAGE_LOG="$LOGS_DEST/usage.jsonl"
if [[ ! -f "$USAGE_LOG" ]]; then
  : > "$USAGE_LOG"
  echo "  created empty log → $USAGE_LOG"
else
  echo "  kept existing log → $USAGE_LOG"
fi

# Persist preference flags (merge into config.json).
if [[ -n "$FLAG_OPEN" ]]; then
  if [[ "$FLAG_OPEN" -eq 1 ]]; then
    set_config_bool openDashboardOnApply true
  else
    set_config_bool openDashboardOnApply false
  fi
fi
if [[ -n "$FLAG_WEEKLY" ]]; then
  if [[ "$FLAG_WEEKLY" -eq 1 ]]; then
    set_config_bool weeklyReview true
  else
    set_config_bool weeklyReview false
  fi
fi

if [[ "$UNINSTALL_SCHEDULE" -eq 1 ]]; then
  uninstall_schedule
fi
if [[ "$INSTALL_SCHEDULE" -eq 1 ]]; then
  # Enabling review when explicitly scheduling is the least surprising default.
  set_config_bool weeklyReview true
  install_schedule
fi

SHOULD_OPEN="$(read_config_bool openDashboardOnApply true)"
if [[ -n "$FLAG_OPEN" ]]; then
  SHOULD_OPEN="$FLAG_OPEN"
fi

DASHBOARD="$DEMO_DEST/dashboard.html"
opened=0
if [[ "$SHOULD_OPEN" -eq 1 ]]; then
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
fi

WEEKLY_ON="$(read_config_bool weeklyReview false)"

echo
echo "Success: auto-model-router applied."
echo "  Skills: ~/.cursor, ~/.claude, ~/.codex (under skills/auto-model-router/)"
echo "  Dashboard: $DASHBOARD"
echo "  Config: $CONFIG_FILE"
if [[ "$SHOULD_OPEN" -eq 0 ]]; then
  echo "  Skipped opening the browser (--no-open or openDashboardOnApply=false)."
  echo "  Open the dashboard path above manually when you want it,"
  echo "  or re-run with --open to enable auto-open again."
elif [[ "$opened" -eq 1 ]]; then
  echo "  Opened the savings dashboard in your default browser."
else
  echo "  Could not auto-open a browser. Open the dashboard path above manually,"
  echo "  then click \"Load sample log\"."
fi
if [[ "$WEEKLY_ON" -eq 1 ]]; then
  echo "  Weekly review: enabled (local usage log only — not vendor billing)."
  echo "  Run: python3 $WEEKLY_DEST --force"
else
  echo "  Weekly review: disabled (opt-in). Enable: ./scripts/apply.sh --enable-weekly-review"
fi
echo
echo "Note: Cursor/Claude loading SKILL.md alone cannot open a GUI."
echo "      \"Apply\" means running this script so the dashboard auto-starts."
