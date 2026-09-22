#!/usr/bin/env python3
from __future__ import annotations

import unittest

from demo.classify import classify, suggest_line
from demo.mode import decide_mode


class ModeHelperTests(unittest.TestCase):
    def test_high_risk_local(self) -> None:
        mode, reason = decide_mode(tier="reasoning", high_risk=True, reversible=False, signals=[])
        self.assertEqual(mode, "local")
        self.assertIn("high-risk", reason)

    def test_steering_local(self) -> None:
        mode, _ = decide_mode(
            tier="reasoning",
            high_risk=False,
            reversible=False,
            signals=["interactive steering"],
        )
        self.assertEqual(mode, "local")

    def test_unattended_reasoning_cloud(self) -> None:
        mode, reason = decide_mode(
            tier="reasoning",
            high_risk=False,
            reversible=False,
            signals=["unattended batch", "long-running"],
        )
        self.assertEqual(mode, "cloud")
        self.assertIn("cloud", reason)

    def test_fast_reversible_local(self) -> None:
        mode, _ = decide_mode(tier="fast", high_risk=False, reversible=True, signals=[])
        self.assertEqual(mode, "local")

    def test_default_local(self) -> None:
        mode, _ = decide_mode(tier="standard", high_risk=False, reversible=False, signals=[])
        self.assertEqual(mode, "local")


class ClassifyModeTests(unittest.TestCase):
    def test_fast_reversible_stays_local_and_keeps_gate(self) -> None:
        task = "Rename the variable foo to bar in utils.py"
        result = classify(task)
        self.assertEqual(result["tier"], "fast")
        self.assertEqual(result["gate"], "auto_continue")
        self.assertEqual(result["mode"], "local")
        self.assertIn("quick reversible", result["mode_reason"])
        self.assertIn("/ local", suggest_line(task, result))

    def test_steering_is_local(self) -> None:
        task = "steer this rename in this chat"
        result = classify(task)
        self.assertEqual(result["mode"], "local")
        self.assertIn("steering", result["mode_reason"])
        self.assertIn("interactive steering", result["signals"])
        self.assertIn("/ local", suggest_line(task, result))

    def test_unattended_reasoning_is_cloud(self) -> None:
        task = "Investigate the overnight migration of the entire codebase while I am away"
        result = classify(task)
        self.assertEqual(result["tier"], "reasoning")
        self.assertEqual(result["gate"], "confirm")
        self.assertEqual(result["mode"], "cloud")
        self.assertIn("/ cloud", suggest_line(task, result))

    def test_empty_task_has_mode(self) -> None:
        result = classify("  ")
        self.assertEqual(result["mode"], "local")
        self.assertEqual(result["gate"], "confirm")
        self.assertTrue(result["mode_reason"])


if __name__ == "__main__":
    unittest.main()
