#!/usr/bin/env python3
"""Savings Desk audit — active model first, then ask before optimizing.

Detects the host/tier/model you are using from local context (--current-tier,
config, recent usage.jsonl). Reports that pick's burn. Then asks whether to
optimize. Does not apply maps or flags.

Does not access vendor billing, quota, picker, or token APIs.
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
    active_burn,
    detect_active,
    filter_hosts,
    filter_window,
    codefriends_invite,
    honesty_lines,
    load_config,
    load_usage_entries,
    optimize_offers,
    optimize_prompt,
    resolve_usage_log,
    sample_log_candidates,
    summarize,
)


def _fmt_sources(sources: Dict[str, str]) -> str:
    if not sources:
        return "undeclared"
    return ", ".join(f"{key}←{value}" for key, value in sources.items())


def human_report(
    *,
    window_days: Optional[int],
    log_path: Path,
    summary: Dict[str, Any],
    burn: Dict[str, Any],
    used_sample: bool,
    missing_ts: int,
    cfg: Dict[str, Any],
    now: datetime,
    host_filter: List[str],
    active: Dict[str, Any],
) -> str:
    host = active.get("host") or "unknown host"
    tier = active.get("tier") or "unknown tier"
    model = active.get("model") or "undeclared picker label"
    lines = [
        "Auto Model Router — Savings Desk audit",
        "Flow: detect active model → audit that usage → ask “optimize?” → apply only if yes.",
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
            f"Hosts filter: {', '.join(host_filter) if host_filter else 'all logged hosts (active host highlighted)'}",
            f"auditOptIn: {'true' if cfg.get('auditOptIn') else 'false'}",
            "",
            *honesty_lines(),
            "",
            "1. Active model (what you are using now — local context, not a live meter)",
            f"  host:  {host}",
            f"  tier:  {tier}",
            f"  model: {model}",
            f"  source: {_fmt_sources(active.get('sources') or {})}",
            f"  {active.get('note')}",
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

    host_summary = burn.get("host_summary") or {}
    if host_summary.get("task_count"):
        host_counts = ", ".join(
            f"{t}={host_summary['tasks_by_tier'][t]}"
            for t in TIERS
            if host_summary["tasks_by_tier"][t]
        ) or "none"
        lines.extend(
            [
                f"2. Burn for active host ({host})",
                f"  Decisions on this host: {host_summary['task_count']} ({host_counts})",
                f"  Routed: {host_summary['routed_relative_units']:.1f} relative units",
                f"  Est. vs always-max on this host: {host_summary['estimated_savings_vs_always_max_pct']:.1f}%",
                f"  Confirm {host_summary['confirm_rate_pct']:.1f}%  |  Override {host_summary['override_rate_pct']:.1f}%",
                f"  Heavy-tier on likely-light tasks (this host): {host_summary['heavy_on_light_count']}",
            ]
        )
        if active.get("tier"):
            lines.append(
                f"  Current tier {tier}: {burn.get('current_tier_task_count', 0)} logged task(s), "
                f"{burn.get('current_tier_relative_units', 0):.1f} rel units"
            )
            lighter = burn.get("one_step_lighter_tier")
            if lighter and burn.get("current_tier_if_one_step_lighter_units") is not None:
                lines.append(
                    f"  If those current-tier rows had been {lighter}: "
                    f"{burn['current_tier_if_one_step_lighter_units']:.1f} rel units "
                    f"(illustrative only)"
                )
        lines.append("")
    elif summary["task_count"] == 0:
        lines.extend(
            [
                "No routing decisions in this window.",
                "After you opt in, agents may append non-sensitive lines to usage.jsonl.",
                "See SKILL.md / docs/SAVINGS_DESK.md. Audit stays consent-gated.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"2. Burn for active host ({host}): no log rows matched this host.",
                "  Showing the full local log below so you can still see the pattern.",
                "",
            ]
        )

    if summary["task_count"]:
        counts = ", ".join(
            f"{t}={summary['tasks_by_tier'][t]}"
            for t in TIERS
            if summary["tasks_by_tier"][t]
        ) or "none"
        lines.extend(
            [
                "All logged hosts (same window, still local-only):",
                f"  Decisions: {summary['task_count']} ({counts})",
                f"  Confirm rate: {summary['confirm_rate_pct']:.1f}% "
                f"({summary['confirmed_count']}/{summary['task_count']})",
                f"  Override rate: {summary['override_rate_pct']:.1f}% "
                f"({summary['override_count']}/{summary['task_count']})",
                f"  Switch-downs: {summary['switch_down_count']}  |  Switch-ups: {summary['switch_up_count']}",
                f"  Routed: {summary['routed_relative_units']:.1f} rel units  |  "
                f"vs always-max: {summary['estimated_savings_vs_always_max_pct']:.1f}%",
                "",
                "Burns by host:",
            ]
        )
        burns = summary.get("burns_by_host") or {}
        if not burns:
            lines.append("  (no host field on these rows)")
        else:
            for name, stats in burns.items():
                marker = "  ← active" if name == active.get("host") else ""
                tier_bits = ", ".join(
                    f"{t}={stats['tasks_by_tier'][t]}"
                    for t in TIERS
                    if stats["tasks_by_tier"][t]
                )
                lines.append(
                    f"  {name}: {stats['count']} task(s), "
                    f"{stats['relative_units']:.1f} rel units ({tier_bits}){marker}"
                )

        lines.extend(["", f"Heavy-tier use on likely-light tasks: {summary['heavy_on_light_count']}"])
        if summary["heavy_on_light_count"] == 0:
            lines.append("  (none, or task_kind was not logged)")
        else:
            for row in summary["heavy_on_light"][:12]:
                when = row.get("timestamp") or "unknown-time"
                lines.append(
                    f"  {when}  {row.get('host')}  {row.get('tier')} on task_kind={row.get('task_kind')}"
                )

    if missing_ts:
        lines.append(
            f"\nNote: {missing_ts} log line(s) lacked a parseable timestamp and were excluded."
        )

    offers = optimize_offers(host_summary or summary, cfg, active)
    lines.extend(["", "3. Optimize? (not applied yet)"])
    for action in offers:
        lines.append(f"  • {action['title']}")
        lines.append(f"      {action['detail']}")
    lines.append("")
    lines.extend(optimize_prompt(active))
    lines.extend(["", *codefriends_invite(cfg, after="audit")])
    lines.extend(
        [
            "",
            "Percentages estimate this local log only; no savings are guaranteed.",
            "No vendor billing, picker, or token API was accessed.",
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
        help="path to usage.jsonl or a JSON array",
    )
    parser.add_argument(
        "--host",
        action="append",
        dest="hosts",
        default=None,
        help="restrict the full-log section to a host (repeatable). Active host is detected separately",
    )
    parser.add_argument(
        "--current-tier",
        dest="current_tier",
        default=None,
        help="declare the active capability tier (fast|standard|reasoning|max)",
    )
    parser.add_argument(
        "--current-model",
        dest="current_model",
        default=None,
        help="declare the active picker/model label (not scraped)",
    )
    parser.add_argument(
        "--active-host",
        dest="active_host",
        default=None,
        help="declare the active host (default: detect from env/config/latest log)",
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
    now = datetime.now(timezone.utc).astimezone()
    in_window, missing = filter_window(entries, days=args.days, now=now)
    if used_sample and args.days is not None and not in_window and entries:
        in_window = entries
        missing = []

    active = detect_active(
        cfg=cfg,
        entries=in_window,
        host=args.active_host or (host_filter[0] if len(host_filter) == 1 else None),
        tier=args.current_tier,
        model=args.current_model,
    )
    view = filter_hosts(in_window, host_filter) if host_filter else in_window
    summary = summarize(view)
    burn = active_burn(in_window, active)
    print(
        human_report(
            window_days=args.days,
            log_path=log_path,
            summary=summary,
            burn=burn,
            used_sample=used_sample,
            missing_ts=len(missing),
            cfg=cfg,
            now=now,
            host_filter=host_filter,
            active=active,
        )
    )

    if args.json:
        payload = {
            "window_days": args.days,
            "log": str(log_path),
            "used_sample": used_sample,
            "missing_timestamp_count": len(missing),
            "host_filter": host_filter,
            "active": active,
            "active_burn": burn,
            "summary": summary,
            "optimize_offers": optimize_offers(burn.get("host_summary") or summary, cfg, active),
            "applied": False,
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
