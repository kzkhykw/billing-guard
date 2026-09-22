#!/usr/bin/env python3
"""Codex PreToolUse guard for CLI deployments. Fails closed on cost preflight."""
import json
import re
import subprocess
import sys
from pathlib import Path

DEPLOY = re.compile(r"\b(?:vercel\s+(?:deploy|--prod)|wrangler\s+deploy|firebase\s+deploy|fly\s+deploy|railway\s+up|netlify\s+deploy|npm\s+run\s+deploy|pnpm\s+(?:run\s+)?deploy|yarn\s+deploy)\b", re.I)
PUSH = re.compile(r"\bgit\s+push\b", re.I)


def production_push(command, cwd):
    if not PUSH.search(command):
        return False
    root = Path(cwd)
    package = root / "package.json"
    has_cost_surface = (root / ".billing-guard.json").exists() or (root / "vercel.json").exists() or (root / "wrangler.toml").exists()
    if package.exists():
        has_cost_surface = has_cost_surface or '"next"' in package.read_text(errors="replace")
    if not has_cost_surface:
        return False
    if re.search(r"\b(?:main|master|production)\b", command, re.I):
        return True
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, text=True, capture_output=True)
    return branch.returncode == 0 and branch.stdout.strip() in {"main", "master", "production"}


def main():
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    args = event.get("tool_input") or {}
    command = args.get("command") or args.get("cmd") or ""
    if not isinstance(command, str):
        return 0
    cwd = args.get("workdir") or event.get("cwd") or "."
    if not DEPLOY.search(command) and not production_push(command, cwd):
        return 0
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("guard.py")), "preflight", "--repo", str(cwd)], text=True, capture_output=True, timeout=25)
        if result.returncode == 0:
            return 0
        details = (result.stdout + result.stderr)[-6000:]
    except (OSError, subprocess.TimeoutExpired) as error:
        details = str(error)
    reason = "Billing preflight failed.\n" + details
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
