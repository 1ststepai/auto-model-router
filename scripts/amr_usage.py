#!/usr/bin/env python3
"""Shared local usage-log helpers for Auto Model Router / Savings Desk.

Honest scope: reads only local JSON/JSONL routing logs and ~/.auto-model-router
config. Does not call or scrape Cursor, Claude Code, Codex, Gemini, or any
vendor billing/quota/token API.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TIERS = ("fast", "standard", "reasoning", "max")
TIER_RANK = {tier: index for index, tier in enumerate(TIERS)}
EXAMPLE_RATES = {"fast": 1.0, "standard": 3.0, "reasoning": 8.0, "max": 20.0}
HEAVY_TIERS = ("reasoning", "max")
KNOWN_HOSTS = ("cursor", "claude-code", "codex", "gemini")

# Non-sensitive task_kind labels that usually belong on fast/standard.
# Used only when the log already has task_kind — never inferred from prompts.
LIGHT_TASK_KINDS = frozenset(
    {
        "rename",
        "format",
        "lint",
        "comment",
        "docs",
        "doc",
        "summarize",
        "summary",
        "typo",
        "list",
        "factual",
        "procedure",
        "indent",
        "boilerplate",
    }
)

DEFAULT_HOSTS = ["cursor", "claude-code", "codex"]

DEFAULT_CONFIG: Dict[str, Any] = {
    "openDashboardOnApply": True,
    "weeklyReview": False,
    "auditOptIn": False,
    "hosts": list(DEFAULT_HOSTS),
    "usageLogPath": "",
    "boundaryGatedConfirms": False,
}

COLLECTED_FIELDS = (
    "timestamp",
    "tier",
    "suggested_tier",
    "confirmed",
    "overridden",
    "host",
    "task_kind",
    "gate",
)

NEVER_COLLECTED = (
    "prompts",
    "task text",
    "code",
    "secrets",
    "customer data",
    "vendor credentials",
    "billing/quota API data",
)


def amr_home() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
    if not home:
        raise SystemExit("error: HOME / USERPROFILE is not set")
    return Path(home) / ".auto-model-router"


def config_path() -> Path:
    return amr_home() / "config.json"


def default_usage_log() -> Path:
    return amr_home() / "logs" / "usage.jsonl"


def maps_dir() -> Path:
    return amr_home()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def normalize_hosts(value: Any) -> List[str]:
    if value is None:
        return list(DEFAULT_HOSTS)
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace(";", ",").split(",")]
        return [part for part in parts if part]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [str(item).strip() for item in value if str(item).strip()]
    return list(DEFAULT_HOSTS)


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or config_path()
    cfg = dict(DEFAULT_CONFIG)
    cfg["hosts"] = list(DEFAULT_HOSTS)
    if not cfg_path.is_file():
        return cfg
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cfg
    if not isinstance(data, dict):
        return cfg
    cfg.update(data)
    cfg["openDashboardOnApply"] = as_bool(cfg.get("openDashboardOnApply", True))
    cfg["weeklyReview"] = as_bool(cfg.get("weeklyReview", False))
    cfg["auditOptIn"] = as_bool(cfg.get("auditOptIn", False))
    cfg["boundaryGatedConfirms"] = as_bool(cfg.get("boundaryGatedConfirms", False))
    cfg["hosts"] = normalize_hosts(cfg.get("hosts", DEFAULT_HOSTS))
    cfg["usageLogPath"] = str(cfg.get("usageLogPath") or "")
    return cfg


def save_config(updates: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = load_config(cfg_path)
    cfg.update(updates)
    if "hosts" in cfg:
        cfg["hosts"] = normalize_hosts(cfg.get("hosts"))
    for key in ("openDashboardOnApply", "weeklyReview", "auditOptIn", "boundaryGatedConfirms"):
        if key in cfg:
            cfg[key] = as_bool(cfg[key])
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return cfg


def resolve_usage_log(cfg: Optional[Dict[str, Any]] = None, override: Optional[Path] = None) -> Path:
    if override is not None:
        return Path(override).expanduser()
    cfg = cfg if cfg is not None else load_config()
    raw = str(cfg.get("usageLogPath") or "").strip()
    if raw:
        return Path(os.path.expanduser(raw))
    return default_usage_log()


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


def _tier(value: Any) -> Optional[str]:
    tier = str(value or "").strip().lower()
    return tier if tier in TIERS else None


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and _tier(obj.get("tier")):
            entries.append(obj)
    return entries


def load_sample_json(path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return entries_from_payload(payload)


def entries_from_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = None
        for key in ("decisions", "usage", "log", "entries"):
            if isinstance(payload.get(key), list):
                raw = payload[key]
                break
        if raw is None:
            return []
    else:
        return []
    return [item for item in raw if isinstance(item, dict) and _tier(item.get("tier"))]


def load_usage_entries(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8").lstrip()
    if not text:
        return []
    if text.startswith("{") or text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return load_jsonl(path)
        loaded = entries_from_payload(payload)
        if loaded:
            return loaded
    return load_jsonl(path)


def sample_log_candidates() -> List[Path]:
    here = Path(__file__).resolve()
    return [
        amr_home() / "demo" / "sample_usage_log.json",
        here.parent.parent / "demo" / "sample_usage_log.json",
        here.parent / "sample_usage_log.json",
    ]


def filter_window(
    entries: List[Dict[str, Any]], *, days: Optional[int], now: datetime
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (in_window, missing_timestamp). days=None keeps all dated rows."""
    if days is None:
        return list(entries), []
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


