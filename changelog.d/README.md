# Changelog fragments

Do not edit `CHANGELOG.md` in a PR. Add one file here instead, so parallel PRs never conflict.

- File name: `YYYY-MM-DD-short-slug.md` (for example `2026-10-18-drug-heatmap-scroll.md`).
- Content: the changelog entry as plain text, without the leading `- `. One entry per file; line breaks are joined into one bullet.
- Compile: `python3 scripts/changelog.py` moves all fragments (newest file name first) to the top of "## Unreleased" in `CHANGELOG.md` and deletes them. Run it in its own small PR, for example when a milestone closes.
- Fallback: `.gitattributes` marks `CHANGELOG.md` as `merge=union`, so if two PRs do edit it, git keeps both sides instead of raising a conflict.
