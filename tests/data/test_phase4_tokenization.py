"""Unit tests for Phase 4: Subword Tokenization Profiling."""

import csv
import io
import json
import os
import subprocess
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
    DEFAULT_TOKENIZER_REVISION,
    EXPECTED_TOKENIZER_ASSETS,
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
        """Asserts metadata, pinned revision, and governance declarations are complete."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        meta = self.profile.get("metadata", {})
        self.assertEqual(meta.get("tokenizer_checkpoint"), "facebook/xlm-v-base")
        self.assertEqual(meta.get("tokenizer_revision"), "68c75dd7733d2640b3a98114e3e94196dc543fe1")
        self.assertEqual(meta.get("tokenizer_type"), "XLMRobertaTokenizer")
        self.assertEqual(meta.get("vocab_size"), 901629)
        self.assertFalse(meta.get("mock_mode"), "Production profile must not be generated in mock mode")
        self.assertEqual(meta.get("cutoffs"), [128, 256, 384, 512])

        # Verify asset hashes
        asset_hashes = meta.get("tokenizer_asset_hashes", {})
        for asset_name, exp_h in EXPECTED_TOKENIZER_ASSETS.items():
            self.assertEqual(asset_hashes.get(asset_name), exp_h, f"Mismatch in {asset_name} hash")

        gov = self.profile.get("governance_scope", {})
        self.assertIn("weak administrative supervision", gov.get("supervision_status", "").lower())
        self.assertIn("auxiliary", gov.get("auxiliary_benchmark", "").lower())
        self.assertIn("no evidence of multilingual or held-out cross-domain generalization", gov.get("generalization_boundary", "").lower())
        self.assertIn("ratio_definition", gov)

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
        """Asserts both content-level and sequence-level subword expansion ratios are correctly bounded."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        canon = self.profile.get("canonical_cfpb", {})
        norm = canon.get("text_normalized_overall", {})

        # Content ratio (excluding special tokens)
        cr = norm.get("content_subword_ratio", {})
        self.assertGreater(cr["mean"], 1.3)
        self.assertLess(cr["mean"], 1.6)
        self.assertGreater(cr["median"], 1.2)
        self.assertLess(cr["median"], 1.5)
        self.assertGreater(cr["p90"], 1.6)
        self.assertLess(cr["p90"], 2.1)
        self.assertEqual(cr["min"], 1.0)
        self.assertGreater(cr["max"], 10.0)  # Dense inquiry template

        # Sequence ratio (including special tokens)
        sr = norm.get("sequence_subword_ratio", {})
        self.assertGreater(sr["mean"], cr["mean"])
        self.assertGreater(sr["max"], cr["max"])

    def test_09_csv_manifest_schema_and_reconciliation(self):
        """Asserts tokenization_profile.csv has 26 columns, 23 rows, and matches JSON row-by-row."""
        self.assertTrue(os.path.isfile(PROFILE_CSV_PATH))
        with open(PROFILE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            rows = list(reader)

        self.assertEqual(len(cols), 26)
        self.assertEqual(len(rows), 23)

        # Check that normalized_overall row matches JSON
        norm_row = next(r for r in rows if r["partition"] == "normalized_overall")
        self.assertEqual(int(norm_row["sample_size"]), 45723)
        self.assertAlmostEqual(float(norm_row["mean_tokens"]), 323.75, places=2)
        self.assertAlmostEqual(float(norm_row["trunc_512_pct"]), 15.96, places=2)
        self.assertAlmostEqual(float(norm_row["content_ratio_mean"]), 1.437, places=2)

    def test_10_profiler_unit_functions(self):
        """Tests pure math helper functions in tokenization_profiler."""
        data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        pcts = compute_percentiles(data, [50.0])
        self.assertAlmostEqual(pcts["p50"], 55.0, places=1)

        seq_tokens = [102, 202, 302, 402, 602]
        content_tokens = [100, 200, 300, 400, 600]
        words = [80, 150, 200, 300, 400]
        stats = compute_token_statistics(seq_tokens, content_tokens, words, cutoffs=[128, 256, 512])

        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["min"], 102)
        self.assertEqual(stats["max"], 602)
        self.assertEqual(stats["truncation_coverage"]["128"]["truncated_count"], 4)
        self.assertEqual(stats["truncation_coverage"]["512"]["truncated_count"], 1)
        self.assertIn("content_subword_ratio", stats)
        self.assertIn("sequence_subword_ratio", stats)

    def test_11_mock_tokenizer_deterministic_across_processes(self):
        """Asserts MockSentencePieceTokenizer token IDs are deterministic across independent processes."""
        code = """
import sys
from src.data.tokenization_profiler import MockSentencePieceTokenizer
tok = MockSentencePieceTokenizer()
ids = tok.encode('Test complaint with <REDACTED> info.')
print(ids)
"""
        env1 = dict(os.environ, PYTHONHASHSEED="42")
        env2 = dict(os.environ, PYTHONHASHSEED="9999")

        out1 = subprocess.check_output([sys.executable, "-c", code], env=env1, text=True).strip()
        out2 = subprocess.check_output([sys.executable, "-c", code], env=env2, text=True).strip()

        self.assertEqual(out1, out2, "MockSentencePieceTokenizer must produce identical token IDs across random hash seeds")

    def test_12_tokenization_profiler_input_validation(self):
        """Tests that TokenizationProfiler validates inputs and fails closed."""
        profiler = TokenizationProfiler(mock=True)
        with self.assertRaises(ValueError):
            profiler.tokenize_batch(["text"], batch_size=0)
        with self.assertRaises(ValueError):
            profiler.tokenize_batch(["text"], batch_size=-5)

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

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as rep_tmp:
            rep_path = rep_tmp.name

        try:
            passed = run_phase4_audit(report_path=rep_path, profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on mutated dataset SHA-256")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(rep_path):
                os.remove(rep_path)

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
            pcts["p90"] = pcts["p25"] - 10.0
            mutated["canonical_cfpb"]["text_normalized_overall"]["percentiles"] = pcts
            json.dump(mutated, tmp)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as rep_tmp:
            rep_path = rep_tmp.name

        try:
            passed = run_phase4_audit(report_path=rep_path, profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on non-monotonic percentiles")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(rep_path):
                os.remove(rep_path)

    def test_15_audit_failure_injection_mock_mode(self):
        """Asserts audit failure when profile indicates mock_mode: true."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            mutated = dict(self.profile)
            mutated["metadata"] = dict(mutated["metadata"])
            mutated["metadata"]["mock_mode"] = True
            json.dump(mutated, tmp)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as rep_tmp:
            rep_path = rep_tmp.name

        try:
            passed = run_phase4_audit(report_path=rep_path, profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL closed when mock_mode is True")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(rep_path):
                os.remove(rep_path)

    def test_16_audit_failure_injection_mutated_csv_value(self):
        """Asserts audit failure when a CSV metric is mutated out of sync with JSON manifest."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        if not os.path.isfile(PROFILE_CSV_PATH):
            self.skipTest("Profile CSV not available")

        with open(PROFILE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        # Mutate normalized_overall mean_tokens by +50.0
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=list(reader[0].keys()))
            writer.writeheader()
            for r in reader:
                r_copy = dict(r)
                if r_copy["partition"] == "normalized_overall":
                    r_copy["mean_tokens"] = str(float(r_copy["mean_tokens"]) + 50.0)
                writer.writerow(r_copy)
            tmp_csv_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as rep_tmp:
            rep_path = rep_tmp.name

        try:
            passed = run_phase4_audit(report_path=rep_path, profile_csv_path=tmp_csv_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL when CSV is mutated out of sync with JSON")
        finally:
            if os.path.exists(tmp_csv_path):
                os.remove(tmp_csv_path)
            if os.path.exists(rep_path):
                os.remove(rep_path)

    def test_17_audit_failure_injection_mutated_revision(self):
        """Asserts audit failure when tokenizer revision does not match expected pinned commit."""
        if os.environ.get("PHASE4_AUDIT_RUNNING") == "1":
            return
        if not self.has_profile:
            self.skipTest("Profile JSON not available")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            mutated = dict(self.profile)
            mutated["metadata"] = dict(mutated["metadata"])
            mutated["metadata"]["tokenizer_revision"] = "unpinned-main-head"
            json.dump(mutated, tmp)
            tmp_path = tmp.name

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as rep_tmp:
            rep_path = rep_tmp.name

        try:
            passed = run_phase4_audit(report_path=rep_path, profile_json_path=tmp_path, skip_unit_tests=True)
            self.assertFalse(passed, "Audit must FAIL on unpinned tokenizer revision")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(rep_path):
                os.remove(rep_path)


if __name__ == "__main__":
    unittest.main()
