# Manifest

Put `.billing-guard.json` at the repository root. See `examples/.billing-guard.json` for a deliberately incomplete starter. The example fails preflight until real controls are implemented and verified.

Required fields:

- `version`: `1`
- `owner`: team or role responsible for cost review
- `metered_services`: each service needs `name`, positive `monthly_budget_usd`, `enforcement: "hard-stop"`, `verified_at` (ISO date within 30 days), `verified_by`, `verification_reference`, and `evidence`
- `public_routes` and `paid_actions`: arrays of `{ "path": "...", "evidence": [...] }`; use `[]` only when there are none
- `reviewed_findings`: each scanner result needs `kind`, `file`, a specific `mitigation`, and `evidence`
- `incident_response.kill_switch`: a concrete way to stop the affected service

`evidence` is a nonempty array of `{ "file": "relative/path", "contains": "literal code or config fragment" }`. It must point to source or configuration inside the repository, not the manifest itself. This is a local consistency check. It does not prove that a live provider limit is enabled. Verify the live setting separately and put a reference to that check in `verification_reference`.

If a provider only offers alerts, implement a separate application-level hard stop or mark `enforcement` as `alert-only`; preflight will block in the latter case. A spending limit can still overshoot because billing signals and shutdown can lag.
