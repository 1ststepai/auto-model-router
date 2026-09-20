#!/usr/bin/env python3
"""Detect the model/tier the user is actively using — local context only.

Looks at --host / --current-tier / --current-model, AMR_* env vars, config
currentHost/currentTier/currentModel, local *-tier-map.json labels, and the
most recent usage.jsonl row.

Does not read live Cursor, Claude Code, Codex, or Gemini pickers or meters.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from amr_usage import (
    detect_active,
    load_config,
    load_usage_entries,
    resolve_usage_log,
    sample_log_candidates,
)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="declare the active host (cursor, claude-code, codex, gemini)")
    parser.add_argument("--current-tier", dest="current_tier", help="declare the active capability tier")
    parser.add_argument("--current-model", dest="current_model", help="declare the active picker/model label")
    parser.add_argument("--log", type=Path, default=None, help="usage.jsonl used as fallback context")
    parser.add_argument("--sample", action="store_true", help="use the bundled sample log as fallback context")
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args(argv[1:])

    cfg = load_config()
    log_path = resolve_usage_log(cfg, args.log)
    entries = load_usage_entries(log_path) if not args.sample else []
    used_sample = False
    if args.sample or not entries:
        for candidate in sample_log_candidates():
            sample = load_usage_entries(candidate)
            if sample:
                entries = sample
                log_path = candidate
                used_sample = True
                break

    active = detect_active(
        cfg=cfg,
        entries=entries,
        host=args.host,
        tier=args.current_tier,
        model=args.current_model,
    )
    active["log"] = str(log_path)
    active["used_sample"] = used_sample

    if args.json:
        print(json.dumps(active, indent=2))
        return 0

    print("Active model (local context only)")
    print(f"  host:  {active.get('host') or '(unknown)'}  source={active.get('sources', {}).get('host', '—')}")
    print(f"  tier:  {active.get('tier') or '(unknown)'}  source={active.get('sources', {}).get('tier', '—')}")
    print(f"  model: {active.get('model') or '(undeclared)'}  source={active.get('sources', {}).get('model', '—')}")
    print(f"  log:   {log_path}" + (" (sample)" if used_sample else ""))
    print()
    print(active["note"])
    print("Next: python3 scripts/audit_usage.py   # audits this active pick first")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
