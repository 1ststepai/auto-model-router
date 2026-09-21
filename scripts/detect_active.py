#!/usr/bin/env python3
"""Detect the host/tier/model currently in use — local context only.

Priority: --host / --current-tier / --current-model → env AMR_HOST,
AMR_CURRENT_TIER, AMR_CURRENT_MODEL → ~/.auto-model-router/config.json
(currentHost / currentTier / currentModel) → most recent usage.jsonl row.

Does not read live Cursor, Claude Code, Codex, or Gemini pickers or meters.
Optional: pass the printed tier to demo/classify.py --current-tier.

  python3 scripts/detect_active.py
  python3 scripts/detect_active.py --json
  python3 scripts/detect_active.py --current-tier max --host cursor
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

TIERS = ("fast", "standard", "reasoning", "max")


def amr_home() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
    if not home:
        raise SystemExit("error: HOME / USERPROFILE is not set")
    return Path(home) / ".auto-model-router"


def load_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("tier"):
            rows.append(obj)
    return rows


def _take(value: Optional[str], source: str, dest: Dict[str, str], key: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None
    dest[key] = source
    return text


def detect_active(
    *,
    cfg: Optional[Dict[str, Any]] = None,
    entries: Optional[List[Dict[str, Any]]] = None,
    host: Optional[str] = None,
    tier: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = cfg or {}
    sources: Dict[str, str] = {}
    host = (
        _take(host, "cli --host", sources, "host")
        or _take(os.environ.get("AMR_HOST") or os.environ.get("AMR_CURRENT_HOST"), "env AMR_HOST", sources, "host")
        or _take(str(cfg.get("currentHost") or ""), "config currentHost", sources, "host")
    )
    tier = (
        _take(tier, "cli --current-tier", sources, "tier")
        or _take(os.environ.get("AMR_CURRENT_TIER"), "env AMR_CURRENT_TIER", sources, "tier")
        or _take(str(cfg.get("currentTier") or ""), "config currentTier", sources, "tier")
    )
    model = (
        _take(model, "cli --current-model", sources, "model")
        or _take(os.environ.get("AMR_CURRENT_MODEL"), "env AMR_CURRENT_MODEL", sources, "model")
        or _take(str(cfg.get("currentModel") or ""), "config currentModel", sources, "model")
    )
    if (not tier or not host) and entries:
        latest = entries[-1]
        if not tier:
            tier = _take(str(latest.get("tier") or ""), "latest usage.jsonl row", sources, "tier")
        if not host:
            host = _take(str(latest.get("host") or ""), "latest usage.jsonl row", sources, "host")
        if not model:
            model = _take(str(latest.get("model") or latest.get("picker") or ""), "latest usage.jsonl row", sources, "model")
    if tier:
        needle = tier.strip().lower()
        needle = {"low": "fast", "high": "reasoning", "frontier": "max"}.get(needle, needle)
        tier = needle if needle in TIERS else None
        if tier is None:
            sources.pop("tier", None)
    return {
        "host": host or None,
        "tier": tier or None,
        "model": model or None,
        "sources": sources,
        "live_meter_read": False,
        "live_picker_read": False,
        "note": "Local context only. Not a live vendor picker or billing meter.",
    }


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=None)
    parser.add_argument("--current-tier", default=None)
    parser.add_argument("--current-model", default=None)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])

    home = amr_home()
    cfg = load_config(home / "config.json")
    log_path = args.log or Path(".auto-model-router") / "usage.jsonl"
    if not log_path.is_file():
        log_path = home / "logs" / "usage.jsonl"
    entries = load_jsonl(log_path)
    active = detect_active(
        cfg=cfg,
        entries=entries,
        host=args.host,
        tier=args.current_tier,
        model=args.current_model,
    )
    active["log"] = str(log_path)
    if args.json:
        print(json.dumps(active, indent=2))
        return 0
    print(f"host:  {active['host'] or '(unknown)'}")
    print(f"tier:  {active['tier'] or '(unknown)'}")
    print(f"model: {active['model'] or '(unknown)'}")
    if active["sources"]:
        bits = ", ".join(f"{k}←{v}" for k, v in active["sources"].items())
        print(f"from:  {bits}")
    print(active["note"])
    if active["tier"]:
        print(
            f"Next: python3 demo/classify.py --suggest --current-tier {active['tier']} "
            '"<your task>"'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
