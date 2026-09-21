#!/usr/bin/env python3
"""
Model Router Prototype — task classifier CLI
=============================================
Heuristic rubric (NOT ML). Demonstrates provider-agnostic Auto routing: pick the lightest model/effort
that still does the job well. Each result includes confidence (0–1). A vague prompt
below LOW_CONFIDENCE (0.55) is downshifted to standard — never guessed as max —
and needs_confirm is true for every non-fast tier.

Tiers (capability labels; not vendor product names)
----------------------------------------------------------------------
fast       Rename, format, short factual, clear procedure, short summarize.
           → cheapest/fastest configured model in the provider family.
standard   Multi-file edits, known patterns, moderate debugging with
           decent clues.
reasoning  Ambiguous requirements, unknown root-cause debug, architecture,
           security-sensitive.
max        Research-level / large redesign / hardest judgment.
           → strongest available in the configured family.

Backward-compatible aliases (accepted as expected labels in tests only via
normalize): low→fast, high→reasoning, frontier→max.

Usage
-----
  echo "rename foo to bar" | python3 classify.py
  python3 classify.py "debug why auth fails intermittently"
  python3 classify.py --suggest "debug why auth fails intermittently"
  python3 classify.py --examples
"""

from __future__ import annotations

import json
import re
import sys
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Signal patterns (prototype heuristics — intentionally simple & readable)
# ---------------------------------------------------------------------------

FAST_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(rename|reformat|format|lint|prettier|indent)\b", "formatting/rename procedure"),
    (r"\b(summarize|summarise|summariz\w*|tl;?dr|brief overview)\b", "short summarization"),
    (r"\b(what is|who is|when was|define|definition of)\b", "short factual question"),
    (r"\b(follow (these |the )?steps|step[- ]by[- ]step|according to|as specified)\b", "clear procedure given"),
    (r"\b(single[- ]file|one file|this file only)\b", "single-file scope"),
    (r"\b(typo|fix spelling|add a comment|update the comment)\b", "trivial edit"),
    (r"\b(convert|translate) .{0,40}\b(to|into)\b", "straightforward conversion"),
    (r"\b(list|enumerate|show me the)\b", "listing/enumeration"),
]

STANDARD_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(multi[- ]file|across (many |several |multiple )?files|a few files)\b", "multi-file edits"),
    (r"\b(known pattern|same pattern|boilerplate|scaffold|wire up)\b", "known patterns"),
    (r"\b(moderate debug|debug .{0,40}\b(with|given) .{0,40}\b(stack|trace|clue|log|error message))\b", "moderate debug with clues"),
    (r"\b(apply (the )?same (fix|change)|propagate|mirror the change)\b", "known-pattern propagation"),
    (r"\b(add (a |an )?(endpoint|handler|test|unit test)|implement (the )?CRUD)\b", "routine feature of known shape"),
]

REASONING_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(ambiguous|unclear|not sure|figure out|investigate)\b", "ambiguous requirements"),
    (r"\b(debug|root cause|intermittent|flaky|heisenbug|race condition)\b", "debugging unknown cause"),
    (r"\b(architect|architecture|design (a |the |system|api)|refactor (the )?architecture)\b", "architecture/design"),
    (r"\b(secur(e|ity)|auth(entication|orization)?|vulnerabilit|xss|csrf|injection|secret|credential)\b", "security-sensitive"),
    (r"\b(novel|from scratch|greenfield|new system|new feature set)\b", "novel design"),
    (r"\b(trade[- ]?off|evaluate options|compare approaches)\b", "judgment/tradeoffs"),
    (r"\b(migrat(e|ion)|rewrite|large refactor)\b", "substantial structural change"),
    (r"\b(why (does|is|are|did)|explain why)\b", "causal reasoning"),
    (r"\b(codebase[- ]wide)\b", "codebase-wide reasoning"),
]

MAX_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(research[- ]level|state[- ]of[- ]the[- ]art|SOTA)\b", "research-level ask"),
    (r"\b(prove|theorem|formal verification|complexity proof)\b", "hard formal reasoning"),
    (r"\b(redesign (the )?(entire|whole|full)|large ambiguous redesign|ground[- ]up redesign)\b", "large ambiguous redesign"),
    (r"\b(novel algorithm|invent (a |an )?new|open[- ]ended research)\b", "open-ended invention"),
    (r"\b(multi[- ]agent orchestration|distributed consensus from scratch)\b", "very hard systems design"),
]

# Soft length / complexity cues
WORD_COUNT_REASONING = 80
WORD_COUNT_MAX = 200

# Below this, a vague prompt must not be guessed upward (especially not max).
LOW_CONFIDENCE = 0.55

# Aliases for documentation / older labels
ALIAS_TO_TIER = {
    "low": "fast",
    "high": "reasoning",
    "frontier": "max",
}


