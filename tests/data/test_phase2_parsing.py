"""Tests for Phase 2: Robust parsing, schema validation, and error diagnostics."""

import csv
import io
import os
import sys
import tempfile
import unittest

from src.data.parser import (
    CFPB_BULK_COLUMNS,
    CFPB_FOIA_COLUMNS,
    BANKING77_COLUMNS,
    CSVParseError,
    ParserDiagnostics,
    REQUIRED_PROVENANCE_FIELDS,
    SAFE_FIELD_SIZE_LIMIT,
    ensure_safe_field_size_limit,
    scan_and_profile,
    stream_complaints,
    verify_scan_provenance_record,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
RAW_EXPORT_2 = os.path.join(REPO_ROOT, "data/raw/cfpb/CCDB_Export_2_May_2018_through_April_2021.zip")
BANKING77_TRAIN = os.path.join(REPO_ROOT, "data/raw/banking77/train.csv")


class TestPhase2Parsing(unittest.TestCase):
    """Test suite for Phase 2 robust parsing and schema validation."""

    def test_01_portable_field_size_limit(self):
        """Asserts that ensure_safe_field_size_limit sets a safe C long limit without OverflowError."""
        limit = ensure_safe_field_size_limit()
        self.assertLessEqual(limit, 2147483647)
        self.assertLessEqual(limit, sys.maxsize)
        self.assertEqual(limit, SAFE_FIELD_SIZE_LIMIT)

    def test_02_multiline_and_quoted_narrative_parsing(self):
        """Asserts that CSV parser correctly handles multi-line text, internal quotes, and commas."""
        sample_csv = io.StringIO(
            'Date received,Product,Sub-product,Issue,Sub-issue,Consumer complaint narrative,Company public response,Company,State,ZIP code,Tags,Submitted via,Date sent to company,Company response to consumer,Timely response?,Complaint ID\n'
            '2019-01-01,Credit card,General,Billing,Late fee,"Line 1 of narrative.\nLine 2 with ""quotes"" and, commas.\nLine 3.",Response text,Acme Bank,CA,90210,,Web,2019-01-02,Closed with relief,Yes,1001\n'
            '2019-01-02,Mortgage,Conventional,Loan,Modification,"Single line narrative.",Response text,Beta Bank,NY,10001,,Web,2019-01-03,Closed with relief,Yes,1002\n'
        )
        
        diag = ParserDiagnostics(archive_path="test.csv", file_name="test.csv")
        rows = list(stream_complaints(sample_csv, diagnostics=diag))
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(diag.total_rows, 2)
        self.assertEqual(diag.valid_rows, 2)
        self.assertEqual(diag.error_rows, 0)
        self.assertEqual(diag.multiline_rows, 1)
        self.assertEqual(diag.quoted_rows, 1)
        
        first = rows[0]
        self.assertEqual(first["Complaint ID"], "1001")
        self.assertEqual(
            first["Consumer complaint narrative"],
            'Line 1 of narrative.\nLine 2 with "quotes" and, commas.\nLine 3.'
        )
        self.assertEqual(first["Product"], "Credit card")
        
        second = rows[1]
        self.assertEqual(second["Complaint ID"], "1002")
        self.assertEqual(second["Consumer complaint narrative"], "Single line narrative.")

    def test_03_schema_mismatch_detection(self):
        """Asserts that mismatched schemas are rejected in record/raise modes and captured in diagnostics."""
        bad_header_csv = io.StringIO(
            'ColA,ColB,ColC\n'
            '1,2,3\n'
        )
        
        # Policy 'raise': Must raise CSVParseError detailing expected vs observed columns
        with self.assertRaises(CSVParseError) as ctx:
            list(stream_complaints(bad_header_csv, expected_columns=CFPB_FOIA_COLUMNS, on_error="raise"))
        self.assertIn("Schema mismatch", str(ctx.exception))
        self.assertIn("Expected 16 columns", str(ctx.exception))
        self.assertIn("got 3 columns", str(ctx.exception))
        
        # Default policy 'record': Must reject the source stream (yield 0 rows) and record schema diagnostic
        bad_header_csv.seek(0)
        diag = ParserDiagnostics(archive_path="test_bad.csv", file_name="test_bad.csv")
        rows = list(stream_complaints(bad_header_csv, expected_columns=CFPB_FOIA_COLUMNS, diagnostics=diag, on_error="record"))
        self.assertEqual(len(rows), 0, "Default record mode must reject incompatible feed and yield 0 rows")
        self.assertEqual(diag.error_rows, 1)
        self.assertEqual(len(diag.errors), 1)
        err = diag.errors[0]
        self.assertEqual(err.error_type, "schema_mismatch")
        self.assertIn("Expected 16 columns", err.error_details)
        self.assertIn("got 3 columns", err.error_details)
        self.assertIn("Expected=", err.raw_snippet)
        self.assertIn("Observed=", err.raw_snippet)
        
        # Explicit opt-in 'permissive' mode allows parsing
        bad_header_csv.seek(0)
        permissive_rows = list(stream_complaints(bad_header_csv, expected_columns=CFPB_FOIA_COLUMNS, on_error="permissive"))
        self.assertEqual(len(permissive_rows), 1)
        self.assertEqual(permissive_rows[0], {"ColA": "1", "ColB": "2", "ColC": "3"})


    def test_04_malformed_row_diagnostic_recording(self):
        """Asserts that malformed rows (wrong column count) are captured in diagnostics."""
        malformed_csv = io.StringIO(
            'ColA,ColB,ColC\n'
            'valA1,valB1,valC1\n'
            'valA2,valB2\n'  # Missing 1 column
            'valA3,valB3,valC3,extraVal\n'  # Extra column
            'valA4,valB4,valC4\n'
        )
        
        diag = ParserDiagnostics(archive_path="test_malformed.csv", file_name="test_malformed.csv")
        rows = list(stream_complaints(malformed_csv, diagnostics=diag, on_error="record"))
        
        self.assertEqual(len(rows), 2)  # Only valid rows yielded
        self.assertEqual(diag.total_rows, 4)
        self.assertEqual(diag.valid_rows, 2)
        self.assertEqual(diag.error_rows, 2)
        self.assertEqual(len(diag.errors), 2)
        
        err1 = diag.errors[0]
        self.assertEqual(err1.line_number, 3)
        self.assertEqual(err1.error_type, "column_count_mismatch")
        self.assertIn("expected 3, got 2", err1.error_details)
        
        err2 = diag.errors[1]
        self.assertEqual(err2.line_number, 4)
        self.assertEqual(err2.error_type, "column_count_mismatch")
        self.assertIn("expected 3, got 4", err2.error_details)

    def test_05_error_log_export(self):
        """Asserts that export_errors_csv writes verified sentinel when zero errors, or full error rows."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_csv = os.path.join(tmp_dir, "parse_errors.csv")
            
            # Case A: Zero errors
            clean_diag = ParserDiagnostics(archive_path="clean.zip", file_name="clean.csv", total_rows=500)
            clean_diag.export_errors_csv(out_csv)
            
            with open(out_csv, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                self.assertEqual(len(reader), 1)
                self.assertEqual(reader[0]["error_type"], "verified_zero_errors")
                self.assertIn("Successfully parsed 500 records", reader[0]["error_details"])
                
            # Case B: With errors
            error_csv = io.StringIO("ColA,ColB\n1\n")
            diag_with_err = ParserDiagnostics(archive_path="err.csv", file_name="err.csv")
            list(stream_complaints(error_csv, diagnostics=diag_with_err, on_error="record"))
            diag_with_err.export_errors_csv(out_csv)
            
            with open(out_csv, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                self.assertEqual(len(reader), 1)
                self.assertEqual(reader[0]["error_type"], "column_count_mismatch")

    def test_06_utf8_bom_handling(self):
        """Asserts that UTF-8 BOM is cleanly stripped from the leading column header."""
        bom_csv = io.StringIO("\ufeffDate received,Product\n2020-01-01,Credit card\n")
        rows = list(stream_complaints(bom_csv))
        self.assertEqual(len(rows), 1)
        self.assertIn("Date received", rows[0])
        self.assertNotIn("\ufeffDate received", rows[0])

    def test_07_empirical_baseline_archive_smoke(self):
        """Asserts that local CCDB_Export_2 archive streams cleanly with valid FOIA schema (if cached)."""
        if not os.path.exists(RAW_EXPORT_2):
            self.skipTest("CCDB_Export_2 not cached locally")
            
        diag = ParserDiagnostics(archive_path=RAW_EXPORT_2, file_name="")
        rows = list(stream_complaints(RAW_EXPORT_2, max_rows=1000, diagnostics=diag))
        
        self.assertEqual(len(rows), 1000)
        self.assertEqual(diag.error_rows, 0)
        self.assertEqual(tuple(diag.header), CFPB_FOIA_COLUMNS)
        for r in rows:
            self.assertNotEqual(r["Complaint ID"], "")
            self.assertNotEqual(r["Product"], "")

    def test_08_empirical_banking77_smoke(self):
        """Asserts that auxiliary banking77 dataset streams cleanly with text/category schema (if cached)."""
        if not os.path.exists(BANKING77_TRAIN):
            self.skipTest("banking77 not cached locally")
            
        diag = ParserDiagnostics(archive_path=BANKING77_TRAIN, file_name="")
        rows = list(stream_complaints(BANKING77_TRAIN, max_rows=500, diagnostics=diag))
        
        self.assertEqual(len(rows), 500)
        self.assertEqual(diag.error_rows, 0)
        self.assertEqual(tuple(diag.header), BANKING77_COLUMNS)
        for r in rows:
            self.assertNotEqual(r["text"], "")
            self.assertNotEqual(r["category"], "")

    def test_09_audit_report_dynamic_failure_reflection(self):
        """Asserts that audit report summary dynamically reflects failed pillars rather than hardcoding PASS."""
        if os.environ.get("PHASE2_AUDIT_RUNNING") == "1":
            # Avoid recursive audit runner invocation inside Pillar 6 test suite
            return
            
        from scripts.audit_phase2 import run_phase2_audit
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_report_path = os.path.join(tmp_dir, "test_audit_report.md")
            
            # Force Pillar 1 failure
            success = run_phase2_audit(report_path=test_report_path, force_pillar_fail=1)
            self.assertFalse(success, "Audit must return False when a pillar fails")
            
            self.assertTrue(os.path.isfile(test_report_path))
            with open(test_report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
                
            self.assertIn("Overall Verdict:** **FAILED**", report_content)
            # Assert summary table contains explicit FAIL for Pillar 1
            self.assertRegex(
                report_content,
                r"\|\s*\*\*1\.\s*Storage Preflight\*\*\s*\|\s*Disk space availability\s*\|\s*FAIL\s*\|",
                "Summary table must dynamically display FAIL for the failed pillar"
            )

    def test_10_parse_errors_manifest_provenance_metadata(self):
        """Asserts that parse_errors.csv ties records to verified source checksums and scan provenance."""
        manifest_path = os.path.join(REPO_ROOT, "data", "manifests", "parse_errors.csv")
        self.assertTrue(os.path.isfile(manifest_path))
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertGreaterEqual(len(reader), 4)
            
            for row in reader:
                self.assertEqual(row["error_type"], "verified_zero_errors")
                details = row["error_details"]
                self.assertIn("SHA-256:", details, "Must anchor scan evidence with SHA-256 checksum")
                self.assertIn("Local Full-Scan Evidence", details, "Must distinguish local full scan from CI")

    def test_11_malformed_rows_permissive_mode_safety(self):
        """Asserts that permissive mode handles rows with too few and too many columns safely without IndexError."""
        csv_text = io.StringIO(
            "ColA,ColB,ColC\n"
            "valA1,valB1,valC1\n"
            "valA2,valB2\n"  # 2 columns instead of 3
            "valA3,valB3,valC3,extra1,extra2\n"  # 5 columns instead of 3
        )
        diag = ParserDiagnostics(archive_path="test_perm.csv", file_name="test_perm.csv")
        rows = list(stream_complaints(csv_text, on_error="permissive", diagnostics=diag))
        
        # All 3 rows yielded safely in permissive mode
        self.assertEqual(len(rows), 3)
        self.assertEqual(diag.total_rows, 3)
        self.assertEqual(diag.valid_rows, 1, "Only row 1 is fully valid")
        self.assertEqual(diag.error_rows, 2, "Rows 2 and 3 must be counted in error_rows")
        
        # Row 1: normal
        self.assertEqual(rows[0], {"ColA": "valA1", "ColB": "valB1", "ColC": "valC1"})
        
        # Row 2: padded with empty string so ColC is not missing
        self.assertEqual(rows[1]["ColA"], "valA2")
        self.assertEqual(rows[1]["ColB"], "valB2")
        self.assertEqual(rows[1]["ColC"], "", "Missing column must be padded with empty string")
        
        # Row 3: overflow safely captured under _overflow_fields
        self.assertEqual(rows[2]["ColA"], "valA3")
        self.assertEqual(rows[2]["ColB"], "valB3")
        self.assertEqual(rows[2]["ColC"], "valC3")
        self.assertEqual(rows[2]["_overflow_fields"], ["extra1", "extra2"])
        
        # Verify null counts did not raise IndexError and tracked empty padded column
        self.assertEqual(diag.null_counts["ColC"], 1)

    def test_12_malformed_rows_strict_mode_rejection(self):
        """Asserts that malformed rows with too few and too many columns are rejected in record and raise modes."""
        csv_text = (
            "ColA,ColB,ColC\n"
            "valA1,valB1,valC1\n"
            "valA2,valB2\n"  # 2 cols
            "valA3,valB3,valC3,extra1\n"  # 4 cols
            "valA4,valB4,valC4\n"  # valid
        )
        
        # Record mode (default): skips malformed rows, counts them in error_rows, yields valid rows
        diag = ParserDiagnostics(archive_path="test_strict.csv", file_name="test_strict.csv")
        rows = list(stream_complaints(io.StringIO(csv_text), on_error="record", diagnostics=diag))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ColA"], "valA1")
        self.assertEqual(rows[1]["ColA"], "valA4")
        self.assertEqual(diag.valid_rows, 2)
        self.assertEqual(diag.error_rows, 2)
        self.assertEqual(len(diag.errors), 2)
        
        # Raise mode: raises CSVParseError on first malformed row
        with self.assertRaises(CSVParseError) as ctx:
            list(stream_complaints(io.StringIO(csv_text), on_error="raise"))
        self.assertIn("Column count mismatch: expected 3, got 2", str(ctx.exception))

    def test_13_scan_provenance_manifest_verification(self):
        """Asserts that full_scan_provenance.csv exists and all records pass verification."""
        prov_path = os.path.join(REPO_ROOT, "data", "manifests", "full_scan_provenance.csv")
        self.assertTrue(os.path.isfile(prov_path), f"Missing {prov_path}")
        
        with open(prov_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 4, "Must contain exactly 4 verified dataset scans")
            
            archives = {r["source_archive"] for r in reader}
            self.assertIn("CCDB_Export_2_May_2018_through_April_2021.zip", archives)
            self.assertIn("complaints.csv.zip", archives)
            self.assertIn("train.csv", archives)
            self.assertIn("test.csv", archives)
            
            for row in reader:
                valid, msg = verify_scan_provenance_record(
                    row,
                    repo_root=REPO_ROOT,
                    verify_local_file=True,
                    expected_parser_version="phase2.1-v1.0"
                )
                self.assertTrue(valid, f"Provenance record failed verification: {msg}")

    def test_14_scan_provenance_validation_edge_cases(self):
        """Asserts that verify_scan_provenance_record catches missing fields, checksum mismatch, and version drift."""
        base_valid_record = {
            "source_archive": "test_archive.zip",
            "source_inner_file": "test.csv",
            "source_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "scan_timestamp_utc": "2026-10-29T10:00:00Z",
            "parser_version": "phase2.1-v1.0",
            "command_configuration": "stream_complaints()",
            "environment_runtime": "Python 3.12",
            "expected_schema": "16 columns",
            "observed_schema": "16 columns",
            "record_count": "100",
            "valid_count": "100",
            "error_count": "0",
            "scan_status": "verified_zero_errors",
            "execution_mode": "local_workstation_full_scan",
            "notes": "Test note",
        }
        
        # Valid record passes
        valid, msg = verify_scan_provenance_record(base_valid_record)
        self.assertTrue(valid, msg)
        
        # Missing required field
        bad_rec = dict(base_valid_record)
        bad_rec["source_sha256"] = ""
        valid, msg = verify_scan_provenance_record(bad_rec)
        self.assertFalse(valid)
        self.assertIn("Missing or empty required field", msg)
        
        # Parser version mismatch
        valid, msg = verify_scan_provenance_record(base_valid_record, expected_parser_version="v2.0-different")
        self.assertFalse(valid)
        self.assertIn("Parser version mismatch", msg)
        
        # Non-zero error count
        bad_err = dict(base_valid_record)
        bad_err["error_count"] = "5"
        valid, msg = verify_scan_provenance_record(bad_err)
        self.assertFalse(valid)
        self.assertIn("Non-zero error count", msg)
        
        # Record count != valid count
        bad_count = dict(base_valid_record)
        bad_count["valid_count"] = "95"
        valid, msg = verify_scan_provenance_record(bad_count)
        self.assertFalse(valid)
        self.assertIn("Count mismatch", msg)
        
        # Checksum mismatch against actual file
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"Hello temporary world")
            tf_path = tf.name
        try:
            bad_hash_rec = dict(base_valid_record)
            bad_hash_rec["source_archive"] = os.path.basename(tf_path)
            bad_hash_rec["source_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
            valid, msg = verify_scan_provenance_record(bad_hash_rec, repo_root=os.path.dirname(tf_path), verify_local_file=True)
            self.assertFalse(valid)
            self.assertIn("SHA-256 mismatch", msg)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_15_supported_schemas_completeness(self):
        """Asserts that CFPB_FOIA_COLUMNS, CFPB_BULK_COLUMNS, and BANKING77_COLUMNS are correctly configured."""
        self.assertEqual(len(CFPB_FOIA_COLUMNS), 16)
        self.assertIn("Consumer complaint narrative", CFPB_FOIA_COLUMNS)
        self.assertEqual(len(CFPB_BULK_COLUMNS), 15)
        self.assertNotIn("Consumer complaint narrative", CFPB_BULK_COLUMNS)
        self.assertEqual(len(BANKING77_COLUMNS), 2)
        self.assertEqual(list(BANKING77_COLUMNS), ["text", "category"])




if __name__ == "__main__":
    unittest.main()
