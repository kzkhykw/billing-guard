---
name: billing-guard
description: Audit and control cost spikes in cloud-hosted or AI-powered apps. Use before production deployment, when adding a metered service or public endpoint, or when investigating an unexpected bill.
---

# Billing Guard

Use this skill for cost exposure, not ordinary code review. Resolve script paths relative to this `SKILL.md`. Run `python3 <skill-directory>/scripts/guard.py scan --repo <path>` to identify likely paid paths and `python3 <skill-directory>/scripts/guard.py preflight --repo <path>` before production deployment or a push that triggers it. The script is a conservative local heuristic; inspect the code and live provider settings yourself.

For every metered service, establish the billing unit, worst plausible request volume, per-request work and bytes, a budget, and a real stopping mechanism. Treat budget emails and dashboards as alerts unless the provider confirms that they halt usage. Account for delay and overshoot even with a provider stop.

For public GET routes, check server rendering, uncached upstream calls, response size, bot access, caching, and rate limits. For paid POST routes or jobs, check server-side authorization or quotas, per-user and per-IP limits, maximum tokens/output/retries, and a daily stop. `robots.txt` does not control spending.

Record the project review in `.billing-guard.json` using [the manifest guide](references/manifest.md). Do not invent evidence to pass preflight. If the deployment is blocked, fix the control or accurately report why it remains unsafe. After release, measure cost per request and inspect live usage. Bulk pause or budget changes require an exact project list and keep-list, followed by verification.