def _match_signals(text: str, patterns: List[Tuple[str, str]]) -> List[str]:
    found: List[str] = []
    lower = text.lower()
    for pat, label in patterns:
        if re.search(pat, lower, re.IGNORECASE):
            if label not in found:
                found.append(label)
    return found


def _finalize(
    tier: str,
    reason: str,
    signals: List[str],
    conf: float,
    *,
    vague: bool,
    guessed_max: bool,
) -> dict:
    """Vague, low-confidence prompts default to standard — never a guessed max."""
    downshifted_from = None
    low = conf < LOW_CONFIDENCE
    signals = list(signals)
    if tier == "max" and low:
        guessed_max = True
    if guessed_max or (vague and low and tier != "standard"):
        downshifted_from = "max" if guessed_max or tier == "max" else tier
        if tier != "standard":
            tier = "standard"
        if downshifted_from == "max":
            reason = (
                "Low confidence on a vague prompt; defaulting to standard "
                "instead of guessing max. Explicit confirmation required."
            )
        else:
            reason = (
                "Low confidence on a vague prompt; defaulting to standard "
                "instead of guessing. Explicit confirmation required."
            )
        signals.append("low confidence downshift → standard")
    if not signals:
        signals = ["no patterned signals"]
    return {
        "tier": tier,
        "reason": reason,
        "signals": signals,
        "confidence": round(conf, 2),
        "needs_confirm": tier != "fast",
        "downshifted_from": downshifted_from,
    }


def classify(task: str) -> dict:
    """Return tier / reason / signals / confidence for a task description."""
    task = (task or "").strip()
    if not task:
        return {
            "tier": "fast",
            "reason": "Empty task; defaulting to lightest tier.",
            "signals": ["empty input"],
            "confidence": 0.3,
            "needs_confirm": False,
            "downshifted_from": None,
        }

    words = len(task.split())
    fast_s = _match_signals(task, FAST_PATTERNS)
    std_s = _match_signals(task, STANDARD_PATTERNS)
    reason_s = _match_signals(task, REASONING_PATTERNS)
    max_s = _match_signals(task, MAX_PATTERNS)

    signals: List[str] = []
    # Length alone used to force max. Only a vague brief (no tier patterns) counts as that guess.
    guessed_max = words >= WORD_COUNT_MAX and not (fast_s or std_s or reason_s or max_s)
    if words >= WORD_COUNT_MAX:
        signals.append(f"very long prompt ({words} words)")
    elif words >= WORD_COUNT_REASONING:
        signals.append(f"long prompt ({words} words)")
        if not reason_s and not max_s and not std_s:
            reason_s = reason_s + ["lengthy underspecified ask"]

    signals.extend(max_s)
    signals.extend(reason_s)
    signals.extend(std_s)
    signals.extend(fast_s)

    reversible = bool(
        re.search(
            r"\b(draft|prototype|try|experiment|reversible|can undo|dry[- ]run)\b",
            task,
            re.I,
        )
    )

    # Prefer lighter when mixed & reversible; never under-provision security/irreversible
    # Decision order: max > reasoning > standard > fast
    if max_s and not reversible:
        tier = "max"
        reason = (
            "Research-level / large redesign / hardest judgment signals; "
            "map to strongest available in the configured provider/model family."
        )
        conf = min(0.55 + 0.12 * len(max_s), 0.92)
    elif max_s and reversible:
        tier = "reasoning"
        reason = (
            "Max-ish wording but task looks reversible/experimental; "
            "route reasoning not max."
        )
        conf = 0.6
        signals.append("reversible — prefer lighter")
    elif reason_s and (fast_s or std_s):
        if reversible and not any(
            s in reason_s
            for s in ("security-sensitive", "debugging unknown cause", "architecture/design")
        ):
            # Mixed but reversible and not security/unknown-debug/arch → lighter
            tier = "standard" if std_s else "fast"
            reason = (
                "Mixed signals but task is reversible and not security/"
                "unknown-debug; prefer lighter tier."
            )
            conf = 0.55
            signals.append(f"mixed + reversible → {tier}")
        else:
            tier = "reasoning"
            reason = (
                "Mixed signals with ambiguity, unknown debug, architecture, "
                "or security cues; escalate to reasoning."
            )
            conf = 0.65
            signals.append("mixed → escalate to reasoning")
    elif reason_s:
        tier = "reasoning"
        reason = (
            "Ambiguous requirements, unknown-cause debug, architecture, "
            "or security-sensitive work."
        )
        conf = min(0.6 + 0.1 * len(reason_s), 0.9)
    elif std_s and fast_s:
        if reversible:
            tier = "fast"
            reason = "Mixed standard/fast signals but reversible; prefer fast."
            conf = 0.55
            signals.append("mixed + reversible → fast")
        else:
            tier = "standard"
            reason = "Multi-file / known-pattern work beyond a trivial single edit."
            conf = 0.65
            signals.append("mixed → standard")
    elif std_s:
        tier = "standard"
        reason = (
            "Multi-file edits, known patterns, or moderate debugging with "
            "decent clues; mid tier sufficient."
        )
        conf = min(0.6 + 0.1 * len(std_s), 0.9)
    elif fast_s:
        tier = "fast"
        reason = "Clear, bounded, low-judgment task; lightest configured provider tier."
        conf = min(0.6 + 0.1 * len(fast_s), 0.9)
    else:
        if words < 15:
            tier = "fast"
            reason = "Short ask with no escalation cues; default fast (prototype heuristic)."
            conf = 0.45
            signals.append("no strong signals; short → fast")
        else:
            tier = "standard"
            reason = (
                "No clear fast-tier cues and ask is non-trivial length; "
                "default standard (prefer not over-provisioning)."
            )
            conf = 0.5
            signals.append("no strong signals; default standard")

    vague = not (fast_s or std_s or reason_s or max_s)
    return _finalize(
        tier, reason, signals, conf, vague=vague, guessed_max=guessed_max
    )


