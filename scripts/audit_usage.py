#!/usr/bin/env python3
"""Savings Desk audit — local usage.jsonl report.

Reads the opt-in local routing log and prints burns by host, heavy-tier use on
likely-light tasks, confirm/override rates, and relative units vs always-max.

Does not access vendor billing, quota, or token APIs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from amr_usage import (
    TIERS,
    filter_hosts,
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
    window_days: Optional[int],
    log_path: Path,
    summary: Dict[str, Any],
    used_sample: bool,
    missing_ts: int,
    cfg: Dict[str, Any],
    now: datetime,
    host_filter: List[str],
) -> str:
    lines = [
        "Auto Model Router — Savings Desk audit",
    ]
    if window_days:
        lines.append(
            f"Window: last {window_days} day(s) (ending {now.date().isoformat()}, local-aware timestamps)"
        )
    else:
        lines.append("Window: all dated entries in the log")
    lines.extend(
        [
            f"Log: {log_path}",
            f"Hosts filter: {', '.join(host_filter) if host_filter else 'all logged hosts'}",
            f"auditOptIn: {'true' if cfg.get('auditOptIn') else 'false'}",
            "",
            *honesty_lines(),
            "",
        ]
    )
    if used_sample:
        lines.extend(
            [
                "Your usage log is empty (or missing). Showing the bundled sample log",
                "so you can see the audit format — not your real routing history.",
                "",
            ]
        )
    if summary["task_count"] == 0:
        lines.extend(
            [
                "No routing decisions in this window.",
                "After you opt in, agents may append non-sensitive lines to usage.jsonl.",
                "See SKILL.md / docs/SAVINGS_DESK.md. Audit stays consent-gated.",
            ]
        )
        return "\n".join(lines)

    counts = ", ".join(
        f"{tier}={summary['tasks_by_tier'][tier]}"
        for tier in TIERS
        if summary["tasks_by_tier"][tier]
    ) or "none"
    lines.extend(
        [
            f"Decisions: {summary['task_count']} ({counts})",
            f"Confirm rate: {summary['confirm_rate_pct']:.1f}% "
            f"({summary['confirmed_count']}/{summary['task_count']})",
            f"Override rate: {summary['override_rate_pct']:.1f}% "
            f"({summary['override_count']}/{summary['task_count']})",
            f"Switch-downs (used lighter than suggested): {summary['switch_down_count']}",
            f"Switch-ups (used heavier than suggested): {summary['switch_up_count']}",
            f"Routed usage: {summary['routed_relative_units']:.1f} relative units",
            f"Est. savings vs always-reasoning: {summary['estimated_savings_vs_always_reasoning_pct']:.1f}%",
            f"Est. savings vs always-max: {summary['estimated_savings_vs_always_max_pct']:.1f}%",
            "",
            "Burns by host (relative units from the local log):",
        ]
    )
    burns = summary.get("burns_by_host") or {}
    if not burns:
        lines.append("  (no host field on these rows)")
    else:
        for host, stats in burns.items():
            tier_bits = ", ".join(
                f"{tier}={stats['tasks_by_tier'][tier]}"
                for tier in TIERS
                if stats["tasks_by_tier"][tier]
            )
            lines.append(
                f"  {host}: {stats['count']} task(s), "
                f"{stats['relative_units']:.1f} rel units ({tier_bits})"
            )

    lines.extend(
        [
            "",
            f"Heavy-tier use on likely-light tasks: {summary['heavy_on_light_count']}",
        ]
    )
    if summary["heavy_on_light_count"] == 0:
        lines.append("  (none, or task_kind was not logged)")
    else:
        for row in summary["heavy_on_light"][:12]:
            when = row.get("timestamp") or "unknown-time"
            lines.append(
                f"  {when}  {row.get('host')}  {row.get('tier')} on task_kind={row.get('task_kind')}"
            )
        extra = summary["heavy_on_light_count"] - 12
        if extra > 0:
            lines.append(f"  … {extra} more")

    if missing_ts:
        lines.append(
            f"\nNote: {missing_ts} log line(s) lacked a parseable timestamp and were excluded."
        )

    actions = next_actions(summary, cfg)
    lines.extend(["", "Next actions (automation complements the skill; it does not replace hosts):"])
    for action in actions:
        lines.append(f"  • {action['title']}")
        lines.append(f"      {action['detail']}")
    lines.extend(
        [
            "",
            "Apply local maps + boundary-gate flag + optional weekly digest:",
            "  python3 scripts/apply_recommendations.py",
            "Percentages estimate this local log only; no savings are guaranteed.",
            "No vendor billing or token API was accessed.",
        ]
    )
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
        help="run even when config auditOptIn is false",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="optional window in days (default: all dated entries)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="path to usage.jsonl or a JSON array (default: config usageLogPath or ~/.auto-model-router/logs/usage.jsonl)",
    )
    parser.add_argument(
        "--host",
        action="append",
        dest="hosts",
        default=None,
        help="filter to a host (repeatable). Default: all hosts in the log",
    )
    parser.add_argument(
        "--open",
        dest="open_dashboard",
        action="store_true",
        help="open the local Savings Desk dashboard after printing",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also print a JSON summary block",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="force the bundled sample log (labeled as sample)",
    )
    args = parser.parse_args(argv[1:])

    if args.days is not None and args.days < 1:
        print("error: --days must be >= 1", file=sys.stderr)
        return 2

    cfg = load_config()
    if not cfg.get("auditOptIn") and not args.force and not args.sample:
        print(
            "Savings Desk audit is disabled (config auditOptIn=false).\n"
            "This is consent-gated: nothing is collected until you opt in.\n"
            "Enable with: ./scripts/apply.sh --enable-audit\n"
            "Or run once with: python3 scripts/audit_usage.py --force\n"
            "Collected if you opt in: tier, host, confirmed/overridden, task_kind, gate, timestamp.\n"
            "Never collected: prompts, code, secrets, vendor credentials, billing APIs.",
            file=sys.stderr,
        )
        return 1

    log_path = resolve_usage_log(cfg, args.log)
    used_sample = False
    entries: List[Dict[str, Any]] = []
    if args.sample:
        used_sample = True
    else:
        entries = load_usage_entries(log_path)

    if args.sample or not entries:
        for candidate in sample_log_candidates():
            sample = load_usage_entries(candidate)
            if sample:
                entries = sample
                used_sample = True
                log_path = candidate
                break

    host_filter = list(args.hosts or [])
    entries = filter_hosts(entries, host_filter)

    now = datetime.now(timezone.utc).astimezone()
    in_window, missing = filter_window(entries, days=args.days, now=now)
    if used_sample and args.days is not None and not in_window and entries:
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
            cfg=cfg,
            now=now,
            host_filter=host_filter,
        )
    )

    if args.json:
        payload = {
            "window_days": args.days,
            "log": str(log_path),
            "used_sample": used_sample,
            "missing_timestamp_count": len(missing),
            "host_filter": host_filter,
            "summary": summary,
            "next_actions": next_actions(summary, cfg),
            "rates_are": "illustrative relative example units, not vendor prices",
            "billing_api_accessed": False,
        }
        print("--- JSON ---")
        print(json.dumps(payload, indent=2))

    if args.open_dashboard:
        home = Path.home() / ".auto-model-router" / "demo" / "dashboard.html"
        dash = home if home.is_file() else Path(__file__).resolve().parent.parent / "demo" / "dashboard.html"
        if open_dashboard(dash):
            print(f"\nOpened dashboard: {dash}")
        else:
            print(f"\nCould not open dashboard; open manually: {dash}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
