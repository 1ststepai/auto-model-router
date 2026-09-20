#!/usr/bin/env python3
"""Weekly review of the local auto-model-router usage log.

Summarizes tiers confirmed/overridden and illustrative relative-unit estimates
from ~/.auto-model-router/logs/usage.jsonl (or a project .auto-model-router/usage.jsonl).

Honest scope: this is a local log summary only. It does not read Cursor, Claude
Code, Codex, or any vendor billing/token API. Rates are example relative units.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from amr_usage import (
    TIERS,
    filter_window,
    honesty_lines,
    load_config,
    load_usage_entries,
    next_actions,
    resolve_usage_log,
    sample_log_candidates,
    summarize,
)


def human_report(
    *,
    window_days: int,
    log_path: Path,
    summary: Dict[str, Any],
    used_sample: bool,
    missing_ts: int,
    now: datetime,
    cfg: Dict[str, Any],
) -> str:
    counts = ", ".join(
        f"{t}={summary['tasks_by_tier'][t]}"
        for t in TIERS
        if summary["tasks_by_tier"][t]
    ) or "none"
    lines = [
        "Auto Model Router — weekly review",
        f"Window: last {window_days} day(s) "
        f"(ending {now.date().isoformat()}, local-aware timestamps)",
        f"Log: {log_path}",
        "",
        *honesty_lines(),
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
            "After authorized runs (confirm or auto-continue), agents may append non-sensitive lines to usage.jsonl.",
            "See SKILL.md for the schema. Nothing is forced; weekly review stays opt-in.",
        ])
        return "\n".join(lines)

    lines.extend([
        f"Decisions in window: {summary['task_count']} ({counts})",
        f"Confirmed: {summary['confirmed_count']}  |  Overrides: {summary['override_count']} "
        f"({summary['override_rate_pct']}%)  |  Confirm rate: {summary['confirm_rate_pct']}%",
        f"Routed usage: {summary['routed_relative_units']:.1f} relative units",
        f"Est. savings vs always-reasoning: {summary['estimated_savings_vs_always_reasoning_pct']:.1f}%",
        f"Est. savings vs always-max: {summary['estimated_savings_vs_always_max_pct']:.1f}%",
        f"Switch-downs: {summary['switch_down_count']}  |  Heavy-on-light: {summary['heavy_on_light_count']}",
    ])
    burns = summary.get("burns_by_host") or {}
    if burns:
        host_bits = ", ".join(
            f"{host}={stats['count']}/{stats['relative_units']:.0f}u"
            for host, stats in burns.items()
        )
        lines.append(f"Burns by host (count/rel units): {host_bits}")
    if missing_ts:
        lines.append(
            f"Note: {missing_ts} log line(s) lacked a parseable timestamp and were excluded."
        )
    actions = next_actions(summary, cfg)
    if actions:
        lines.append("Next: " + "; ".join(action["title"] for action in actions[:3]))
    lines.extend([
        "",
        "Full Savings Desk audit: python3 scripts/audit_usage.py --force",
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

    log_path = resolve_usage_log(cfg, args.log)
    entries = load_usage_entries(log_path)
    used_sample = False
    if not entries:
        for candidate in sample_log_candidates():
            sample = load_usage_entries(candidate)
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
            cfg=cfg,
        )
    )

    if args.json:
        payload = {
            "window_days": args.days,
            "log": str(log_path),
            "used_sample": used_sample,
            "missing_timestamp_count": len(missing),
            "summary": summary,
            "rates_are": "illustrative relative example units, not vendor prices",
            "billing_api_accessed": False,
        }
        print("--- JSON ---")
        print(json.dumps(payload, indent=2))

    if args.open_dashboard:
        dash = Path.home() / ".auto-model-router" / "demo" / "dashboard.html"
        if not dash.is_file():
            dash = Path(__file__).resolve().parent.parent / "demo" / "dashboard.html"
        if open_dashboard(dash):
            print(f"\nOpened dashboard: {dash}")
        else:
            print(f"\nCould not open dashboard; open manually: {dash}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
