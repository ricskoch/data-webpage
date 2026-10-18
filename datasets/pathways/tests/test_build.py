import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build  # noqa: E402

GMT = "\n".join([
    "Apoptosis\tR-HSA-109581\tTP53\tBAX\tBAX\t",
    "Broken line only two\tR-HSA-1",
    "Mouse thing\tR-MMU-1\tTrp53",
    "Empty\tR-HSA-5\t\t ",
    "",
    "Apoptosis again\tR-HSA-109581\tTP53",
])


class ParseGmt(unittest.TestCase):
    def test_valid_line_is_kept_with_sorted_unique_genes(self):
        pathways, _ = build.parse_gmt(GMT)
        self.assertEqual(pathways, [{"id": "R-HSA-109581", "name": "Apoptosis", "genes": ["BAX", "TP53"]}])

    def test_every_other_line_is_rejected_with_a_reason(self):
        _, rejects = build.parse_gmt(GMT)
        self.assertEqual([n for n, _ in rejects], [2, 3, 4, 6])
        self.assertIn("fewer than 3", rejects[0][1])
        self.assertIn("not a human pathway", rejects[1][1])
        self.assertIn("no gene symbols", rejects[2][1])
        self.assertIn("duplicate", rejects[3][1])

    def test_licence_evidence_finds_cc_sentences(self):
        html = "<p>Intro text.</p><p>Reactome data is available under the Creative Commons CC0 1.0 licence. Other text.</p>"
        self.assertEqual(build.licence_evidence(html), ["Reactome data is available under the Creative Commons CC0 1.0 licence."])


if __name__ == "__main__":
    unittest.main()
