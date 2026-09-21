#!/usr/bin/env python3
"""Weekly review of the local auto-model-router usage log.

Summarizes tiers confirmed/overridden and illustrative relative-unit estimates
from ~/.auto-model-router/logs/usage.jsonl (or a project .auto-model-router/usage.jsonl).

Honest scope: this is a local log summary only. It does not read Cursor, Claude
Code, Codex, or any vendor billing/token API. cost_usd and token counts are
used when the log has them; otherwise the report labels illustrative relative units.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve()
for _base in (HERE.parent, *HERE.parents):
    if (_base / "auto_model_router.py").is_file():
        if str(_base) not in sys.path:
            sys.path.insert(0, str(_base))
        break

from auto_model_router import TIERS, summarize_usage  # noqa: E402

DEFAULT_CONFIG = {
    "openDashboardOnApply": True,
    "weeklyReview": False,
}


def amr_home() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
    if not home:
        raise SystemExit("error: HOME / USERPROFILE is not set")
    return Path(home) / ".auto-model-router"


def config_path() -> Path:
    return amr_home() / "config.json"


def default_usage_log() -> Path:
    return amr_home() / "logs" / "usage.jsonl"


def sample_log_candidates() -> List[Path]:
    here = Path(__file__).resolve()
    roots = [
        amr_home() / "demo" / "sample_usage_log.json",
        here.parent.parent / "demo" / "sample_usage_log.json",
    ]
    return roots


def load_config() -> Dict[str, Any]:
    path = config_path()
    cfg = dict(DEFAULT_CONFIG)
    if not path.is_file():
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cfg
    if isinstance(data, dict):
        cfg.update(data)
    return cfg


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    entries: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "tier" in obj:
            entries.append(obj)
    return entries


def load_sample_json(path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict) and "tier" in x]
    if isinstance(payload, dict):
        for key in ("decisions", "usage", "log", "entries"):
            raw = payload.get(key)
            if isinstance(raw, list):
                return [x for x in raw if isinstance(x, dict) and "tier" in x]
    return []


def filter_window(
    entries: List[Dict[str, Any]], *, days: int, now: datetime
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (in_window, missing_timestamp)."""
    start = now - timedelta(days=days)
    in_window: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    for item in entries:
        ts = parse_timestamp(item.get("timestamp"))
        if ts is None:
            missing.append(item)
            continue
        if start <= ts <= now:
            in_window.append(item)
    return in_window, missing


