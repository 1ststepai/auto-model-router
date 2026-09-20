#!/usr/bin/env python3
"""Apply Savings Desk recommendations from a local usage audit.

Writes/updates local host tier maps (Cursor + Claude/Codex stubs), records that
boundary-gated confirms are enabled in config, and can opt in the weekly digest.

Complements the portable skill. Does not replace Cursor/Claude/Codex/Gemini
hosts, flip native Auto pickers, or call billing APIs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from amr_usage import (
    DEFAULT_HOSTS,
    honesty_lines,
    load_config,
    load_usage_entries,
    next_actions,
    resolve_usage_log,
    sample_log_candidates,
    save_config,
    summarize,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
EXAMPLE_REL = {
    "cursor": "cursor-tier-map.example.json",
    "claude-code": "claude-tier-map.example.json",
    "codex": "codex-tier-map.example.json",
    "gemini": "gemini-tier-map.example.json",
}
DEST_NAMES = {
    "cursor": "cursor-tier-map.json",
    "claude-code": "claude-tier-map.json",
    "codex": "codex-tier-map.json",
    "gemini": "gemini-tier-map.json",
}
FALLBACK_MAPS = {
    "cursor": {
        "comment": "Local Cursor adapter example — replace placeholders with labels from YOUR picker. AMR does not read Cursor usage/quota APIs.",
        "fast": {"picker": "<your-fast-model>", "effort": "low"},
        "standard": {"picker": "<your-standard-model>", "effort": "medium"},
        "reasoning": {"picker": "<your-reasoning-model>", "effort": "high"},
        "max": {"picker": "<your-max-model>", "effort": "max"},
    },
    "claude-code": {
        "comment": "Local Claude Code adapter stub — replace placeholders with models you have enabled. Not an Anthropic billing API.",
        "fast": {"model": "<your-fast-claude>", "effort": "low"},
        "standard": {"model": "<your-standard-claude>", "effort": "medium"},
        "reasoning": {"model": "<your-reasoning-claude>", "effort": "high"},
        "max": {"model": "<your-max-claude>", "effort": "max"},
    },
    "codex": {
        "comment": "Local Codex adapter stub — replace placeholders with your Codex model/effort. Not an OpenAI usage meter.",
        "fast": {"model": "<your-fast-codex>", "effort": "low"},
        "standard": {"model": "<your-standard-codex>", "effort": "medium"},
        "reasoning": {"model": "<your-reasoning-codex>", "effort": "high"},
        "max": {"model": "<your-max-codex>", "effort": "max"},
    },
    "gemini": {
        "comment": "Gemini-style agent stub — optional peer host. Not a Google Cloud billing API.",
        "fast": {"model": "<your-fast-gemini>", "effort": "low"},
        "standard": {"model": "<your-standard-gemini>", "effort": "medium"},
        "reasoning": {"model": "<your-reasoning-gemini>", "effort": "high"},
        "max": {"model": "<your-max-gemini>", "effort": "max"},
    },
}


def _example_map(host: str) -> Dict[str, Any]:
    candidates = [
        REPO_ROOT / "integrations" / EXAMPLE_REL[host],
        SCRIPT_DIR / "examples" / EXAMPLE_REL[host],
        Path.home() / ".auto-model-router" / "examples" / EXAMPLE_REL[host],
    ]
    for path in candidates:
        data = _read_json(path)
        if data:
            return data
    return dict(FALLBACK_MAPS[host])


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def merge_map(existing: Optional[Dict[str, Any]], example: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Keep user picker/model labels; fill missing tiers from the example stub."""
    if not existing:
        return dict(example), True
    merged = dict(existing)
    created = False
    for key, value in example.items():
        if key == "comment":
            merged.setdefault(key, value)
            continue
        if key not in merged:
            merged[key] = value
            created = True
            continue
        current = merged[key]
        if isinstance(current, dict) and isinstance(value, dict):
            for inner_key, inner_val in value.items():
                if inner_key not in current:
                    current[inner_key] = inner_val
                    created = True
    return merged, created


