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

REQUIRED_MANIFEST_COLUMNS = [
    "experiment_id",
    "example_id",
    "split",
    "group_id",
    "source_dataset",
    "domain",
    "language_condition",
    "intent_label",
    "split_seed",
    "split_policy_version"
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
        assert os.path.exists(cls.split_manifest), f"Missing {cls.split_manifest}"

        cls.df_canonical = pd.read_parquet(cls.parquet_path)
        cls.df_train = pd.read_csv(cls.train_csv)
        cls.df_val = pd.read_csv(cls.val_csv)
        cls.df_test = pd.read_csv(cls.test_csv)
        cls.df_manifest = pd.read_csv(cls.split_manifest)
        
        with open(cls.label_map_path, "r", encoding="utf-8") as f:
            cls.label_map = json.load(f)

    def test_01_canonical_schema_and_columns(self):
        """Validates that canonical parquet, split CSVs, and split manifest contain exactly the required columns."""
        actual_canonical_cols = list(self.df_canonical.columns)
        self.assertEqual(
            set(actual_canonical_cols), 
            set(REQUIRED_CANONICAL_COLUMNS),
            f"Canonical schema mismatch! Extra: {set(actual_canonical_cols) - set(REQUIRED_CANONICAL_COLUMNS)}, Missing: {set(REQUIRED_CANONICAL_COLUMNS) - set(actual_canonical_cols)}"
        )
        self.assertEqual(len(actual_canonical_cols), len(REQUIRED_CANONICAL_COLUMNS), "Canonical column count mismatch")
        
        # Validate split CSV schemas
        for split_name, df_s in [("train", self.df_train), ("val", self.df_val), ("test", self.df_test)]:
            actual_split_cols = list(df_s.columns)
            self.assertEqual(
                set(actual_split_cols),
                set(REQUIRED_SPLIT_COLUMNS),
                f"{split_name} schema mismatch! Extra: {set(actual_split_cols) - set(REQUIRED_SPLIT_COLUMNS)}, Missing: {set(REQUIRED_SPLIT_COLUMNS) - set(actual_split_cols)}"
            )
            self.assertEqual(len(actual_split_cols), len(REQUIRED_SPLIT_COLUMNS), f"{split_name} column count mismatch")

        # Validate split manifest schema
        actual_manifest_cols = list(self.df_manifest.columns)
        self.assertEqual(
            set(actual_manifest_cols),
            set(REQUIRED_MANIFEST_COLUMNS),
            f"Manifest schema mismatch! Extra: {set(actual_manifest_cols) - set(REQUIRED_MANIFEST_COLUMNS)}, Missing: {set(REQUIRED_MANIFEST_COLUMNS) - set(actual_manifest_cols)}"
        )
        self.assertEqual(len(actual_manifest_cols), len(REQUIRED_MANIFEST_COLUMNS), "Manifest column count mismatch")

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

    def test_09_non_null_keys_and_groups(self):
        """Ensures that example_id, group_id, intent_label, and split are non-null across all datasets."""
        # Canonical assertions
        for col in ["example_id", "group_id", "intent_label", "split", "domain"]:
            self.assertFalse(self.df_canonical[col].isna().any(), f"Found null values in canonical column: {col}")
            
        # Split CSV assertions
        for split_name, df_s in [("train", self.df_train), ("val", self.df_val), ("test", self.df_test)]:
            for col in ["example_id", "group_id", "label", "domain"]:
                self.assertFalse(df_s[col].isna().any(), f"Found null values in {split_name} column: {col}")

        # Manifest assertions
        for col in ["example_id", "group_id", "intent_label", "split", "domain"]:
            self.assertFalse(self.df_manifest[col].isna().any(), f"Found null values in manifest column: {col}")

    def test_10_split_manifest_consistency(self):
        """Validates that split_indomain.csv agrees 100% with canonical dataset and split CSVs."""
        # 1. Exact ID coverage and uniqueness
        self.assertEqual(len(self.df_manifest), len(self.df_canonical), "Manifest and canonical row counts differ")
        self.assertEqual(self.df_manifest["example_id"].nunique(), len(self.df_manifest), "Duplicate IDs in manifest")
        self.assertEqual(
            set(self.df_manifest["example_id"]),
            set(self.df_canonical["example_id"]),
            "Manifest and canonical example IDs do not match exactly"
        )
        
        # 2. Split assignment agreement
        csv_splits = {}
        for eid in self.df_train["example_id"]:
            csv_splits[eid] = "train"
        for eid in self.df_val["example_id"]:
            csv_splits[eid] = "validation"
        for eid in self.df_test["example_id"]:
            csv_splits[eid] = "test"
            
        manifest_splits = dict(zip(self.df_manifest["example_id"], self.df_manifest["split"]))
        self.assertEqual(csv_splits, manifest_splits, "Split assignments in manifest differ from exported CSV files")
        
        # 3. Group ID agreement
        csv_groups = dict(zip(self.df_train["example_id"], self.df_train["group_id"]))
        csv_groups.update(dict(zip(self.df_val["example_id"], self.df_val["group_id"])))
        csv_groups.update(dict(zip(self.df_test["example_id"], self.df_test["group_id"])))
        
        manifest_groups = dict(zip(self.df_manifest["example_id"], self.df_manifest["group_id"]))
        self.assertEqual(csv_groups, manifest_groups, "Group assignments in manifest differ from exported CSV files")


if __name__ == "__main__":
    unittest.main()
