import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import changelog

BASE = "# Changelog\n\n## Unreleased\n- Old entry.\n\n## 0.1\n- Older.\n"


class CompileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.frag = self.tmp / "changelog.d"
        self.frag.mkdir()
        self.log = self.tmp / "CHANGELOG.md"
        self.log.write_text(BASE)

    def test_fragments_go_on_top_of_unreleased_newest_first(self):
        (self.frag / "2026-10-17-a.md").write_text("First one.\n")
        (self.frag / "2026-10-18-b.md").write_text("Second one.\n")
        changelog.compile_fragments(self.log, self.frag)
        self.assertEqual(
            self.log.read_text(),
            "# Changelog\n\n## Unreleased\n- Second one.\n- First one.\n- Old entry.\n\n## 0.1\n- Older.\n",
        )

    def test_fragments_are_removed_but_readme_stays(self):
        (self.frag / "README.md").write_text("how to\n")
        (self.frag / "2026-10-18-b.md").write_text("Second one.\n")
        changelog.compile_fragments(self.log, self.frag)
        self.assertEqual([p.name for p in self.frag.iterdir()], ["README.md"])

    def test_multiline_fragment_is_one_bullet(self):
        (self.frag / "2026-10-18-b.md").write_text("Line one\ncontinues here.\n")
        changelog.compile_fragments(self.log, self.frag)
        self.assertIn("- Line one continues here.\n", self.log.read_text())

    def test_no_fragments_changes_nothing(self):
        self.assertEqual(changelog.compile_fragments(self.log, self.frag), 0)
        self.assertEqual(self.log.read_text(), BASE)

    def test_empty_fragment_is_an_error(self):
        (self.frag / "2026-10-18-b.md").write_text("  \n")
        with self.assertRaises(ValueError):
            changelog.compile_fragments(self.log, self.frag)
        self.assertTrue((self.frag / "2026-10-18-b.md").exists())

    def test_missing_unreleased_heading_is_an_error(self):
        self.log.write_text("# Changelog\n")
        (self.frag / "2026-10-18-b.md").write_text("x\n")
        with self.assertRaises(ValueError):
            changelog.compile_fragments(self.log, self.frag)


if __name__ == "__main__":
    unittest.main()
