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
    ensure_safe_field_size_limit,
    stream_complaints,
    scan_and_profile,
    SAFE_FIELD_SIZE_LIMIT,
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
        """Asserts that mismatched schemas are detected and handled per policy."""
        bad_header_csv = io.StringIO(
            'ColA,ColB,ColC\n'
            '1,2,3\n'
        )
        
        # Policy 'raise'
        with self.assertRaises(CSVParseError):
            list(stream_complaints(bad_header_csv, expected_columns=CFPB_FOIA_COLUMNS, on_error="raise"))
        
        # Default policy yields without crashing if on_error != 'raise'
        bad_header_csv.seek(0)
        rows = list(stream_complaints(bad_header_csv, expected_columns=CFPB_FOIA_COLUMNS, on_error="record"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], {"ColA": "1", "ColB": "2", "ColC": "3"})

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


if __name__ == "__main__":
    unittest.main()
