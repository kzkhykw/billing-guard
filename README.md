# Billing Guard

日本語: [README.ja.md](README.ja.md)

A local cost preflight and Codex skill for cloud and AI applications. It looks for public dynamic pages, uncached fetches, metered AI calls, and hosted runtimes. A repository manifest records budgets, actual stop controls, exposed routes, and evidence. Preflight fails when controls are missing or only alert on spend.

## Quick start

Requires Python 3.9 or newer. No Python packages or credentials are required.

```sh
python3 scripts/guard.py scan --repo /path/to/app
cp examples/.billing-guard.json /path/to/app/.billing-guard.json
# Fill in real controls and evidence in the app's manifest.
python3 scripts/guard.py preflight --repo /path/to/app
```

The example manifest intentionally fails. Read [the manifest guide](references/manifest.md) before editing it. A passing result confirms declared local evidence, not a live billing cap. Verify provider settings separately.

## Codex integration

From a clone of this repository, run:

```sh
python3 scripts/install_codex.py
```

The installer adds a `PreToolUse` hook to the user's Codex `hooks.json` and links this repository as a discoverable skill. It preserves existing hooks and agent instructions. The hook checks common CLI deploy commands and production-branch pushes in likely metered repositories. Run `python3 scripts/install_codex.py --dry-run` to inspect the target paths first.

The hook is a guardrail, not an enforcement boundary: external Git integrations, dashboards, specialized tools, and commands outside Codex may bypass it. Put preflight in CI if the project deploys through Git, and enforce cost limits at the provider or application runtime.

## Checks

Run the included tests with `python3 -m unittest discover -s tests -v`. The scanner uses simple patterns and can report false positives. Review each finding and document a real mitigation; do not silence it with placeholder evidence.

Licensed under MIT.
