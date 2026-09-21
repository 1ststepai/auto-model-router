#!/usr/bin/env python3
"""Shared router: classify, confirm-gate, optional local usage log.

Spendy tiers (standard / reasoning / max) cannot run tools until the user
confirms. Fast auto-continues only when classify() says gate=auto_continue.
Tool arguments cannot self-confirm. No vendor billing API.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.classify import LOW_CONFIDENCE, classify, suggest_line  # noqa: E402

TIERS = ("fast", "standard", "reasoning", "max")
SPENDY_TIERS = frozenset({"standard", "reasoning", "max"})
EXAMPLE_RATES = {"fast": 1.0, "standard": 3.0, "reasoning": 8.0, "max": 20.0}
USAGE_FIELDS = ("input_tokens", "output_tokens", "cost_usd", "currency")

_CONFIRM_RE = re.compile(
    r"^(confirm|confirmed|yes|yep|yeah|approved|approve|go ahead|proceed)\b[.!]?$",
    re.IGNORECASE,
)
_OVERRIDE_RE = re.compile(
    r"^(?:override[:\s]+)?(fast|standard|reasoning|max)\b[.!]?$",
    re.IGNORECASE,
)


def classify_task(task: str) -> dict:
    """Classify with confidence, gate, and low-confidence downshift."""
    return classify(task)


def _checked_local(raw: os.PathLike[str] | str) -> str:
    """realpath + startswith so file IO cannot follow a CLI/LLM path outside local roots."""
    text = os.fspath(raw)
    if "\x00" in text:
        raise ValueError("path must not contain NUL")
    resolved = os.path.realpath(os.path.expanduser(text))
    cwd = os.path.realpath(os.getcwd())
    home = os.path.realpath(os.path.expanduser(os.path.join("~", ".auto-model-router")))
    tmp = os.path.realpath(tempfile.gettempdir())
    repo = os.path.realpath(str(ROOT))
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
    return resolved


def safe_local_path(raw: os.PathLike[str] | str) -> Path:
    return Path(_checked_local(raw))


def read_local_text(raw: os.PathLike[str] | str) -> str:
    text = os.fspath(raw)
    if "\x00" in text:
        raise ValueError("path must not contain NUL")
    resolved = os.path.realpath(os.path.expanduser(text))
    cwd = os.path.realpath(os.getcwd())
    home = os.path.realpath(os.path.expanduser(os.path.join("~", ".auto-model-router")))
    tmp = os.path.realpath(tempfile.gettempdir())
    repo = os.path.realpath(str(ROOT))
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
        return handle.read()


def write_local_text(raw: os.PathLike[str] | str, body: str, *, append: bool = False) -> str:
    text = os.fspath(raw)
    if "\x00" in text:
        raise ValueError("path must not contain NUL")
    resolved = os.path.realpath(os.path.expanduser(text))
    cwd = os.path.realpath(os.getcwd())
    home = os.path.realpath(os.path.expanduser(os.path.join("~", ".auto-model-router")))
    tmp = os.path.realpath(tempfile.gettempdir())
    repo = os.path.realpath(str(ROOT))
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
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    with open(resolved, "a" if append else "w", encoding="utf-8") as handle:
        handle.write(body)
    return resolved


def gate_path(explicit: Optional[os.PathLike[str] | str] = None) -> Path:
    if explicit:
        return safe_local_path(explicit)
    env = os.environ.get("AUTO_MODEL_ROUTER_GATE")
    if env:
        return safe_local_path(env)
    return safe_local_path(Path(".auto-model-router") / "gate.json")


def load_gate(path: Optional[os.PathLike[str] | str] = None) -> Dict[str, Any]:
    try:
        data = json.loads(read_local_text(gate_path(path)))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_gate(state: Mapping[str, Any], path: Optional[os.PathLike[str] | str] = None) -> Path:
    file = gate_path(path)
    write_local_text(file, json.dumps(dict(state), indent=2) + "\n")
    return file


def record_confirmation(
    tier: str,
    *,
    path: Optional[os.PathLike[str] | str] = None,
    overridden: bool = False,
    suggested_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an explicit user confirm. Call from a terminal or prompt hook, not from tool args."""
    chosen = _tier(tier, "confirm")
    state: Dict[str, Any] = {
        "tier": chosen,
        "confirmed": True,
        "overridden": overridden,
        "gate": "confirm",
        "source": "explicit_confirm",
    }
    if suggested_tier:
        state["suggested_tier"] = _tier(suggested_tier, "suggested_tier")
    save_gate(state, path)
    return state


