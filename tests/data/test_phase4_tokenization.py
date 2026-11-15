"""Unit tests for Phase 4: Subword Tokenization Profiling."""

import csv
import io
import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.audit_phase4 import run_phase4_audit
from src.data.tokenization_profiler import (
    DEFAULT_CUTOFFS,
    DEFAULT_TOKENIZER_CHECKPOINT,
    MockSentencePieceTokenizer,
    TokenizationProfiler,
    compute_percentiles,
    compute_sha256,
    compute_token_statistics,
)

MANIFEST_DIR = os.path.join(REPO_ROOT, "data", "manifests")
PROFILE_JSON_PATH = os.path.join(MANIFEST_DIR, "tokenization_profile.json")
PROFILE_CSV_PATH = os.path.join(MANIFEST_DIR, "tokenization_profile.csv")
REPORT_PATH = os.path.join(REPO_ROOT, "docs", "tokenization_report.md")


class TestPhase4Tokenization(unittest.TestCase):
    """Test suite validating Phase 4 subword tokenization profiling metrics and invariants."""

    @classmethod
    def setUpClass(cls):
        cls.has_profile = os.path.isfile(PROFILE_JSON_PATH) and os.path.isfile(PROFILE_CSV_PATH)
        if cls.has_profile:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                cls.profile = json.load(f)
        else:
            cls.profile = {}

    def test_01_profile_manifests_exist(self):
        """Asserts that tokenization_profile.json and tokenization_profile.csv exist and are non-empty."""
        self.assertTrue(os.path.isfile(PROFILE_JSON_PATH), f"Missing {PROFILE_JSON_PATH}")
        self.assertTrue(os.path.isfile(PROFILE_CSV_PATH), f"Missing {PROFILE_CSV_PATH}")
        self.assertGreater(os.path.getsize(PROFILE_JSON_PATH), 2000)
        self.assertGreater(os.path.getsize(PROFILE_CSV_PATH), 1000)

    def test_02_metadata_and_governance(self):
        """Asserts metadata and governance declarations are complete."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        meta = self.profile.get("metadata", {})
        self.assertEqual(meta.get("tokenizer_checkpoint"), "facebook/xlm-v-base")
        self.assertEqual(meta.get("vocab_size"), 901629)
        self.assertEqual(meta.get("cutoffs"), [128, 256, 384, 512])

        gov = self.profile.get("governance_scope", {})
        self.assertIn("weak administrative supervision", gov.get("supervision_status", "").lower())
        self.assertIn("auxiliary", gov.get("auxiliary_benchmark", "").lower())
        self.assertIn("no evidence of multilingual or held-out cross-domain generalization", gov.get("generalization_boundary", "").lower())

    def test_03_canonical_total_and_split_reconciliation(self):
        """Asserts exact row reconciliation across total instances and split partitions."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        total = canon.get("total_instances")
        self.assertEqual(total, 45723, "Canonical total instances must be 45,723")

        splits = canon.get("by_split", {})
        train_count = splits.get("train", {}).get("count", 0)
        val_count = splits.get("validation", {}).get("count", 0)
        test_count = splits.get("test", {}).get("count", 0)

        self.assertEqual(train_count, 32019)
        self.assertEqual(val_count, 6852)
        self.assertEqual(test_count, 6852)
        self.assertEqual(train_count + val_count + test_count, total)

    def test_04_all_16_intent_classes_present_and_reconciled(self):
        """Asserts all 16 intent classes are represented and sum to total canonical instances."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        intents = canon.get("by_intent", {})
        self.assertEqual(len(intents), 16, "Expected exactly 16 intent classes")

        sum_intents = sum(i["count"] for i in intents.values())
        self.assertEqual(sum_intents, 45723)

        # Check closing_process and reporting_improper_use (non-3000 support)
        self.assertEqual(intents.get("closing_process", {}).get("count"), 1661)
        self.assertEqual(intents.get("reporting_improper_use", {}).get("count"), 2062)

    def test_05_banking77_reconciliation(self):
        """Asserts Banking77 auxiliary partitions reconcile and have zero 128-token truncation."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        b77 = self.profile.get("auxiliary_banking77", {})
        train = b77.get("train", {})
        test = b77.get("test", {})

        self.assertEqual(train.get("total_instances"), 10003)
        self.assertEqual(test.get("total_instances"), 3080)

        train_trunc = train.get("stats", {}).get("truncation_coverage", {}).get("128", {}).get("truncated_percent")
        test_trunc = test.get("stats", {}).get("truncation_coverage", {}).get("128", {}).get("truncated_percent")
        self.assertEqual(train_trunc, 0.0)
        self.assertEqual(test_trunc, 0.0)

    def test_06_percentiles_monotonic(self):
        """Asserts token length percentiles are strictly monotonic across canonical and splits."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        checks = [canon.get("text_normalized_overall", {})]
        checks.extend(canon.get("by_split", {}).values())

        for stats in checks:
            p = stats.get("percentiles", {})
            self.assertLessEqual(stats["min"], p["p25"])
            self.assertLessEqual(p["p25"], p["p50"])
            self.assertLessEqual(p["p50"], p["p75"])
            self.assertLessEqual(p["p75"], p["p90"])
            self.assertLessEqual(p["p90"], p["p95"])
            self.assertLessEqual(p["p95"], p["p99"])
            self.assertLessEqual(p["p99"], stats["max"])

    def test_07_truncation_monotonic(self):
        """Asserts truncation counts decrease monotonically as context window cutoffs increase."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        stats = canon.get("text_normalized_overall", {})
        tc = stats.get("truncation_coverage", {})

        c128 = tc.get("128", {}).get("truncated_count", 0)
        c256 = tc.get("256", {}).get("truncated_count", 0)
        c384 = tc.get("384", {}).get("truncated_count", 0)
        c512 = tc.get("512", {}).get("truncated_count", 0)

        self.assertGreater(c128, c256)
        self.assertGreater(c256, c384)
        self.assertGreater(c384, c512)

        trunc_512_pct = tc.get("512", {}).get("truncated_percent", 0.0)
        self.assertGreaterEqual(trunc_512_pct, 15.0)
        self.assertLessEqual(trunc_512_pct, 17.0)

    def test_08_subword_expansion_ratio_bounds(self):
        """Asserts subword expansion ratio is reasonable for English consumer complaints."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        ratio_stats = canon.get("text_normalized_overall", {}).get("subword_expansion_ratio", {})

        mean_r = ratio_stats.get("mean", 0.0)
        med_r = ratio_stats.get("median", 0.0)
        p90_r = ratio_stats.get("p90", 0.0)

        self.assertGreater(mean_r, 1.3)
        self.assertLess(mean_r, 1.6)
        self.assertGreater(med_r, 1.2)
        self.assertLess(med_r, 1.5)
        self.assertGreater(p90_r, 1.6)
        self.assertLess(p90_r, 2.1)

    def test_09_csv_manifest_schema_and_rows(self):
        """Asserts tokenization_profile.csv has exactly 21 columns and 23 rows."""
        self.assertTrue(os.path.isfile(PROFILE_CSV_PATH))
        with open(PROFILE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            rows = list(reader)

        self.assertEqual(len(cols), 21)
        self.assertEqual(len(rows), 23)

        datasets = {r["dataset"] for r in rows}
        self.assertIn("CFPB Canonical", datasets)
        self.assertIn("Banking77 (Auxiliary)", datasets)

    def test_10_profiler_unit_functions(self):
        """Tests pure math helper functions in tokenization_profiler."""
        # compute_percentiles
        data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        pcts = compute_percentiles(data, [50.0])
        self.assertAlmostEqual(pcts["p50"], 55.0, places=1)

        # compute_token_statistics
        tokens = [100, 200, 300, 400, 600]
        words = [80, 150, 200, 300, 400]
        stats = compute_token_statistics(tokens, words, cutoffs=[128, 256, 512])

        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["min"], 100)
        self.assertEqual(stats["max"], 600)
        self.assertEqual(stats["truncation_coverage"]["128"]["truncated_count"], 4)
        self.assertEqual(stats["truncation_coverage"]["256"]["truncated_count"], 3)
        self.assertEqual(stats["truncation_coverage"]["512"]["truncated_count"], 1)

    def test_11_mock_tokenizer_contract(self):
        """Tests MockSentencePieceTokenizer behavior and output formatting."""
        mock_tok = MockSentencePieceTokenizer()
        text = "Unauthorized overdraft <REDACTED> fee charged."
        enc = mock_tok(text, add_special_tokens=True)

        input_ids = enc["input_ids"][0]
        self.assertGreater(len(input_ids), 5)
        self.assertEqual(input_ids[0], 1)  # <s>
        self.assertEqual(input_ids[-1], 2)  # </s>

        # Test batch encode
        batch_enc = mock_tok([text, "Second text."], add_special_tokens=True)
        self.assertEqual(len(batch_enc["input_ids"]), 2)

    def test_12_tokenization_profiler_mock_texts(self):
        """Tests TokenizationProfiler in mock mode with texts."""
        profiler = TokenizationProfiler(mock=True)
        self.assertTrue(profiler.mock_mode)

        texts = [
            "Short complaint.",
            "Longer complaint with several words detailing loan dispute.",
            "Another complaint with <REDACTED> information.",
        ]
        res = profiler.profile_texts(texts)
        self.assertEqual(res["count"], 3)
        self.assertGreater(res["mean"], 0)
        self.assertIn("128", res["truncation_coverage"])

    def test_13_audit_failure_injection_mutated_hash(self):
        """Asserts audit failure upon mutating dataset SHA-256."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            mutated = dict(self.profile)
            mutated["canonical_cfpb"] = dict(mutated["canonical_cfpb"])
            mutated["canonical_cfpb"]["source_sha256"] = "deadbeef00000000000000000000000000000000000000000000000000000000"
            json.dump(mutated, tmp)
            tmp_path = tmp.name

        try:
            passed = run_phase4_audit(profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on mutated dataset SHA-256")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_14_audit_failure_injection_non_monotonic_percentiles(self):
        """Asserts audit failure upon non-monotonic percentiles."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            mutated = dict(self.profile)
            mutated["canonical_cfpb"] = dict(mutated["canonical_cfpb"])
            mutated["canonical_cfpb"]["text_normalized_overall"] = dict(mutated["canonical_cfpb"]["text_normalized_overall"])
            pcts = dict(mutated["canonical_cfpb"]["text_normalized_overall"]["percentiles"])
            pcts["p90"] = pcts["p25"] - 10.0  # Invert order!
            mutated["canonical_cfpb"]["text_normalized_overall"]["percentiles"] = pcts
            json.dump(mutated, tmp)
            tmp_path = tmp.name

        try:
            passed = run_phase4_audit(profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on non-monotonic percentiles")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_15_audit_failure_injection_pillar_force(self):
        """Asserts audit failure on forced pillar failure."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        passed = run_phase4_audit(force_pillar_fail=2, skip_unit_tests=True)
        self.assertFalse(passed, "Audit must FAIL when pillar 2 fails")


if __name__ == "__main__":
    unittest.main()

