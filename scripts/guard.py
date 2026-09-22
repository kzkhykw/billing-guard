#!/usr/bin/env python3
"""Conservative, local cost preflight. Makes no network calls or mutations."""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SKIP = {".git", "node_modules", ".next", "dist", "build", "coverage", ".venv", "vendor"}
EXT = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".json", ".toml", ".yaml", ".yml"}


def root_for(path):
    path = Path(path).resolve()
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path, text=True, capture_output=True)
    return Path(result.stdout.strip()) if result.returncode == 0 else path


def files(root):
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part in SKIP or part in {"test", "tests", "__tests__", "data", "docs"} for part in rel.parts):
            continue
        if p.name in {"pnpm-lock.yaml", "package-lock.json", ".billing-guard.json"} or ".test." in p.name or ".spec." in p.name:
            continue
        if p.is_file() and p.suffix in EXT and p.stat().st_size < 500_000:
            yield p


def scan(root):
    findings = []
    for p in files(root):
        rel = str(p.relative_to(root))
        try:
            s = p.read_text(errors="replace")
        except OSError:
            continue
        if re.search(r"(?:app|pages)/page\.(?:tsx|jsx|ts|js)$", rel) and re.search(r"(?:cache\s*:\s*['\"]no-store|force-dynamic|getServerSideProps|Promise\.allSettled|Promise\.all\()", s):
            findings.append(("public-dynamic-page", rel, "Check per-request rendering and upstream calls"))
        if re.search(r"cache\s*:\s*['\"]no-store", s):
            findings.append(("uncached-fetch", rel, "Check per-request upstream work and egress"))
        if p.suffix in {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs"} and re.search(r"(?:from\s+['\"](?:openai|@anthropic|@ai-sdk/)|require\(['\"](?:openai|@anthropic|@ai-sdk/)|new (?:OpenAI|Anthropic)\s*\(|roundtable\()", s, re.I):
            findings.append(("metered-ai", rel, "Check auth, rate limits, token limits, and daily stop"))
        if re.search(r"(?:@vercel/functions|next|@cloudflare/workers-types|wrangler)", s) and p.name == "package.json":
            findings.append(("metered-hosting", rel, "Check egress, execution limits, and a kill switch"))
    return sorted(set(findings))


def evidence_ok(root, items):
    if not isinstance(items, list) or not items:
        return False
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str) or not isinstance(item.get("contains"), str):
            return False
        p = (root / item["file"]).resolve()
        if (not p.is_relative_to(root) or not p.is_file() or p.name == ".billing-guard.json"
                or p.suffix not in EXT or item["contains"] not in p.read_text(errors="replace")):
            return False
    return True


def preflight(root):
    errors = []
    manifest_path = root / ".billing-guard.json"
    if not manifest_path.exists():
        return ["Missing .billing-guard.json: record budgets, hard stops, and public routes"]
    try:
        m = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as e:
        return [f"Cannot read .billing-guard.json: {e}"]
    if not isinstance(m, dict):
        return [".billing-guard.json must be a JSON object"]
    if m.get("version") != 1 or not m.get("owner"):
        errors.append("version: 1 and owner are required")
    services = m.get("metered_services")
    if not isinstance(services, list) or not services:
        errors.append("List hosting, AI, database, and other paid services in metered_services")
        services = []
    for svc in services:
        name = svc.get("name", "(unknown)") if isinstance(svc, dict) else "(invalid)"
        if not isinstance(svc, dict) or not isinstance(svc.get("monthly_budget_usd"), (int, float)) or svc.get("monthly_budget_usd") <= 0:
            errors.append(f"{name}: monthly_budget_usd must be positive")
            continue
        if svc.get("enforcement") != "hard-stop":
            errors.append(f"{name}: {svc.get('enforcement', 'unset')} is not a hard cap; verify a real hard stop")
        try:
            verified = date.fromisoformat(svc.get("verified_at", ""))
            if (date.today() - verified).days not in range(31) or not svc.get("verified_by") or not svc.get("verification_reference"):
                raise ValueError("stale or incomplete")
        except (TypeError, ValueError):
            errors.append(f"{name}: verified_at (within 30 days), verified_by, and verification_reference are required")
        if not evidence_ok(root, svc.get("evidence")):
            errors.append(f"{name}: evidence(file, contains) for the stop control is missing")
    for key, description in (("public_routes", "public GET routes"), ("paid_actions", "paid actions")):
        routes = m.get(key)
        if not isinstance(routes, list):
            errors.append(f"List {description} in {key} (use [] if none)")
            continue
        for route in routes:
            path = route.get("path", "(unknown)") if isinstance(route, dict) else "(invalid)"
            if not isinstance(route, dict) or not evidence_ok(root, route.get("evidence")):
                errors.append(f"{key} {path}: local evidence of caching, rate limiting, response bounds, or auth is required")
    findings = scan(root)
    reviewed = m.get("reviewed_findings", [])
    for kind, file, _ in findings:
        matches = [x for x in reviewed if isinstance(x, dict) and x.get("kind") == kind and x.get("file") == file]
        if not matches or not any(x.get("mitigation") and evidence_ok(root, x.get("evidence")) for x in matches):
            errors.append(f"Unreviewed finding: {kind} {file}")
    incident = m.get("incident_response")
    if not isinstance(incident, dict) or not incident.get("kill_switch"):
        errors.append("Document a kill switch in incident_response.kill_switch")
    return errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["scan", "preflight"])
    p.add_argument("--repo", default=".")
    args = p.parse_args()
    root = root_for(args.repo)
    findings = scan(root)
    print(f"Billing guard: {root}")
    print(f"Cost signals: {len(findings)}")
    for kind, file, message in findings[:100]:
        print(f"  {kind}: {file} — {message}")
    if args.command == "preflight":
        errors = preflight(root)
        for error in errors:
            print(f"BLOCK: {error}")
        if errors:
            print(f"FAIL: {len(errors)} issue(s); production deployment is not cleared")
            return 1
        print("PASS: declared controls have local evidence. Verify live provider settings separately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
