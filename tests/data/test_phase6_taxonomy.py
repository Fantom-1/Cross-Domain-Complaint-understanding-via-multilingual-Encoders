#!/usr/bin/env python3
"""Comprehensive unit test suite for Phase 6: Label Taxonomy Codebook & Pilot Adjudication.

Covers:
- Taxonomy JSON schema, 16 classes, and definition completeness.
- Operational taxonomy codebook presence, boundaries, and multi-issue guidelines.
- Source label mapping schema, counts (221 total, 198 mapped, 23 unmapped), and collision detection (17 collisions).
- Stratified pilot sampling determinism, exact 320-record size, and 20-per-class balance.
- Mathematical correctness of Cohen's Kappa under synthetic and edge-case distributions.
- Adjudication log schema (15 columns), label validity, and zero-null invariants.
- Inter-annotator agreement metrics and empirical divergence thresholds.
- Cross-process determinism under differing PYTHONHASHSEED environments.
- Governance notices and exact headline reconciliation.
- Failure-injection tests for all audit pillars isolated to temporary files.
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
    ADJUDICATION_LOG_CSV,
    ANNOTATION_AGREEMENT_MD,
    EXPECTED_ADJUDICATION_COLUMNS,
    EXPECTED_CLASS_COUNT,
    EXPECTED_COLLISION_COUNT,
    EXPECTED_MAPPED_COUNT,
    EXPECTED_PILOT_PER_CLASS,
    EXPECTED_PILOT_SIZE,
    EXPECTED_TOTAL_MAPPINGS,
    EXPECTED_UNMAPPED_COUNT,
    PILOT_SAMPLING_CSV,
    SOURCE_MAPPING_CSV,
    TAXONOMY_CODEBOOK_MD,
    TAXONOMY_JSON,
    _run_phase6_audit_internal,
)
from src.data.taxonomy_auditor import (
    TaxonomyAuditor,
    compute_cohens_kappa,
    compute_per_class_metrics,
    load_taxonomy,
)


CANONICAL_PARQUET = os.path.join(REPO_ROOT, "data", "processed", "canonical_dataset.parquet")


class TestPhase6Taxonomy(unittest.TestCase):
    """Unit and regression tests for Phase 6 taxonomy, audit, and pilot adjudication."""

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

        # Verify each collision record has valid structure
        for c in res["collisions"]:
            self.assertIn("source_label", c)
            self.assertIn("assigned_label", c)
            self.assertGreater(len(c["matching_intents"]), 1)

    def test_05_stratified_pilot_sampling_size_and_balance(self):
        """Asserts stratified sampling produces exactly 320 records (20 per class)."""
        if not os.path.isfile(CANONICAL_PARQUET):
            self.skipTest("canonical_dataset.parquet untracked locally (CI mode)")
        samples = self.auditor.sample_stratified_pilot()
        self.assertEqual(len(samples), EXPECTED_PILOT_SIZE)

        counts = collections.Counter(s["weak_cfpb_label"] for s in samples)
        self.assertEqual(len(counts), EXPECTED_CLASS_COUNT)
        for cls_name, cnt in counts.items():
            self.assertEqual(cnt, EXPECTED_PILOT_PER_CLASS, f"Class {cls_name} count must be {EXPECTED_PILOT_PER_CLASS}")

    def test_05b_synthetic_stratified_pilot_sampling(self):
        """Asserts stratified sampling logic on synthetic DataFrame fixture (runs in both CI and local)."""
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
            samples = self.auditor.sample_stratified_pilot(parquet_path=tmp_parquet)
            self.assertEqual(len(samples), EXPECTED_PILOT_SIZE)
            counts = collections.Counter(s["weak_cfpb_label"] for s in samples)
            self.assertEqual(len(counts), EXPECTED_CLASS_COUNT)
            for cls_name, cnt in counts.items():
                self.assertEqual(cnt, EXPECTED_PILOT_PER_CLASS)
        finally:
            if os.path.exists(tmp_parquet):
                os.remove(tmp_parquet)

    def test_06_stratified_pilot_unique_example_ids(self):
        """Asserts all 320 example_ids in the pilot sampling manifest are distinct."""
        with open(PILOT_SAMPLING_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), EXPECTED_PILOT_SIZE)
        eids = [r["example_id"] for r in rows]
        self.assertEqual(len(set(eids)), EXPECTED_PILOT_SIZE)

    def test_07_cohens_kappa_perfect_and_chance_agreement(self):
        """Asserts compute_cohens_kappa returns 1.0 on identical ratings and <= 0.0 on chance."""
        r1 = ["a", "b", "c", "d"]
        r2 = ["a", "b", "c", "d"]
        po, kappa = compute_cohens_kappa(r1, r2)
        self.assertEqual(po, 1.0)
        self.assertEqual(kappa, 1.0)

        # Inverted ratings
        r3 = ["a", "a", "b", "b"]
        r4 = ["b", "b", "a", "a"]
        po_inv, kappa_inv = compute_cohens_kappa(r3, r4)
        self.assertEqual(po_inv, 0.0)
        self.assertLess(kappa_inv, 0.0)

    def test_08_cohens_kappa_known_numerical_vector(self):
        """Asserts compute_cohens_kappa matches known hand-calculated matrix."""
        # Standard 2x2 agreement:
        # Rater1: 15 yes, 10 no
        # Rater2: 18 yes, 7 no
        # Overlap: 14 both yes, 6 both no -> 20 agree out of 25 (Po = 20/25 = 0.80)
        # Pe = (15/25)*(18/25) + (10/25)*(7/25) = (0.60*0.72) + (0.40*0.28) = 0.432 + 0.112 = 0.544
        # Kappa = (0.80 - 0.544) / (1 - 0.544) = 0.256 / 0.456 = 0.5614
        r1 = ["yes"] * 14 + ["yes"] * 1 + ["no"] * 4 + ["no"] * 6
        r2 = ["yes"] * 14 + ["no"] * 1 + ["yes"] * 4 + ["no"] * 6
        po, kappa = compute_cohens_kappa(r1, r2)
        self.assertAlmostEqual(po, 0.80, places=3)
        self.assertAlmostEqual(kappa, 0.5614, places=3)

    def test_09_adjudication_log_schema_and_zero_nulls(self):
        """Asserts adjudication_log.csv has 320 rows, 15 columns, and zero null fields."""
        self.assertTrue(os.path.exists(ADJUDICATION_LOG_CSV), "adjudication_log.csv must exist")
        with open(ADJUDICATION_LOG_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), EXPECTED_PILOT_SIZE)
        self.assertEqual(list(rows[0].keys()), EXPECTED_ADJUDICATION_COLUMNS)

        for i, r in enumerate(rows):
            for col in EXPECTED_ADJUDICATION_COLUMNS:
                # secondary_labels can be empty if single-issue
                if col != "secondary_labels":
                    self.assertTrue(r[col], f"Row {i} column {col} cannot be empty")

    def test_10_adjudication_log_label_taxonomy_validity(self):
        """Asserts all assigned annotator and adjudicated labels are members of the 16-class taxonomy."""
        with open(ADJUDICATION_LOG_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        valid_classes = set(self.auditor.class_names)
        for r in rows:
            self.assertIn(r["annotator_1_label"], valid_classes)
            self.assertIn(r["annotator_2_label"], valid_classes)
            self.assertIn(r["adjudicated_label"], valid_classes)
            self.assertIn(r["weak_cfpb_label"], valid_classes)

    def test_11_inter_annotator_agreement_thresholds(self):
        """Asserts inter-annotator observed agreement Po >= 0.90 and Kappa >= 0.70."""
        stats = self.auditor.analyze_adjudication_log(ADJUDICATION_LOG_CSV)
        self.assertGreaterEqual(stats["raw_inter_annotator_agreement"], 0.90)
        self.assertGreaterEqual(stats["cohens_kappa_inter_annotator"], 0.70)

    def test_12_weak_cfpb_divergence_metrics(self):
        """Asserts empirical divergence between weak CFPB labels and gold intent is substantial."""
        stats = self.auditor.analyze_adjudication_log(ADJUDICATION_LOG_CSV)
        self.assertGreaterEqual(stats["divergence_rate"], 0.25)
        self.assertLessEqual(stats["divergence_rate"], 0.65)
        self.assertGreaterEqual(stats["multi_issue_rate"], 0.10)
        self.assertLessEqual(stats["ambiguous_rate"], 0.05)

    def test_13_governance_disclaimers_in_report(self):
        """Asserts annotation_agreement.md contains required weak supervision and auxiliary notices."""
        self.assertTrue(os.path.exists(ANNOTATION_AGREEMENT_MD), "Report must exist")
        with open(ANNOTATION_AGREEMENT_MD, "r", encoding="utf-8") as f:
            text = f.read()

        self.assertIn("CFPB administrative routing labels are weak supervision tags", text)
        self.assertIn("PolyAI/banking77", text)
        self.assertIn("strictly isolated", text)

    def test_14_cross_process_pilot_sampling_determinism(self):
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

    def test_14b_synthetic_cross_process_determinism(self):
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
            'split': 'train',
            'group_id': f'grp_{c}_{i}'
        })
with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
    tpath = tmp.name
try:
    pd.DataFrame(synth_rows).to_parquet(tpath)
    samples = auditor.sample_stratified_pilot(parquet_path=tpath)
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

    # -------------------------------------------------------------------------
    # Failure Injection Tests (15-20) Isolated to Temporary Report Files
    # -------------------------------------------------------------------------
    def test_15_failure_injection_pillar_1(self):
        """Asserts audit failure when Pillar 1 environment preflight fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=1)
            self.assertFalse(passed, "Audit must fail when Pillar 1 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_16_failure_injection_pillar_2(self):
        """Asserts audit failure when Pillar 2 provenance fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=2)
            self.assertFalse(passed, "Audit must fail when Pillar 2 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_17_failure_injection_pillar_3(self):
        """Asserts audit failure when Pillar 3 codebook invariant fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=3)
            self.assertFalse(passed, "Audit must fail when Pillar 3 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_18_failure_injection_pillar_4(self):
        """Asserts audit failure when Pillar 4 collision audit fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=4)
            self.assertFalse(passed, "Audit must fail when Pillar 4 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_19_failure_injection_pillar_5(self):
        """Asserts audit failure when Pillar 5 pilot adjudication fails."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            passed = _run_phase6_audit_internal(skip_tests=True, report_path=tmp_path, force_pillar_fail=5)
            self.assertFalse(passed, "Audit must fail when Pillar 5 fails")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_20_failure_injection_pillar_6(self):
        """Asserts audit failure when Pillar 6 agreement metrics fail."""
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
