#!/usr/bin/env python3
"""
Model Router Prototype — task classifier CLI
=============================================
Heuristic rubric (NOT ML). Demonstrates provider-agnostic Auto routing: pick the lightest model/effort
that still does the job well.

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

Confirm gate (heuristic, not ML)
--------------------------------
hard_gate      Must wait: security/secrets/auth, purchases, sends, irreversible.
auto_continue  Do not block: clearly fast (or strongly-fitting standard),
               reversible, not near a tier boundary, user did not demand confirm.
confirm        Wait: near-boundary, ambiguous/architecture, high-risk, or
               escalation after a failed light attempt.

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

# Irreversible / high-risk cues that always hard-gate (also keep tier at least reasoning)
HARD_GATE_PATTERNS: List[Tuple[str, str]] = [
    (
        r"\b(secur(e|ity)|auth(entication|orization)?|vulnerabilit|xss|csrf|injection|secret|credential|password|api[- ]?key)\b",
        "security/secrets/auth",
    ),
    (r"\b(purchas\w*|process( a| the)? payment|charge the customer|buy now)\b", "purchase/payment"),
    (
        r"\b(send (an? )?(email|sms|newsletter)|email (all |every )?customers|notify (all )?customers)\b",
        "irreversible send",
    ),
    (
        r"\b(deploy to prod(uction)?|drop (the )?(table|database)|delete production|force[- ]push)\b",
        "irreversible external action",
    ),
]

USER_CONFIRM_PATTERNS: List[Tuple[str, str]] = [
    (
        r"\b(choose carefully|pick carefully|confirm (first|before)|ask me (first|before)|"
        r"wait for (my )?confirm|don'?t auto-?continue|require confirm)\b",
        "user requested confirm",
    ),
]

ESCALATION_PATTERNS: List[Tuple[str, str]] = [
    (
        r"\b((light|fast) attempt (failed|did not work)|failed light attempt|"
        r"that didn'?t work[,.]? try (again|a stronger|reasoning|max)|escalate (to|after))\b",
        "escalation after failed light attempt",
    ),
]

# Labels that count as easy-undo / no side-effect work for the confirm gate
REVERSIBLE_SIGNAL_LABELS = {
    "formatting/rename procedure",
    "short summarization",
    "short factual question",
    "trivial edit",
    "single-file scope",
    "listing/enumeration",
    "clear procedure given",
    "straightforward conversion",
    "multi-file edits",
    "known patterns",
    "known-pattern propagation",
    "routine feature of known shape",
    "moderate debug with clues",
}

TIER_ORDER = ("fast", "standard", "reasoning", "max")
HARD_GATE_LABELS = {
    "security-sensitive",
    "security/secrets/auth",
    "purchase/payment",
    "irreversible send",
    "irreversible external action",
}
CLEAR_STANDARD_MIN_CONFIDENCE = 0.7

# Soft length / complexity cues
WORD_COUNT_REASONING = 80
WORD_COUNT_MAX = 200

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


def _families_present(fast_s: List[str], std_s: List[str], reason_s: List[str], max_s: List[str]) -> List[str]:
    return [
        name
        for name, hits in (
            ("fast", fast_s),
            ("standard", std_s),
            ("reasoning", reason_s),
            ("max", max_s),
        )
        if hits
    ]


def _adjacent_families(families: List[str]) -> bool:
    idxs = [TIER_ORDER.index(f) for f in families]
    return any(abs(a - b) == 1 for i, a in enumerate(idxs) for b in idxs[i + 1 :])


def _is_reversible(task: str, matched_labels: List[str], high_risk: bool) -> bool:
    """Easy-undo / no side-effect work. High-risk actions are never treated as reversible."""
    if high_risk:
        return False
    if re.search(
        r"\b(draft|prototype|try|experiment|reversible|can undo|easy undo|dry[- ]run|local edit)\b",
        task,
        re.I,
    ):
        return True
    return any(label in REVERSIBLE_SIGNAL_LABELS for label in matched_labels)


def decide_gate(
    *,
    tier: str,
    high_risk: bool,
    reversible: bool,
    near_boundary: bool,
    user_requested_confirm: bool,
    escalation: bool,
    confidence: float,
    families: List[str],
) -> Tuple[str, str]:
    """Return (gate, gate_reason). Honest rubric — not a learned model."""
    if high_risk:
        return "hard_gate", "security-sensitive, secrets/auth, purchase, send, or irreversible action"
    if user_requested_confirm:
        return "confirm", "user asked Auto to choose carefully / confirm first"
    if escalation:
        return "confirm", "escalation after a failed light attempt"
    if near_boundary:
        return "confirm", "signals sit near a tier boundary"
    if tier in ("reasoning", "max"):
        return "confirm", "ambiguous, architectural, or high-judgment work"
    if tier == "fast" and reversible:
        return "auto_continue", "clear fast reversible work"
    if (
        tier == "standard"
        and reversible
        and families == ["standard"]
        and confidence >= CLEAR_STANDARD_MIN_CONFIDENCE
    ):
        return "auto_continue", "clear standard fit; reversible local work"
    return "confirm", "not a clear auto-continue case"


def classify(task: str) -> dict:
    """Return tier, reason, signals, confidence, and heuristic confirm-gate fields."""
    task = (task or "").strip()
    if not task:
        return {
            "tier": "fast",
            "reason": "Empty task; defaulting to lightest tier.",
            "signals": ["empty input"],
            "confidence": 0.3,
            "reversible": False,
            "high_risk": False,
            "near_boundary": True,
            "gate": "confirm",
            "gate_reason": "empty or unspecified task; not a clear auto-continue case",
        }

    words = len(task.split())
    fast_s = _match_signals(task, FAST_PATTERNS)
    std_s = _match_signals(task, STANDARD_PATTERNS)
    reason_s = _match_signals(task, REASONING_PATTERNS)
    max_s = _match_signals(task, MAX_PATTERNS)
    hard_s = _match_signals(task, HARD_GATE_PATTERNS)
    user_confirm_s = _match_signals(task, USER_CONFIRM_PATTERNS)
    escalation_s = _match_signals(task, ESCALATION_PATTERNS)

    signals: List[str] = []
    if words >= WORD_COUNT_MAX:
        signals.append(f"very long prompt ({words} words)")
        if "long ambiguous brief" not in max_s:
            max_s = max_s + ["long ambiguous brief"]
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

    if not signals:
        signals = ["no patterned signals"]

    high_risk = bool(hard_s) or any(label in HARD_GATE_LABELS for label in reason_s)
    if high_risk:
        for label in hard_s:
            if label not in signals:
                signals.append(label)
        if tier in ("fast", "standard"):
            tier = "reasoning"
            reason = (
                "Security-sensitive or irreversible external action; "
                "never under-provision (at least reasoning)."
            )
            conf = max(conf, 0.7)
            signals.append("high-risk → at least reasoning")

    families = _families_present(fast_s, std_s, reason_s, max_s)
    mixed_decision = any(
        s.startswith("mixed") or s.startswith("reversible —") or "mixed +" in s
        for s in signals
    )
    # Honest heuristic: adjacent-tier hits or a mixed-signal decision, not a learned score.
    near_boundary = bool(_adjacent_families(families) or mixed_decision)
    if near_boundary and "near-boundary / ambiguous families" not in signals:
        signals.append("near-boundary / ambiguous families")

    reversible = _is_reversible(task, fast_s + std_s + signals, high_risk)
    user_requested_confirm = bool(user_confirm_s)
    escalation = bool(escalation_s)
    if user_requested_confirm:
        signals.extend(label for label in user_confirm_s if label not in signals)
    if escalation:
        signals.extend(label for label in escalation_s if label not in signals)

    gate, gate_reason = decide_gate(
        tier=tier,
        high_risk=high_risk,
        reversible=reversible,
        near_boundary=near_boundary,
        user_requested_confirm=user_requested_confirm,
        escalation=escalation,
        confidence=round(conf, 2),
        families=families,
    )

    return {
        "tier": tier,
        "reason": reason,
        "signals": signals,
        "confidence": round(conf, 2),
        "reversible": reversible,
        "high_risk": high_risk,
        "near_boundary": near_boundary,
        "gate": gate,
        "gate_reason": gate_reason,
    }


# (task, expected_tier, expected_gate)
EXAMPLES: List[Tuple[str, str, str]] = [
    ("Rename the variable foo to bar in utils.py", "fast", "auto_continue"),
    ("Summarize this 3-paragraph email in two bullets", "fast", "auto_continue"),
    ("What is the capital of France?", "fast", "auto_continue"),
    ("Follow these steps to add a logging line to main.py", "fast", "auto_continue"),
    ("Apply the same null-check pattern across a few files", "standard", "auto_continue"),
    ("Wire up a CRUD endpoint using the existing handler pattern", "standard", "auto_continue"),
    (
        "Rename the helper and apply the same null-check pattern across a few files",
        "standard",
        "confirm",
    ),
    ("Debug why auth fails intermittently in production", "reasoning", "hard_gate"),
    ("Design the architecture for a multi-tenant billing system", "reasoning", "confirm"),
    ("Investigate ambiguous requirements and propose an API shape", "reasoning", "confirm"),
    ("Review this auth change for XSS and credential leaks", "reasoning", "hard_gate"),
    ("Choose carefully: rename foo to bar in utils.py", "fast", "confirm"),
    ("Send a newsletter to all customers about the outage", "reasoning", "hard_gate"),
    (
        "The light attempt failed; escalate after that debug of the timeout",
        "reasoning",
        "confirm",
    ),
    ("Prove a novel consensus algorithm and redesign the entire distributed store", "max", "confirm"),
    ("Open-ended research: invent a new indexing approach for this corpus", "max", "confirm"),
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
    gate = result.get("gate", "confirm")
    if gate == "auto_continue":
        return f"Auto continues on **{tier}** — {short_why}."
    if gate == "hard_gate":
        return (
            f"Auto suggests **{tier}** — {short_why}. "
            "Confirm required (high-risk / hard to undo), or override "
            "(fast | standard | reasoning | max)."
        )
    return (
        f"Auto suggests **{tier}** — {short_why}. "
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
    print("UX: classify → suggest → boundary-gated confirm/override → run\n")
    passed = 0
    failed = 0
    for task, expected_tier, expected_gate in EXAMPLES:
        result = classify(task)
        ok = result["tier"] == expected_tier and result.get("gate") == expected_gate
        mark = "✓" if ok else "✗"
        if ok:
            passed += 1
        else:
            failed += 1
        print(
            f"{mark} expected={expected_tier:10}/{expected_gate:13} "
            f"got={result['tier']:10}/{result.get('gate')}  {task}"
        )
        print(f"   reason: {result['reason']}")
        print(f"   signals: {result['signals']}")
        print(
            f"   confidence: {result['confidence']}  "
            f"near_boundary: {result.get('near_boundary')}  "
            f"high_risk: {result.get('high_risk')}  "
            f"reversible: {result.get('reversible')}"
        )
        print(f"   gate: {result.get('gate')} — {result.get('gate_reason')}")
        print(f"   suggest: {suggest_line(task, result)}")
        print()
    print(f"Summary: {passed}/{passed + failed} passed")
    print("--- JSON ---")
    out = [
        {"task": t, "expected_tier": e, "expected_gate": g, "result": classify(t)}
        for t, e, g in EXAMPLES
    ]
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
