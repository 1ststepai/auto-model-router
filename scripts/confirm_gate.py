#!/usr/bin/env python3
"""Pre-tool confirm gate for Codex, Claude Code, and Cursor hooks.

Exit 2 denies the tool call. Tool arguments cannot confirm themselves.
A user prompt hook (or this script's --confirm, run outside the agent)
is what records confirmation.

  # user terminal, not an agent tool:
  python3 scripts/confirm_gate.py --suggest "Wire up a CRUD endpoint"
  python3 scripts/confirm_gate.py --confirm standard

Hook stdin is the host JSON payload. See hooks/*.json and INSTALL.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for _base in (ROOT, ROOT.parent):
    if (_base / "auto_model_router.py").is_file() and str(_base) not in sys.path:
        sys.path.insert(0, str(_base))
        break

from auto_model_router import (  # noqa: E402
    evaluate_tool,
    ingest_user_prompt,
    load_gate,
    record_confirmation,
    save_gate,
)


def _emit(decision: dict) -> None:
    reason = decision["reason"]
    if decision["allowed"]:
        json.dump({"permission": "allow"}, sys.stdout)
        sys.stdout.write("\n")
        return
    body = {
        "permission": "deny",
        "user_message": reason,
        "agent_message": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }
    json.dump(body, sys.stdout)
    sys.stdout.write("\n")
    print(reason, file=sys.stderr)


def _is_tool_event(payload: dict) -> bool:
    if payload.get("tool_name") or payload.get("tool_input") or payload.get("toolInput"):
        return True
    event = str(payload.get("hook_event_name") or payload.get("event") or "")
    return event.lower() in {"pretooluse", "beforeshellexecution", "beforemcpexecution"}


def handle_payload(payload: dict, state_file: Path) -> int:
    if _is_tool_event(payload):
        decision = evaluate_tool(load_gate(state_file), payload)
        _emit(decision)
        return 0 if decision["allowed"] else 2
    event = str(payload.get("hook_event_name") or payload.get("event") or "")
    if "prompt" in payload or event in {"UserPromptSubmit", "beforeSubmitPrompt"}:
        text = payload.get("prompt")
        if text is None:
            text = payload.get("user_message") or payload.get("text") or ""
        state = ingest_user_prompt(str(text), load_gate(state_file))
        save_gate(state, state_file)
        _emit({"allowed": True, "reason": "user prompt recorded"})
        return 0
    print("blocked: unrecognized hook payload", file=sys.stderr)
    _emit({
        "allowed": False,
        "reason": "blocked: unrecognized hook payload; refusing tool execution",
    })
    return 2


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suggest", metavar="TASK", help="classify a task and store an unconfirmed gate")
    parser.add_argument("--confirm", metavar="TIER", help="record an explicit user confirm (run outside the agent)")
    parser.add_argument("--state", type=Path, default=None, help="gate file (default: $AUTO_MODEL_ROUTER_GATE or .auto-model-router/gate.json)")
    parser.add_argument("--status", action="store_true", help="print the current gate file")
    args = parser.parse_args(argv[1:])

    if args.confirm:
        state = record_confirmation(args.confirm, path=args.state)
        print(json.dumps(state))
        return 0
    if args.suggest:
        state = ingest_user_prompt(args.suggest, None)
        save_gate(state, args.state)
        print(json.dumps(state, indent=2))
        return 0
    if args.status:
        print(json.dumps(load_gate(args.state), indent=2))
        return 0

    if sys.stdin.isatty():
        parser.print_help()
        return 2
    raw = sys.stdin.read()
    if not raw.strip():
        print("blocked: empty hook payload", file=sys.stderr)
        return 2
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"blocked: invalid hook JSON ({exc})", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("blocked: hook payload must be a JSON object", file=sys.stderr)
        return 2
    return handle_payload(payload, args.state)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
