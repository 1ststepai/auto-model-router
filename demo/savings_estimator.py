#!/usr/bin/env python3
"""Estimate relative routing savings from tasks or a usage decision log.

This is an illustrative estimator. It does not read Cursor, Claude Code, Codex,
or any vendor billing/token API. Rates are example relative units only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    from classify import classify
except ImportError:  # Running as demo.savings_estimator from the repo root.
    from demo.classify import classify

TIERS = ("fast", "standard", "reasoning", "max")
EXAMPLE_RATES = {"fast": 1.0, "standard": 3.0, "reasoning": 8.0, "max": 20.0}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _tier(value: Any, where: str) -> str:
    value = str(value).strip().lower()
    if value not in TIERS:
        raise ValueError(f"{where}: tier must be one of {', '.join(TIERS)}; got {value!r}")
    return value


def _entries(payload: Any, mode: str | None) -> tuple[str, List[Any]]:
    if isinstance(payload, dict):
        for key in ("decisions", "usage", "log", "entries"):
            if key in payload:
                return "log", payload[key]
        if "tasks" in payload:
            return "tasks", payload["tasks"]
        raise ValueError("JSON object must contain tasks, decisions, usage, log, or entries")
    if not isinstance(payload, list):
        raise ValueError("JSON input must be a list or an object containing a list")
    if mode:
        return mode, payload
    if all(isinstance(item, str) for item in payload):
        return "tasks", payload
    if all(isinstance(item, dict) and "tier" in item for item in payload):
        return "log", payload
    if all(isinstance(item, dict) and "task" in item for item in payload):
        return "tasks", payload
    raise ValueError("Could not detect input: use strings for tasks or objects with tier for a log")


def normalize(payload: Any, mode: str | None = None) -> tuple[str, List[Dict[str, Any]]]:
    kind, raw = _entries(payload, mode)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{kind} input must be a non-empty JSON list")

    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(raw, 1):
        if kind == "tasks":
            task = item if isinstance(item, str) else item.get("task", "")
            if not str(task).strip():
                raise ValueError(f"tasks[{index}] has no task text")
            result = classify(str(task))
            selected = _tier(result["tier"], f"tasks[{index}]")
            normalized.append({
                "task": str(task),
                "tier": selected,
                "confirmed": True,
                "overridden": False,
                "source": "classified task",
            })
        else:
            if not isinstance(item, dict):
                raise ValueError(f"decisions[{index}] must be an object")
            selected = _tier(item.get("tier"), f"decisions[{index}]")
            normalized.append({
                "tier": selected,
                "confirmed": _as_bool(item.get("confirmed", False)),
                "overridden": _as_bool(item.get("overridden", False)),
                "timestamp": item.get("timestamp"),
                **({"suggested_tier": item["suggested_tier"]} if item.get("suggested_tier") else {}),
            })
    return kind, normalized


def percent_saved(baseline: float, routed: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - routed) / baseline * 100, 1)


def estimate(entries: Iterable[Dict[str, Any]], source: str) -> Dict[str, Any]:
    entries = list(entries)
    by_tier = Counter(item["tier"] for item in entries)
    routed_units = sum(EXAMPLE_RATES[item["tier"]] for item in entries)
    always_max = len(entries) * EXAMPLE_RATES["max"]
    always_reasoning = len(entries) * EXAMPLE_RATES["reasoning"]
    overrides = sum(1 for item in entries if item.get("overridden", False))
    confirmed = sum(1 for item in entries if item.get("confirmed", False))
    return {
        "source": source,
        "rates_are": "illustrative relative example units, not vendor prices",
        "example_rates": EXAMPLE_RATES,
        "task_count": len(entries),
        "tasks_by_tier": {tier: by_tier.get(tier, 0) for tier in TIERS},
        "confirmed_count": confirmed,
        "override_count": overrides,
        "override_rate_pct": round(overrides / len(entries) * 100, 1),
        "routed_relative_units": round(routed_units, 2),
        "always_reasoning_relative_units": round(always_reasoning, 2),
        "always_max_relative_units": round(always_max, 2),
        "estimated_savings_vs_always_reasoning_pct": percent_saved(always_reasoning, routed_units),
        "estimated_savings_vs_always_max_pct": percent_saved(always_max, routed_units),
    }


def human_summary(result: Dict[str, Any]) -> str:
    counts = ", ".join(
        f"{tier}={result['tasks_by_tier'][tier]}" for tier in TIERS if result["tasks_by_tier"][tier]
    ) or "none"
    return "\n".join([
        "Savings estimator",
        "Rates: EXAMPLE relative units only (not real vendor prices)",
        f"Analyzed {result['task_count']} routed task(s): {counts}",
        f"Routed usage: {result['routed_relative_units']:.1f} relative units",
        f"Estimated savings vs always-reasoning: {result['estimated_savings_vs_always_reasoning_pct']:.1f}%",
        f"Estimated savings vs always-max: {result['estimated_savings_vs_always_max_pct']:.1f}%",
        f"Override rate: {result['override_rate_pct']:.1f}% ({result['override_count']}/{result['task_count']})",
        "Percentages estimate this local log only; no savings are guaranteed.",
        "No Cursor, Claude Code, Codex, token, or billing API was accessed.",
    ])


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="demo/sample_usage_log.json", help="JSON tasks or routing log")
    parser.add_argument("--tasks", action="store_true", help="treat a JSON array/object as task descriptions")
    parser.add_argument("--log", action="store_true", help="treat a JSON array/object as routing decisions")
    args = parser.parse_args(argv[1:])
    if args.tasks and args.log:
        parser.error("choose at most one of --tasks and --log")
    mode = "tasks" if args.tasks else "log" if args.log else None
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        kind, entries = normalize(payload, mode)
        result = estimate(entries, kind)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(human_summary(result))
    print("--- JSON ---")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
