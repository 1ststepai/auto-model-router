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
    from amr_usage import LIGHT_TASK_KINDS, detect_active, next_actions, summarize  # noqa: WPS433

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

    inferred = detect_active(cfg={}, entries=sample)
    if inferred.get("host") != "cursor" or inferred.get("tier") != "fast":
        errors.append(f"latest sample row should infer cursor/fast, got {inferred}")
    if inferred.get("live_meter_read") or inferred.get("live_picker_read"):
        errors.append("detect_active must not claim a live meter/picker read")
    declared = detect_active(cfg={}, entries=sample, host="claude-code", tier="reasoning", model="my-sonnet")
    if declared.get("host") != "claude-code" or declared.get("tier") != "reasoning":
        errors.append(f"cli declare should win, got {declared}")
    if declared.get("sources", {}).get("host") != "cli --host":
        errors.append(f"expected cli host source, got {declared.get('sources')}")

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

        detect = run(
            [sys.executable, str(SCRIPTS / "detect_active.py"), "--sample", "--json"],
            env=env,
        )
        if detect.returncode != 0:
            errors.append(f"detect_active --sample failed: {detect.stderr}")
        detected = json.loads(detect.stdout)
        if detected.get("host") != "cursor" or detected.get("live_meter_read"):
            errors.append(f"detect_active sample should be cursor from log, got {detected}")

        forced = run(
            [
                sys.executable,
                str(SCRIPTS / "audit_usage.py"),
                "--force",
                "--sample",
                "--json",
                "--current-tier",
                "max",
                "--active-host",
                "cursor",
            ],
            env=env,
        )
        if forced.returncode != 0:
            errors.append(f"audit --force --sample failed: {forced.stderr}")
        if "Active model" not in forced.stdout:
            errors.append("audit should lead with the active model")
        if "Optimize?" not in forced.stdout:
            errors.append("audit should ask optimize? before applying")
        if "apply_recommendations.py --yes" not in forced.stdout:
            errors.append("audit should require --yes to apply")
        payload = json.loads(forced.stdout.split("--- JSON ---", 1)[1])
        if payload.get("active", {}).get("tier") != "max":
            errors.append(f"active tier should be declared max, got {payload.get('active')}")
        if payload.get("applied") is not False:
            errors.append("audit must not apply automation")
        if payload.get("billing_api_accessed") is not False:
            errors.append("audit JSON claimed a billing API")
        burn = payload.get("active_burn") or {}
        if burn.get("current_tier_task_count", 0) < 1:
            errors.append("cursor+max should have at least the docs row")

        no_yes = run(
            [
                sys.executable,
                str(SCRIPTS / "apply_recommendations.py"),
                "--force",
                "--sample",
                "--dest",
                str(home / ".auto-model-router"),
            ],
            env=env,
        )
        if no_yes.returncode != 2 or "without --yes" not in no_yes.stdout:
            errors.append(f"apply without --yes should refuse writes: {no_yes.returncode} {no_yes.stdout}")
        if (home / ".auto-model-router" / "cursor-tier-map.json").is_file():
            errors.append("maps must not be written before --yes")

        rec = run(
            [
                sys.executable,
                str(SCRIPTS / "apply_recommendations.py"),
                "--force",
                "--yes",
                "--sample",
                "--enable-weekly-review",
                "--dest",
                str(home / ".auto-model-router"),
            ],
            env=env,
        )
        if rec.returncode != 0:
            errors.append(f"apply_recommendations --yes --force failed: {rec.stderr}\n{rec.stdout}")
        dest = home / ".auto-model-router"
        for name in ("cursor-tier-map.json", "claude-tier-map.json", "codex-tier-map.json"):
            path = dest / name
            if not path.is_file():
                errors.append(f"missing written map {path}")
        cfg = json.loads((dest / "config.json").read_text(encoding="utf-8"))
        if cfg.get("boundaryGatedConfirms") is not True:
            errors.append("boundaryGatedConfirms not set after --yes")
        if cfg.get("weeklyReview") is not True:
            errors.append("weeklyReview not set by --enable-weekly-review")

        actions = next_actions(summary, {"auditOptIn": True, "boundaryGatedConfirms": True, "weeklyReview": True})
        titles = " ".join(a["title"] for a in actions)
        if "map fast" not in titles.lower() and "Keep logging" not in titles:
            errors.append(f"unexpected remaining actions: {actions}")

    dash = (DEMO / "dashboard.html").read_text(encoding="utf-8")
    for needle in (
        "What are you using right now?",
        "Active model burn",
        "Optimize this pick?",
        "Yes, show apply commands",
        "--yes",
        "auditOptIn",
        "Never:",
    ):
        if needle not in dash:
            errors.append(f"dashboard.html missing {needle!r}")
    pro_at = dash.find("Export report (Pro)")
    active_at = dash.find("What are you using right now?")
    if pro_at != -1 and active_at != -1 and pro_at < active_at:
        errors.append("dashboard must not lead with the Pro upsell")
    if "<details" not in dash or "pro-panel" not in dash:
        errors.append("Pro copy should be collapsed at the bottom, not the lead")

    for rel in (
        "docs/SAVINGS_DESK.md",
        "docs/STACK.md",
        "scripts/detect_active.py",
        "integrations/config.example.json",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"missing {rel}")

    if errors:
        for line in errors:
            print(f"ERROR {line}", file=sys.stderr)
        print(f"Failed: {len(errors)} problem(s).", file=sys.stderr)
        return 1
    print("OK: Savings Desk detect → audit → ask → yes path validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