def percent_saved(baseline: float, routed: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - routed) / baseline * 100, 1)


def _task_kind(item: Dict[str, Any]) -> str:
    return str(item.get("task_kind") or "").strip().lower()


def is_light_task_kind(kind: str) -> bool:
    return kind in LIGHT_TASK_KINDS


def filter_hosts(entries: Iterable[Dict[str, Any]], hosts: Optional[Sequence[str]]) -> List[Dict[str, Any]]:
    if not hosts:
        return list(entries)
    allowed = {str(host).strip().lower() for host in hosts if str(host).strip()}
    if not allowed:
        return list(entries)
    selected: List[Dict[str, Any]] = []
    for item in entries:
        host = str(item.get("host") or "").strip().lower()
        if host in allowed:
            selected.append(item)
    return selected


def summarize(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_tier: Counter[str] = Counter()
    hosts: Counter[str] = Counter()
    task_kinds: Counter[str] = Counter()
    gates: Counter[str] = Counter()
    confirmed = 0
    overridden = 0
    routed = 0.0
    switch_downs = 0
    switch_ups = 0
    host_units: Dict[str, float] = {}
    host_tiers: Dict[str, Counter[str]] = {}
    heavy_on_light: List[Dict[str, Any]] = []

    for item in entries:
        tier = _tier(item.get("tier"))
        if not tier:
            continue
        by_tier[tier] += 1
        routed += EXAMPLE_RATES[tier]
        if as_bool(item.get("confirmed")):
            confirmed += 1
        if as_bool(item.get("overridden")):
            overridden += 1

        host = str(item.get("host") or "").strip() or "unspecified"
        hosts[host] += 1
        host_units[host] = host_units.get(host, 0.0) + EXAMPLE_RATES[tier]
        host_tiers.setdefault(host, Counter())[tier] += 1

        kind = _task_kind(item)
        if kind:
            task_kinds[kind] += 1

        gate = str(item.get("gate") or "").strip().lower()
        if gate:
            gates[gate] += 1

        suggested = _tier(item.get("suggested_tier"))
        if suggested:
            if TIER_RANK[tier] < TIER_RANK[suggested]:
                switch_downs += 1
            elif TIER_RANK[tier] > TIER_RANK[suggested]:
                switch_ups += 1

        if tier in HEAVY_TIERS and kind and is_light_task_kind(kind):
            heavy_on_light.append(
                {
                    "timestamp": item.get("timestamp"),
                    "host": host,
                    "tier": tier,
                    "task_kind": kind,
                    "suggested_tier": suggested,
                }
            )

    count = sum(by_tier.values())
    always_reasoning = count * EXAMPLE_RATES["reasoning"]
    always_max = count * EXAMPLE_RATES["max"]
    burns_by_host = {
        host: {
            "count": hosts[host],
            "relative_units": round(host_units.get(host, 0.0), 2),
            "tasks_by_tier": {tier: host_tiers[host].get(tier, 0) for tier in TIERS},
        }
        for host in sorted(hosts)
    }

    return {
        "task_count": count,
        "tasks_by_tier": {tier: by_tier.get(tier, 0) for tier in TIERS},
        "confirmed_count": confirmed,
        "override_count": overridden,
        "confirm_rate_pct": round(confirmed / count * 100, 1) if count else 0.0,
        "override_rate_pct": round(overridden / count * 100, 1) if count else 0.0,
        "hosts": dict(hosts),
        "burns_by_host": burns_by_host,
        "task_kinds": dict(task_kinds),
        "gates": dict(gates),
        "heavy_on_light_count": len(heavy_on_light),
        "heavy_on_light": heavy_on_light,
        "switch_down_count": switch_downs,
        "switch_up_count": switch_ups,
        "routed_relative_units": round(routed, 2),
        "always_reasoning_relative_units": round(always_reasoning, 2),
        "always_max_relative_units": round(always_max, 2),
        "estimated_savings_vs_always_reasoning_pct": percent_saved(always_reasoning, routed),
        "estimated_savings_vs_always_max_pct": percent_saved(always_max, routed),
        "rates_are": "illustrative relative example units, not vendor prices",
        "example_rates": dict(EXAMPLE_RATES),
        "billing_api_accessed": False,
    }


def next_actions(summary: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    """Concrete follow-ups after an audit. Complements the skill; does not replace hosts."""
    actions: List[Dict[str, str]] = []
    if not as_bool(cfg.get("auditOptIn")):
        actions.append(
            {
                "id": "enable-audit",
                "title": "Opt in to the local usage audit",
                "detail": "Set auditOptIn=true in ~/.auto-model-router/config.json "
                "(or run ./scripts/apply.sh --enable-audit). Nothing is logged until you consent.",
            }
        )
    if not as_bool(cfg.get("boundaryGatedConfirms")):
        actions.append(
            {
                "id": "enable-boundary-gates",
                "title": "Enable boundary-gated confirms",
                "detail": "Confirm only at risk/ambiguity boundaries to avoid confirm-fatigue. "
                "Apply recommendations writes boundaryGatedConfirms=true and points at docs/boundary-gated-confirms.md.",
            }
        )

    fast_hosts = []
    burns = summary.get("burns_by_host") or {}
    for host, stats in burns.items():
        if stats.get("tasks_by_tier", {}).get("fast") or any(
            row.get("host") == host for row in summary.get("heavy_on_light") or []
        ):
            fast_hosts.append(host)
    if summary.get("heavy_on_light_count") or not _map_exists("cursor"):
        host_hint = ", ".join(sorted(set(fast_hosts))) or "your configured hosts"
        actions.append(
            {
                "id": "map-fast",
                "title": f"Map fast → a cheap/fast picker on {host_hint}",
                "detail": "Write local cursor-tier-map.json (and Claude/Codex stubs) so the skill "
                "can name a concrete switch-down. AMR does not flip the host picker itself.",
            }
        )
    if not as_bool(cfg.get("weeklyReview")):
        actions.append(
            {
                "id": "weekly-digest",
                "title": "Turn on the weekly digest",
                "detail": "Enable weeklyReview and optionally --install-schedule. Local log only — not vendor billing.",
            }
        )
    if not actions:
        actions.append(
            {
                "id": "keep-logging",
                "title": "Keep logging locally and re-run the audit after more sessions",
                "detail": "Policy maps and boundary gates are already enabled. Relative units stay estimates.",
            }
        )
    return actions


def _map_exists(host: str) -> bool:
    names = {
        "cursor": "cursor-tier-map.json",
        "claude-code": "claude-tier-map.json",
        "codex": "codex-tier-map.json",
        "gemini": "gemini-tier-map.json",
    }
    name = names.get(host)
    if not name:
        return False
    return (maps_dir() / name).is_file()


def honesty_lines() -> List[str]:
    return [
        "Honest scope: local usage log only. Not live Cursor/Claude/Codex/Gemini billing.",
        "Rates below are illustrative relative units (fast=1x, standard=3x, reasoning=8x, max=20x).",
        "Collected when you opt in: " + ", ".join(COLLECTED_FIELDS) + ".",
        "Never collected: " + ", ".join(NEVER_COLLECTED) + ".",
    ]
