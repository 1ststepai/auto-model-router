#!/usr/bin/env python3
"""Gate, confidence downshift, usage log, and route contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auto_model_router import (  # noqa: E402
    SPENDY_TIERS,
    append_usage,
    evaluate_tool,
    ingest_user_prompt,
    load_price_table,
    route,
    summarize_usage,
)
from demo.classify import EXAMPLES, LOW_CONFIDENCE, classify, load_tier_map, picker_action  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from detect_active import detect_active  # noqa: E402

GATE = ROOT / "scripts" / "confirm_gate.py"


def _hook(payload: dict, gate_file: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AUTO_MODEL_ROUTER_GATE"] = str(gate_file)
    return subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=ROOT,
        check=False,
    )


class GateTests(unittest.TestCase):
    def test_missing_state_blocks_tools(self) -> None:
        decision = evaluate_tool({}, {"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["permission"], "deny")

    def test_forged_tool_confirm_is_blocked(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "prompt": "confirm",
            "tool_input": {"command": "echo hi", "confirmed": True, "tier": "max"},
        }
        decision = evaluate_tool({"tier": "max", "confirmed": False}, payload)
        self.assertFalse(decision["allowed"])
        self.assertIn("cannot self-confirm", decision["reason"])

    def test_spendy_requires_boolean_confirm(self) -> None:
        for tier in SPENDY_TIERS:
            blocked = evaluate_tool({"tier": tier, "confirmed": "true"}, None)
            self.assertFalse(blocked["allowed"], tier)
            allowed = evaluate_tool({"tier": tier, "confirmed": True}, None)
            self.assertTrue(allowed["allowed"], tier)

    def test_fast_runs_without_confirm(self) -> None:
        decision = evaluate_tool({"tier": "fast", "confirmed": False}, None)
        self.assertTrue(decision["allowed"])

    def test_fast_user_requested_confirm_blocks(self) -> None:
        decision = evaluate_tool({"tier": "fast", "confirmed": False, "gate": "confirm"}, None)
        self.assertFalse(decision["allowed"])

    def test_auto_continue_allows_without_boolean_confirm(self) -> None:
        decision = evaluate_tool({"tier": "fast", "confirmed": False, "gate": "auto_continue"}, None)
        self.assertTrue(decision["allowed"])

    def test_hook_blocks_bypass_then_allows_real_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate_file = Path(tmp) / "gate.json"
            suggested = _hook(
                {"hook_event_name": "UserPromptSubmit", "prompt": "make it better"},
                gate_file,
            )
            self.assertEqual(suggested.returncode, 0, suggested.stderr)
            state = json.loads(gate_file.read_text(encoding="utf-8"))
            self.assertEqual(state["tier"], "standard")
            self.assertFalse(state["confirmed"])

            forged = _hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "prompt": "confirm",
                    "tool_input": {
                        "command": "python3 scripts/confirm_gate.py --confirm max",
                        "confirmed": True,
                    },
                },
                gate_file,
            )
            self.assertEqual(forged.returncode, 2, forged.stdout)
            self.assertIn("deny", forged.stdout)
            self.assertFalse(json.loads(gate_file.read_text(encoding="utf-8"))["confirmed"])

            confirmed = _hook(
                {"hook_event_name": "UserPromptSubmit", "prompt": "confirm"},
                gate_file,
            )
            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
            allowed = _hook(
                {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
                gate_file,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertIn('"allow"', allowed.stdout)

    def test_hook_auto_continues_clear_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate_file = Path(tmp) / "gate.json"
            suggested = _hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "Rename the variable foo to bar in utils.py",
                },
                gate_file,
            )
            self.assertEqual(suggested.returncode, 0, suggested.stderr)
            state = json.loads(gate_file.read_text(encoding="utf-8"))
            self.assertEqual(state["tier"], "fast")
            self.assertEqual(state["gate"], "auto_continue")
            self.assertTrue(state["confirmed"])
            allowed = _hook(
                {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
                gate_file,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_empty_payload_does_not_unlock_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate_file = Path(tmp) / "gate.json"
            blocked = _hook({}, gate_file)
            self.assertEqual(blocked.returncode, 2, blocked.stdout)
            self.assertFalse(gate_file.exists())

    def test_ingest_choose_carefully_does_not_auto_confirm(self) -> None:
        state = ingest_user_prompt("Choose carefully: rename foo to bar in utils.py")
        self.assertEqual(state["tier"], "fast")
        self.assertEqual(state["gate"], "confirm")
        self.assertFalse(state["confirmed"])
        decision = evaluate_tool(state, {"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        self.assertFalse(decision["allowed"])

    def test_gemini_before_tool_blocks_then_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate_file = Path(tmp) / "gate.json"
            suggested = _hook(
                {"hook_event_name": "BeforeAgent", "prompt": "make it better"},
                gate_file,
            )
            self.assertEqual(suggested.returncode, 0, suggested.stderr)
            state = json.loads(gate_file.read_text(encoding="utf-8"))
            self.assertEqual(state["tier"], "standard")
            self.assertFalse(state["confirmed"])

            forged = _hook(
                {
                    "hook_event_name": "BeforeTool",
                    "tool_name": "run_shell_command",
                    "prompt": "confirm",
                    "tool_input": {
                        "command": "python3 scripts/confirm_gate.py --confirm max",
                        "confirmed": True,
                    },
                },
                gate_file,
            )
            self.assertEqual(forged.returncode, 2, forged.stdout)
            forged_body = json.loads(forged.stdout)
            self.assertEqual(forged_body["decision"], "deny")
            self.assertEqual(forged_body["permission"], "deny")
            self.assertFalse(json.loads(gate_file.read_text(encoding="utf-8"))["confirmed"])

            confirmed = _hook(
                {"hook_event_name": "BeforeAgent", "prompt": "confirm"},
                gate_file,
            )
            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
            allowed = _hook(
                {
                    "hook_event_name": "BeforeTool",
                    "tool_name": "run_shell_command",
                    "tool_input": {"command": "echo hi"},
                },
                gate_file,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            allowed_body = json.loads(allowed.stdout)
            self.assertEqual(allowed_body["decision"], "allow")
            self.assertEqual(allowed_body["permission"], "allow")

    def test_gemini_hook_snippet_wires_same_gate(self) -> None:
        data = json.loads((ROOT / "hooks" / "gemini.settings.snippet.json").read_text(encoding="utf-8"))
        self.assertIn("BeforeAgent", data["hooks"])
        self.assertIn("BeforeTool", data["hooks"])
        tool_cmd = data["hooks"]["BeforeTool"][0]["hooks"][0]["command"]
        self.assertIn("confirm_gate.py", tool_cmd)


class ConfidenceTests(unittest.TestCase):
    def test_examples_keep_their_tiers_and_gates(self) -> None:
        for task, expected_tier, expected_gate in EXAMPLES:
            result = classify(task)
            self.assertEqual(result["tier"], expected_tier, task)
            self.assertEqual(result["gate"], expected_gate, task)

    def test_vague_short_prompt_downshifts_to_standard(self) -> None:
        result = classify("make it better")
        self.assertEqual(result["tier"], "standard")
        self.assertNotEqual(result["tier"], "max")
        self.assertEqual(result["downshifted_from"], "fast")
        self.assertLess(result["confidence"], LOW_CONFIDENCE)
        self.assertTrue(result["needs_confirm"])
        self.assertEqual(result["gate"], "confirm")

    def test_long_vague_prompt_does_not_guess_max(self) -> None:
        result = classify(" ".join(["blah"] * 220))
        self.assertEqual(result["tier"], "standard")
        self.assertEqual(result["downshifted_from"], "max")
        self.assertLess(result["confidence"], LOW_CONFIDENCE)
        self.assertTrue(result["needs_confirm"])
        self.assertIn("confidence", result)

    def test_clear_max_and_fast_stay(self) -> None:
        hard = classify("Prove a novel consensus algorithm and redesign the entire distributed store")
        self.assertEqual(hard["tier"], "max")
        self.assertIsNone(hard["downshifted_from"])
        self.assertTrue(hard["needs_confirm"])
        easy = classify("Rename the variable foo to bar in utils.py")
        self.assertEqual(easy["tier"], "fast")
        self.assertFalse(easy["needs_confirm"])
        self.assertEqual(easy["gate"], "auto_continue")
        self.assertGreaterEqual(easy["confidence"], LOW_CONFIDENCE)

    def test_standard_never_auto_continues(self) -> None:
        result = classify("Wire up a CRUD endpoint using the existing handler pattern")
        self.assertEqual(result["tier"], "standard")
        self.assertEqual(result["gate"], "confirm")
        self.assertTrue(result["needs_confirm"])

    def test_picker_action_uses_placeholders(self) -> None:
        mapping = {
            "fast": {"picker": "<your-fast-model>", "effort": "low"},
            "reasoning": {"picker": "<your-reasoning-model>", "effort": "high"},
        }
        heavier = picker_action("fast", mapping, current_tier="max")
        self.assertIn("<your-fast-model>", heavier)
        self.assertIn("heavier than needed", heavier)

    def test_gemini_tier_map_uses_model_and_family(self) -> None:
        mapping = load_tier_map(str(ROOT / "integrations" / "gemini-tier-map.example.json"))
        self.assertEqual(mapping["fast"]["model"], "<your-flash-or-flash-lite>")
        self.assertEqual(mapping["standard"]["family"], "Pro")
        heavier = picker_action("fast", mapping, current_tier="max", host="Gemini")
        self.assertIn("<your-flash-or-flash-lite>", heavier)
        self.assertIn("Gemini", heavier)
        self.assertIn("heavier than needed", heavier)
        family_only = picker_action("max", {"max": {"family": "thinking / deep"}}, host="Gemini")
        self.assertIn("thinking / deep", family_only)


class UsageTests(unittest.TestCase):
    def test_logged_cost_preferred_and_tier_only_is_labeled(self) -> None:
        summary = summarize_usage([
            {
                "tier": "fast",
                "confirmed": True,
                "overridden": False,
                "input_tokens": 800,
                "output_tokens": 120,
                "cost_usd": 0.0012,
                "currency": "USD",
            },
            {"tier": "reasoning", "confirmed": True, "overridden": False},
        ])
        self.assertEqual(summary["basis"], "mixed")
        self.assertEqual(summary["measured_cost_usd"], 0.0012)
        self.assertEqual(summary["input_tokens"], 800)
        self.assertEqual(summary["output_tokens"], 120)
        self.assertEqual(summary["priced_entry_count"], 1)
        self.assertEqual(summary["illustrative"]["entries"], 1)
        self.assertIn("illustrative", summary["illustrative"]["rates_are"])
        self.assertFalse(summary["billing_api_accessed"])

    def test_empty_price_table_does_not_invent_dollars(self) -> None:
        table = load_price_table(ROOT / "demo" / "prices.example.json")
        summary = summarize_usage(
            [{"tier": "standard", "confirmed": True, "overridden": False, "input_tokens": 1000, "output_tokens": 10}],
            table,
        )
        self.assertIsNone(summary["measured_cost_usd"])
        self.assertEqual(summary["basis"], "illustrative_tier_rates")
        self.assertEqual(summary["price_table_status"], "missing_rates")

    def test_filled_price_table_prices_tokens(self) -> None:
        table = {
            "currency": "USD",
            "tiers": {
                t: {"input_per_million": 1.0, "output_per_million": 2.0}
                for t in ("fast", "standard", "reasoning", "max")
            },
        }
        summary = summarize_usage(
            [{
                "tier": "fast",
                "confirmed": True,
                "overridden": False,
                "input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            }],
            table,
        )
        self.assertEqual(summary["basis"], "measured")
        self.assertEqual(summary["measured_cost_usd"], 3.0)
        self.assertIsNone(summary["illustrative"])

    def test_append_usage_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.jsonl"
            append_usage(path, {
                "timestamp": "2026-09-21T00:00:00Z",
                "tier": "standard",
                "confirmed": True,
                "overridden": False,
                "input_tokens": 50,
                "output_tokens": 5,
                "cost_usd": 0.01,
                "currency": "USD",
            })
            proc = subprocess.run(
                [sys.executable, str(ROOT / "demo" / "savings_estimator.py"), str(path)],
                text=True,
                capture_output=True,
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.split("--- JSON ---", 1)[1])
            self.assertEqual(payload["basis"], "measured")
            self.assertEqual(payload["measured_cost_usd"], 0.01)
            self.assertEqual(payload["input_tokens"], 50)


class RouteTests(unittest.TestCase):
    def test_route_contract_blocks_then_logs(self) -> None:
        task = "Wire up a CRUD endpoint using the existing handler pattern"
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "usage.jsonl"
            blocked = route(task, confirmed=False, log_path=log, host="agent")
            self.assertFalse(blocked["allowed"])
            self.assertFalse(blocked["logged"])
            self.assertEqual(blocked["tier"], "standard")
            self.assertEqual(blocked["gate"], "confirm")
            self.assertIn("confidence", blocked)
            self.assertIn("suggestion", blocked)
            self.assertFalse(log.exists())

            forged = route(task, confirmed="true", log_path=log)  # type: ignore[arg-type]
            self.assertFalse(forged["allowed"])

            allowed = route(
                task,
                confirmed=True,
                host="agent",
                log_path=log,
                usage={"input_tokens": 100, "output_tokens": 20, "cost_usd": 0.002, "currency": "USD"},
            )
            self.assertTrue(allowed["allowed"])
            self.assertTrue(allowed["logged"])
            self.assertEqual(allowed["suggested_tier"], "standard")
            row = json.loads(log.read_text(encoding="utf-8"))
            self.assertEqual(row["host"], "agent")
            self.assertEqual(row["tier"], "standard")
            self.assertTrue(row["confirmed"])
            self.assertEqual(row["input_tokens"], 100)
            self.assertEqual(row["output_tokens"], 20)
            self.assertEqual(row["cost_usd"], 0.002)
            self.assertNotIn("task", row)

            overridden = route(
                "Debug why auth fails intermittently in production",
                override="fast",
                confirmed=False,
            )
            self.assertTrue(overridden["allowed"])
            self.assertEqual(overridden["tier"], "fast")
            self.assertTrue(overridden["overridden"])

    def test_route_auto_continues_rename(self) -> None:
        result = route("Rename the variable foo to bar in utils.py", confirmed=False)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["gate"], "auto_continue")
        self.assertFalse(result["needs_confirm"])


class DetectActiveTests(unittest.TestCase):
    def test_cli_beats_config_and_log(self) -> None:
        active = detect_active(
            cfg={"currentHost": "claude-code", "currentTier": "max"},
            entries=[{"tier": "standard", "host": "codex"}],
            host="cursor",
            tier="fast",
        )
        self.assertEqual(active["host"], "cursor")
        self.assertEqual(active["tier"], "fast")
        self.assertEqual(active["sources"]["host"], "cli --host")
        self.assertFalse(active["live_picker_read"])
        self.assertFalse(active["live_meter_read"])

    def test_falls_back_to_latest_log_row(self) -> None:
        active = detect_active(
            cfg={},
            entries=[{"tier": "reasoning", "host": "cursor"}],
        )
        self.assertEqual(active["tier"], "reasoning")
        self.assertEqual(active["host"], "cursor")
        self.assertIn("usage.jsonl", active["sources"]["tier"])


if __name__ == "__main__":
    unittest.main()
