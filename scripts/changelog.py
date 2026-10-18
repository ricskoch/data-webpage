"""Compile changelog.d/*.md fragments into CHANGELOG.md.

Each PR adds one fragment file instead of editing CHANGELOG.md, so parallel
PRs never touch the same lines. Run `python3 scripts/changelog.py` to move the
fragments (newest file name first) to the top of "## Unreleased" and delete them.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = "## Unreleased\n"


def compile_fragments(changelog: Path, fragments: Path) -> int:
    files = sorted(
        (p for p in fragments.glob("*.md") if p.name.lower() != "readme.md"),
        key=lambda p: p.name,
        reverse=True,
    )
    if not files:
        return 0
    bullets = []
    for p in files:
        text = " ".join(p.read_text().split())
        if not text:
            raise ValueError(f"{p.name} is empty")
        bullets.append(f"- {text}\n")
    log = changelog.read_text()
    if HEADING not in log:
        raise ValueError(f"CHANGELOG.md has no '{HEADING.strip()}' heading")
    changelog.write_text(log.replace(HEADING, HEADING + "".join(bullets), 1))
    for p in files:
        p.unlink()
    return len(files)


if __name__ == "__main__":
    n = compile_fragments(ROOT / "CHANGELOG.md", ROOT / "changelog.d")
    print(f"compiled {n} fragment(s)")
    sys.exit(0)
