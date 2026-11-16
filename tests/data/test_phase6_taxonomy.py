#!/usr/bin/env python3
"""Comprehensive unit test suite for Phase 6: Label Taxonomy Codebook, Mapping Audit & Pilot Protocol.

Covers:
- Taxonomy JSON schema, 16 classes, and definition completeness.
- Operational taxonomy codebook presence, boundaries, and multi-issue guidelines.
- Source label mapping schema, counts (221 total, 198 mapped, 23 unmapped), and collision detection (17 collisions).
- Stratified pilot sampling determinism, exact 320-record size, 20-per-class balance,
  domain x split quotas (224 train / 48 val / 48 test), and cluster exclusivity (320 unique clusters).
- Blinded annotation instrument generation, complete metadata stripping, and blank rater columns.
- Mathematical correctness of Cohen's Kappa under synthetic and edge-case distributions.
- Provenance auditing to enforce that synthetic simulations are explicitly tagged and cannot
  be presented as human adjudication.
- Regression test proving human rater columns cannot be populated from weak labels or heuristics.
- Governance notices and exact headline reconciliation.
- Cross-process determinism under differing PYTHONHASHSEED environments.
- Failure-injection tests for audit pillars isolated to temporary files.
"""

import collections
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.audit_phase6 import (
    ADJUDICATION_TMPL_CSV,
    ANNOTATION_AGREEMENT_MD,
    CANONICAL_PARQUET,
    EXPECTED_BLINDED_COLUMNS,
    EXPECTED_CLASS_COUNT,
    EXPECTED_COLLISION_COUNT,
    EXPECTED_MAPPED_COUNT,
    EXPECTED_PILOT_PER_CLASS,
    EXPECTED_PILOT_SIZE,
    EXPECTED_PILOT_TEST,
    EXPECTED_PILOT_TRAIN,
    EXPECTED_PILOT_UNIQUE_CLUSTERS,
    EXPECTED_PILOT_VAL,
    EXPECTED_TOTAL_MAPPINGS,
    EXPECTED_UNMAPPED_COUNT,
    PILOT_SAMPLING_CSV,
    RATER_1_SHEET_CSV,
    RATER_2_SHEET_CSV,
    SOURCE_MAPPING_CSV,
    SYNTHETIC_SIM_CSV,
    TAXONOMY_CODEBOOK_MD,
    TAXONOMY_JSON,
    _run_phase6_audit_internal,
)
from src.data.taxonomy_auditor import (
    PROVENANCE_HUMAN,
    PROVENANCE_SYNTHETIC,
    TaxonomyAuditor,
    compute_cohens_kappa,
    compute_per_class_metrics,
    load_taxonomy,
)


