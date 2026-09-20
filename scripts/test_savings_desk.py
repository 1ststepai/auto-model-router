#!/usr/bin/env python3
"""Stdlib checks for Savings Desk audit + apply-recommendations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DEMO = ROOT / "demo"


def run(args: list[str], *, env: dict[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    errors: list[str] = []

    sample = json.loads((DEMO / "sample_usage_log.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(SCRIPTS))
    from amr_usage import LIGHT_TASK_KINDS, next_actions, summarize  # noqa: WPS433

    summary = summarize(sample)
    if summary["task_count"] != 14:
        errors.append(f"sample task_count {summary['task_count']} != 14")
    if summary["billing_api_accessed"] is not False:
        errors.append("summarize claimed a billing API")
    if summary["heavy_on_light_count"] < 1:
        errors.append("sample should include at least one heavy-on-light row (max + docs)")
    if "cursor" not in summary["burns_by_host"]:
        errors.append("sample burns_by_host missing cursor")
    if summary["estimated_savings_vs_always_max_pct"] <= 0:
        errors.append("sample should show positive relative savings vs always-max")
    kinds = {row["task_kind"] for row in summary["heavy_on_light"]}
    if not kinds <= set(LIGHT_TASK_KINDS):
        errors.append(f"unexpected heavy-on-light kinds: {kinds}")

    # Consent gate without HOME config
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        denied = run([sys.executable, str(SCRIPTS / "audit_usage.py")], env=env)
        if denied.returncode != 1 or "auditOptIn=false" not in denied.stderr:
            errors.append(f"audit without consent should exit 1, got {denied.returncode}: {denied.stderr}")

        rec_denied = run([sys.executable, str(SCRIPTS / "apply_recommendations.py")], env=env)
        if rec_denied.returncode != 1 or "audit consent" not in rec_denied.stderr:
            errors.append(f"apply_recommendations without consent should refuse: {rec_denied.stderr}")

        forced = run(
            [sys.executable, str(SCRIPTS / "audit_usage.py"), "--force", "--sample", "--json"],
            env=env,
        )
        if forced.returncode != 0:
            errors.append(f"audit --force --sample failed: {forced.stderr}")
        if "Savings Desk audit" not in forced.stdout:
            errors.append("audit human report missing title")
        if "Never collected" not in forced.stdout:
            errors.append("audit should document never-collected fields")
        if "--- JSON ---" not in forced.stdout:
            errors.append("audit --json missing JSON block")
        payload = json.loads(forced.stdout.split("--- JSON ---", 1)[1])
        if payload.get("used_sample") is not True:
            errors.append("sample audit should set used_sample")
        if payload.get("billing_api_accessed") is not False:
            errors.append("audit JSON claimed a billing API")

        rec = run(
            [
                sys.executable,
                str(SCRIPTS / "apply_recommendations.py"),
                "--force",
                "--sample",
                "--enable-weekly-review",
                "--dest",
                str(home / ".auto-model-router"),
            ],
            env=env,
        )
        if rec.returncode != 0:
            errors.append(f"apply_recommendations --force failed: {rec.stderr}\n{rec.stdout}")
        dest = home / ".auto-model-router"
        for name in ("cursor-tier-map.json", "claude-tier-map.json", "codex-tier-map.json"):
            path = dest / name
            if not path.is_file():
                errors.append(f"missing written map {path}")
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "fast" not in data:
                    errors.append(f"{name} missing fast mapping")
        cfg_path = dest / "config.json"
        if not cfg_path.is_file():
            errors.append("apply_recommendations did not write config.json")
        else:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("boundaryGatedConfirms") is not True:
                errors.append("boundaryGatedConfirms not set")
            if cfg.get("weeklyReview") is not True:
                errors.append("weeklyReview not set by --enable-weekly-review")

        actions = next_actions(summary, {"auditOptIn": True, "boundaryGatedConfirms": True, "weeklyReview": True})
        titles = " ".join(a["title"] for a in actions)
        if "map fast" not in titles.lower() and "Keep logging" not in titles:
            errors.append(f"unexpected remaining actions: {actions}")

    dash = (DEMO / "dashboard.html").read_text(encoding="utf-8")
    for needle in (
        "Savings Desk",
        "hosts filter",
        "Switch-downs",
        "Enable automation",
        "Savings Desk Pro",
        "Export report (Pro)",
        "Never:",
        "auditOptIn",
    ):
        if needle not in dash:
            errors.append(f"dashboard.html missing {needle!r}")

    for rel in (
        "docs/SAVINGS_DESK.md",
        "docs/STACK.md",
        "docs/boundary-gated-confirms.md",
        "scripts/context_budget_checklist.md",
        "integrations/cursor-tier-map.example.json",
        "integrations/config.example.json",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"missing {rel}")

    if errors:
        for line in errors:
            print(f"ERROR {line}", file=sys.stderr)
        print(f"Failed: {len(errors)} problem(s).", file=sys.stderr)
        return 1
    print("OK: Savings Desk audit, apply-recommendations, and dashboard copy validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