def write_maps(dest_dir: Path, hosts: List[str], *, dry_run: bool) -> List[str]:
    notes: List[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for host in hosts:
        if host not in DEST_NAMES:
            notes.append(f"skip unknown host {host!r} (no map stub)")
            continue
        example = _example_map(host)
        if not example:
            notes.append(f"missing example map for {host}")
            continue
        dest = dest_dir / DEST_NAMES[host]
        existing = _read_json(dest)
        merged, filled = merge_map(existing, example)
        if existing and not filled:
            notes.append(f"kept existing {dest}")
            continue
        if dry_run:
            action = "would write" if not existing else "would fill missing keys in"
            notes.append(f"{action} {dest}")
            continue
        dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        notes.append(("wrote " if not existing else "updated ") + str(dest))
    return notes


def load_entries_for_audit(cfg: Dict[str, Any], log: Optional[Path], use_sample: bool) -> Tuple[List[Dict[str, Any]], Path, bool]:
    if use_sample:
        for candidate in sample_log_candidates():
            sample = load_usage_entries(candidate)
            if sample:
                return sample, candidate, True
        return [], Path("sample"), True
    log_path = resolve_usage_log(cfg, log)
    entries = load_usage_entries(log_path)
    if entries:
        return entries, log_path, False
    for candidate in sample_log_candidates():
        sample = load_usage_entries(candidate)
        if sample:
            return sample, candidate, True
    return [], log_path, False


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="apply even when auditOptIn is false (still writes only local files)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print actions without writing maps or config",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="directory for tier maps (default: ~/.auto-model-router)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="also write maps under <project>/.auto-model-router/",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="usage log used to phrase next actions",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="phrase recommendations from the bundled sample log",
    )
    parser.add_argument(
        "--enable-weekly-review",
        action="store_true",
        help="set weeklyReview=true (does not install cron; use apply.sh --install-schedule)",
    )
    parser.add_argument(
        "--no-maps",
        action="store_true",
        help="update config / print actions only; do not write tier maps",
    )
    args = parser.parse_args(argv[1:])

    cfg = load_config()
    if not cfg.get("auditOptIn") and not args.force:
        print(
            "Refusing to apply automation before audit consent.\n"
            "Opt in first: ./scripts/apply.sh --enable-audit\n"
            "Then: python3 scripts/audit_usage.py && python3 scripts/apply_recommendations.py\n"
            "Or pass --force for a local dry run of the map stubs.",
            file=sys.stderr,
        )
        return 1

    hosts = list(cfg.get("hosts") or DEFAULT_HOSTS)
    dest = (args.dest or (Path.home() / ".auto-model-router")).expanduser()
    entries, log_path, used_sample = load_entries_for_audit(cfg, args.log, args.sample)
    summary = summarize(entries)

    print("Auto Model Router — apply Savings Desk recommendations")
    print(f"Log: {log_path}" + (" (sample)" if used_sample else ""))
    print(f"Maps directory: {dest}")
    print()
    for line in honesty_lines():
        print(line)
    print()

    notes: List[str] = []
    if args.no_maps:
        notes.append("skipped writing tier maps (--no-maps)")
    else:
        notes.extend(write_maps(dest, hosts, dry_run=args.dry_run))
        if args.project:
            project_dir = args.project.expanduser().resolve() / ".auto-model-router"
            notes.extend(write_maps(project_dir, hosts, dry_run=args.dry_run))

    updates: Dict[str, Any] = {
        "boundaryGatedConfirms": True,
        "hosts": hosts,
    }
    if args.enable_weekly_review:
        updates["weeklyReview"] = True
    if not args.dry_run:
        cfg = save_config(updates)
        notes.append("config → boundaryGatedConfirms=true (policy flag only; hosts still confirm at their UI)")
        if args.enable_weekly_review:
            notes.append("config → weeklyReview=true (run apply.sh --install-schedule to add cron)")
    else:
        notes.append("would set boundaryGatedConfirms=true")
        if args.enable_weekly_review:
            notes.append("would set weeklyReview=true")

    print("Changes:")
    for note in notes:
        print(f"  • {note}")

    # Recompute actions against the post-apply config so remaining work is honest.
    preview_cfg = dict(cfg)
    preview_cfg.update(updates)
    remaining = next_actions(summary, preview_cfg)
    print()
    print("Concrete next actions:")
    print("  • enable boundary gates — documented in docs/boundary-gated-confirms.md; flag is on.")
    print("  • map fast→X — fill <your-fast-model> placeholders in the local *-tier-map.json files.")
    print("  • turn on weekly digest — ./scripts/apply.sh --enable-weekly-review")
    print("    Optional schedule (never silent): ./scripts/apply.sh --install-schedule")
    if remaining:
        print()
        print("Still open:")
        for action in remaining:
            print(f"  • {action['title']}")
            print(f"      {action['detail']}")

    print()
    print("AMR remains a skill / agent policy. It does not flip Cursor Auto or read vendor meters.")
    print("Open the dashboard: ~/.auto-model-router/demo/dashboard.html or demo/dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
