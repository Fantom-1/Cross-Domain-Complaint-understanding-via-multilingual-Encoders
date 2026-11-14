"""Unit tests for Phase 3: Full-corpus profiling before filtering or sampling."""

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

from scripts.audit_phase3 import run_phase3_audit
from src.data.parser import CFPB_BULK_COLUMNS, CFPB_FOIA_COLUMNS
from src.data.profiler import CorpusProfiler

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
        if self.has_profile:
            self.assertEqual(self.profile.get("source_sha256"), "4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45")
            self.assertEqual(self.profile.get("provenance_parser_version"), "phase2.1-v1.0")

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

    def test_11_profiler_missingness_and_narrative_counting(self):
        """Asserts deterministic fixture-based missingness and narrative counting on in-memory stream."""
        rows = [
            {"Complaint ID": "1001", "Date received": "2020-01-01", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": "First valid narrative text here.", "State": "CA"},
            {"Complaint ID": "1002", "Date received": "2020-01-02", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": "Second narrative text is present.", "State": "NY"},
            {"Complaint ID": "1003", "Date received": "2020-01-03", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": "Third narrative with enough words.", "State": ""},
            {"Complaint ID": "1004", "Date received": "2020-01-04", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": "", "State": "TX"},
            {"Complaint ID": "1005", "Date received": "2020-01-05", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": "   ", "State": ""},
            {"Complaint ID": "1006", "Date received": "2020-01-06", "Product": "Credit card", "Issue": "Billing", "Consumer complaint narrative": None, "State": "FL"},
        ]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CFPB_FOIA_COLUMNS)
        for r in rows:
            writer.writerow([r.get(c, "") or "" for c in CFPB_FOIA_COLUMNS])
        buf.seek(0)

        profiler = CorpusProfiler()
        result = profiler.profile_cfpb_foia_archive(buf)

        self.assertEqual(result["total_rows"], 6)
        narr_prof = result["narrative_profile"]
        self.assertEqual(narr_prof["narratives_present"], 3)
        self.assertEqual(narr_prof["narratives_missing"], 3)
        self.assertEqual(narr_prof["narrative_availability_rate_percent"], 50.0)
        
        field_nulls = result["field_missingness"]
        self.assertEqual(field_nulls["State"]["null_count"], 2)
        self.assertEqual(field_nulls["State"]["non_null_count"], 4)

    def test_12_profiler_exact_duplicate_and_boilerplate_clustering(self):
        """Asserts deterministic duplicate detection and boilerplate frequency counting."""
        repeated_template = "This is a standard repeated dispute template pursuant to FCRA regulations."
        rows = [
            {"Complaint ID": f"200{i}", "Date received": "2020-01-01", "Product": "Credit reporting", "Issue": "Incorrect info", "Consumer complaint narrative": repeated_template}
            for i in range(4)
        ]
        rows.append({"Complaint ID": "2010", "Date received": "2020-01-02", "Product": "Mortgage", "Issue": "Trouble", "Consumer complaint narrative": "Unique text complaint alpha."})
        rows.append({"Complaint ID": "2011", "Date received": "2020-01-03", "Product": "Debt collection", "Issue": "Debt not owed", "Consumer complaint narrative": "Unique text complaint beta."})

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CFPB_FOIA_COLUMNS)
        for r in rows:
            writer.writerow([r.get(c, "") or "" for c in CFPB_FOIA_COLUMNS])
        buf.seek(0)

        profiler = CorpusProfiler()
        result = profiler.profile_cfpb_foia_archive(buf)

        dups = result["narrative_profile"]["exact_duplicates"]
        self.assertEqual(dups["total_narratives"], 6)
        self.assertEqual(dups["unique_narratives"], 3)
        self.assertEqual(dups["exact_duplicates_count"], 3)
        self.assertEqual(dups["top_duplicate_hash_frequencies"][0]["occurrences"], 4)

    def test_13_profiler_natural_class_distribution_mapping(self):
        """Asserts weak intent classification across project taxonomy classes on synthetic stream."""
        rows = [
            {"Complaint ID": "3001", "Date received": "2020-01-01", "Product": "Credit reporting, credit repair services, or other personal consumer reports", "Issue": "Incorrect information on your report", "Sub-issue": "Information belongs to someone else", "Consumer complaint narrative": "Someone else's account is on my file."},
            {"Complaint ID": "3002", "Date received": "2020-01-02", "Product": "Credit reporting, credit repair services, or other personal consumer reports", "Issue": "Problem with a credit reporting company's investigation into an existing problem", "Sub-issue": "Investigation took more than 30 days", "Consumer complaint narrative": "The bureau took 60 days to complete investigation."},
            {"Complaint ID": "3003", "Date received": "2020-01-03", "Product": "Debt collection", "Issue": "Attempts to collect debt not owed", "Sub-issue": "Debt is not yours", "Consumer complaint narrative": "This collection agency contacted me about debt that is not mine."},
        ]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CFPB_FOIA_COLUMNS)
        for r in rows:
            writer.writerow([r.get(c, "") or "" for c in CFPB_FOIA_COLUMNS])
        buf.seek(0)

        profiler = CorpusProfiler()
        result = profiler.profile_cfpb_foia_archive(buf)

        counts = result["natural_class_distribution"]["counts"]
        self.assertGreaterEqual(counts.get("reporting_incorrect_information", 0), 1)
        self.assertGreaterEqual(counts.get("reporting_investigation_dispute", 0), 1)
        self.assertGreaterEqual(counts.get("debt_not_owed", 0), 1)

    def test_14_profiler_rejects_ineligible_schema(self):
        """Asserts that profile_cfpb_foia_archive raises ValueError when passed a 15-column active feed."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CFPB_BULK_COLUMNS)  # 15 columns, missing Consumer complaint narrative
        writer.writerow(["2020-01-01", "Credit card", "General", "Billing", "Late fee", "Resp", "Bank", "CA", "90210", "", "Web", "2020-01-02", "Closed", "Yes", "999"])
        buf.seek(0)

        profiler = CorpusProfiler()
        with self.assertRaises(ValueError) as cm:
            profiler.profile_cfpb_foia_archive(buf)
        self.assertIn("16-column", str(cm.exception))

    def test_15_profiler_rejects_malformed_rows_after_valid_rows(self):
        """Asserts that malformed short or overflow rows following valid rows cause ValueError."""
        # Short row test
        buf_short = io.StringIO(
            "Date received,Product,Sub-product,Issue,Sub-issue,Consumer complaint narrative,Company public response,Company,State,ZIP code,Tags,Submitted via,Date sent to company,Company response to consumer,Timely response?,Complaint ID\n"
            "2020-01-01,Credit card,General,Billing,Late fee,Valid narrative one,Response,Bank,CA,90210,,Web,2020-01-02,Closed,Yes,9991\n"
            "2020-01-02,Credit card,General,Billing,Late fee,Valid narrative two,Response,Bank,CA,90210,,Web,2020-01-03,Closed,Yes,9992\n"
            "MALFORMED,SHORT,ROW,ONLY,FIVE\n"
            "2020-01-03,Credit card,General,Billing,Late fee,Valid narrative three,Response,Bank,CA,90210,,Web,2020-01-04,Closed,Yes,9993\n"
        )
        profiler = CorpusProfiler()
        with self.assertRaises(ValueError) as cm:
            profiler.profile_cfpb_foia_archive(buf_short)
        self.assertIn("malformed", str(cm.exception).lower())

        # Overflow row test
        buf_overflow = io.StringIO(
            "Date received,Product,Sub-product,Issue,Sub-issue,Consumer complaint narrative,Company public response,Company,State,ZIP code,Tags,Submitted via,Date sent to company,Company response to consumer,Timely response?,Complaint ID\n"
            "2020-01-01,Credit card,General,Billing,Late fee,Valid narrative one,Response,Bank,CA,90210,,Web,2020-01-02,Closed,Yes,9991\n"
            "2020-01-02,Credit card,General,Billing,Late fee,Overflow,Response,Bank,CA,90210,,Web,2020-01-03,Closed,Yes,9992,OVERFLOW1,OVERFLOW2\n"
        )
        with self.assertRaises(ValueError) as cm:
            profiler.profile_cfpb_foia_archive(buf_overflow)
        self.assertIn("malformed", str(cm.exception).lower())

    def test_16_profiler_max_rows_exact_accounting(self):
        """Asserts that max_rows caps streaming without off-by-one errors."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CFPB_FOIA_COLUMNS)
        for i in range(10):
            writer.writerow([
                "2020-01-01", "Credit card", "General", "Billing", "Late fee",
                f"Narrative row {i} with sufficient words.", "Resp", "Bank", "CA", "90210", "", "Web",
                "2020-01-02", "Closed", "Yes", f"888{i}"
            ])
        buf.seek(0)

        profiler = CorpusProfiler()
        result = profiler.profile_cfpb_foia_archive(buf, max_rows=5)
        self.assertEqual(result["total_rows"], 5, "Total rows must exactly equal max_rows=5")
        self.assertEqual(result["narrative_profile"]["total_rows"], 5)

    def test_17_audit_provenance_binding_failure_injection(self):
        """Asserts that mutating source_sha256 or row counts fails mechanical provenance binding in audit."""
        if os.environ.get("PHASE3_AUDIT_RUNNING") == "1":
            return
        if not os.path.isfile(PROFILE_JSON_PATH):
            self.skipTest("Profile JSON not available")

        with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
            base_profile = json.load(f)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Case A: Mutate source_sha256
            mutated_sha_profile = dict(base_profile)
            mutated_sha_profile["source_sha256"] = "deadbeef" * 8
            sha_json_path = os.path.join(tmpdir, "mutated_sha.json")
            sha_report_path = os.path.join(tmpdir, "audit_sha_fail.md")
            with open(sha_json_path, "w", encoding="utf-8") as f:
                json.dump(mutated_sha_profile, f)

            result_sha = run_phase3_audit(report_path=sha_report_path, profile_json_path=sha_json_path, skip_unit_tests=True)
            self.assertFalse(result_sha, "Audit must fail when source_sha256 does not match provenance")
            with open(sha_report_path, "r", encoding="utf-8") as f:
                report_text = f.read()
            self.assertIn("Provenance binding mismatch on source_sha256", report_text)

            # Case B: Mutate total_rows
            mutated_rows_profile = dict(base_profile)
            mutated_rows_profile["total_rows"] = 999999
            rows_json_path = os.path.join(tmpdir, "mutated_rows.json")
            rows_report_path = os.path.join(tmpdir, "audit_rows_fail.md")
            with open(rows_json_path, "w", encoding="utf-8") as f:
                json.dump(mutated_rows_profile, f)

            result_rows = run_phase3_audit(report_path=rows_report_path, profile_json_path=rows_json_path, skip_unit_tests=True)
            self.assertFalse(result_rows, "Audit must fail when total_rows does not match provenance record_count")
            with open(rows_report_path, "r", encoding="utf-8") as f:
                report_text = f.read()
            self.assertIn("Provenance binding mismatch on total_rows", report_text)

            # Case C: Mutate narrative counts so present + missing != total_rows
            mutated_narr_profile = dict(base_profile)
            mutated_narr_profile["narrative_profile"] = dict(base_profile["narrative_profile"])
            mutated_narr_profile["narrative_profile"]["narratives_present"] = 100
            narr_json_path = os.path.join(tmpdir, "mutated_narr.json")
            narr_report_path = os.path.join(tmpdir, "audit_narr_fail.md")
            with open(narr_json_path, "w", encoding="utf-8") as f:
                json.dump(mutated_narr_profile, f)

            result_narr = run_phase3_audit(report_path=narr_report_path, profile_json_path=narr_json_path, skip_unit_tests=True)
            self.assertFalse(result_narr, "Audit must fail when narrative present + missing != provenance count")
            with open(narr_report_path, "r", encoding="utf-8") as f:
                report_text = f.read()
            self.assertIn("does not reconcile to provenance record_count", report_text)


if __name__ == "__main__":
    unittest.main()

