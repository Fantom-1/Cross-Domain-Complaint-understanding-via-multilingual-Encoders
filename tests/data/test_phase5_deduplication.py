#!/usr/bin/env python3
"""Comprehensive unit test suite for Phase 5: Duplicate, Overlap, and Contamination Audit.

Covers:
- Exact SHA-256 text hashing determinism.
- Word shingling, set Jaccard similarity, and edge cases.
- Union-Find disjoint set data structure with path compression.
- MinHash LSH signature generation and band hashing.
- Synthetic exact duplicate, near-duplicate, and label conflict detection.
- Empirical validation of zero split leakage on the canonical dataset.
- Duplicate audit manifest and cluster catalog schema/content invariants.
- Failure-injection regression tests (injected split leakage, mutated cluster sizes, schema corruptions).
- LSH candidate verification and false-bridge rejection.
- Symmetric Unicode NFC and whitespace normalization collision tests.
- Positive near-duplicate cross-dataset fixture.
- Cross-process determinism under randomized PYTHONHASHSEED.
- Independent example_id vs source_id uniqueness tracking.
"""

import collections
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.audit_phase5 import (
    EXPECTED_AUDIT_METRICS_COUNT,
    EXPECTED_CLUSTER_COLUMNS,
    EXPECTED_DUPLICATE_EXAMPLE_IDS,
    EXPECTED_DUPLICATE_SOURCE_IDS,
    EXPECTED_EXACT_CONFLICTS,
    EXPECTED_GROUP_CONFLICTS,
    EXPECTED_MAX_CLUSTER_SIZE,
    EXPECTED_MULTI_ITEM_CLUSTERS,
    EXPECTED_MULTI_ITEM_INSTANCES,
    EXPECTED_TOTAL_GROUPS,
    EXPECTED_TOTAL_RECORDS,
    EXPECTED_UNIQUE_EXAMPLE_IDS,
    EXPECTED_UNIQUE_SOURCE_IDS,
    run_phase5_audit,
)
from src.data.duplicate_auditor import (
    DuplicateAuditor,
    MinHasher,
    UnionFind,
    compute_sha256,
    compute_word_shingles,
    jaccard_similarity,
    normalize_for_comparison,
)

CANONICAL_PARQUET = os.path.join(REPO_ROOT, "data", "processed", "canonical_dataset.parquet")
AUDIT_CSV = os.path.join(REPO_ROOT, "data", "manifests", "duplicate_audit.csv")
CLUSTERS_CSV = os.path.join(REPO_ROOT, "data", "manifests", "duplicate_clusters.csv")
REPORT_MD = os.path.join(REPO_ROOT, "docs", "split_leakage_audit.md")
BANKING77_TRAIN = os.path.join(REPO_ROOT, "data", "raw", "banking77", "train.csv")
BANKING77_TEST = os.path.join(REPO_ROOT, "data", "raw", "banking77", "test.csv")