EXAMPLES: List[Tuple[str, str]] = [
    ("Rename the variable foo to bar in utils.py", "fast"),
    ("Summarize this 3-paragraph email in two bullets", "fast"),
    ("What is the capital of France?", "fast"),
    ("Follow these steps to add a logging line to main.py", "fast"),
    ("Apply the same null-check pattern across a few files", "standard"),
    ("Wire up a CRUD endpoint using the existing handler pattern", "standard"),
    ("Debug why auth fails intermittently in production", "reasoning"),
    ("Design the architecture for a multi-tenant billing system", "reasoning"),
    ("Investigate ambiguous requirements and propose an API shape", "reasoning"),
    ("Review this auth change for XSS and credential leaks", "reasoning"),
    ("Prove a novel consensus algorithm and redesign the entire distributed store", "max"),
    ("Open-ended research: invent a new indexing approach for this corpus", "max"),
]


def suggest_line(task: str, result=None) -> str:
    """Human-facing Auto suggestion for the confirm/override UX."""
    result = result or classify(task)
    tier = result["tier"]
    why = result["reason"].rstrip(".")
    # Keep the spoken why short (first clause-ish)
    short_why = why
    if len(short_why) > 120:
        short_why = short_why[:117].rsplit(" ", 1)[0] + "…"
    note = ""
    if result.get("downshifted_from"):
        note = (
            f" Confidence {result['confidence']} is low, so this is standard "
            f"rather than {result['downshifted_from']}."
        )
    return (
        f"Auto suggests **{tier}** — {short_why}.{note} "
        "Confirm to run, or override (fast | standard | reasoning | max)."
    )


def print_suggestion(task: str) -> dict:
    result = classify(task)
    print(suggest_line(task, result))
    print("--- JSON ---")
    print(json.dumps(result, indent=2))
    return result


def print_examples() -> None:
    print("Prototype rubric examples — provider-agnostic Auto:\n")
    print("UX: classify → suggest → user confirm/override → run\n")
    passed = 0
    failed = 0
    for task, expected in EXAMPLES:
        result = classify(task)
        ok = result["tier"] == expected
        mark = "✓" if ok else "✗"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"{mark} expected={expected:10} got={result['tier']:10}  {task}")
        print(f"   reason: {result['reason']}")
        print(f"   signals: {result['signals']}")
        print(f"   confidence: {result['confidence']}")
        print(f"   suggest: {suggest_line(task, result)}")
        print()
    print(f"Summary: {passed}/{passed + failed} passed")
    print("--- JSON ---")
    out = [{"task": t, "expected": e, "result": classify(t)} for t, e in EXAMPLES]
    print(json.dumps(out, indent=2))
    return failed == 0


def main(argv: List[str]) -> int:
    if len(argv) >= 2 and argv[1] in ("--examples", "-e"):
        ok = print_examples()
        return 0 if ok else 1

    if len(argv) >= 2 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0

    if len(argv) >= 2 and argv[1] in ("--suggest", "-s"):
        if len(argv) >= 3:
            task = " ".join(argv[2:])
        else:
            if sys.stdin.isatty():
                print(
                    "Usage: classify.py --suggest <task>\n"
                    "Or pipe a task on stdin with --suggest.",
                    file=sys.stderr,
                )
                return 2
            task = sys.stdin.read()
        print_suggestion(task)
        return 0

    if len(argv) >= 2:
        task = " ".join(argv[1:])
    else:
        if sys.stdin.isatty():
            print(
                "Usage: classify.py <task> | classify.py --examples\n"
                "Or pipe a task description on stdin.",
                file=sys.stderr,
            )
            return 2
        task = sys.stdin.read()

    print(json.dumps(classify(task), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