def ingest_user_prompt(
    text: str,
    prior: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Update gate state from a user message. Not for tool-call payloads."""
    prior_state = dict(prior or {})
    message = (text or "").strip()
    if not message:
        return prior_state or {"tier": None, "confirmed": False, "source": "empty_prompt"}
    override = _OVERRIDE_RE.match(message)
    if override:
        tier = override.group(1).lower()
        suggested = prior_state.get("tier")
        return {
            "tier": tier,
            "confirmed": True,
            "overridden": suggested not in (None, tier),
            "suggested_tier": suggested,
            "gate": "confirm",
            "source": "user_override",
        }
    if _CONFIRM_RE.match(message):
        tier = prior_state.get("tier")
        if tier not in TIERS:
            return {
                "tier": None,
                "confirmed": False,
                "source": "confirm_without_tier",
            }
        return {
            **prior_state,
            "tier": tier,
            "confirmed": True,
            "overridden": bool(prior_state.get("overridden", False)),
            "source": "user_confirm",
        }
    result = classify_task(message)
    auto = result.get("gate") == "auto_continue"
    return {
        "tier": result["tier"],
        "confirmed": auto,
        "overridden": False,
        "gate": result["gate"],
        "confidence": result["confidence"],
        "needs_confirm": result["needs_confirm"],
        "downshifted_from": result["downshifted_from"],
        "reason": result["reason"],
        "source": "classified_prompt",
    }


def _forged_confirm(payload: Optional[Mapping[str, Any]]) -> bool:
    """True when the tool call tries to grant itself permission."""
    if not payload:
        return False
    blob = json.dumps(payload, default=str).lower()
    if "confirm_gate.py" in blob and "--confirm" in blob:
        return True
    tool_input = payload.get("tool_input")
    if tool_input is None:
        tool_input = payload.get("toolInput")
    if not isinstance(tool_input, dict):
        return False
    flag = tool_input.get("confirmed")
    if flag is True or (isinstance(flag, str) and flag.strip().lower() == "true"):
        return True
    return False


def evaluate_tool(
    state: Optional[Mapping[str, Any]],
    payload: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Block spendy (and gated-fast) tool execution unless the user confirmed.

    Fields inside the tool payload are ignored. A forged ``confirmed: true``
    does not allow the call.
    """
    state = dict(state or {})
    tier = state.get("tier")
    confirmed = state.get("confirmed") is True
    gate = state.get("gate")
    forged = _forged_confirm(payload)
    if forged and not confirmed:
        allowed = False
        reason = "blocked: tool arguments cannot self-confirm a spendy run"
    elif confirmed:
        allowed = True
        reason = "explicit user confirm is on file"
    elif gate == "auto_continue":
        allowed = True
        reason = "fast auto-continue: clear reversible work, policy-authorized"
    elif tier == "fast" and gate not in ("confirm", "hard_gate"):
        allowed = True
        reason = "fast tier may run tools without a spendy confirm"
    else:
        allowed = False
        if tier in SPENDY_TIERS:
            reason = f"blocked: {tier} requires explicit user confirm before tools run"
        elif gate in ("confirm", "hard_gate"):
            reason = f"blocked: gate={gate}; wait for confirm before tools run"
        else:
            reason = "blocked: no confirmed tier on file; refusing tool execution"
    return {
        "allowed": allowed,
        "permission": "allow" if allowed else "deny",
        "reason": reason,
        "tier": tier if tier in TIERS else None,
        "gate": gate if gate in ("auto_continue", "confirm", "hard_gate") else None,
    }


def _tier(value: Any, where: str) -> str:
    text = str(value).strip().lower()
    if text not in TIERS:
        raise ValueError(f"{where}: tier must be one of {', '.join(TIERS)}; got {value!r}")
    return text


def route(
    task: str,
    *,
    confirmed: bool = False,
    override: Optional[str] = None,
    host: Optional[str] = None,
    log_path: Optional[os.PathLike[str] | str] = None,
    usage: Optional[Mapping[str, Any]] = None,
    state_path: Optional[os.PathLike[str] | str] = None,
) -> Dict[str, Any]:
    """Classify, gate, and optionally append one usage.jsonl row.

    ``confirmed`` must be the boolean ``True``. Strings and other truthy
    values do not count. An ``override`` tier is an explicit user choice.
    Auto-continue (clear reversible fast) is allowed without ``confirmed``.
    Nothing is logged when the gate blocks the run.
    """
    classified = classify_task(task)
    suggested = classified["tier"]
    if override is not None:
        chosen = _tier(override, "override")
        overridden = chosen != suggested
        user_confirmed = True
        gate = classified.get("gate", "confirm")
    else:
        chosen = suggested
        overridden = False
        user_confirmed = confirmed is True
        gate = classified.get("gate", "confirm")
    decision = evaluate_tool(
        {"tier": chosen, "confirmed": user_confirmed, "gate": gate if override is None else "confirm"},
        None,
    )
    record: Dict[str, Any] = {
        "tier": chosen,
        "suggested_tier": suggested,
        "reason": classified["reason"],
        "confidence": classified["confidence"],
        "needs_confirm": classified.get("needs_confirm", chosen != "fast") and not user_confirmed,
        "downshifted_from": classified.get("downshifted_from"),
        "gate": classified.get("gate"),
        "signals": classified.get("signals"),
        "allowed": decision["allowed"],
        "overridden": overridden,
        "suggestion": suggest_line(task, {**classified, "tier": chosen}),
        "logged": False,
    }
    if state_path is not None:
        save_gate(
            {
                "tier": chosen,
                "confirmed": user_confirmed or decision["allowed"],
                "overridden": overridden,
                "suggested_tier": suggested,
                "confidence": classified["confidence"],
                "gate": classified.get("gate"),
                "source": "route",
            },
            state_path,
        )
    if decision["allowed"] and log_path is not None:
        append_usage(
            log_path,
            _usage_record(
                tier=chosen,
                confirmed=user_confirmed or classified.get("gate") == "auto_continue",
                overridden=overridden,
                suggested_tier=suggested,
                confidence=classified["confidence"],
                gate=classified.get("gate"),
                host=host,
                usage=usage,
            ),
        )
        record["logged"] = True
    return record


def _usage_record(
    *,
    tier: str,
    confirmed: bool,
    overridden: bool,
    suggested_tier: str,
    confidence: float,
    gate: Optional[str],
    host: Optional[str],
    usage: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tier": tier,
        "confirmed": confirmed,
        "overridden": overridden,
        "suggested_tier": suggested_tier,
        "confidence": confidence,
    }
    if gate:
        record["gate"] = gate
    if host:
        record["host"] = host
    if usage:
        for key in USAGE_FIELDS:
            if key in usage and usage[key] is not None:
                record[key] = usage[key]
    return record


def append_usage(path: os.PathLike[str] | str, record: Mapping[str, Any]) -> Path:
    """Append one JSON object to a local usage.jsonl. Does not call a vendor API."""
    _tier(record.get("tier"), "usage")
    resolved = write_local_text(
        path,
        json.dumps(dict(record), separators=(",", ":")) + "\n",
        append=True,
    )
    return Path(resolved)


def load_price_table(path: Optional[os.PathLike[str] | str]) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    try:
        data = json.loads(read_local_text(path))
    except FileNotFoundError:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: price table must be a JSON object")
    return data


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return value == 1


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tier_rates(table: Mapping[str, Any], tier: str) -> Optional[tuple[float, float]]:
    tiers = table.get("tiers")
    if not isinstance(tiers, dict):
        return None
    row = tiers.get(tier)
    if not isinstance(row, dict):
        return None
    incoming = _num(row.get("input_per_million"))
    outgoing = _num(row.get("output_per_million"))
    if incoming is None or outgoing is None:
        return None
    return incoming, outgoing


def _token_cost(entry: Mapping[str, Any], table: Optional[Mapping[str, Any]], tier: str) -> Optional[float]:
    if not table:
        return None
    rates = _tier_rates(table, tier)
    if rates is None:
        return None
    incoming = _num(entry.get("input_tokens"))
    outgoing = _num(entry.get("output_tokens"))
    if incoming is None and outgoing is None:
        return None
    in_rate, out_rate = rates
    return ((incoming or 0.0) / 1_000_000.0) * in_rate + ((outgoing or 0.0) / 1_000_000.0) * out_rate


def summarize_usage(
    entries: Iterable[Mapping[str, Any]],
    price_table: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefer logged cost_usd, then a user-filled price table, else labeled relative units.

    This never invents vendor dollar rates. Nulls in the example price table stay unpriced.
    """
    rows = list(entries)
    by_tier = dict.fromkeys(TIERS, 0)
    confirmed = 0
    overridden = 0
    input_tokens = 0
    output_tokens = 0
    measured = 0.0
    priced = 0
    illustrative_units = 0.0
    illustrative_count = 0
    table_applied = False
    table_incomplete = False
    notes: List[str] = []

    for item in rows:
        tier = str(item.get("tier", "")).strip().lower()
        if tier not in TIERS:
            continue
        by_tier[tier] += 1
        if _flag(item.get("confirmed")):
            confirmed += 1
        if _flag(item.get("overridden")):
            overridden += 1
        in_tok = _num(item.get("input_tokens"))
        out_tok = _num(item.get("output_tokens"))
        if in_tok is not None:
            input_tokens += int(in_tok)
        if out_tok is not None:
            output_tokens += int(out_tok)

        logged = _num(item.get("cost_usd"))
        if logged is not None:
            measured += logged
            priced += 1
            continue
        computed = _token_cost(item, price_table, tier)
        if computed is not None:
            measured += computed
            priced += 1
            table_applied = True
            continue
        if price_table and (in_tok is not None or out_tok is not None):
            table_incomplete = True
        illustrative_units += EXAMPLE_RATES[tier]
        illustrative_count += 1

    count = sum(by_tier.values())
    if count == 0:
        basis = "empty"
    elif priced and illustrative_count:
        basis = "mixed"
    elif priced:
        basis = "measured"
    else:
        basis = "illustrative_tier_rates"

    illustrative = None
    if illustrative_count:
        always_reasoning = illustrative_count * EXAMPLE_RATES["reasoning"]
        always_max = illustrative_count * EXAMPLE_RATES["max"]
        illustrative = {
            "entries": illustrative_count,
            "rates_are": "illustrative relative example units, not vendor prices",
            "example_rates": dict(EXAMPLE_RATES),
            "routed_relative_units": round(illustrative_units, 2),
            "always_reasoning_relative_units": round(always_reasoning, 2),
            "always_max_relative_units": round(always_max, 2),
            "estimated_savings_vs_always_reasoning_pct": _pct(always_reasoning, illustrative_units),
            "estimated_savings_vs_always_max_pct": _pct(always_max, illustrative_units),
        }

    if basis == "illustrative_tier_rates":
        notes.append(
            "No cost_usd or priced tokens on these rows. "
            "Relative units are a labeled fallback, not dollars."
        )
    if basis == "mixed":
        notes.append(
            "Some rows have real cost or priced tokens; the rest fall back to labeled relative units."
        )
    if table_incomplete or (price_table and not table_applied and any(
        _num(item.get("input_tokens")) is not None or _num(item.get("output_tokens")) is not None
        for item in rows
    )):
        notes.append(
            "Token counts without a complete per-tier price were not converted to dollars. "
            "Fill input_per_million and output_per_million in your local price table."
        )
    if not notes and basis == "measured":
        notes.append(
            "Dollar figures come from logged cost_usd and/or your local price table, not a vendor billing API."
        )

    if price_table is None:
        price_status = "not_loaded"
    elif table_applied:
        price_status = "applied"
    else:
        price_status = "missing_rates"

    return {
        "basis": basis,
        "currency": "USD",
        "task_count": count,
        "tasks_by_tier": by_tier,
        "confirmed_count": confirmed,
        "override_count": overridden,
        "override_rate_pct": round(overridden / count * 100, 1) if count else 0.0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "priced_entry_count": priced,
        "illustrative_entry_count": illustrative_count,
        "measured_cost_usd": round(measured, 6) if priced else None,
        "illustrative": illustrative,
        "price_table_status": price_status,
        "billing_api_accessed": False,
        "notes": notes,
        "rates_are": (illustrative or {}).get(
            "rates_are",
            "measured local log fields, not vendor prices",
        ),
        "example_rates": dict(EXAMPLE_RATES) if illustrative else None,
        "routed_relative_units": None if not illustrative else illustrative["routed_relative_units"],
        "estimated_savings_vs_always_reasoning_pct": None
        if not illustrative
        else illustrative["estimated_savings_vs_always_reasoning_pct"],
        "estimated_savings_vs_always_max_pct": None
        if not illustrative
        else illustrative["estimated_savings_vs_always_max_pct"],
    }


def _pct(baseline: float, value: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - value) / baseline * 100, 1)


__all__ = [
    "EXAMPLE_RATES",
    "LOW_CONFIDENCE",
    "SPENDY_TIERS",
    "TIERS",
    "append_usage",
    "classify_task",
    "evaluate_tool",
    "gate_path",
    "ingest_user_prompt",
    "load_gate",
    "load_price_table",
    "record_confirmation",
    "route",
    "save_gate",
    "summarize_usage",
]
