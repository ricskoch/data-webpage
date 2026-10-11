# Working rules for coding agents

The spec in `docs/spec.md` is the source of truth. If a task conflicts with it, stop and ask.

## Always
- One roadmap item per PR, referencing its feature ID (F1 to F23) and acceptance criterion. Keep PRs under about 400 changed lines.
- Write the failing test first for recipe logic, statistics and data validation.
- Fill in the PR template, in plain language: what changed, why, what could go wrong, cost impact.
- Update docs and the changelog with the code.
- State what you could not verify. Never claim a check passed without running it.
- Data work: never delete or silently coerce rows. Write rejected rows with reasons. Every transformation is a named, tested function. Mapping changes are YAML diffs. Statistics need an independent reference test (see spec section 14).

## Stop and ask the human before
- Adding a service, paid feature, runtime dependency, secret, or API key.
- Touching secrets, permissions, DNS, billing, Cloudflare or GitHub settings.
- Changing licence fields, the unified data model, or any statistical method.
- Merging to `main`, running a data release, or publishing any dataset.
- Any change that could create usage-based cost.

## Never
- Commit secrets, raw data, or large files. Data lives in object storage, not git.
- Add paid LLM API calls to the site or CI.
- Skip, disable or weaken a test or check to get green.
- Rewrite history on shared branches.

## Where things live
- `docs/` spec, ADRs (`docs/adr/`), runbooks (`docs/ops/`), learning notes (`docs/learning/`).
- Code layout is decided in M1 and recorded as an ADR.

## Instructions for third-party dashboards
Menus and defaults for services such as Cloudflare and GitHub change often. Never write click-by-click steps from memory as if they were certain: check current documentation where possible, say when you could not, and fix the docs as soon as the human reports a difference.
