"""Unit tests for Phase 3: Full-corpus profiling before filtering or sampling."""

import csv
import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

MANIFEST_DIR = os.path.join(REPO_ROOT, "data", "manifests")
PROFILE_JSON_PATH = os.path.join(MANIFEST_DIR, "source_profile.json")
PROFILE_CSV_PATH = os.path.join(MANIFEST_DIR, "source_profile.csv")
PROFILE_REPORT_PATH = os.path.join(REPO_ROOT, "docs", "profile_report.md")


class TestPhase3Profiling(unittest.TestCase):
    """Test suite validating Phase 3 corpus profiling metrics and invariants."""

    @classmethod
    def setUpClass(cls):
        cls.has_profile = os.path.isfile(PROFILE_JSON_PATH) and os.path.isfile(PROFILE_CSV_PATH)
        if cls.has_profile:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                cls.profile = json.load(f)
        else:
            cls.profile = {}

    def test_01_profile_manifests_exist(self):
        """Asserts that source_profile.json and source_profile.csv exist and are populated."""
        self.assertTrue(os.path.isfile(PROFILE_JSON_PATH), f"Missing {PROFILE_JSON_PATH}")
        self.assertTrue(os.path.isfile(PROFILE_CSV_PATH), f"Missing {PROFILE_CSV_PATH}")
        self.assertGreater(os.path.getsize(PROFILE_JSON_PATH), 1000)
        self.assertGreater(os.path.getsize(PROFILE_CSV_PATH), 500)

    def test_02_total_population_reconciliation(self):
        """Asserts exact row reconciliation across total scanned, narratives present, and missing."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        total_rows = self.profile.get("total_rows")
        self.assertEqual(total_rows, 1041632, "Total rows must exactly equal 1,041,632")
        
        narr_prof = self.profile.get("narrative_profile", {})
        present = narr_prof.get("narratives_present")
        missing = narr_prof.get("narratives_missing")
        
        self.assertEqual(present, 439860, "Narratives present must equal 439,860")
        self.assertEqual(missing, 601772, "Narratives missing must equal 601,772")
        self.assertEqual(present + missing, total_rows, "Present + missing must reconcile to total rows")
        self.assertAlmostEqual(narr_prof.get("narrative_availability_rate_percent", 0), 42.23, places=1)

    def test_03_date_coverage_integrity(self):
        """Asserts date bounds and contiguous annual coverage (2018 through 2021)."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        date_cov = self.profile.get("date_coverage", {})
        self.assertEqual(date_cov.get("min_date"), "2018-05-01")
        self.assertEqual(date_cov.get("max_date"), "2021-04-30")
        
        years = date_cov.get("year_counts", {})
        self.assertIn("2018", years)
        self.assertIn("2019", years)
        self.assertIn("2020", years)
        self.assertIn("2021", years)
        self.assertEqual(sum(years.values()), 1041632)

    def test_04_narrative_length_percentiles_monotonic(self):
        """Asserts that percentile distributions for characters and words are strictly monotonic."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        narr_prof = self.profile.get("narrative_profile", {})
        
        for kind in ("char_length_stats", "word_length_stats"):
            stats = narr_prof.get(kind, {})
            pct_keys = ["p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99"]
            values = [stats[k] for k in pct_keys]
            
            for i in range(len(values) - 1):
                self.assertLessEqual(
                    values[i],
                    values[i + 1],
                    f"Percentile {pct_keys[i]} ({values[i]}) > {pct_keys[i+1]} ({values[i+1]}) in {kind}"
                )
            self.assertGreater(stats["mean"], 0)
            self.assertGreater(stats["std"], 0)

    def test_05_complaint_id_uniqueness(self):
        """Asserts zero duplicate Complaint IDs across the entire population."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        integrity = self.profile.get("integrity_checks", {})
        self.assertEqual(integrity.get("duplicate_complaint_id_count"), 0)
        self.assertEqual(integrity.get("complaint_id_integrity"), "PASSED")

    def test_06_natural_class_distribution_coverage(self):
        """Asserts that all 16 canonical taxonomy classes are profiled and class imbalance is recorded."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        nat_class = self.profile.get("natural_class_distribution", {})
        counts = nat_class.get("counts", {})
        
        # Verify 16 canonical classes + unmapped
        self.assertGreaterEqual(len(counts), 16)
        self.assertIn("reporting_incorrect_information", counts)
        self.assertIn("reporting_investigation_dispute", counts)
        self.assertIn("debt_not_owed", counts)
        self.assertIn("closing_process", counts)
        
        # Confirm dominant natural class (> 25% of all narratives)
        pcts = nat_class.get("percentages", {})
        self.assertGreater(pcts.get("reporting_incorrect_information", 0), 25.0)

    def test_07_exact_duplicates_metrics(self):
        """Asserts that exact duplicate narratives are quantified and template counts are captured."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        dups = self.profile.get("narrative_profile", {}).get("exact_duplicates", {})
        total_narr = dups.get("total_narratives", 0)
        unique_narr = dups.get("unique_narratives", 0)
        dup_count = dups.get("exact_duplicates_count", 0)
        
        self.assertEqual(total_narr - unique_narr, dup_count)
        self.assertGreater(dup_count, 50000)
        self.assertAlmostEqual(dups.get("exact_duplicate_rate_percent", 0), 12.92, places=1)
        
        top_hashes = dups.get("top_duplicate_hash_frequencies", [])
        self.assertGreater(len(top_hashes), 0)
        self.assertGreater(top_hashes[0]["occurrences"], 500)

    def test_08_banking77_profile_invariants(self):
        """Asserts that auxiliary benchmark banking77 train and test profiles match expected invariants."""
        if not self.has_profile:
            self.skipTest("Profile JSON not available")
            
        b77 = self.profile.get("banking77", {})
        self.assertIn("train", b77)
        self.assertIn("test", b77)
        
        train_p = b77["train"]
        self.assertEqual(train_p["rows"], 10003)
        self.assertEqual(train_p["null_count"], 0)
        self.assertEqual(train_p["num_categories"], 77)
        
        test_p = b77["test"]
        self.assertEqual(test_p["rows"], 3080)
        self.assertEqual(test_p["null_count"], 0)
        self.assertEqual(test_p["num_categories"], 77)

    def test_09_profile_csv_schema_and_sections(self):
        """Asserts that source_profile.csv matches the required 9-column schema and expected sections."""
        if not os.path.isfile(PROFILE_CSV_PATH):
            self.skipTest("Profile CSV not available")
            
        with open(PROFILE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertGreater(len(reader), 30)
            
            expected_fields = [
                "section",
                "item_name",
                "metric_1_name",
                "metric_1_value",
                "metric_2_name",
                "metric_2_value",
                "metric_3_name",
                "metric_3_value",
                "notes",
            ]
            self.assertEqual(reader[0].keys(), set(expected_fields))
            
            sections = {r["section"] for r in reader}
            self.assertIn("field_missingness", sections)
            self.assertIn("canonical_product_domain", sections)
            self.assertIn("natural_class_distribution", sections)
            self.assertIn("length_percentiles", sections)

    def test_10_profile_report_documentation(self):
        """Asserts that docs/profile_report.md documents all key findings, length tails, and drift."""
        self.assertTrue(os.path.isfile(PROFILE_REPORT_PATH), f"Missing {PROFILE_REPORT_PATH}")
        with open(PROFILE_REPORT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("1,041,632", content)
        self.assertIn("439,860", content)
        self.assertIn("42.23%", content)
        self.assertIn("128,540", content)
        self.assertIn("56,822", content)
        self.assertIn("12.92%", content)
        self.assertIn("PolyAI/banking77", content)


if __name__ == "__main__":
    unittest.main()

