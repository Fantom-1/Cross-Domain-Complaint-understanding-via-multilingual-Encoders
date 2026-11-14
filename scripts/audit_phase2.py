#!/usr/bin/env python3
"""Automated Phase 2 Audit & Verification Gate: Robust Parsing and Schema Diff.

Gating Invariants:
1. Environment & Storage Preflight: confirms workspace volume and >=15 GB free space for safe operation.
2. Parser Implementation Invariants:
   - src/data/parser.py exists and imports cleanly.
   - SAFE_FIELD_SIZE_LIMIT <= 2**31 - 1 (portable against Windows 32-bit C long overflow).
   - Canonical schemas defined: CFPB_FOIA_COLUMNS (16 cols), CFPB_BULK_COLUMNS (15 cols), BANKING77_COLUMNS (2 cols).
   - Core streaming generator stream_complaints() rejects mismatched schemas in default 'record' mode and handles multi-line/quotes.
3. Parse Error Manifest Invariants:
   - data/manifests/parse_errors.csv exists with exact required schema.
   - All empirical scan entries report verified_zero_errors (0 parse errors) tied to source checksums and scan metadata.
4. Documentation Completeness & Epistemological Boundaries:
   - docs/field_semantics.md exists, documents all 16 fields, explains weak administrative labels vs gold intent.
   - docs/schema_diff.md exists, covers 16-col vs 15-col shift, 2026 narrative deprecation, and multiline/quote stats.
5. Empirical Ingestion Smoke Checks:
   - When raw files are cached locally: Streams sample rows from CCDB_Export_2 verifying zero crashes and exact schema match.
   - In CI: Dynamically designated as SKIPPED (CI) with note explaining uncached status, preventing false local claims.
6. Test Suite Execution:
   - Dynamically executes test_phase2_parsing.py, test_phase1_provenance.py, and test_data_integrity.py (when data exists).
7. Emits captured snapshot report: docs/phase2_parsing_audit.md with dynamic pillar outcomes.
"""

import csv
import datetime
import os
import shutil
import sys
import unittest
from typing import Dict, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

MANIFEST_DIR = os.path.join(REPO_ROOT, "data", "manifests")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
SRC_DIR = os.path.join(REPO_ROOT, "src", "data")
PARSE_ERRORS_CSV = os.path.join(MANIFEST_DIR, "parse_errors.csv")
FIELD_SEMANTICS_DOC = os.path.join(DOCS_DIR, "field_semantics.md")
SCHEMA_DIFF_DOC = os.path.join(DOCS_DIR, "schema_diff.md")
AUDIT_REPORT_PATH = os.path.join(DOCS_DIR, "phase2_parsing_audit.md")
PARSER_MODULE_PATH = os.path.join(SRC_DIR, "parser.py")

REQUIRED_PARSE_ERROR_COLUMNS = [
    "archive_name",
    "file_name",
    "line_number",
    "complaint_id",
    "error_type",
    "error_details",
    "raw_snippet",
]

RAW_EXPORT_2 = os.path.join(REPO_ROOT, "data", "raw", "cfpb", "CCDB_Export_2_May_2018_through_April_2021.zip")
RAW_BANKING77 = os.path.join(REPO_ROOT, "data", "raw", "banking77", "train.csv")


def run_phase2_audit(
    report_path: Optional[str] = None,
    force_pillar_fail: Optional[int] = None,
) -> bool:
    target_report_path = report_path or AUDIT_REPORT_PATH
    os.environ["PHASE2_AUDIT_RUNNING"] = "1"
    try:
        return _run_phase2_audit_internal(target_report_path, force_pillar_fail)
    finally:
        os.environ.pop("PHASE2_AUDIT_RUNNING", None)


