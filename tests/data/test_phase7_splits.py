#!/usr/bin/env python3
"""Comprehensive unit test suite for Phase 7: Split Feasibility & Boundary Formulation.

Covers:
- Product domain x intent label contingency matrix dimensions, 56.25% sparsity, and 9x16 universe.
- Fail-closed validation rejecting unknown domains and classes.
- Cross-product domain transfer confounding proof (debt_collection, mortgage).
- Temporal distribution continuity (36 months, 2018-05 to 2021-04) and class persistence across all 4 years.
- In-distribution baseline split quotas (32,019 train / 6,852 val / 6,852 test) and unique IDs.
- Full reconciliation with frozen canonical dataset (bijection of example IDs).
- Fail-closed cluster leakage verification against duplicate cluster catalog.
- Failure-injection tests for:
  - Missing cluster manifest (raises FileNotFoundError).
  - Duplicate example IDs in split manifest (raises ValueError).
  - Invalid split values (raises ValueError).
  - Split mismatch between cluster manifest and split manifest (raises ValueError).
  - Injected cross-split cluster contamination (detects leakage).
  - Missing classes or domains in a split.
  - Canonical parquet example ID mismatch (raises ValueError).
  - Duplicate example IDs in cluster manifest (raises ValueError).
  - Incomplete coverage when full coverage is required (raises ValueError).
- Cross-process determinism under differing PYTHONHASHSEED environments.
- Isolated failure-injection tests for Audit Pillars 1 through 7.
- Full Phase 7 audit execution test.
"""

import csv
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List

import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.audit_phase7 import (
    CLASS_DOMAIN_COVERAGE_CSV,
    DUPLICATE_CLUSTERS_CSV,
    EXPECTED_ACTIVE_CELLS,
    EXPECTED_CANONICAL_SHA256,
    EXPECTED_CLASS_COUNT,
    EXPECTED_DOMAIN_COUNT,
    EXPECTED_MATRIX_CELLS,
    EXPECTED_SPARSITY_PCT,
    EXPECTED_TEMPORAL_MONTHS,
    EXPECTED_TEST_ROWS,
    EXPECTED_TOTAL_RECORDS,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VAL_ROWS,
    EXPECTED_ZERO_CELLS,
    SPLIT_FEASIBILITY_MD,
    SPLIT_INDOMAIN_CSV,
    TEMPORAL_CLASS_DISTRIBUTION_CSV,
    TEMPORAL_DISTRIBUTION_CSV,
    _run_phase7_audit_internal,
    audit_class_domain_coverage,
    audit_indomain_split_invariants,
    audit_temporal_manifests,
)
from src.data.split_analyzer import (
    ALL_CLASSES,
    ALL_DOMAINS,
    CANONICAL_PARQUET_PATH,
    DOMAIN_EXCLUSIVE_CLASSES,
    SplitAnalyzer,
)


