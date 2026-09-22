import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "scripts" / "guard.py"
PRETOOL = REPO / "scripts" / "pretool.py"


def write_manifest(root, enforcement):
    (root / "control.py").write_text("HARD_STOP_LIMIT_USD = 10\n")
    (root / ".billing-guard.json").write_text(json.dumps({
        "version": 1, "owner": "example service owner",
        "metered_services": [{"name": "hosting", "monthly_budget_usd": 10,
                              "enforcement": enforcement, "verified_at": date.today().isoformat(),
                              "verified_by": "operator", "verification_reference": "billing dashboard",
                              "evidence": [{"file": "control.py", "contains": "HARD_STOP_LIMIT_USD"}]}],
        "public_routes": [], "paid_actions": [], "reviewed_findings": [],
        "incident_response": {"kill_switch": "disable this service"}}))


class GuardTests(unittest.TestCase):
    def test_alert_only_blocks_deploy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "alert-only")
            result = subprocess.run([sys.executable, str(GUARD), "preflight", "--repo", directory],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("alert-only is not a hard cap", result.stdout)

    def test_complete_manifest_passes_syntactic_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "hard-stop")
            result = subprocess.run([sys.executable, str(GUARD), "preflight", "--repo", directory],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_hook_denies_deploy_and_production_push(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "alert-only")
            for command, denied in (("vercel deploy --prod", True), ("git push origin main", True),
                                    ("git status --short", False)):
                event = {"tool_name": "Bash", "cwd": directory, "tool_input": {"command": command}}
                result = subprocess.run([sys.executable, str(PRETOOL)], input=json.dumps(event),
                                        capture_output=True, text=True)
                self.assertEqual(bool(result.stdout.strip()), denied)
                if denied:
                    self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_hook_detects_push_from_repository_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            write_manifest(root, "alert-only")
            nested = root / "src"
            nested.mkdir()
            event = {"tool_name": "Bash", "cwd": str(nested),
                     "tool_input": {"command": "git push origin main"}}
            result = subprocess.run([sys.executable, str(PRETOOL)], input=json.dumps(event),
                                    capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_scanner_flags_uncached_public_page(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "app" / "page.tsx"
            page.parent.mkdir()
            page.write_text("export default async function Page() { await fetch('/api', {cache: 'no-store'}); return null }")
            result = subprocess.run([sys.executable, str(GUARD), "scan", "--repo", directory],
                                    capture_output=True, text=True)
            self.assertIn("public-dynamic-page: app/page.tsx", result.stdout)
            self.assertIn("uncached-fetch: app/page.tsx", result.stdout)


class InstallerTests(unittest.TestCase):
    def test_preserves_existing_hooks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            hooks = home / "hooks.json"
            hooks.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "true"}]}]}}))
            installer = REPO / "scripts" / "install_codex.py"
            for _ in range(2):
                result = subprocess.run([sys.executable, str(installer), "--codex-home", directory],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(hooks.read_text())
            self.assertEqual(data["hooks"]["SessionStart"][0]["hooks"][0]["command"], "true")
            self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)
            self.assertEqual((home / "skills" / "billing-guard").resolve(), REPO)


if __name__ == "__main__":
    unittest.main()
