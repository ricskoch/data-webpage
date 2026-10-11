# M0: Foundations

**What we build:** a repository with the rules, safety checks and cost controls in place, before any website code.

**New concepts:** repository, branch, pull request, CI, branch protection, secret scanning.

**Why first:** the cheapest mistakes to prevent are the ones that cost money or leak credentials. We set the guardrails before there is anything to protect.

**How you verify it yourself**
1. Open the first PR. Under "Checks" you should see CI running.
2. Click into a check and read what it did. You do not need to understand every line.
3. After you turn on branch protection (steps below), try to push to `main` directly. It should be refused.

**Branch protection, your clicks** (GitHub: repo > Settings > Branches > Add branch protection rule or ruleset)
- Branch name pattern: `main`
- Require a pull request before merging
- Require status checks to pass (select `secret-scan` and `repo-hygiene` once they have run once)
- Block force pushes
- Optionally: do not allow bypassing, including administrators

**Also turn on** (repo > Settings > Code security): secret scanning and push protection, Dependabot alerts.

**How it can go wrong:** secrets committed by accident (scanner catches most, not all); data files committed (CI rejects them); unexpected cost (card limit and alerts, see `docs/ops/`).
