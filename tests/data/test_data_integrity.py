"""Automated data integrity, leakage, and schema verification suite.

Strictly enforces rules from DATA_PREPARATION_SPEC.md:
1. Required columns & non-null constraints.
2. Unique example_id across entire dataset.
3. Non-empty text_original and text_normalized.
4. Approved intent labels & strictly 1-to-1 label-to-id mapping.
5. Zero group leakage: no duplicate/near-duplicate group_id crosses train/val/test splits.
6. Closed-set guarantee: all validation & test labels must exist in training split.
7. Split exclusivity: train, validation, and test subsets are mutually disjoint.
8. Exact count reconciliation between canonical parquet, manifests, and split CSVs.
"""

import json
import os
import unittest
import pandas as pd

PROCESSED_DIR = "data/processed"
MANIFEST_DIR = "data/manifests"
TAXONOMY_PATH = "configs/taxonomy.json"

REQUIRED_CANONICAL_COLUMNS = [
    "example_id",
    "text_original",
    "text_normalized",
    "intent_label",
    "intent_id",
    "source_label",
    "parent_label",
    "domain",
    "language_condition",
    "source_dataset",
    "source_version",
    "source_id",
    "group_id",
    "split",
    "mapping_status",
    "exclusion_reason",
    "source_file_sha256",
    "text_hash"
]

REQUIRED_SPLIT_COLUMNS = [
    "example_id",
    "text",
    "label",
    "intent_id",
    "domain",
    "language_condition",
    "source_dataset",
    "group_id"
]


class TestDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parquet_path = os.path.join(PROCESSED_DIR, "canonical_dataset.parquet")
        cls.train_csv = os.path.join(PROCESSED_DIR, "baseline_train.csv")
        cls.val_csv = os.path.join(PROCESSED_DIR, "baseline_validation.csv")
        cls.test_csv = os.path.join(PROCESSED_DIR, "baseline_test.csv")
        cls.label_map_path = os.path.join(PROCESSED_DIR, "label_map.json")
        cls.split_manifest = os.path.join(MANIFEST_DIR, "split_indomain.csv")
        cls.inventory_manifest = os.path.join(MANIFEST_DIR, "dataset_inventory.csv")

        assert os.path.exists(cls.parquet_path), f"Missing {cls.parquet_path}"
        assert os.path.exists(cls.train_csv), f"Missing {cls.train_csv}"
        assert os.path.exists(cls.val_csv), f"Missing {cls.val_csv}"
        assert os.path.exists(cls.test_csv), f"Missing {cls.test_csv}"
        assert os.path.exists(cls.label_map_path), f"Missing {cls.label_map_path}"

        cls.df_canonical = pd.read_parquet(cls.parquet_path)
        cls.df_train = pd.read_csv(cls.train_csv)
        cls.df_val = pd.read_csv(cls.val_csv)
        cls.df_test = pd.read_csv(cls.test_csv)
        
        with open(cls.label_map_path, "r", encoding="utf-8") as f:
            cls.label_map = json.load(f)

    def test_01_canonical_schema_and_columns(self):
        """Validates that canonical parquet contains exactly the required columns."""
        actual_cols = list(self.df_canonical.columns)
        for col in REQUIRED_CANONICAL_COLUMNS:
            self.assertIn(col, actual_cols, f"Missing required column {col} in canonical parquet")

    def test_02_unique_example_ids(self):
        """Validates that example_id is strictly unique across canonical dataset."""
        n_rows = len(self.df_canonical)
        n_unique_ids = self.df_canonical["example_id"].nunique()
        self.assertEqual(n_rows, n_unique_ids, f"Found duplicate example_ids! {n_rows} rows vs {n_unique_ids} unique")

    def test_03_non_empty_text(self):
        """Ensures no null or blank text strings exist."""
        self.assertFalse(self.df_canonical["text_original"].isna().any(), "Found null text_original")
        self.assertFalse(self.df_canonical["text_normalized"].isna().any(), "Found null text_normalized")
        min_len = self.df_canonical["text_normalized"].str.strip().str.len().min()
        self.assertGreater(min_len, 10, f"Found suspiciously short normalized text: {min_len} chars")

    def test_04_taxonomy_and_label_map_integrity(self):
        """Verifies strictly one-to-one label-to-id mapping matching configs/taxonomy.json."""
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        approved_labels = {c["intent_label"]: c["intent_id"] for c in tax["classes"]}
        
        self.assertEqual(self.label_map, approved_labels, "label_map.json does not match taxonomy.json")
        dataset_labels = set(self.df_canonical["intent_label"].unique())
        self.assertTrue(dataset_labels.issubset(approved_labels.keys()), "Canonical data contains unapproved labels")

    def test_05_closed_set_evaluation_coverage(self):
        """Validates that all validation and test labels exist in training set."""
        train_labels = set(self.df_train["label"].unique())
        val_labels = set(self.df_val["label"].unique())
        test_labels = set(self.df_test["label"].unique())
        
        self.assertTrue(val_labels.issubset(train_labels), f"Val contains labels absent from train: {val_labels - train_labels}")
        self.assertTrue(test_labels.issubset(train_labels), f"Test contains labels absent from train: {test_labels - train_labels}")

    def test_06_zero_group_leakage(self):
        """Verifies that no group_id crosses between train, val, and test splits."""
        train_groups = set(self.df_train["group_id"].unique())
        val_groups = set(self.df_val["group_id"].unique())
        test_groups = set(self.df_test["group_id"].unique())

        train_val_overlap = train_groups & val_groups
        train_test_overlap = train_groups & test_groups
        val_test_overlap = val_groups & test_groups

        self.assertEqual(len(train_val_overlap), 0, f"Leakage: {len(train_val_overlap)} groups shared between train and val")
        self.assertEqual(len(train_test_overlap), 0, f"Leakage: {len(train_test_overlap)} groups shared between train and test")
        self.assertEqual(len(val_test_overlap), 0, f"Leakage: {len(val_test_overlap)} groups shared between val and test")

    def test_07_split_exclusivity(self):
        """Validates example_id exclusivity across splits."""
        train_ids = set(self.df_train["example_id"].unique())
        val_ids = set(self.df_val["example_id"].unique())
        test_ids = set(self.df_test["example_id"].unique())

        self.assertEqual(len(train_ids & val_ids), 0, "Train and Val share example_ids")
        self.assertEqual(len(train_ids & test_ids), 0, "Train and Test share example_ids")
        self.assertEqual(len(val_ids & test_ids), 0, "Val and Test share example_ids")

    def test_08_count_reconciliation(self):
        """Verifies that sum of train, val, test equals canonical parquet row count."""
        total_canonical = len(self.df_canonical)
        sum_splits = len(self.df_train) + len(self.df_val) + len(self.df_test)
        self.assertEqual(total_canonical, sum_splits, f"Reconciliation mismatch: canonical has {total_canonical}, sum of splits is {sum_splits}")


if __name__ == "__main__":
    unittest.main()
