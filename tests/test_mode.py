#!/usr/bin/env python3
from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
