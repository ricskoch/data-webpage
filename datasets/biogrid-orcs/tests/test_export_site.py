"""Tests for the prototype site bundle."""
import pathlib
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import export_site  # noqa: E402


class ExportSite(unittest.TestCase):
    def test_shard_is_stable_and_in_range(self):
        self.assertEqual(export_site.shard_of("entrez:7157"), export_site.shard_of("entrez:7157"))
        self.assertTrue(0 <= export_site.shard_of("orcs:77294U") < export_site.N_SHARDS)

    def test_nan_becomes_null(self):
        self.assertIsNone(export_site.num(float("nan")))
        self.assertEqual(export_site.num(0.123456), 0.1235)

    def test_gene_rows_keep_every_row(self):
        r = pd.DataFrame({"perturbation_id": ["entrez:1", "entrez:1", "entrez:2"], "screen_id": ["a", "b", "a"],
                          "effect_rank": [0.1, np.nan, 0.9], "effect_scaled": [np.nan] * 3,
                          "effect_z": [-1.0, np.nan, 2.0], "hit_source": [True, False, False],
                          "score_1": [-0.5, 3.0, 1.0]})
        shards = export_site.gene_rows(r, {"a": 0, "b": 1})
        g1 = shards[export_site.shard_of("entrez:1")]["entrez:1"]
        self.assertEqual(g1, [[0, 0.1, None, -1.0, 1, -0.5], [1, None, None, None, 0, 3.0]])
        self.assertEqual(sum(len(v) for s in shards.values() for v in s.values()), 3)


if __name__ == "__main__":
    unittest.main()
