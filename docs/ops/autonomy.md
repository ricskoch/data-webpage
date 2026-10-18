# Autonomy: how PRs merge and deploys are checked

Decision (Richard, 2026-10-18, "Auto, with exceptions"): Claude's PRs merge by themselves once the required checks pass. Richard no longer reviews every PR or every deploy.

## How a PR merges
1. Claude opens a PR from a `claude/*` branch. Dependabot PRs are handled the same way.
2. `.github/workflows/auto-merge.yml` decides if Richard must look first. If not, it switches on GitHub auto-merge (squash).
3. GitHub merges when the required checks of the `main-protection` ruleset are green: `secret-scan`, `repo-hygiene`, `site`, `data-pipeline-tests`.
4. The Cloudflare PR-branch preview check is known-red. It is never required.

## What still waits for Richard
The workflow adds the label `needs-richard` and does not enable auto-merge when any of these is true:
- the PR template box "Yes" under cost and permissions is ticked (new service, secret, dependency, paid feature, usage-based cost);
- the PR touches `AGENTS.md`, `docs/spec.md`, `docs/adr/`, `wrangler.jsonc`, `.github/`, or in `datasets/<name>/` the `dataset.yaml`, `LICENCE*`, mapping or direction files (data model, licence, statistics, permissions);
- a Dependabot PR is a major version bump (TypeScript 7 broke the build once);
- someone put the label `needs-richard` on it by hand.

Also always Richard's: billing and account settings, DNS, secrets, data releases, publishing any dataset.

## Deploys
After a merge to `main`, Claude checks that the Cloudflare deploy of `data-webpage` succeeded and that the live site loads. A failed deploy is fixed in a new PR. Claude uses the Cloudflare connector for the check.
The "Publish ... to R2 staging" workflows stay manual. Claude may start them with `workflow_dispatch` after a merge that needs new data, never for a data release or public dataset.

## Guardrails that stay
- GitHub Actions spending limit stays at 0.
- One daily one-line summary of what merged.
- The kill switch (`kill-switch.md`) works as before.
- Undo a bad merge: revert the squash commit with a new PR; the revert goes through the same path.

## Status
Auto-merge and the four required checks were switched on by Richard on 2026-10-18.

## Settings that only Richard can change
`allow_auto_merge` on the repository, and the required checks in the ruleset. Both are listed in the PR that introduced this file.

## Adding an npm dependency from the cloud sandbox
The sandbox Claude works in cannot reach the npm registry, so it cannot update `package-lock.json`. Claude edits `package.json`, opens the PR and adds the label `update-lockfile`; `.github/workflows/update-lockfile.yml` then regenerates the lockfile on a runner and commits it to the PR branch. That bot commit does not start the checks, so Claude pushes one more real commit afterwards. New runtime dependencies still tick the cost and permissions box and wait for Richard.
