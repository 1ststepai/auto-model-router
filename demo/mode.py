"""Execution-mode axis for Auto Model Router.

Advisory only: does not launch Cursor/Codex/cloud agents.
"""
from __future__ import annotations

from typing import List, Tuple

MODE_STEERING_PATTERNS: List[Tuple[str, str]] = [
    (r"\\b(steer|iterate|tweak|adjust|review this|look at this|in this chat|walk me through)\\b", "interactive steering"),
    (r"\\b(blocking|blocking on|can't proceed|need this now|right now|while I wait)\\b", "blocking dependency"),
]

MODE_CLOUD_PATTERNS: List[Tuple[str, str]] = [
    (r"\\b(overnight|background|while I am away|unattended|don't wait|do not wait)\\b", "unattended batch"),
    (r"\\b(long[- ]running|hours? of work|full migration|entire codebase|overnight refactor)\\b", "long-running"),
]


def decide_mode(
    *,
    tier: str,
    high_risk: bool,
    reversible: bool,
    signals: List[str],
) -> Tuple[str, str]:
    if high_risk:
        return "local", "high-risk work stays in-session"
    if any(s in ("interactive steering", "blocking dependency") for s in signals):
        return "local", "steering or blocking — must stay in-session"
    if any(s in ("unattended batch", "long-running") for s in signals) and tier in ("reasoning", "max"):
        return "cloud", "long unattended work; cloud frees the session"
    if tier == "fast" and reversible:
        return "local", "quick reversible work; local is cheaper"
    return "local", "default local"
