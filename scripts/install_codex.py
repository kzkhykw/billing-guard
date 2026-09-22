#!/usr/bin/env python3
"""Install the Codex hook and skill without replacing existing configuration."""
import argparse
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path


def install(codex_home, repository, dry_run=False):
    hooks_file = codex_home / "hooks.json"
    skill_link = codex_home / "skills" / "billing-guard"
    pretool = repository / "scripts" / "pretool.py"
    if hooks_file.exists():
        data = json.loads(hooks_file.read_text())
    else:
        data = {"hooks": {}}
    if not isinstance(data.get("hooks"), dict):
        raise ValueError("hooks.json must contain a hooks object")
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(pretool))}"
    entries = data["hooks"].setdefault("PreToolUse", [])
    exists = any(command == hook.get("command") for group in entries if isinstance(group, dict)
                 for hook in group.get("hooks", []) if isinstance(hook, dict))
    if not exists:
        entries.append({"matcher": "^Bash$", "hooks": [{"type": "command", "command": command,
                                                     "timeout": 30, "statusMessage": "Checking deployment cost controls"}]})
    if skill_link.is_symlink() and skill_link.resolve() == repository:
        skill_action = "already installed"
    elif skill_link.exists() or skill_link.is_symlink():
        raise FileExistsError(f"A different skill already exists at {skill_link}")
    else:
        skill_action = "create symlink"
    print(f"Codex hooks: {hooks_file} ({'already installed' if exists else 'add PreToolUse'})")
    print(f"Codex skill: {skill_link} ({skill_action})")
    if dry_run:
        return
    codex_home.mkdir(parents=True, exist_ok=True)
    skill_link.parent.mkdir(parents=True, exist_ok=True)
    if not exists:
        with tempfile.NamedTemporaryFile("w", dir=codex_home, prefix=".hooks.", delete=False) as temporary:
            json.dump(data, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(hooks_file)
    if skill_action == "create symlink":
        skill_link.symlink_to(repository, target_is_directory=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    args = parser.parse_args()
    install(args.codex_home.expanduser().resolve(), Path(__file__).resolve().parents[1], args.dry_run)


if __name__ == "__main__":
    main()