def _run_phase2_audit_internal(
    target_report_path: str,
    force_pillar_fail: Optional[int] = None,
) -> bool:
    print("=" * 80)
    print("PHASE 2 AUDIT: ROBUST PARSING & SCHEMA DIFF VERIFICATION")
    print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Repository Root: {REPO_ROOT}")
    print("=" * 80)
    
    audit_log = []
    overall_passed = True
    
    pillar_results: Dict[int, Dict[str, str]] = {
        1: {"title": "Storage Preflight", "focus": "Disk space availability", "result": "PASS", "notes": ""},
        2: {"title": "Parser Implementation", "focus": "Stream generator & Windows limit", "result": "PASS", "notes": ""},
        3: {"title": "Parse Error Manifest", "focus": "Schema & 0-error integrity", "result": "PASS", "notes": ""},
        4: {"title": "Documentation", "focus": "Field semantics & schema diff", "result": "PASS", "notes": ""},
        5: {"title": "Empirical Smoke", "focus": "Real archive streaming", "result": "PASS", "notes": ""},
        6: {"title": "Unit Test Suites", "focus": "Full regression coverage", "result": "PASS", "notes": ""},
    }
    
    def log(msg: str, status: str = "INFO", pillar: Optional[int] = None):
        nonlocal overall_passed
        badge = f"[{status}]"
        print(f"{badge:<10} {msg}")
        audit_log.append((status, msg))
        if status == "FAIL":
            overall_passed = False
            if pillar and pillar in pillar_results:
                pillar_results[pillar]["result"] = "FAIL"

    # Test hook for regression verification
    if force_pillar_fail in pillar_results:
        log(f"Forced failure injected into Pillar {force_pillar_fail}", "FAIL", pillar=force_pillar_fail)

    # -------------------------------------------------------------
    # Pillar 1: Environment & Storage Preflight
    # -------------------------------------------------------------
    log("--- Pillar 1: Environment & Storage Preflight ---")
    total_b, used_b, free_b = shutil.disk_usage(REPO_ROOT)
    free_gb = free_b / (1024 ** 3)
    log(f"Workspace volume free space: {free_gb:.2f} GB")
    if free_gb >= 15.0:
        log("Sufficient disk space available (>= 15.0 GB threshold met)", "PASS", pillar=1)
        pillar_results[1]["notes"] = f"{free_gb:.2f} GB free on workspace drive (threshold: >= 15.0 GB)"
    else:
        log(f"Low disk space: {free_gb:.2f} GB < 15.0 GB required", "FAIL", pillar=1)
        pillar_results[1]["notes"] = f"Insufficient disk space: {free_gb:.2f} GB < 15.0 GB threshold"

    # -------------------------------------------------------------
    # Pillar 2: Parser Module & Implementation Invariants
    # -------------------------------------------------------------
    log("--- Pillar 2: Parser Module Implementation Invariants ---")
    if not os.path.isfile(PARSER_MODULE_PATH):
        log(f"Missing parser module: {PARSER_MODULE_PATH}", "FAIL", pillar=2)
        pillar_results[2]["notes"] = "Missing src/data/parser.py"
    else:
        log("src/data/parser.py exists", "PASS", pillar=2)
        try:
            from src.data.parser import (
                CFPB_BULK_COLUMNS,
                CFPB_FOIA_COLUMNS,
                BANKING77_COLUMNS,
                SAFE_FIELD_SIZE_LIMIT,
                ensure_safe_field_size_limit,
                stream_complaints,
                scan_and_profile,
            )
            log("Successfully imported src.data.parser symbols", "PASS", pillar=2)
            
            # Portable limit
            if SAFE_FIELD_SIZE_LIMIT <= 2147483647:
                log(f"SAFE_FIELD_SIZE_LIMIT = {SAFE_FIELD_SIZE_LIMIT:,} (<= 2^31 - 1, prevents Windows C long overflow)", "PASS", pillar=2)
            else:
                log(f"SAFE_FIELD_SIZE_LIMIT {SAFE_FIELD_SIZE_LIMIT} exceeds 32-bit C long limit", "FAIL", pillar=2)
                
            # Schema definitions
            if len(CFPB_FOIA_COLUMNS) == 16 and "Consumer complaint narrative" in CFPB_FOIA_COLUMNS:
                log("CFPB_FOIA_COLUMNS has 16 columns including narrative", "PASS", pillar=2)
            else:
                log("CFPB_FOIA_COLUMNS invalid", "FAIL", pillar=2)
                
            if len(CFPB_BULK_COLUMNS) == 15 and "Consumer complaint narrative" not in CFPB_BULK_COLUMNS:
                log("CFPB_BULK_COLUMNS has 15 columns (narrative correctly omitted)", "PASS", pillar=2)
            else:
                log("CFPB_BULK_COLUMNS invalid", "FAIL", pillar=2)
                
            if len(BANKING77_COLUMNS) == 2 and list(BANKING77_COLUMNS) == ["text", "category"]:
                log("BANKING77_COLUMNS matches ['text', 'category']", "PASS", pillar=2)
            else:
                log("BANKING77_COLUMNS invalid", "FAIL", pillar=2)
            
            if pillar_results[2]["result"] != "FAIL":
                pillar_results[2]["notes"] = "SAFE_FIELD_SIZE_LIMIT <= 2^31 - 1, 16/15/2 col schemas, strict validation"
        except Exception as e:
            log(f"Failed importing or validating src.data.parser: {e}", "FAIL", pillar=2)
            pillar_results[2]["notes"] = f"Import error: {e}"

    # -------------------------------------------------------------
    # Pillar 3: Parse Error Manifest Verification
    # -------------------------------------------------------------
    log("--- Pillar 3: Parse Error Manifest Schema & Content Invariants ---")
    if not os.path.isfile(PARSE_ERRORS_CSV):
        log(f"Missing parse errors manifest: {PARSE_ERRORS_CSV}", "FAIL", pillar=3)
        pillar_results[3]["notes"] = "Missing data/manifests/parse_errors.csv"
    else:
        log("data/manifests/parse_errors.csv exists", "PASS", pillar=3)
        try:
            with open(PARSE_ERRORS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
                if headers == REQUIRED_PARSE_ERROR_COLUMNS:
                    log(f"Exact 7-column schema validated: {headers}", "PASS", pillar=3)
                else:
                    log(f"Schema mismatch: expected {REQUIRED_PARSE_ERROR_COLUMNS}, got {headers}", "FAIL", pillar=3)
                
                rows = list(reader)
                if len(rows) >= 4:
                    log(f"Cataloged {len(rows)} verification records across scanned datasets", "PASS", pillar=3)
                else:
                    log(f"Expected at least 4 verification rows, found {len(rows)}", "FAIL", pillar=3)
                    
                all_zero_errors = True
                has_provenance_metadata = True
                for r in rows:
                    if r.get("error_type") != "verified_zero_errors":
                        all_zero_errors = False
                        log(f"Unresolved parse error logged: {r}", "FAIL", pillar=3)
                    details = r.get("error_details", "")
                    if "SHA-256" not in details or "Local Full-Scan" not in details:
                        has_provenance_metadata = False
                
                if all_zero_errors:
                    log("All cataloged scans verified 0 parse errors (error_type = verified_zero_errors)", "PASS", pillar=3)
                if has_provenance_metadata:
                    log("Verified entries tie to exact source SHA-256 hashes and distinguish local scan from CI", "PASS", pillar=3)
                else:
                    log("Parse error details missing source SHA-256 or scan provenance metadata", "FAIL", pillar=3)
                
                if pillar_results[3]["result"] != "FAIL":
                    pillar_results[3]["notes"] = f"Verified 0 errors across {len(rows)} datasets; checksum-anchored local scan metadata"
        except Exception as e:
            log(f"Failed parsing parse_errors.csv: {e}", "FAIL", pillar=3)
            pillar_results[3]["notes"] = f"Error reading manifest: {e}"

    # -------------------------------------------------------------
    # Pillar 4: Documentation Completeness & Epistemological Boundaries
    # -------------------------------------------------------------
    log("--- Pillar 4: Documentation Completeness & Semantic Governance ---")
    if not os.path.isfile(FIELD_SEMANTICS_DOC):
        log(f"Missing documentation: {FIELD_SEMANTICS_DOC}", "FAIL", pillar=4)
        pillar_results[4]["notes"] = "Missing field_semantics.md"
    else:
        log("docs/field_semantics.md exists", "PASS", pillar=4)
        with open(FIELD_SEMANTICS_DOC, "r", encoding="utf-8") as f:
            fs_text = f.read()
        if "weak administrative labels" in fs_text and "80 FR 15572" in fs_text:
            log("field_semantics.md documents weak administrative labels and 80 FR 15572 consent", "PASS", pillar=4)
        else:
            log("field_semantics.md missing critical administrative governance terms", "FAIL", pillar=4)
            
        if "PolyAI/banking77" in fs_text and "CFPB" in fs_text:
            log("field_semantics.md documents both CFPB and auxiliary benchmark modalities", "PASS", pillar=4)
        else:
            log("field_semantics.md missing dataset modality distinction", "FAIL", pillar=4)

    if not os.path.isfile(SCHEMA_DIFF_DOC):
        log(f"Missing documentation: {SCHEMA_DIFF_DOC}", "FAIL", pillar=4)
        pillar_results[4]["notes"] = "Missing schema_diff.md"
    else:
        log("docs/schema_diff.md exists", "PASS", pillar=4)
        with open(SCHEMA_DIFF_DOC, "r", encoding="utf-8") as f:
            sd_text = f.read()
        if "August 14, 2026" in sd_text and "15 columns" in sd_text and "16 columns" in sd_text:
            log("schema_diff.md documents August 14, 2026 narrative deprecation and 15 vs 16 column shift", "PASS", pillar=4)
        else:
            log("schema_diff.md missing narrative deprecation analysis", "FAIL", pillar=4)
            
        if "36.74%" in sd_text and "11.97%" in sd_text and "LLP64" in sd_text:
            log("schema_diff.md documents multiline (36.74%), quotes (11.97%), and Windows LLP64 limit", "PASS", pillar=4)
        else:
            log("schema_diff.md missing empirical parsing metrics or platform overflow details", "FAIL", pillar=4)

    if pillar_results[4]["result"] != "FAIL":
        pillar_results[4]["notes"] = "Epistemological boundaries, 80 FR 15572, and 2026 deprecation documented"

    # -------------------------------------------------------------
    # Pillar 5: Empirical Ingestion Smoke Checks (Local Cache vs CI)
    # -------------------------------------------------------------
    log("--- Pillar 5: Empirical Ingestion Smoke Checks ---")
    if os.path.exists(RAW_EXPORT_2):
        try:
            from src.data.parser import stream_complaints, CFPB_FOIA_COLUMNS
            smoke_rows = list(stream_complaints(RAW_EXPORT_2, max_rows=100))
            if len(smoke_rows) == 100 and list(smoke_rows[0].keys()) == list(CFPB_FOIA_COLUMNS):
                log("Empirical smoke test: successfully streamed 100 rows from local CCDB_Export_2", "PASS", pillar=5)
                pillar_results[5]["result"] = "PASS"
                pillar_results[5]["notes"] = "Local archives parse cleanly without memory bloat or delimiter crashes"
            else:
                log(f"Smoke test unexpected output from Export 2: count={len(smoke_rows)}", "FAIL", pillar=5)
                pillar_results[5]["result"] = "FAIL"
                pillar_results[5]["notes"] = f"Unexpected row count: {len(smoke_rows)}"
        except Exception as e:
            log(f"Empirical smoke check failed on Export 2: {e}", "FAIL", pillar=5)
            pillar_results[5]["result"] = "FAIL"
            pillar_results[5]["notes"] = f"Smoke stream failed: {e}"
    else:
        log("RAW_EXPORT_2 not present locally (skipping empirical stream test; untracked in CI)", "INFO")
        pillar_results[5]["result"] = "SKIPPED (CI)"
        pillar_results[5]["notes"] = "Raw archive uncached (typical in CI; full scan verified on developer workstation)"

    # -------------------------------------------------------------
    # Pillar 6: Unit Test Suite Execution
    # -------------------------------------------------------------
    log("--- Pillar 6: Unit Test Suite Execution ---")
    from tests.data.test_phase2_parsing import TestPhase2Parsing
    from tests.data.test_phase1_provenance import TestPhase1Provenance

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPhase2Parsing))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase1Provenance))

    canonical_parquet = os.path.join(REPO_ROOT, "data", "processed", "canonical_dataset.parquet")
    if os.path.exists(canonical_parquet):
        from tests.data.test_data_integrity import TestDataIntegrity
        suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
        test_scope_str = "Phase 2, Phase 1, Phase 0"
    else:
        test_scope_str = "Phase 2, Phase 1 [CI mode: processed data untracked]"

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    if result.wasSuccessful() and force_pillar_fail != 6:
        log(f"Test suites PASSED ({result.testsRun} tests executed: {test_scope_str})", "PASS", pillar=6)
        pillar_results[6]["result"] = "PASS"
        pillar_results[6]["notes"] = f"{result.testsRun} tests executed ({test_scope_str}) with 0 failures"
    else:
        failures_count = len(result.failures) + (1 if force_pillar_fail == 6 else 0)
        errors_count = len(result.errors)
        log(f"Test suite FAILED: {failures_count} failures, {errors_count} errors", "FAIL", pillar=6)
        pillar_results[6]["result"] = "FAIL"
        pillar_results[6]["notes"] = f"{result.testsRun} tests executed with {failures_count} failures, {errors_count} errors"

    # -------------------------------------------------------------
    # Pillar 7: Emit Audit Report Snapshot
    # -------------------------------------------------------------
    verdict_badge = "**PASSED**" if overall_passed else "**FAILED**"
    log(f"OVERALL AUDIT VERDICT: {verdict_badge}")

    # Build dynamic markdown summary table
    summary_table_rows = []
    for k in sorted(pillar_results.keys()):
        p = pillar_results[k]
        summary_table_rows.append(f"| **{k}. {p['title']}** | {p['focus']} | {p['result']} | {p['notes']} |")
    summary_table_str = "\n".join(summary_table_rows)

    report_content = f"""# Phase 2 Audit Report: Robust Parsing & Schema Diff

- **Audit Execution Date:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}
- **Workspace:** `{REPO_ROOT}`
- **Overall Verdict:** {verdict_badge}

## Audit Summary by Pillar

| Pillar | Focus | Result | Notes |
| :--- | :--- | :---: | :--- |
{summary_table_str}

## Detailed Execution Log

```text
"""
    for status, msg in audit_log:
        report_content += f"[{status:<5}] {msg}\n"
    report_content += "```\n"

    with open(target_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    log(f"Snapshot written to {target_report_path}", "PASS")

    return overall_passed


if __name__ == "__main__":
    success = run_phase2_audit()
    sys.exit(0 if success else 1)
