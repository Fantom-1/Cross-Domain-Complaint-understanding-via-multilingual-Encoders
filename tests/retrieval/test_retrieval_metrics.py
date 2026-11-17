import unittest

import pandas as pd

from src.retrieval.evaluate_retrieval import _validate_frames, evaluate_ranks


class RetrievalMetricTests(unittest.TestCase):
    def setUp(self):
        self.query = pd.DataFrame([
            {"example_id":"q1","text":"query one","label":"a","domain":"bank"},
            {"example_id":"q2","text":"query two","label":"b","domain":"card"},
        ])
        self.gallery = pd.DataFrame([
            {"example_id":"g1","text":"gallery one","label":"a","domain":"card"},
            {"example_id":"g2","text":"gallery two","label":"b","domain":"bank"},
            {"example_id":"g3","text":"gallery three","label":"b","domain":"bank"},
        ])

    def test_split_isolation(self):
        _validate_frames(self.query, self.gallery)
        overlapping = self.gallery.copy()
        overlapping.loc[0, "example_id"] = "q1"
        with self.assertRaisesRegex(ValueError, "leakage"):
            _validate_frames(self.query, overlapping)

    def test_metric_computation(self):
        ranks = [[(0, 0.9), (1, 0.2)], [(1, 0.8), (2, 0.7)]]
        metrics, rows = evaluate_ranks(self.query, self.gallery, ranks, 2, False)
        self.assertAlmostEqual(metrics["recall@2"], 1.0)
        self.assertAlmostEqual(metrics["mrr@2"], 1.0)
        self.assertEqual(metrics["evaluated_query_count"], 2)
        self.assertEqual(len(rows), 4)

    def test_cross_domain_support(self):
        ranks = [[(0, 0.9)], [(1, 0.8)]]
        metrics, _ = evaluate_ranks(self.query, self.gallery, ranks, 1, True)
        self.assertEqual(metrics["evaluated_query_count"], 2)
        self.assertTrue(metrics["cross_domain_only"])


if __name__ == "__main__":
    unittest.main()
