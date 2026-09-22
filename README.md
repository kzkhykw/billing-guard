# Billing Guard

日本語: [README.ja.md](README.ja.md)

A local cost preflight and Codex skill for cloud and AI applications. It looks for public dynamic pages, uncached fetches, metered AI calls, and hosted runtimes. A repository manifest records budgets, declared stop controls, exposed routes, and evidence. Preflight fails when controls are missing or only alert on spend.

## Status and scope

This is an experimental, incident-driven checklist and guardrail, not a guarantee against a large bill. The scanner currently favors Next.js and common JavaScript AI integrations; the optional deployment hook is specific to Codex and recognizes a limited set of CLI commands. The tool has not been validated across unrelated production stacks. False positives and missed cost paths are possible.

The manifest's `evidence` check only confirms that a literal string exists in a local source or config file. It cannot show that the code executes, that a provider setting is enabled, or that a hard stop works under load. A `PASS` means the declarations passed these local checks, not that spending is capped. The requirement for a hard stop on every metered service is a deliberately conservative policy and may not fit applications that prioritize availability. Verify live controls and failure behavior separately.

Reports of false positives, missed paths, and results from other stacks are welcome. Please remove credentials, customer data, and account details from shared examples.

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
