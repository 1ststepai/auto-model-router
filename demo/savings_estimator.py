#!/usr/bin/env python3
"""Summarize a local routing log.

Prefers input_tokens, output_tokens, and cost_usd when a row has them.
Rows with only a tier fall back to illustrative relative units (fast=1, standard=3,
reasoning=8, max=20), labeled as such. Dollar rates for token counts come only
from a price table you fill (--prices). This script does not scrape vendor billing
and does not ship real vendor prices.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve()
for _base in HERE.parents:
    if (_base / "auto_model_router.py").is_file():
        sys.path.insert(0, str(_base))
        break

try:
    from classify import classify
except ImportError:
    from demo.classify import classify

from auto_model_router import TIERS, load_price_table, summarize_usage  # noqa: E402


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


def _usage_fields(item: dict) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    for key in (
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "currency",
        "timestamp",
        "suggested_tier",
        "host",
        "gate",
        "confidence",
    ):
        if item.get(key) is not None:
            extra[key] = item[key]
    return extra


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
                "confidence": result.get("confidence"),
                "gate": result.get("gate"),
            })
        else:
            if not isinstance(item, dict):
                raise ValueError(f"decisions[{index}] must be an object")
            selected = _tier(item.get("tier"), f"decisions[{index}]")
            normalized.append({
                "tier": selected,
                "confirmed": _as_bool(item.get("confirmed", False)),
                "overridden": _as_bool(item.get("overridden", False)),
                **_usage_fields(item),
            })
    return kind, normalized


def estimate(entries: List[Dict[str, Any]], source: str, price_table: Dict[str, Any] | None = None) -> Dict[str, Any]:
    summary = summarize_usage(entries, price_table)
    summary["source"] = source
    return summary


def human_summary(result: Dict[str, Any]) -> str:
    counts = ", ".join(
        f"{tier}={result['tasks_by_tier'][tier]}" for tier in TIERS if result["tasks_by_tier"][tier]
    ) or "none"
    lines = [
        "Savings estimator",
        f"Basis: {result['basis']}",
        f"Analyzed {result['task_count']} routed task(s): {counts}",
        f"Tokens logged: input={result['input_tokens']} output={result['output_tokens']}",
    ]
    if result.get("measured_cost_usd") is not None:
        lines.append(
            f"Measured cost: ${result['measured_cost_usd']:.6f} "
            f"from {result['priced_entry_count']} row(s) with cost_usd or your price table"
        )
    else:
        lines.append("Measured cost: none (no cost_usd and no complete local price table)")
    illustrative = result.get("illustrative")
    if illustrative:
        lines.extend([
            f"Illustrative fallback ({illustrative['entries']} row(s) with tier only): "
            f"{illustrative['routed_relative_units']:.1f} relative units",
            "Rates: EXAMPLE relative units only (not real vendor prices) "
            f"fast={illustrative['example_rates']['fast']:g}x "
            f"standard={illustrative['example_rates']['standard']:g}x "
            f"reasoning={illustrative['example_rates']['reasoning']:g}x "
            f"max={illustrative['example_rates']['max']:g}x",
            f"Estimated savings vs always-reasoning (illustrative rows only): "
            f"{illustrative['estimated_savings_vs_always_reasoning_pct']:.1f}%",
            f"Estimated savings vs always-max (illustrative rows only): "
            f"{illustrative['estimated_savings_vs_always_max_pct']:.1f}%",
        ])
    lines.append(
        f"Override rate: {result['override_rate_pct']:.1f}% "
        f"({result['override_count']}/{result['task_count']})"
    )
    lines.extend(result.get("notes") or [])
    lines.append("No Cursor, Claude Code, Codex, Gemini, or billing API was accessed.")
    if result.get("price_table_status") == "missing_rates":
        lines.append(
            "Token rows stayed unpriced. Copy demo/prices.example.json, fill per-million rates, "
            "and pass --prices. This repo does not invent those rates."
        )
    return "\n".join(lines)


def load_input(path: Path | str) -> Any:
    text = os.fspath(path)
    if "\x00" in text:
        raise ValueError("path must not contain NUL")
    resolved = os.path.realpath(os.path.expanduser(text))
    cwd = os.path.realpath(os.getcwd())
    home = os.path.realpath(os.path.expanduser(os.path.join("~", ".auto-model-router")))
    tmp = os.path.realpath(tempfile.gettempdir())
    repo = os.path.realpath(str(HERE.parent.parent if HERE.parent.name == "demo" else HERE.parent))
    if not (
        resolved.startswith(cwd + os.sep)
        or resolved == cwd
        or resolved.startswith(home + os.sep)
        or resolved == home
        or resolved.startswith(tmp + os.sep)
        or resolved == tmp
        or resolved.startswith(repo + os.sep)
        or resolved == repo
    ):
        raise ValueError(f"refusing path outside allowed directories: {resolved}")
    with open(resolved, encoding="utf-8") as handle:
        body = handle.read()
    if resolved.endswith(".jsonl"):
        rows = []
        for line in body.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    return json.loads(body)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="demo/sample_usage_log.json", help="JSON tasks, routing log, or usage.jsonl")
    parser.add_argument("--tasks", action="store_true", help="treat a JSON array/object as task descriptions")
    parser.add_argument("--log", action="store_true", help="treat a JSON array/object as routing decisions")
    parser.add_argument("--prices", default=None, help="local price table JSON you filled (optional)")
    args = parser.parse_args(argv[1:])
    if args.tasks and args.log:
        parser.error("choose at most one of --tasks and --log")
    mode = "tasks" if args.tasks else "log" if args.log else None
    try:
        payload = load_input(args.input)
        prices = load_price_table(args.prices) if args.prices else None
        if args.prices and prices is None:
            raise ValueError(f"price table not found: {args.prices}")
        kind, entries = normalize(payload, mode)
        result = estimate(entries, kind, prices)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(human_summary(result))
    print("--- JSON ---")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
