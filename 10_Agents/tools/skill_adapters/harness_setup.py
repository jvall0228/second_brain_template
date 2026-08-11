#!/usr/bin/env python3
"""Read-only project verification and user-global setup preview.

This planner is intentionally incapable of applying a global plan.  It gives
``onboard-harness`` a deterministic executable boundary for its default
project check and its approval-gated external-path preview.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from gen_skill_adapters import AdapterError, catalog, check


HARNESSES = (
    "claude-code",
    "codex",
    "opencode",
    "pi",
    "cursor",
    "copilot",
    "muse-code",
)

PROJECT_SURFACES = {
    "claude-code": ("CLAUDE.md", ".claude/skills"),
    "codex": ("AGENTS.md", ".agents/skills"),
    "opencode": ("AGENTS.md", "opencode.json", ".agents/skills", ".claude/skills"),
    "pi": ("AGENTS.md", ".agents/skills"),
    "cursor": ("AGENTS.md", ".agents/skills", ".claude/skills"),
    "copilot": (
        "AGENTS.md",
        ".github/copilot-instructions.md",
        ".agents/skills",
        ".claude/skills",
    ),
    "muse-code": ("AGENTS.md", ".agents/skills"),
}

MEMORY_SURFACES = {
    "claude-code": ".claude/CLAUDE.md",
    "codex": ".codex/AGENTS.md",
    "opencode": ".config/opencode/AGENTS.md",
    "pi": ".pi/agent/AGENTS.md",
    "copilot": ".copilot/copilot-instructions.md",
}


def _path_state(path: Path) -> str:
    try:
        if path.is_symlink():
            return "symlink"
        if path.exists():
            return "existing"
        return "absent"
    except OSError as exc:
        raise AdapterError(f"cannot inspect preview path {path}: {exc}") from exc


def project_plan(repo: Path, harness: str) -> dict[str, object]:
    findings = check(repo)
    if findings:
        raise AdapterError("repository adapters are not fresh: " + ", ".join(findings))
    actions = [
        {
            "operation": "verify",
            "path": (repo / surface).as_posix(),
            "state": _path_state(repo / surface),
        }
        for surface in PROJECT_SURFACES[harness]
    ]
    return {
        "schemaVersion": 1,
        "mode": "project",
        "harness": harness,
        "repo": repo.as_posix(),
        "writesOutsideRepo": False,
        "actions": actions,
    }


def global_preview(repo: Path, home: Path, harness: str) -> dict[str, object]:
    # Catalog validation happens before paths are constructed; a malicious
    # skill name can therefore never escape the intended target root.
    skills = catalog(repo)
    common = [
        ("reconcile-registry", home / ".agents/second-brain/AGENTS.md"),
        ("reconcile-manifest", home / ".agents/second-brain-manifest.json"),
    ]
    actions = [
        {"operation": operation, "path": path.as_posix(), "state": _path_state(path)}
        for operation, path in common
    ]
    warnings: list[str] = []

    if harness == "copilot":
        actions.append(
            {
                "operation": "register-skill-directory",
                "command": [
                    "copilot",
                    "skill",
                    "add",
                    (repo / "10_Agents/skills").as_posix(),
                ],
                "state": "requires-provider-preflight",
            }
        )
    else:
        skill_root = home / (".claude/skills" if harness == "claude-code" else ".agents/skills")
        for skill in skills:
            target = skill_root / skill.name
            actions.append(
                {
                    "operation": "link-or-copy-skill",
                    "path": target.as_posix(),
                    "source": skill.source.parent.resolve().as_posix(),
                    "state": _path_state(target),
                }
            )

    memory = MEMORY_SURFACES.get(harness)
    if memory:
        memory_path = home / memory
        actions.append(
            {
                "operation": "reconcile-memory-marker",
                "path": memory_path.as_posix(),
                "state": _path_state(memory_path),
            }
        )
    else:
        warnings.append(
            f"{harness} has no stable documented user-memory file; preview schedules no memory write"
        )

    return {
        "schemaVersion": 1,
        "mode": "global-preview",
        "harness": harness,
        "repo": repo.as_posix(),
        "home": home.as_posix(),
        "readOnly": True,
        "actions": actions,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("project", "global-preview"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--harness", choices=HARNESSES, required=True)
    parser.add_argument("--home", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    try:
        if args.mode == "project":
            if args.home is not None:
                raise AdapterError("--home is valid only for global-preview")
            plan = project_plan(repo, args.harness)
        else:
            home = (args.home or Path(os.path.expanduser("~"))).resolve()
            plan = global_preview(repo, home, args.harness)
    except AdapterError as exc:
        print(f"harness-setup: error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"harness-setup: {plan['mode']} {plan['harness']}")
        for action in plan["actions"]:
            target = action.get("path") or " ".join(action["command"])
            print(f"- {action['operation']}: {target} [{action['state']}]")
        for warning in plan.get("warnings", []):
            print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