def summarize(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = summarize_usage(entries)
    hosts: Counter = Counter()
    for item in entries:
        tier = str(item.get("tier", "")).strip().lower()
        host = item.get("host")
        if tier in TIERS and host:
            hosts[str(host)] += 1
    summary["hosts"] = dict(hosts)
    return summary


def human_report(
    *,
    window_days: int,
    log_path: Path,
    summary: Dict[str, Any],
    used_sample: bool,
    missing_ts: int,
    now: datetime,
) -> str:
    start = now - timedelta(days=window_days)
    counts = ", ".join(
        f"{t}={summary['tasks_by_tier'][t]}"
        for t in TIERS
        if summary["tasks_by_tier"][t]
    ) or "none"
    lines = [
        "Auto Model Router — weekly review",
        f"Window: last {window_days} day(s) "
        f"({start.date().isoformat()} → {now.date().isoformat()}, local-aware timestamps)",
        f"Log: {log_path}",
        "",
        "Honest scope: local usage log only. Not live Cursor/Claude/Codex billing.",
        "Dollar figures appear only when a log row includes cost_usd.",
        "This review does not apply a price table. Tier-only rows stay on labeled illustrative relative units.",
        "",
    ]
    if used_sample:
        lines.extend([
            "Your usage log is empty (or missing). Showing the bundled sample log",
            "so you can see the review format — not your real routing history.",
            "",
        ])
    if summary["task_count"] == 0:
        lines.extend([
            "No routing decisions in this window.",
            "After confirmed runs, agents may append non-sensitive lines to usage.jsonl.",
            "See SKILL.md for the schema. Nothing is forced; weekly review stays opt-in.",
        ])
        return "\n".join(lines)

    lines.extend([
        f"Decisions in window: {summary['task_count']} ({counts})",
        f"Confirmed: {summary['confirmed_count']}  |  Overrides: {summary['override_count']} "
        f"({summary['override_rate_pct']}%)",
        f"Tokens logged: input={summary['input_tokens']} output={summary['output_tokens']}",
    ])
    if summary.get("measured_cost_usd") is not None:
        lines.append(f"Measured cost: ${summary['measured_cost_usd']:.6f}")
    else:
        lines.append("Measured cost: none")
    illustrative = summary.get("illustrative")
    if illustrative:
        lines.extend([
            f"Illustrative fallback: {illustrative['routed_relative_units']:.1f} relative units "
            f"({illustrative['entries']} tier-only row(s); not vendor prices)",
            f"Est. savings vs always-reasoning (illustrative rows only): "
            f"{illustrative['estimated_savings_vs_always_reasoning_pct']:.1f}%",
            f"Est. savings vs always-max (illustrative rows only): "
            f"{illustrative['estimated_savings_vs_always_max_pct']:.1f}%",
        ])
    if summary["hosts"]:
        host_bits = ", ".join(f"{h}={n}" for h, n in sorted(summary["hosts"].items()))
        lines.append(f"Hosts (when logged): {host_bits}")
    if missing_ts:
        lines.append(
            f"Note: {missing_ts} log line(s) lacked a parseable timestamp and were excluded."
        )
    lines.extend([
        "",
        "Percentages estimate this local log only; no savings are guaranteed.",
        "No vendor billing or token API was accessed.",
    ])
    return "\n".join(lines)


def open_dashboard(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False, capture_output=True)
            return True
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        for cmd in (("xdg-open", str(path)), ("sensible-browser", str(path))):
            try:
                subprocess.run(cmd, check=False, capture_output=True)
                return True
            except FileNotFoundError:
                continue
    except OSError:
        return False
    return False


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="run even when config weeklyReview is false",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="review window in days (default: 7)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="path to usage.jsonl (default: ~/.auto-model-router/logs/usage.jsonl)",
    )
    parser.add_argument(
        "--open",
        dest="open_dashboard",
        action="store_true",
        help="open the local savings dashboard after printing the review",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also print a JSON summary block",
    )
    args = parser.parse_args(argv[1:])

    if args.days < 1:
        print("error: --days must be >= 1", file=sys.stderr)
        return 2

    cfg = load_config()
    enabled = bool(cfg.get("weeklyReview", False))
    if not enabled and not args.force:
        print(
            "weekly review is disabled (config weeklyReview=false).\n"
            "Enable with: ./scripts/apply.sh --enable-weekly-review\n"
            "Or run once with: python3 scripts/weekly_review.py --force",
            file=sys.stderr,
        )
        return 1

    log_path = args.log or default_usage_log()
    entries = load_jsonl(log_path)
    used_sample = False
    if not entries:
        for candidate in sample_log_candidates():
            sample = load_sample_json(candidate)
            if sample:
                entries = sample
                used_sample = True
                log_path = candidate
                break

    now = datetime.now(timezone.utc).astimezone()
    in_window, missing = filter_window(entries, days=args.days, now=now)
    # Sample logs may span a fixed demo week; if filtering empties a sample, show all sample rows.
    if used_sample and not in_window and entries:
        in_window = entries
        missing = []

    summary = summarize(in_window)
    print(
        human_report(
            window_days=args.days,
            log_path=log_path,
            summary=summary,
            used_sample=used_sample,
            missing_ts=len(missing),
            now=now,
        )
    )

    if args.json:
        payload = {
            "window_days": args.days,
            "log": str(log_path),
            "used_sample": used_sample,
            "missing_timestamp_count": len(missing),
            "summary": summary,
            "rates_are": summary.get("rates_are"),
            "billing_api_accessed": False,
        }
        print("--- JSON ---")
        print(json.dumps(payload, indent=2))

    if args.open_dashboard:
        dash = amr_home() / "demo" / "dashboard.html"
        if not dash.is_file():
            dash = Path(__file__).resolve().parent.parent / "demo" / "dashboard.html"
        if open_dashboard(dash):
            print(f"\nOpened dashboard: {dash}")
        else:
            print(f"\nCould not open dashboard; open manually: {dash}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