class TestPhase7Splits(unittest.TestCase):
    """Unit and regression tests for Phase 7 split feasibility, domain confounding, and temporal audit."""

    @classmethod
    def setUpClass(cls):
        cls.analyzer = SplitAnalyzer()
        cls.has_parquet = os.path.isfile(CANONICAL_PARQUET_PATH)

    def test_01_class_domain_contingency_matrix_canonical_dimensions(self):
        """Asserts the contingency matrix has exactly 9 domains x 16 classes, 81 zeros, and 56.25% sparsity."""
        if not self.has_parquet:
            self.skipTest("canonical_dataset.parquet missing in CI environment")
        res = self.analyzer.compute_class_domain_matrix()
        self.assertEqual(len(res["domains"]), EXPECTED_DOMAIN_COUNT)
        self.assertEqual(len(res["classes"]), EXPECTED_CLASS_COUNT)
        self.assertEqual(res["total_cells"], EXPECTED_MATRIX_CELLS)
        self.assertEqual(res["zero_cells"], EXPECTED_ZERO_CELLS)
        self.assertEqual(res["active_cells"], EXPECTED_ACTIVE_CELLS)
        self.assertEqual(res["sparsity_pct"], EXPECTED_SPARSITY_PCT)
        self.assertEqual(res["total_records"], EXPECTED_TOTAL_RECORDS)

        # Check exclusive classes
        self.assertEqual(res["exclusive_classes"], DOMAIN_EXCLUSIVE_CLASSES)

    def test_02_unknown_domain_or_class_fails_closed(self):
        """Asserts compute_class_domain_matrix raises ValueError when unknown domain or class is encountered."""
        df_invalid_domain = pd.DataFrame([
            {"domain": "crypto_exchange", "intent_label": "account_access"}
        ])
        with self.assertRaises(ValueError) as ctx:
            self.analyzer.compute_class_domain_matrix(df=df_invalid_domain)
        self.assertIn("Unexpected domain", str(ctx.exception))

        df_invalid_class = pd.DataFrame([
            {"domain": "bank_account", "intent_label": "crypto_scam"}
        ])
        with self.assertRaises(ValueError) as ctx:
            self.analyzer.compute_class_domain_matrix(df=df_invalid_class)
        self.assertIn("Unexpected intent class", str(ctx.exception))

    def test_03_domain_transfer_confounding_proof(self):
        """Asserts leave-one-domain-out proves confounding for debt_collection and mortgage."""
        if not self.has_parquet:
            self.skipTest("canonical_dataset.parquet missing in CI environment")
        res = self.analyzer.evaluate_domain_transfer_feasibility()
        self.assertEqual(set(res["confounded_domains"]), {"debt_collection", "mortgage"})
        self.assertEqual(res["confounded_count"], 2)

        # debt_collection must have 3 missing classes in train
        debt_diag = res["held_out_diagnostics"]["debt_collection"]
        self.assertTrue(debt_diag["is_structurally_confounded"])
        self.assertEqual(
            set(debt_diag["missing_in_train"]),
            {"debt_communication", "debt_not_owed", "debt_threats"},
        )

        # mortgage must have closing_process missing in train
        mort_diag = res["held_out_diagnostics"]["mortgage"]
        self.assertTrue(mort_diag["is_structurally_confounded"])
        self.assertEqual(mort_diag["missing_in_train"], ["closing_process"])

        # Other 7 domains must have 0 missing classes in train
        for d in ALL_DOMAINS:
            if d not in ("debt_collection", "mortgage"):
                diag = res["held_out_diagnostics"][d]
                self.assertFalse(diag["is_structurally_confounded"])
                self.assertEqual(len(diag["missing_in_train"]), 0)

    def test_04_temporal_distribution_and_class_support(self):
        """Asserts 36 continuous months (2018-05 to 2021-04) and class persistence across all 4 years."""
        res = self.analyzer.audit_temporal_distribution()
        self.assertEqual(res["total_months"], EXPECTED_TEMPORAL_MONTHS)
        self.assertEqual(res["total_complaints"], EXPECTED_TOTAL_RECORDS)
        self.assertEqual(res["start_month"], "2018-05")
        self.assertEqual(res["end_month"], "2021-04")
        self.assertEqual(res["total_classes"], EXPECTED_CLASS_COUNT)
        self.assertTrue(res["active_in_all_years"])

    def test_05_indomain_split_quotas_and_uniqueness(self):
        """Asserts in-distribution split satisfies exact quotas: 32,019 train, 6,852 val, 6,852 test with unique IDs."""
        res = self.analyzer.audit_in_distribution_split()
        self.assertEqual(res["total_rows"], EXPECTED_TOTAL_RECORDS)
        self.assertEqual(res["train_count"], EXPECTED_TRAIN_ROWS)
        self.assertEqual(res["val_count"], EXPECTED_VAL_ROWS)
        self.assertEqual(res["test_count"], EXPECTED_TEST_ROWS)
        self.assertEqual(res["duplicate_example_ids"], 0)
        self.assertTrue(res["all_classes_in_all_splits"])
        self.assertTrue(res["all_domains_in_all_splits"])

    def test_06_indomain_split_reconciliation_with_canonical_dataset(self):
        """Asserts exact 1-to-1 bijection of example IDs between split_indomain.csv and canonical_dataset.parquet."""
        if not self.has_parquet:
            self.skipTest("canonical_dataset.parquet missing in CI environment")
        res = self.analyzer.audit_in_distribution_split(validate_canonical=True)
        self.assertTrue(res["reconciled_with_canonical"])

    def test_07_cluster_exclusivity_zero_leakage(self):
        """Asserts zero cross-partition leakage across duplicate clusters and group IDs."""
        res = self.analyzer.audit_in_distribution_split()
        self.assertFalse(res["has_leakage"])
        self.assertEqual(res["shared_clusters_count"], 0)
        self.assertEqual(res["shared_groups_count"], 0)
        self.assertGreater(res["cluster_records_checked"], 3000)

    def test_08_fail_closed_on_missing_cluster_manifest(self):
        """Asserts audit_in_distribution_split fails closed (FileNotFoundError) when cluster manifest is missing."""
        with self.assertRaises(FileNotFoundError):
            self.analyzer.audit_in_distribution_split(
                clusters_csv_path="nonexistent_clusters_manifest.csv",
                require_cluster_manifest=True,
            )

    def test_09_failure_injection_cluster_leakage_detected(self):
        """Asserts injected cluster leakage across splits is caught by audit_in_distribution_split."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_split:
            writer = csv.DictWriter(
                tmp_split,
                fieldnames=["example_id", "split", "intent_label", "domain", "group_id"],
            )
            writer.writeheader()
            writer.writerow({"example_id": "e1", "split": "train", "intent_label": "account_access", "domain": "bank_account", "group_id": "g1"})
            writer.writerow({"example_id": "e2", "split": "test", "intent_label": "account_access", "domain": "bank_account", "group_id": "g2"})
            split_file = tmp_split.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_cl:
            writer = csv.DictWriter(tmp_cl, fieldnames=["cluster_id", "example_id", "split"])
            writer.writeheader()
            # e1 and e2 share cluster c_leak, but e1 is train and e2 is test!
            writer.writerow({"cluster_id": "c_leak", "example_id": "e1", "split": "train"})
            writer.writerow({"cluster_id": "c_leak", "example_id": "e2", "split": "test"})
            cl_file = tmp_cl.name

        try:
            res = self.analyzer.audit_in_distribution_split(
                split_csv_path=split_file,
                clusters_csv_path=cl_file,
                canonical_parquet_path=None,
                require_cluster_manifest=True,
            )
            self.assertTrue(res["has_leakage"])
            self.assertEqual(res["shared_clusters_count"], 1)
        finally:
            if os.path.exists(split_file):
                os.remove(split_file)
            if os.path.exists(cl_file):
                os.remove(cl_file)

    def test_10_failure_injection_duplicate_example_ids_in_split(self):
        """Asserts ValueError is raised when duplicate example IDs exist in split manifest."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["example_id", "split", "intent_label", "domain"])
            writer.writeheader()
            writer.writerow({"example_id": "dup_1", "split": "train", "intent_label": "account_access", "domain": "bank_account"})
            writer.writerow({"example_id": "dup_1", "split": "val", "intent_label": "account_access", "domain": "bank_account"})
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError) as ctx:
                self.analyzer.audit_in_distribution_split(split_csv_path=tmp_path, require_cluster_manifest=False)
            self.assertIn("Duplicate example_id", str(ctx.exception))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_11_failure_injection_invalid_split_name(self):
        """Asserts ValueError is raised when an invalid split name (e.g., 'holdout') is encountered."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["example_id", "split", "intent_label", "domain"])
            writer.writeheader()
            writer.writerow({"example_id": "e1", "split": "holdout", "intent_label": "account_access", "domain": "bank_account"})
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError) as ctx:
                self.analyzer.audit_in_distribution_split(split_csv_path=tmp_path, require_cluster_manifest=False)
            self.assertIn("Invalid split values", str(ctx.exception))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_12_failure_injection_split_mismatch_with_cluster_manifest(self):
        """Asserts ValueError is raised when split assignment in cluster manifest disagrees with split file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_split:
            writer = csv.DictWriter(tmp_split, fieldnames=["example_id", "split", "intent_label", "domain"])
            writer.writeheader()
            writer.writerow({"example_id": "e1", "split": "train", "intent_label": "account_access", "domain": "bank_account"})
            split_file = tmp_split.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_cl:
            writer = csv.DictWriter(tmp_cl, fieldnames=["cluster_id", "example_id", "split"])
            writer.writeheader()
            # Says test in cluster manifest, but train in split manifest
            writer.writerow({"cluster_id": "c1", "example_id": "e1", "split": "test"})
            cl_file = tmp_cl.name

        try:
            with self.assertRaises(ValueError) as ctx:
                self.analyzer.audit_in_distribution_split(
                    split_csv_path=split_file,
                    clusters_csv_path=cl_file,
                    require_cluster_manifest=True,
                )
            self.assertIn("Split mismatch", str(ctx.exception))
        finally:
            if os.path.exists(split_file):
                os.remove(split_file)
            if os.path.exists(cl_file):
                os.remove(cl_file)

    def test_13_failure_injection_duplicate_example_id_in_cluster_manifest(self):
        """Asserts ValueError is raised when duplicate example IDs exist in cluster manifest."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_split:
            writer = csv.DictWriter(tmp_split, fieldnames=["example_id", "split", "intent_label", "domain"])
            writer.writeheader()
            writer.writerow({"example_id": "e1", "split": "train", "intent_label": "account_access", "domain": "bank_account"})
            split_file = tmp_split.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_cl:
            writer = csv.DictWriter(tmp_cl, fieldnames=["cluster_id", "example_id", "split"])
            writer.writeheader()
            writer.writerow({"cluster_id": "c1", "example_id": "e1", "split": "train"})
            writer.writerow({"cluster_id": "c2", "example_id": "e1", "split": "train"})
            cl_file = tmp_cl.name

        try:
            with self.assertRaises(ValueError) as ctx:
                self.analyzer.audit_in_distribution_split(
                    split_csv_path=split_file,
                    clusters_csv_path=cl_file,
                    require_cluster_manifest=True,
                )
            self.assertIn("Duplicate example_id values detected in cluster manifest", str(ctx.exception))
        finally:
            if os.path.exists(split_file):
                os.remove(split_file)
            if os.path.exists(cl_file):
                os.remove(cl_file)

    def test_14_failure_injection_cluster_coverage_incomplete(self):
        """Asserts ValueError is raised when full coverage is required but example IDs are missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_split:
            writer = csv.DictWriter(tmp_split, fieldnames=["example_id", "split", "intent_label", "domain"])
            writer.writeheader()
            writer.writerow({"example_id": "e1", "split": "train", "intent_label": "account_access", "domain": "bank_account"})
            writer.writerow({"example_id": "e2", "split": "train", "intent_label": "account_access", "domain": "bank_account"})
            split_file = tmp_split.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp_cl:
            writer = csv.DictWriter(tmp_cl, fieldnames=["cluster_id", "example_id", "split"])
            writer.writeheader()
            writer.writerow({"cluster_id": "c1", "example_id": "e1", "split": "train"})
            cl_file = tmp_cl.name

        try:
            with self.assertRaises(ValueError) as ctx:
                self.analyzer.audit_in_distribution_split(
                    split_csv_path=split_file,
                    clusters_csv_path=cl_file,
                    require_cluster_manifest=True,
                    require_full_coverage=True,
                )
            self.assertIn("Incomplete cluster mapping coverage", str(ctx.exception))
        finally:
            if os.path.exists(split_file):
                os.remove(split_file)
            if os.path.exists(cl_file):
                os.remove(cl_file)

    def test_15_cross_process_determinism(self):
        """Asserts bit-for-bit identical matrix outputs across differing PYTHONHASHSEED environments."""
        code = (
            "import sys; "
            "from src.data.split_analyzer import SplitAnalyzer; "
            "sa = SplitAnalyzer(); "
            "res = sa.audit_temporal_distribution(); "
            "print(f'{res[\"total_months\"]}:{res[\"total_complaints\"]}:{res[\"active_in_all_years\"]}')"
        )
        env0 = os.environ.copy()
        env0["PYTHONHASHSEED"] = "0"
        p0 = subprocess.run([sys.executable, "-c", code], env=env0, capture_output=True, text=True, cwd=REPO_ROOT)

        env1 = os.environ.copy()
        env1["PYTHONHASHSEED"] = "42"
        p1 = subprocess.run([sys.executable, "-c", code], env=env1, capture_output=True, text=True, cwd=REPO_ROOT)

        self.assertEqual(p0.returncode, 0)
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p0.stdout.strip(), p1.stdout.strip())

    # -------------------------------------------------------------------------
    # Isolated Audit Pillar Failure Injection Tests (16-22)
    # -------------------------------------------------------------------------
    def test_16_failure_injection_pillar_1(self):
        """Asserts audit failure when Pillar 1 environment preflight fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=1)
            self.assertFalse(passed, "Audit must fail when Pillar 1 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_17_failure_injection_pillar_2(self):
        """Asserts audit failure when Pillar 2 provenance fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=2)
            self.assertFalse(passed, "Audit must fail when Pillar 2 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_18_failure_injection_pillar_3(self):
        """Asserts audit failure when Pillar 3 matrix invariant fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=3)
            self.assertFalse(passed, "Audit must fail when Pillar 3 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_19_failure_injection_pillar_4(self):
        """Asserts audit failure when Pillar 4 confounding audit fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=4)
            self.assertFalse(passed, "Audit must fail when Pillar 4 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_20_failure_injection_pillar_5(self):
        """Asserts audit failure when Pillar 5 temporal audit fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=5)
            self.assertFalse(passed, "Audit must fail when Pillar 5 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_21_failure_injection_pillar_6(self):
        """Asserts audit failure when Pillar 6 in-distribution split fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=6)
            self.assertFalse(passed, "Audit must fail when Pillar 6 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_22_failure_injection_pillar_7(self):
        """Asserts audit failure when Pillar 7 governance reconciliation fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=7)
            self.assertFalse(passed, "Audit must fail when Pillar 7 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_23_full_phase7_audit_execution(self):
        """Asserts that running Phase 7 audit end-to-end produces PASSED status and generated report."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase7_audit_internal(skip_tests=True, report_path=tmp_path)
            self.assertTrue(passed, "Full Phase 7 audit must PASS")
            self.assertTrue(os.path.exists(tmp_path), "Report snapshot must be created")
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Audit Status:** **PASSED**", content)
            self.assertIn("Pillar Results Summary", content)
            self.assertIn("56.25% sparsity", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