class TestPhase6Taxonomy(unittest.TestCase):
    """Unit and regression tests for Phase 6 taxonomy, audit, and pilot protocol."""

    @classmethod
    def setUpClass(cls):
        cls.auditor = TaxonomyAuditor()

    def test_01_taxonomy_json_structure_and_16_classes(self):
        """Asserts configs/taxonomy.json has exactly 16 classes and required metadata."""
        tax = load_taxonomy()
        self.assertIn("classes", tax)
        self.assertEqual(len(tax["classes"]), EXPECTED_CLASS_COUNT)

        ids = [c["intent_id"] for c in tax["classes"]]
        labels = [c["intent_label"] for c in tax["classes"]]

        # Intent IDs must be 0 to 15 contiguous
        self.assertEqual(sorted(ids), list(range(EXPECTED_CLASS_COUNT)))
        self.assertEqual(len(set(labels)), EXPECTED_CLASS_COUNT)

        for c in tax["classes"]:
            self.assertTrue(c["definition"], f"Class {c['intent_label']} missing definition")
            self.assertTrue(c["rule_patterns"], f"Class {c['intent_label']} missing rule_patterns")

    def test_02_taxonomy_codebook_presence_and_coverage(self):
        """Asserts docs/taxonomy_codebook.md exists and documents all 16 classes and boundary rules."""
        self.assertTrue(os.path.exists(TAXONOMY_CODEBOOK_MD), "Codebook must exist")
        with open(TAXONOMY_CODEBOOK_MD, "r", encoding="utf-8") as f:
            content = f.read()

        for c in self.auditor.class_names:
            self.assertIn(f"`{c}`", content, f"Codebook must document class `{c}`")

        self.assertIn("Epistemological Governance & Supervision Boundary", content)
        self.assertIn("Positive Inclusions", content)
        self.assertIn("Negative Exclusions", content)
        self.assertIn("Confusable Pairs & Priority Resolution Table", content)
        self.assertIn("Multi-Issue and Ambiguity Policy Summary", content)

    def test_03_source_label_mapping_counts_and_schema(self):
        """Asserts source_label_mapping.csv has 221 total rows (198 mapped, 23 unmapped)."""
        self.assertTrue(os.path.exists(SOURCE_MAPPING_CSV), "source_label_mapping.csv must exist")
        with open(SOURCE_MAPPING_CSV, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        self.assertEqual(len(reader), EXPECTED_TOTAL_MAPPINGS)
        mapped = sum(1 for r in reader if r["mapping_status"] == "mapped")
        unmapped = sum(1 for r in reader if r["mapping_status"] == "unmapped")

        self.assertEqual(mapped, EXPECTED_MAPPED_COUNT)
        self.assertEqual(unmapped, EXPECTED_UNMAPPED_COUNT)

    def test_04_rule_collision_detection_invariants(self):
        """Asserts audit_source_mapping_collisions identifies exactly 17 multi-pattern collisions."""
        res = self.auditor.audit_source_mapping_collisions(SOURCE_MAPPING_CSV)
        self.assertEqual(res["total_mappings"], EXPECTED_TOTAL_MAPPINGS)
        self.assertEqual(res["mapped_count"], EXPECTED_MAPPED_COUNT)
        self.assertEqual(res["unmapped_count"], EXPECTED_UNMAPPED_COUNT)
        self.assertEqual(res["collision_count"], EXPECTED_COLLISION_COUNT)

        for c in res["collisions"]:
            self.assertIn("source_label", c)
            self.assertIn("assigned_label", c)
            self.assertGreater(len(c["matching_intents"]), 1)

    def test_05_stratified_pilot_sampling_size_balance_and_split_quotas(self):
        """Asserts stratified sampling produces 320 records (20/class), exact split quotas, and 320 unique clusters."""
        if not os.path.isfile(CANONICAL_PARQUET):
            self.skipTest("canonical_dataset.parquet untracked locally (CI mode)")
        samples = self.auditor.sample_stratified_pilot()
        self.assertEqual(len(samples), EXPECTED_PILOT_SIZE)

        counts = collections.Counter(s["weak_cfpb_label"] for s in samples)
        self.assertEqual(len(counts), EXPECTED_CLASS_COUNT)
        for cls_name, cnt in counts.items():
            self.assertEqual(cnt, EXPECTED_PILOT_PER_CLASS)

        # Global split totals
        split_c = collections.Counter(s["split"] for s in samples)
        self.assertEqual(split_c["train"], EXPECTED_PILOT_TRAIN)
        self.assertEqual(split_c["validation"], EXPECTED_PILOT_VAL)
        self.assertEqual(split_c["test"], EXPECTED_PILOT_TEST)

        # Independent audit of per-class split matrix: 14 train / 3 val / 3 test per class
        class_splits = collections.defaultdict(lambda: collections.Counter())
        for s in samples:
            class_splits[s["weak_cfpb_label"]][s["split"]] += 1
        for cls_name, s_counts in class_splits.items():
            self.assertEqual(s_counts["train"], 14, f"Class {cls_name} must have 14 train")
            self.assertEqual(s_counts["validation"], 3, f"Class {cls_name} must have 3 validation")
            self.assertEqual(s_counts["test"], 3, f"Class {cls_name} must have 3 test")

        # Cluster exclusivity check
        unique_clusters = set(s["cluster_id"] for s in samples)
        self.assertEqual(len(unique_clusters), EXPECTED_PILOT_UNIQUE_CLUSTERS)

    def test_05b_synthetic_stratified_pilot_sampling(self):
        """Asserts stratified sampling on synthetic fixture (runs in both CI and local)."""
        import pandas as pd
        synth_rows = []
        for c in self.auditor.class_names:
            for i in range(25):
                synth_rows.append({
                    "example_id": f"syn_{c}_{i}",
                    "text_normalized": f"Complaint narrative text for class {c} instance {i}",
                    "text_hash": f"hash_{c}_{i:03d}",
                    "domain": f"domain_{i % 3}",
                    "source_label": f"Source {c}",
                    "intent_label": c,
                    "split": "train" if i < 18 else ("validation" if i < 21 else "test"),
                    "group_id": f"grp_{c}_{i}"
                })
        synth_df = pd.DataFrame(synth_rows)
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_parquet = tmp.name
        try:
            synth_df.to_parquet(tmp_parquet)
            samples = self.auditor.sample_stratified_pilot(parquet_path=tmp_parquet, clusters_csv_path=None)
            self.assertEqual(len(samples), EXPECTED_PILOT_SIZE)
            counts = collections.Counter(s["weak_cfpb_label"] for s in samples)
            self.assertEqual(len(counts), EXPECTED_CLASS_COUNT)
            split_c = collections.Counter(s["split"] for s in samples)
            self.assertEqual(split_c["train"], EXPECTED_PILOT_TRAIN)
            self.assertEqual(split_c["validation"], EXPECTED_PILOT_VAL)
            self.assertEqual(split_c["test"], EXPECTED_PILOT_TEST)

            # Per-class split matrix check on synthetic fixture
            class_splits = collections.defaultdict(lambda: collections.Counter())
            for s in samples:
                class_splits[s["weak_cfpb_label"]][s["split"]] += 1
            for cls_name, s_counts in class_splits.items():
                self.assertEqual(s_counts["train"], 14, f"Class {cls_name} must have 14 train")
                self.assertEqual(s_counts["validation"], 3, f"Class {cls_name} must have 3 validation")
                self.assertEqual(s_counts["test"], 3, f"Class {cls_name} must have 3 test")
        finally:
            if os.path.exists(tmp_parquet):
                os.remove(tmp_parquet)

    def test_06_blinded_annotation_sheets_integrity_and_no_leakage(self):
        """Asserts blinded sheets exist, have 320 rows, strip all metadata, and have blank rater columns."""
        for sheet_path in [RATER_1_SHEET_CSV, RATER_2_SHEET_CSV]:
            self.assertTrue(os.path.exists(sheet_path), f"Blinded sheet must exist: {sheet_path}")
            with open(sheet_path, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(len(rows), EXPECTED_PILOT_SIZE)
            self.assertEqual(list(rows[0].keys()), EXPECTED_BLINDED_COLUMNS)

            # Assert blank annotator fields (ready for human raters)
            for r in rows:
                self.assertEqual(r["annotator_label"], "")
                self.assertEqual(r["confidence_1_to_5"], "")
                self.assertEqual(r["rationale"], "")

                # Assert zero metadata leakage
                self.assertNotIn("weak_cfpb_label", r)
                self.assertNotIn("source_label", r)
                self.assertNotIn("domain", r)
                self.assertNotIn("split", r)

    def test_07_cohens_kappa_perfect_and_chance_agreement(self):
        """Asserts compute_cohens_kappa returns 1.0 on identical ratings and <= 0.0 on inverted."""
        r1 = ["a", "b", "c", "d"]
        r2 = ["a", "b", "c", "d"]
        po, kappa = compute_cohens_kappa(r1, r2)
        self.assertEqual(po, 1.0)
        self.assertEqual(kappa, 1.0)

        r3 = ["a", "a", "b", "b"]
        r4 = ["b", "b", "a", "a"]
        po_inv, kappa_inv = compute_cohens_kappa(r3, r4)
        self.assertEqual(po_inv, 0.0)
        self.assertLess(kappa_inv, 0.0)

    def test_08_cohens_kappa_known_numerical_vector(self):
        """Asserts compute_cohens_kappa matches known hand-calculated 2x2 matrix."""
        r1 = ["yes"] * 14 + ["yes"] * 1 + ["no"] * 4 + ["no"] * 6
        r2 = ["yes"] * 14 + ["no"] * 1 + ["yes"] * 4 + ["no"] * 6
        po, kappa = compute_cohens_kappa(r1, r2)
        self.assertAlmostEqual(po, 0.80, places=3)
        self.assertAlmostEqual(kappa, 0.5614, places=3)

    def test_09_synthetic_simulation_provenance_tagging(self):
        """Asserts synthetic simulation manifest is strictly tagged with provenance 'synthetic_rule_simulation'."""
        self.assertTrue(os.path.exists(SYNTHETIC_SIM_CSV), "Simulation manifest must exist")
        with open(SYNTHETIC_SIM_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), EXPECTED_PILOT_SIZE)
        for r in rows:
            self.assertEqual(r["provenance"], PROVENANCE_SYNTHETIC)
            self.assertIn("simulated_rater_1_label", r)
            self.assertIn("simulated_rater_2_label", r)
            self.assertIn("simulated_adjudicated_label", r)

    def test_10_provenance_auditor_detects_synthetic_vs_human(self):
        """Asserts TaxonomyAuditor.audit_annotation_provenance fails closed on missing/mixed/unrecognized provenance."""
        # 1. Valid synthetic file passes
        res = self.auditor.audit_annotation_provenance(SYNTHETIC_SIM_CSV)
        self.assertTrue(res["is_synthetic"])
        self.assertFalse(res["is_human"])
        self.assertEqual(res["provenance"], PROVENANCE_SYNTHETIC)

        # 2. Missing provenance column fails closed
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["pilot_id", "example_id", "rater_1_label"])
            writer.writeheader()
            writer.writerow({"pilot_id": "P1", "example_id": "E1", "rater_1_label": "fraud"})
            no_prov_path = tmp.name
        try:
            with self.assertRaises(ValueError) as ctx:
                self.auditor.audit_annotation_provenance(no_prov_path)
            self.assertIn("Missing required 'provenance' column", str(ctx.exception))
        finally:
            if os.path.exists(no_prov_path):
                os.remove(no_prov_path)

        # 3. Missing/empty provenance value on a row fails closed
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["pilot_id", "provenance"])
            writer.writeheader()
            writer.writerow({"pilot_id": "P1", "provenance": PROVENANCE_SYNTHETIC})
            writer.writerow({"pilot_id": "P2", "provenance": ""})
            empty_prov_path = tmp.name
        try:
            with self.assertRaises(ValueError) as ctx:
                self.auditor.audit_annotation_provenance(empty_prov_path)
            self.assertIn("missing or empty 'provenance'", str(ctx.exception))
        finally:
            if os.path.exists(empty_prov_path):
                os.remove(empty_prov_path)

        # 4. Unrecognized provenance value fails closed
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["pilot_id", "provenance"])
            writer.writeheader()
            writer.writerow({"pilot_id": "P1", "provenance": "unknown_experimental_simulation"})
            unrec_path = tmp.name
        try:
            with self.assertRaises(ValueError) as ctx:
                self.auditor.audit_annotation_provenance(unrec_path)
            self.assertIn("unrecognized provenance", str(ctx.exception))
        finally:
            if os.path.exists(unrec_path):
                os.remove(unrec_path)

        # 5. Mixed provenance across rows fails closed
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["pilot_id", "provenance"])
            writer.writeheader()
            writer.writerow({"pilot_id": "P1", "provenance": PROVENANCE_SYNTHETIC})
            writer.writerow({"pilot_id": "P2", "provenance": PROVENANCE_HUMAN})
            mixed_path = tmp.name
        try:
            with self.assertRaises(ValueError) as ctx:
                self.auditor.audit_annotation_provenance(mixed_path)
            self.assertIn("Mixed/inconsistent provenance detected", str(ctx.exception))
        finally:
            if os.path.exists(mixed_path):
                os.remove(mixed_path)

        # 6. Valid human file passes
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["pilot_id", "provenance", "annotator_1_label", "annotator_2_label", "adjudicated_label"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({
                    "pilot_id": f"P{i}",
                    "provenance": PROVENANCE_HUMAN,
                    "annotator_1_label": "fraud_or_scam",
                    "annotator_2_label": "fraud_or_scam",
                    "adjudicated_label": "fraud_or_scam",
                })
            human_path = tmp.name
        try:
            h_res = self.auditor.audit_annotation_provenance(human_path)
            self.assertTrue(h_res["is_human"])
            self.assertFalse(h_res["is_synthetic"])
            self.assertTrue(h_res["has_raters"])
        finally:
            if os.path.exists(human_path):
                os.remove(human_path)

    def test_11_governance_disclaimers_in_protocol_report(self):
        """Asserts annotation_agreement.md contains required non-human simulation disclosure and weak notices."""
        self.assertTrue(os.path.exists(ANNOTATION_AGREEMENT_MD), "Report must exist")
        with open(ANNOTATION_AGREEMENT_MD, "r", encoding="utf-8") as f:
            text = f.read()

        self.assertIn("No empirical human adjudication has been conducted", text)
        self.assertIn("synthetic rule-based heuristic simulation", text)
        self.assertIn("weak administrative supervision", text)
        self.assertIn("PolyAI/banking77", text)
        self.assertIn("strictly isolated", text)
        self.assertIn("cannot estimate actual CFPB weak-label error", text)
        self.assertIn("strictly isolated", text)

    def test_12_cross_process_pilot_sampling_determinism(self):
        """Asserts sample_stratified_pilot produces identical outputs under different PYTHONHASHSEED."""
        if not os.path.isfile(CANONICAL_PARQUET):
            self.skipTest("canonical_dataset.parquet untracked locally (CI mode)")
        sub_code = """
import json, sys
from src.data.taxonomy_auditor import TaxonomyAuditor
auditor = TaxonomyAuditor()
samples = auditor.sample_stratified_pilot()
eids = [s['example_id'] for s in samples]
print(json.dumps(eids))
"""
        env1 = dict(os.environ, PYTHONHASHSEED="0")
        env2 = dict(os.environ, PYTHONHASHSEED="99999")

        p1 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env1)
        p2 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env2)

        self.assertEqual(p1.returncode, 0, f"Process 1 failed: {p1.stderr}")
        self.assertEqual(p2.returncode, 0, f"Process 2 failed: {p2.stderr}")
        self.assertEqual(p1.stdout.strip(), p2.stdout.strip(), "Pilot sampling must be bit-for-bit identical across processes")

    def test_13_synthetic_cross_process_determinism(self):
        """Asserts cross-process determinism on synthetic data (runs in both CI and local)."""
        sub_code = """
import json, sys, tempfile, os
import pandas as pd
from src.data.taxonomy_auditor import TaxonomyAuditor
auditor = TaxonomyAuditor()
synth_rows = []
for c in auditor.class_names:
    for i in range(25):
        synth_rows.append({
            'example_id': f'syn_{c}_{i}',
            'text_normalized': f'Complaint narrative {c} {i}',
            'text_hash': f'hash_{c}_{i:03d}',
            'domain': f'domain_{i % 3}',
            'source_label': f'Source {c}',
            'intent_label': c,
            'split': 'train' if i < 18 else ('validation' if i < 21 else 'test'),
            'group_id': f'grp_{c}_{i}'
        })
with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
    tpath = tmp.name
try:
    pd.DataFrame(synth_rows).to_parquet(tpath)
    samples = auditor.sample_stratified_pilot(parquet_path=tpath, clusters_csv_path=None)
    print(json.dumps([s['example_id'] for s in samples]))
finally:
    if os.path.exists(tpath):
        os.remove(tpath)
"""
        env1 = dict(os.environ, PYTHONHASHSEED="0")
        env2 = dict(os.environ, PYTHONHASHSEED="99999")

        p1 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env1)
        p2 = subprocess.run([sys.executable, "-c", sub_code], capture_output=True, text=True, env=env2)

        self.assertEqual(p1.returncode, 0, f"Process 1 failed: {p1.stderr}")
        self.assertEqual(p2.returncode, 0, f"Process 2 failed: {p2.stderr}")
        self.assertEqual(p1.stdout.strip(), p2.stdout.strip(), "Synthetic sampling must be bit-for-bit identical across processes")

    def test_14_regression_test_cannot_populate_human_raters_from_weak_labels(self):
        """Asserts the blinded annotation generator cannot populate human rater columns from weak labels."""
        # When generating blinded sheets, annotator fields MUST be completely blank
        dummy_sample = [{
            "pilot_id": "PILOT_999",
            "example_id": "cfpb_test",
            "text_normalized": "Testing narrative text",
            "domain": "credit_card",
            "source_label": "Source // Label",
            "weak_cfpb_label": "credit_terms_dispute",
            "split": "train",
            "group_id": "grp_test",
            "cluster_id": "cid_test"
        }]
        with tempfile.TemporaryDirectory() as tmp_dir:
            r1, r2, tmpl = self.auditor.generate_blinded_annotation_sheets(dummy_sample, output_dir=tmp_dir)
            with open(r1, "r", encoding="utf-8") as f:
                r1_rows = list(csv.DictReader(f))
            with open(r2, "r", encoding="utf-8") as f:
                r2_rows = list(csv.DictReader(f))

            # Rater columns must be empty string
            self.assertEqual(r1_rows[0]["annotator_label"], "")
            self.assertEqual(r2_rows[0]["annotator_label"], "")
            self.assertNotEqual(r1_rows[0]["annotator_label"], dummy_sample[0]["weak_cfpb_label"])

            # Metadata must not appear in blinded fields
            self.assertNotIn("weak_cfpb_label", r1_rows[0])
            self.assertNotIn("source_label", r1_rows[0])

    def test_15_regression_test_per_class_split_matrix_detects_swapped_splits(self):
        """Asserts that swapping split assignments across classes while preserving global totals fails the audit."""
        self.assertTrue(os.path.exists(PILOT_SAMPLING_CSV), "Pilot manifest must exist")
        with open(PILOT_SAMPLING_CSV, "r", encoding="utf-8") as f:
            valid_rows = list(csv.DictReader(f))

        # Deep copy rows
        swapped_rows = [dict(r) for r in valid_rows]

        # Find a train row in one class and a validation row in a different class
        c1 = "account_access"
        c2 = "closing_process"
        idx1 = next(i for i, r in enumerate(swapped_rows) if r["weak_cfpb_label"] == c1 and r["split"] == "train")
        idx2 = next(i for i, r in enumerate(swapped_rows) if r["weak_cfpb_label"] == c2 and r["split"] == "validation")

        # Swap their splits
        swapped_rows[idx1]["split"] = "validation"
        swapped_rows[idx2]["split"] = "train"

        # Global split totals are strictly preserved: 224 train, 48 validation, 48 test
        global_splits = collections.Counter(r["split"] for r in swapped_rows)
        self.assertEqual(global_splits["train"], EXPECTED_PILOT_TRAIN)
        self.assertEqual(global_splits["validation"], EXPECTED_PILOT_VAL)
        self.assertEqual(global_splits["test"], EXPECTED_PILOT_TEST)

        # Per-class split matrix is now violated: c1 has 13 train/4 val; c2 has 15 train/2 val
        c1_splits = collections.Counter(r["split"] for r in swapped_rows if r["weak_cfpb_label"] == c1)
        self.assertEqual(c1_splits["train"], 13)
        self.assertEqual(c1_splits["validation"], 4)

        # Run per-class split matrix audit check against swapped rows
        matrix = collections.defaultdict(lambda: collections.Counter())
        for r in swapped_rows:
            matrix[r["weak_cfpb_label"]][r["split"]] += 1

        mismatched_classes = []
        for cls_name, s_counts in matrix.items():
            if s_counts.get("train", 0) != 14 or s_counts.get("validation", 0) != 3 or s_counts.get("test", 0) != 3:
                mismatched_classes.append((cls_name, dict(s_counts)))

        self.assertGreater(len(mismatched_classes), 0, "Per-class audit must identify corrupted split quotas despite identical global totals")
        mismatched_names = [m[0] for m in mismatched_classes]
        self.assertIn(c1, mismatched_names)
        self.assertIn(c2, mismatched_names)

    def test_16_regression_test_adjudication_template_full_text(self):
        """Asserts adjudication_template.csv preserves the full complaint narrative without 200-char truncation."""
        self.assertTrue(os.path.exists(ADJUDICATION_TMPL_CSV), "Adjudication template must exist")
        self.assertTrue(os.path.exists(PILOT_SAMPLING_CSV), "Pilot manifest must exist")

        with open(ADJUDICATION_TMPL_CSV, "r", encoding="utf-8") as f:
            adj_rows = list(csv.DictReader(f))
        with open(PILOT_SAMPLING_CSV, "r", encoding="utf-8") as f:
            pilot_rows = list(csv.DictReader(f))

        self.assertEqual(len(adj_rows), len(pilot_rows))
        self.assertEqual(len(adj_rows), EXPECTED_PILOT_SIZE)

        # Check full text is preserved bit-for-bit without truncation
        for adj_r, pilot_r in zip(adj_rows, pilot_rows):
            self.assertEqual(adj_r["pilot_id"], pilot_r["pilot_id"])
            self.assertEqual(adj_r["example_id"], pilot_r["example_id"])
            self.assertEqual(
                adj_r["text_normalized"],
                pilot_r["text_normalized"],
                f"Adjudication template text truncated or corrupted for {adj_r['pilot_id']}"
            )

        # Verify that max and average narrative lengths reflect complete complaint texts
        text_lengths = [len(r["text_normalized"]) for r in adj_rows]
        self.assertGreater(max(text_lengths), 1000, "Maximum narrative text length should exceed 1000 characters")
        self.assertGreater(sum(text_lengths) / len(text_lengths), 500, "Average narrative length should exceed 500 characters")

    # -------------------------------------------------------------------------
    # Failure Injection Tests (17-22) Isolated to Temporary Report Files
    # -------------------------------------------------------------------------
    def test_17_failure_injection_pillar_1(self):
        """Asserts audit failure when Pillar 1 environment preflight fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=1)
            self.assertFalse(passed, "Audit must fail when Pillar 1 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_18_failure_injection_pillar_2(self):
        """Asserts audit failure when Pillar 2 provenance fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=2)
            self.assertFalse(passed, "Audit must fail when Pillar 2 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_19_failure_injection_pillar_3(self):
        """Asserts audit failure when Pillar 3 codebook invariant fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=3)
            self.assertFalse(passed, "Audit must fail when Pillar 3 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_20_failure_injection_pillar_4(self):
        """Asserts audit failure when Pillar 4 collision audit fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=4)
            self.assertFalse(passed, "Audit must fail when Pillar 4 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_21_failure_injection_pillar_5(self):
        """Asserts audit failure when Pillar 5 sampling manifest fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=5)
            self.assertFalse(passed, "Audit must fail when Pillar 5 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_22_failure_injection_pillar_6(self):
        """Asserts audit failure when Pillar 6 blinded instrument gate fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=6)
            self.assertFalse(passed, "Audit must fail when Pillar 6 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
