import unittest

import pandas as pd

from src.contrastive.pair_sampler import generate_pairs


class PairSamplerTests(unittest.TestCase):
    def setUp(self):
        self.train = pd.DataFrame([
            {"example_id":"a1","text":"A one","label":"intent_a","group_id":"g1","domain":"bank"},
            {"example_id":"a2","text":"A two","label":"intent_a","group_id":"g2","domain":"bank"},
            {"example_id":"a3","text":"A three","label":"intent_a","group_id":"g3","domain":"card"},
            {"example_id":"b1","text":"B one","label":"intent_b","group_id":"g4","domain":"bank"},
            {"example_id":"b2","text":"B two","label":"intent_b","group_id":"g5","domain":"card"},
        ])
        self.clusters = pd.DataFrame([
            {"example_id":x,"cluster_id":"c_"+x} for x in self.train.example_id
        ])
        self.splits = pd.DataFrame([
            {"example_id":x,"split":"train"} for x in self.train.example_id
        ])

    def test_same_domain_positive_and_negative_are_distinct(self):
        pairs, stats = generate_pairs(
            self.train, self.clusters, self.splits, seed=7, positive_mode="same-domain"
        )
        self.assertGreater(len(pairs), 0)
        for row in pairs.to_dict("records"):
            self.assertEqual(row["anchor_domain"], row["positive_domain"])
            self.assertNotEqual(row["weak_label"], " ")
            self.assertNotEqual(row["anchor_id"], row["positive_id"])
            self.assertNotEqual(row["anchor_id"], row["negative_id"])
            self.assertNotEqual(row["positive_id"], row["negative_id"])
            self.assertEqual(row["supervision"], "weak_label")
        self.assertEqual(stats["seed"], 7)

    def test_cross_domain_positive(self):
        pairs, _ = generate_pairs(
            self.train, self.clusters, self.splits, seed=7, positive_mode="cross-domain"
        )
        self.assertGreater(len(pairs), 0)
        self.assertTrue((pairs.anchor_domain != pairs.positive_domain).all())

    def test_deterministic(self):
        a, _ = generate_pairs(self.train, self.clusters, self.splits, seed=99)
        b, _ = generate_pairs(self.train, self.clusters, self.splits, seed=99)
        pd.testing.assert_frame_equal(a, b)

    def test_incomplete_cluster_mapping_fails_closed(self):
        with self.assertRaisesRegex(ValueError, r"cover every train ID|cover exactly"):
            generate_pairs(self.train, self.clusters.iloc[:-1], self.splits)

    def test_non_train_row_fails(self):
        splits = self.splits.copy()
        splits.loc[0, "split"] = "test"
        with self.assertRaisesRegex(ValueError, "exactly match"):
            generate_pairs(self.train, self.clusters, splits)

    def test_duplicate_group_is_not_a_pair(self):
        train = self.train.copy()
        train.loc[1, "group_id"] = train.loc[0, "group_id"]
        pairs, _ = generate_pairs(train, self.clusters, self.splits)
        self.assertFalse(((pairs.anchor_id == "a1") & (pairs.positive_id == "a2")).any())


if __name__ == "__main__":
    unittest.main()
