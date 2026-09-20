#!/usr/bin/env python3
"""Best-effort validation of Cursor, Claude Code, Codex, and Agent Plugins manifests.

Uses stdlib only. Optionally validates against downloaded JSON Schemas when
the ``jsonschema`` package is installed and the network is available.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "auto-model-router"
HOMEPAGE = "https://github.com/1ststepai/auto-model-router"
LICENSE = "MIT"
NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$"
)

ERRORS: list[str] = []
NOTES: list[str] = []


def error(msg: str) -> None:
    ERRORS.append(msg)


def note(msg: str) -> None:
    NOTES.append(msg)


def load_json(rel: str) -> dict:
    path = ROOT / rel
    if not path.is_file():
        error(f"missing {rel}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error(f"{rel}: invalid JSON ({exc})")
        return {}
    if not isinstance(data, dict):
        error(f"{rel}: top-level value must be an object")
        return {}
    return data


def require(data: dict, rel: str, *keys: str) -> None:
    for key in keys:
        if key not in data:
            error(f"{rel}: missing required field {key!r}")


def expect_eq(data: dict, rel: str, key: str, value: object) -> None:
    if data.get(key) != value:
        error(f"{rel}: {key} must be {value!r}, got {data.get(key)!r}")


def expect_homepage(data: dict, rel: str) -> None:
    if data.get("homepage") != HOMEPAGE:
        error(f"{rel}: homepage must be {HOMEPAGE}")


def expect_license(data: dict, rel: str) -> None:
    if data.get("license") != LICENSE:
        error(f"{rel}: license must be {LICENSE}")


def expect_name(data: dict, rel: str, key: str = "name") -> None:
    name = data.get(key)
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
        error(f"{rel}: {key} {name!r} is not a valid kebab-case plugin name")


def expect_semver(data: dict, rel: str) -> None:
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        error(f"{rel}: version {version!r} is not semver")


def skills_path_ok(value: object, rel: str) -> None:
    if isinstance(value, list):
        if not value:
            error(f"{rel}: skills path list is empty")
            return
        value = value[0]
    if not isinstance(value, str) or not value:
        error(f"{rel}: skills path must be a non-empty string")
        return
    rel_path = value[2:] if value.startswith("./") else value
    rel_path = rel_path.rstrip("/")
    target = (ROOT / rel_path).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        error(f"{rel}: skills path escapes the repo ({value})")
        return
    skill = target / PLUGIN_NAME / "SKILL.md"
    if not skill.is_file():
        error(f"{rel}: skills path {value!r} does not contain {PLUGIN_NAME}/SKILL.md")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[4:end]
    meta: dict[str, str] = {}
    for raw in block.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta


def validate_skill() -> None:
    canonical = ROOT / "skills" / PLUGIN_NAME / "SKILL.md"
    compat = ROOT / "SKILL.md"
    if not canonical.is_file():
        error("missing skills/auto-model-router/SKILL.md")
        return
    text = canonical.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta.get("name") != PLUGIN_NAME:
        error("skills/auto-model-router/SKILL.md: frontmatter name must be auto-model-router")
    if "description" not in meta:
        error("skills/auto-model-router/SKILL.md: missing YAML description frontmatter")
    if not compat.is_file():
        error("missing root SKILL.md compatibility copy")
    elif compat.read_text(encoding="utf-8") != text:
        error("root SKILL.md is out of sync with skills/auto-model-router/SKILL.md")


def validate_apply_scripts() -> None:
    sh = ROOT / "scripts" / "apply.sh"
    ps = ROOT / "scripts" / "apply.ps1"
    if not sh.is_file() or 'SKILL_SRC="$ROOT/skills/auto-model-router/SKILL.md"' not in sh.read_text(
        encoding="utf-8"
    ):
        error("scripts/apply.sh no longer points at skills/auto-model-router/SKILL.md")
    if not ps.is_file() or r"skills\auto-model-router\SKILL.md" not in ps.read_text(
        encoding="utf-8"
    ):
        error("scripts/apply.ps1 no longer points at skills\\auto-model-router\\SKILL.md")


def validate_agent_plugins() -> dict:
    rel = "plugin.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "$schema", "name")
    expect_eq(
        data,
        rel,
        "$schema",
        "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    )
    expect_name(data, rel)
    expect_semver(data, rel)
    expect_homepage(data, rel)
    expect_license(data, rel)
    allowed = {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
    extra = set(data) - allowed
    if extra:
        error(f"{rel}: unknown Agent Plugins fields: {sorted(extra)}")
    extensions = data.get("extensions")
    if extensions is not None and (
        not isinstance(extensions, dict)
        or any(not isinstance(v, dict) for v in extensions.values())
    ):
        error(f"{rel}: extensions must be an object of objects")
    if "skills" in data:
        error(f"{rel}: Agent Plugins 1.0 forbids a skills field; skills are discovered from skills/")
    return data


def validate_cursor_plugin() -> dict:
    rel = ".cursor-plugin/plugin.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name")
    expect_name(data, rel)
    expect_semver(data, rel)
    expect_homepage(data, rel)
    expect_license(data, rel)
    skills_path_ok(data.get("skills"), rel)
    author = data.get("author")
    if not isinstance(author, dict) or "name" not in author:
        error(f"{rel}: author.name is required")
    elif set(author) - {"name", "email"}:
        error(f"{rel}: author may only contain name and email")
    return data


def validate_cursor_marketplace() -> dict:
    rel = ".cursor-plugin/marketplace.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name", "plugins")
    expect_name(data, rel)
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        error(f"{rel}: plugins must be a non-empty array")
        return data
    extra_top = set(data) - {"name", "owner", "metadata", "plugins"}
    if extra_top:
        error(f"{rel}: unknown fields {sorted(extra_top)}")
    for i, entry in enumerate(plugins):
        prefix = f"{rel}: plugins[{i}]"
        if not isinstance(entry, dict):
            error(f"{prefix} must be an object")
            continue
        require(entry, prefix, "name", "source")
        extra = set(entry) - {"name", "source", "description", "minClientVersions"}
        if extra:
            error(f"{prefix}: Cursor marketplace entries allow only name, source, description, minClientVersions; extra {sorted(extra)}")
        if entry.get("source") not in {".", "./"}:
            error(f"{prefix}: source should be '.' so the repo root is the plugin")
        if entry.get("name") != PLUGIN_NAME:
            error(f"{prefix}: name must be {PLUGIN_NAME}")
    return data


def validate_claude_plugin() -> dict:
    rel = ".claude-plugin/plugin.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name")
    expect_name(data, rel)
    expect_semver(data, rel)
    expect_homepage(data, rel)
    expect_license(data, rel)
    skills_path_ok(data.get("skills"), rel)
    return data


def validate_claude_marketplace() -> dict:
    rel = ".claude-plugin/marketplace.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name", "owner", "plugins")
    expect_name(data, rel)
    owner = data.get("owner")
    if not isinstance(owner, dict) or not owner.get("name"):
        error(f"{rel}: owner.name is required")
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        error(f"{rel}: plugins must be a non-empty array")
        return data
    for i, entry in enumerate(plugins):
        prefix = f"{rel}: plugins[{i}]"
        if not isinstance(entry, dict):
            error(f"{prefix} must be an object")
            continue
        require(entry, prefix, "name", "source")
        source = entry.get("source")
        if not isinstance(source, str) or not source.startswith("./"):
            error(f"{prefix}: source must be a relative path starting with ./")
        if entry.get("name") != PLUGIN_NAME:
            error(f"{prefix}: name must be {PLUGIN_NAME}")
        if "skills" in entry:
            skills_path_ok(entry.get("skills"), prefix)
    return data


def validate_codex_plugin() -> dict:
    rel = ".codex-plugin/plugin.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name")
    expect_name(data, rel)
    expect_semver(data, rel)
    expect_homepage(data, rel)
    expect_license(data, rel)
    skills_path_ok(data.get("skills"), rel)
    skills = data.get("skills")
    if skills != "./skills/":
        error(f"{rel}: skills should be './skills/' for Codex compatibility manifests")
    return data


def validate_codex_marketplace() -> dict:
    rel = ".agents/plugins/marketplace.json"
    data = load_json(rel)
    if not data:
        return data
    require(data, rel, "name", "plugins")
    expect_name(data, rel)
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        error(f"{rel}: plugins must be a non-empty array")
        return data
    for i, entry in enumerate(plugins):
        prefix = f"{rel}: plugins[{i}]"
        if not isinstance(entry, dict):
            error(f"{prefix} must be an object")
            continue
        require(entry, prefix, "name", "source", "policy", "category")
        if entry.get("name") != PLUGIN_NAME:
            error(f"{prefix}: name must be {PLUGIN_NAME}")
        source = entry.get("source")
        if isinstance(source, str):
            if not source.startswith("./"):
                error(f"{prefix}: string source must start with ./")
        elif isinstance(source, dict):
            if source.get("source") != "local":
                error(f"{prefix}: source.source should be 'local' for this repo")
            path = source.get("path")
            if path not in {"./", "."}:
                error(f"{prefix}: source.path should be './' so the repo root is the plugin")
        else:
            error(f"{prefix}: source must be a string or object")
        policy = entry.get("policy")
        if not isinstance(policy, dict):
            error(f"{prefix}: policy must be an object")
        else:
            if policy.get("installation") not in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}:
                error(f"{prefix}: policy.installation is invalid")
            if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
                error(f"{prefix}: policy.authentication is invalid")
    return data


def maybe_jsonschema() -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        note("jsonschema not installed; used structural checks only (stdlib).")
        return

    targets = [
        (
            "plugin.json",
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        ),
        (
            ".cursor-plugin/plugin.json",
            "https://raw.githubusercontent.com/cursor/plugins/main/schemas/plugin.schema.json",
        ),
        (
            ".cursor-plugin/marketplace.json",
            "https://raw.githubusercontent.com/cursor/plugins/main/schemas/marketplace.schema.json",
        ),
        (
            ".claude-plugin/plugin.json",
            "https://json.schemastore.org/claude-code-plugin-manifest.json",
        ),
        (
            ".claude-plugin/marketplace.json",
            "https://json.schemastore.org/claude-code-marketplace.json",
        ),
    ]
    for rel, url in targets:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                schema = json.loads(resp.read().decode("utf-8"))
            instance = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=instance, schema=schema)
            note(f"jsonschema OK: {rel}")
        except Exception as exc:  # noqa: BLE001 — report any schema/network failure
            error(f"jsonschema {rel}: {exc}")


def main() -> int:
    validate_skill()
    validate_apply_scripts()
    validate_agent_plugins()
    validate_cursor_plugin()
    validate_cursor_marketplace()
    validate_claude_plugin()
    validate_claude_marketplace()
    validate_codex_plugin()
    validate_codex_marketplace()
    maybe_jsonschema()

    for line in NOTES:
        print(f"NOTE  {line}")
    if ERRORS:
        for line in ERRORS:
            print(f"ERROR {line}", file=sys.stderr)
        print(f"\nFailed: {len(ERRORS)} problem(s).", file=sys.stderr)
        return 1
    print("OK: plugin manifests, skill, and apply-script paths validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
