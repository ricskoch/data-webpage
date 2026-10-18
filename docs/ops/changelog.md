# Changelog without merge conflicts

Why: every PR used to add a line at the top of "## Unreleased" in `CHANGELOG.md`. Two PRs open at once edited the same line, so the second one conflicted, and fixing that by merging `main` into the branch cost an auto-merge round.

Now: a PR adds one file in `changelog.d/` (see `changelog.d/README.md`) and does not touch `CHANGELOG.md`. `python3 scripts/changelog.py` folds the fragments into `CHANGELOG.md` and deletes them (tests: `python3 -m unittest discover -s scripts/tests`). `.gitattributes` sets `CHANGELOG.md merge=union` as a fallback for PRs that still edit it directly.

`CHANGELOG.md` is not in the list of files that make a PR wait for Richard, so a changelog edit alone never causes `needs-richard`.