class TestPhase5Deduplication(unittest.TestCase):
    """Unit tests for Phase 5 Duplicate, Overlap & Contamination Audit."""

    def test_01_compute_sha256_determinism(self):
        """Asserts that compute_sha256 produces exact deterministic 64-char hex digests."""
        t1 = "Consumer complaint narrative regarding unauthorized credit inquiry."
        h1 = compute_sha256(t1)
        self.assertEqual(len(h1), 64)
        self.assertEqual(h1, compute_sha256(t1))
        # Empty string hash check
        self.assertEqual(compute_sha256(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_02_compute_word_shingles(self):
        """Asserts word shingling handles case-insensitivity, whitespace, and short texts."""
        text = "The quick   brown fox jumps over the lazy dog."
        shingles = compute_word_shingles(text, k=3)
        self.assertIn("the quick brown", shingles)
        self.assertIn("quick brown fox", shingles)
        self.assertIn("lazy dog", compute_word_shingles("Lazy dog", k=5))
        self.assertEqual(compute_word_shingles("", k=3), set())

    def test_03_jaccard_similarity(self):
        """Asserts exact Jaccard similarity computation across edge cases."""
        s1 = {"a", "b", "c"}
        s2 = {"b", "c", "d"}
        self.assertAlmostEqual(jaccard_similarity(s1, s2), 2 / 4)
        self.assertEqual(jaccard_similarity(set(), set()), 1.0)
        self.assertEqual(jaccard_similarity(s1, set()), 0.0)
        self.assertEqual(jaccard_similarity(s1, s1), 1.0)

    def test_04_union_find_cycle_free_and_compression(self):
        """Asserts UnionFind correctly merges components and prevents cycles."""
        uf = UnionFind()
        self.assertEqual(uf.find("A"), "A")
        self.assertTrue(uf.union("A", "B"))
        self.assertEqual(uf.find("A"), uf.find("B"))
        self.assertFalse(uf.union("A", "B"), "Repeated union must return False")

        # Transitive merging: C with B -> C with A
        self.assertTrue(uf.union("B", "C"))
        self.assertEqual(uf.find("C"), uf.find("A"))

    def test_05_minhasher_signature_stability(self):
        """Asserts MinHasher produces reproducible signatures and band hashes."""
        m1 = MinHasher(n_perm=64, bands=16, seed=13)
        m2 = MinHasher(n_perm=64, bands=16, seed=13)

        sh = {"credit reporting dispute", "unauthorized inquiry account", "fcra violation 30 days"}
        sig1 = m1.signature(sh)
        sig2 = m2.signature(sh)
        self.assertEqual(sig1, sig2)
        self.assertEqual(len(sig1), 64)

        bands1 = m1.band_hashes(sig1)
        bands2 = m2.band_hashes(sig2)
        self.assertEqual(bands1, bands2)
        self.assertEqual(len(bands1), 16)

    def test_06_synthetic_exact_duplicate_detection(self):
        """Asserts DuplicateAuditor accurately identifies exact duplicate collisions."""
        records = [
            {"example_id": "1", "text_normalized": "Identical complaint text.", "split": "train", "intent_label": "dispute"},
            {"example_id": "2", "text_normalized": "Identical complaint text.", "split": "train", "intent_label": "dispute"},
            {"example_id": "3", "text_normalized": "Unique complaint narrative.", "split": "train", "intent_label": "fraud"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["total_records"], 3)
        self.assertEqual(s["unique_normalized_hashes"], 2)
        self.assertEqual(s["exact_duplicate_instances"], 2)
        self.assertEqual(s["exact_duplicate_hash_count"], 1)
        self.assertEqual(s["exact_clusters_with_label_conflict"], 0)

    def test_07_synthetic_near_duplicate_clustering(self):
        """Asserts DuplicateAuditor correctly groups near-duplicates and tallies multi-item clusters."""
        records = [
            {"example_id": "1", "text_normalized": "I dispute this credit inquiry under FCRA section 609.", "split": "train", "intent_label": "dispute"},
            {"example_id": "2", "text_normalized": "I dispute this credit inquiry under FCRA section 609 immediately.", "split": "train", "intent_label": "dispute"},
            {"example_id": "3", "text_normalized": "Completely unrelated narrative about mortgage interest rate increase.", "split": "train", "intent_label": "mortgage"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["total_groups"], 2)
        self.assertEqual(s["singleton_groups"], 1)
        self.assertEqual(s["multi_item_clusters"], 1)
        self.assertEqual(s["multi_item_instances"], 2)
        self.assertEqual(s["max_cluster_size"], 2)

    def test_08_synthetic_label_conflict_detection(self):
        """Asserts DuplicateAuditor detects conflicting labels within exact duplicate groups."""
        records = [
            {"example_id": "1", "text_normalized": "Identical boilerplate dispute letter.", "split": "train", "intent_label": "label_A"},
            {"example_id": "2", "text_normalized": "Identical boilerplate dispute letter.", "split": "train", "intent_label": "label_B"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["exact_clusters_with_label_conflict"], 1)
        self.assertEqual(s["group_clusters_with_label_conflict"], 1)
        self.assertEqual(len(res["exact_conflicts"]), 1)
        self.assertIn("label_A", res["exact_conflicts"][0]["labels"])
        self.assertIn("label_B", res["exact_conflicts"][0]["labels"])

    def test_09_synthetic_split_leakage_detection(self):
        """Asserts DuplicateAuditor catches simulated split contamination across train and test."""
        # Leaked text across train and test
        records = [
            {"example_id": "1", "text_normalized": "Boilerplate inquiry template.", "split": "train", "intent_label": "dispute"},
            {"example_id": "2", "text_normalized": "Boilerplate inquiry template.", "split": "test", "intent_label": "dispute"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertFalse(s["zero_leakage_verified"])
        self.assertEqual(s["train_test_group_leakage"], 1)
        self.assertEqual(s["train_test_hash_leakage"], 1)

    def test_10_canonical_dataset_zero_leakage(self):
        """Empirically verifies that canonical_dataset.parquet has strictly 0 split leakage."""
        if not os.path.isfile(CANONICAL_PARQUET):
            self.skipTest("canonical_dataset.parquet untracked locally (CI mode)")

        import pandas as pd
        df = pd.read_parquet(CANONICAL_PARQUET)
        records = df.to_dict("records")

        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertTrue(s["zero_leakage_verified"], "Zero partition leakage must hold across all records")
        self.assertEqual(s["train_val_group_leakage"], 0)
        self.assertEqual(s["train_test_group_leakage"], 0)
        self.assertEqual(s["val_test_group_leakage"], 0)
        self.assertEqual(s["train_val_hash_leakage"], 0)
        self.assertEqual(s["train_test_hash_leakage"], 0)
        self.assertEqual(s["val_test_hash_leakage"], 0)

    def test_11_duplicate_audit_manifest_schema_and_metrics(self):
        """Asserts duplicate_audit.csv schema, row count, and core metric values."""
        self.assertTrue(os.path.isfile(AUDIT_CSV), f"Missing {AUDIT_CSV}")

        with open(AUDIT_CSV, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), EXPECTED_AUDIT_METRICS_COUNT)
            m_dict = {r["metric_name"]: r["metric_value"] for r in reader}

        self.assertEqual(int(m_dict["total_records"]), EXPECTED_TOTAL_RECORDS)
        self.assertEqual(int(m_dict["unique_example_ids"]), EXPECTED_UNIQUE_EXAMPLE_IDS)
        self.assertEqual(int(m_dict["duplicate_example_ids"]), EXPECTED_DUPLICATE_EXAMPLE_IDS)
        self.assertEqual(int(m_dict["unique_source_ids"]), EXPECTED_UNIQUE_SOURCE_IDS)
        self.assertEqual(int(m_dict["duplicate_source_ids"]), EXPECTED_DUPLICATE_SOURCE_IDS)
        self.assertEqual(int(m_dict["total_groups"]), EXPECTED_TOTAL_GROUPS)
        self.assertEqual(int(m_dict["multi_item_clusters"]), EXPECTED_MULTI_ITEM_CLUSTERS)
        self.assertEqual(int(m_dict["multi_item_instances"]), EXPECTED_MULTI_ITEM_INSTANCES)
        self.assertEqual(int(m_dict["max_cluster_size"]), EXPECTED_MAX_CLUSTER_SIZE)
        self.assertEqual(int(m_dict["exact_clusters_with_label_conflict"]), EXPECTED_EXACT_CONFLICTS)
        self.assertEqual(int(m_dict["group_clusters_with_label_conflict"]), EXPECTED_GROUP_CONFLICTS)
        self.assertEqual(m_dict["zero_leakage_verified"].strip().lower(), "true")
        self.assertEqual(int(m_dict["banking77_contamination_count"]), 0)

    def test_12_duplicate_clusters_manifest_schema_and_counts(self):
        """Asserts duplicate_clusters.csv schema and instance counts."""
        self.assertTrue(os.path.isfile(CLUSTERS_CSV), f"Missing {CLUSTERS_CSV}")

        with open(CLUSTERS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, EXPECTED_CLUSTER_COLUMNS)
            rows = list(reader)
            self.assertEqual(len(rows), EXPECTED_MULTI_ITEM_INSTANCES)

            unique_clusters = set(r["cluster_id"] for r in rows)
            self.assertEqual(len(unique_clusters), EXPECTED_MULTI_ITEM_CLUSTERS)

    def test_13_duplicate_clusters_row_level_size_reconciliation(self):
        """Asserts each row in duplicate_clusters.csv has cluster_size matching actual members."""
        with open(CLUSTERS_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        counts = collections.Counter(r["cluster_id"] for r in rows)
        for r in rows:
            claimed_size = int(r["cluster_size"])
            actual_size = counts[r["cluster_id"]]
            self.assertEqual(claimed_size, actual_size, f"Size mismatch for {r['cluster_id']}")

    def test_14_cluster_diameter_and_chain_merging_quantification(self):
        """Asserts compute_cluster_diameters produces valid pairwise metrics."""
        records = [
            {"example_id": "1", "text_normalized": "Short text for cluster A shingle test.", "cluster_id": "cA"},
            {"example_id": "2", "text_normalized": "Short text for cluster A shingle test variant.", "cluster_id": "cA"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.compute_cluster_diameters(records, sample_clusters=5)
        self.assertEqual(res["evaluated_clusters"], 1)
        self.assertGreater(res["aggregate_mean_jaccard"], 0.0)

    def test_15_cross_dataset_banking77_zero_contamination(self):
        """Asserts zero exact or near-duplicate text collisions between CFPB complaints and Banking77 queries."""
        if not os.path.isfile(CANONICAL_PARQUET) or not os.path.isfile(BANKING77_TRAIN):
            self.skipTest("Canonical dataset or Banking77 untracked locally (CI mode)")

        import pandas as pd
        df_cfpb = pd.read_parquet(CANONICAL_PARQUET)
        b77_tr = pd.read_csv(BANKING77_TRAIN)
        b77_te = pd.read_csv(BANKING77_TEST)
        df_b77 = pd.concat([b77_tr, b77_te], ignore_index=True)

        cfpb_set = {normalize_for_comparison(t) for t in df_cfpb["text_normalized"]}
        b77_set = {normalize_for_comparison(t) for t in df_b77["text"]}

        overlap = cfpb_set.intersection(b77_set)
        self.assertEqual(len(overlap), 0, "No query should collide across CFPB and Banking77")

    def test_16_audit_pillar1_failure_injection_disk(self):
        """Asserts audit fails when Pillar 1 environment preflight is violated."""
        if os.environ.get("PHASE5_AUDIT_RUNNING") == "1":
            return
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp_rep = tmp.name
        try:
            passed = run_phase5_audit(force_pillar_fail=1, report_path=tmp_rep, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on Pillar 1 failure injection")
        finally:
            if os.path.exists(tmp_rep):
                os.remove(tmp_rep)

    def test_17_audit_pillar2_failure_injection_provenance(self):
        """Asserts audit fails when Pillar 2 provenance checksum is violated."""
        if os.environ.get("PHASE5_AUDIT_RUNNING") == "1":
            return
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp_rep = tmp.name
        try:
            passed = run_phase5_audit(force_pillar_fail=2, report_path=tmp_rep, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on Pillar 2 failure injection")
        finally:
            if os.path.exists(tmp_rep):
                os.remove(tmp_rep)

    def test_18_audit_failure_injection_mutated_leakage(self):
        """Asserts audit fails when split leakage metrics are non-zero."""
        if os.environ.get("PHASE5_AUDIT_RUNNING") == "1":
            return

        with open(AUDIT_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # Mutate train_val_group_leakage to 5
        for r in rows:
            if r["metric_name"] == "train_val_group_leakage":
                r["metric_value"] = "5"

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["metric_name", "metric_value", "description"])
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp_rep = tmp.name

        try:
            passed = run_phase5_audit(audit_csv_path=tmp_path, report_path=tmp_rep, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL when split leakage is non-zero")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_rep):
                os.remove(tmp_rep)

    def test_19_audit_failure_injection_corrupted_cluster_size(self):
        """Asserts audit fails when row-level cluster size does not reconcile with instance count."""
        if os.environ.get("PHASE5_AUDIT_RUNNING") == "1":
            return

        with open(CLUSTERS_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # Mutate the first row's cluster_size
        rows[0]["cluster_size"] = "9999"

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=EXPECTED_CLUSTER_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp_rep = tmp.name

        try:
            passed = run_phase5_audit(clusters_csv_path=tmp_path, report_path=tmp_rep, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL when cluster size is inconsistent")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_rep):
                os.remove(tmp_rep)

    def test_20_audit_failure_injection_mutated_total_records(self):
        """Asserts audit fails when total_records does not equal 45,723."""
        if os.environ.get("PHASE5_AUDIT_RUNNING") == "1":
            return

        with open(AUDIT_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for r in rows:
            if r["metric_name"] == "total_records":
                r["metric_value"] = "99999"

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["metric_name", "metric_value", "description"])
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp_rep = tmp.name

        try:
            passed = run_phase5_audit(audit_csv_path=tmp_path, report_path=tmp_rep, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL when total records is mutated")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_rep):
                os.remove(tmp_rep)

    def test_21_lsh_candidate_verification_and_false_bridge_rejection(self):
        """Asserts that MinHash candidate pairs are verified against Jaccard threshold and false bridges are rejected."""
        records = [
            # Pair (1, 2) has high Jaccard (>= 0.50)
            {"example_id": "1", "text_normalized": "dispute credit inquiry under fcra section 609 notice", "split": "train"},
            {"example_id": "2", "text_normalized": "dispute credit inquiry under fcra section 609 notice immediately", "split": "train"},
            # Doc 3 shares some prefix words with (1, 2) but has low Jaccard (< 0.50)
            {"example_id": "3", "text_normalized": "dispute credit inquiry mortgage billing fee penalty statement error", "split": "train"},
        ]
        auditor = DuplicateAuditor(jaccard_threshold=0.50)
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["lsh_verified_pairs"], 1, "Only genuine near-duplicate pair must be verified")
        cids = {r["example_id"]: r["cluster_id"] for r in records}
        self.assertEqual(cids["1"], cids["2"], "Near duplicate documents (1, 2) must be in the same cluster")
        self.assertNotEqual(cids["1"], cids["3"], "False bridge candidate (3) must be rejected and in a distinct cluster")

        # Transitive merging test: A-B >= 0.5, B-C >= 0.5, but A-C < 0.5
        tA = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
        tB = "alpha bravo charlie delta echo foxtrot golf hotel india kilo"
        tC = "alpha bravo charlie delta echo foxtrot golf hotel lima kilo"
        tD = "totally unrelated text about checking account overdraft fees and charges"

        trans_records = [
            {"example_id": "A", "text_normalized": tA, "split": "train"},
            {"example_id": "B", "text_normalized": tB, "split": "train"},
            {"example_id": "C", "text_normalized": tC, "split": "train"},
            {"example_id": "D", "text_normalized": tD, "split": "train"},
        ]
        res_trans = auditor.audit_records(trans_records)
        trans_cids = {r["example_id"]: r["cluster_id"] for r in trans_records}
        self.assertEqual(trans_cids["A"], trans_cids["B"])
        self.assertEqual(trans_cids["B"], trans_cids["C"])
        self.assertEqual(trans_cids["A"], trans_cids["C"], "Transitive chaining must merge components in UnionFind")
        self.assertNotEqual(trans_cids["A"], trans_cids["D"], "Unrelated narrative must remain isolated")

    def test_22_symmetric_case_and_whitespace_normalization(self):
        """Asserts symmetric NFC Unicode normalization and whitespace collapsing across datasets."""
        raw_text_1 = "  Dispute \t Under  FCRA \n SECTION 609 \u00a0 "
        raw_text_2 = "dispute under fcra section 609"

        n1 = normalize_for_comparison(raw_text_1)
        n2 = normalize_for_comparison(raw_text_2)
        self.assertEqual(n1, n2)
        self.assertEqual(compute_sha256(n1), compute_sha256(n2))

        records = [
            {"example_id": "1", "text_normalized": raw_text_1, "split": "train"},
            {"example_id": "2", "text_normalized": raw_text_2, "split": "train"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["exact_duplicate_instances"], 2)
        self.assertEqual(s["exact_duplicate_hash_count"], 1)

    def test_23_cross_dataset_positive_near_duplicate_fixture(self):
        """Asserts positive detection when a synthetic near-duplicate cross-dataset contamination is injected."""
        cfpb_record = {
            "example_id": "cfpb_101",
            "text_normalized": "i need to dispute an unauthorized charge on my credit card immediately",
            "split": "train",
        }
        # Auxiliary near-duplicate (sharing 5 out of 6 5-word shingles, J >= 0.50)
        aux_contaminant = {
            "text": "i need to dispute an unauthorized charge on my credit card",
        }
        aux_clean = {
            "text": "mortgage escrow refund check never arrived in the postal mail at my address",
        }

        auditor = DuplicateAuditor(jaccard_threshold=0.50)
        res = auditor.audit_records([cfpb_record], auxiliary_records=[aux_contaminant, aux_clean])
        s = res["summary"]

        self.assertEqual(s["banking77_near_contamination"], 1)
        self.assertEqual(s["banking77_contamination_count"], 1)
        self.assertEqual(len(res["banking77_contaminated_samples"]), 1)
        self.assertEqual(res["banking77_contaminated_samples"][0]["type"], "near_duplicate")

    def test_24_cross_process_cluster_diameter_determinism(self):
        """Asserts that compute_cluster_diameters produces bit-for-bit identical metrics across Python processes under different PYTHONHASHSEED."""
        sub_code = """
import json, sys
from src.data.duplicate_auditor import DuplicateAuditor

records = [
    {'example_id': f'e_{i}', 'text_normalized': f'Consumer complaint narrative template variant {i % 5} for testing', 'cluster_id': 'grp_1'}
    for i in range(40)
]
auditor = DuplicateAuditor(seed=42)
res = auditor.compute_cluster_diameters(records, sample_clusters=1, max_pairs_per_cluster=50)
print(json.dumps(res, sort_keys=True))
"""
        env1 = dict(os.environ, PYTHONHASHSEED="0")
        env2 = dict(os.environ, PYTHONHASHSEED="99999")

        p1 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env1)
        p2 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env2)

        self.assertEqual(p1.returncode, 0, f"Process 1 failed: {p1.stderr}")
        self.assertEqual(p2.returncode, 0, f"Process 2 failed: {p2.stderr}")
        self.assertEqual(p1.stdout.strip(), p2.stdout.strip(), "Cluster sampling outputs must be bit-for-bit identical across processes")

    def test_25_source_id_and_example_id_metrics(self):
        """Asserts independent tracking of example_id and source_id fields."""
        records = [
            {"example_id": "cfpb_101", "source_id": "101", "text_normalized": "Text 1", "split": "train"},
            {"example_id": "cfpb_102", "source_id": "101", "text_normalized": "Text 2", "split": "train"},  # duplicate source_id
            {"example_id": "cfpb_103", "source_id": "103", "text_normalized": "Text 3", "split": "train"},
        ]
        auditor = DuplicateAuditor()
        res = auditor.audit_records(records)
        s = res["summary"]

        self.assertEqual(s["unique_example_ids"], 3)
        self.assertEqual(s["duplicate_example_ids"], 0)
        self.assertEqual(s["unique_source_ids"], 2)
        self.assertEqual(s["duplicate_source_ids"], 1)


if __name__ == "__main__":
    unittest.main()
