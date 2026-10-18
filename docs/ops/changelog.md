# Changelog without merge conflicts

Why: every PR used to add a line at the top of "## Unreleased" in `CHANGELOG.md`. Two PRs open at once edited the same line, so the second one conflicted, and fixing that by merging `main` into the branch cost an auto-merge round.

Now: a PR adds one file in `changelog.d/` (see `changelog.d/README.md`) and does not touch `CHANGELOG.md`. `python3 scripts/changelog.py` folds the fragments into `CHANGELOG.md` and deletes them (tests: `python3 -m unittest discover -s scripts/tests`). `.gitattributes` sets `CHANGELOG.md merge=union` as a fallback for PRs that still edit it directly.

`CHANGELOG.md` is not in the list of files that make a PR wait for Richard, so a changelog edit alone never causes `needs-richard`.

## Labels and pushes (`auto-merge.yml`)
- `needs-richard` counts as a reason only when a person added it. A label added by the workflow is re-decided on every run and removed when no reason is left.
- A push (for example merging `main` to fix a conflict) no longer switches off auto-merge on a PR held only by a `needs-richard` label that a person added. Any other hold reason still disables it on every event.
