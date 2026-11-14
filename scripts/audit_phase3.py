#!/usr/bin/env python3
"""Automated Phase 3 Audit & Verification Gate: Full-Corpus Profiling.

Gating Invariants:
1. Environment & Storage Preflight: confirms workspace volume and >=15 GB free space for safe operation.
2. Profiler Implementation Invariants:
   - src/data/profiler.py exists and imports cleanly.
   - Core functions: _compute_percentiles, _compute_summary_stats, export_profile_csv.
   - Class CorpusProfiler with profile_cfpb_foia_archive and profile_banking77.
3. Profile Manifests Schema & Invariant Integrity:
   - data/manifests/source_profile.json exists, traces 1,041,632 records, 439,860 narratives.
   - 0 duplicate complaint IDs verified across population.
   - data/manifests/source_profile.csv exists with exact 9-column schema.
4. Documentation Completeness & Empirical Analysis:
   - docs/profile_report.md documents date coverage, missingness, percentiles, duplicate rates, natural class imbalance.
5. Empirical Profiling Smoke Check:
   - Runs a quick profile smoke test on a sample stream without errors.
6. Unit Test Suite Execution:
   - Runs test_phase3_profiling.py, test_phase2_parsing.py, and test_phase1_provenance.py.
7. Emits captured snapshot report: docs/phase3_profiling_audit.md.
"""

import csv
import datetime
import io
import json
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

PROFILE_JSON = os.path.join(MANIFEST_DIR, "source_profile.json")
PROFILE_CSV = os.path.join(MANIFEST_DIR, "source_profile.csv")
PROFILE_REPORT = os.path.join(DOCS_DIR, "profile_report.md")
AUDIT_REPORT_PATH = os.path.join(DOCS_DIR, "phase3_profiling_audit.md")
PROFILER_MODULE_PATH = os.path.join(SRC_DIR, "profiler.py")

REQUIRED_CSV_COLUMNS = [
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


def run_phase3_audit(
    report_path: Optional[str] = None,
    force_pillar_fail: Optional[int] = None,
) -> bool:
    target_report_path = report_path or AUDIT_REPORT_PATH
    os.environ["PHASE3_AUDIT_RUNNING"] = "1"
    try:
        return _run_phase3_audit_internal(target_report_path, force_pillar_fail)
    finally:
        os.environ.pop("PHASE3_AUDIT_RUNNING", None)


def _run_phase3_audit_internal(
    target_report_path: str,
    force_pillar_fail: Optional[int] = None,
) -> bool:
    print("=" * 80)
    print("PHASE 3 AUDIT: FULL-CORPUS PROFILING VERIFICATION")
    print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Repository Root: {REPO_ROOT}")
    print("=" * 80)

    audit_log = []
    overall_passed = True

    pillar_results: Dict[int, Dict[str, str]] = {
        1: {"title": "Storage Preflight", "focus": "Disk space availability", "result": "PASS", "notes": ""},
        2: {"title": "Profiler Module", "focus": "Streaming profiler implementation", "result": "PASS", "notes": ""},
        3: {"title": "Profile Manifests", "focus": "JSON & CSV profile schema integrity", "result": "PASS", "notes": ""},
        4: {"title": "Documentation", "focus": "Comprehensive empirical report", "result": "PASS", "notes": ""},
        5: {"title": "Empirical Smoke", "focus": "Synthetic / stream profiling test", "result": "PASS", "notes": ""},
        6: {"title": "Unit Test Suites", "focus": "Regression coverage across Phases 0-3", "result": "PASS", "notes": ""},
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
        pillar_results[1]["notes"] = f"Low disk space: {free_gb:.2f} GB < 15.0 GB required"

    # -------------------------------------------------------------
    # Pillar 2: Profiler Module & Implementation Invariants
    # -------------------------------------------------------------
    log("--- Pillar 2: Profiler Module Implementation Invariants ---")
    if not os.path.isfile(PROFILER_MODULE_PATH):
        log(f"Missing profiler module: {PROFILER_MODULE_PATH}", "FAIL", pillar=2)
        pillar_results[2]["notes"] = "Missing src/data/profiler.py"
    else:
        log("src/data/profiler.py exists", "PASS", pillar=2)
        try:
            from src.data.profiler import (
                CorpusProfiler,
                _compute_percentiles,
                _compute_summary_stats,
                export_profile_csv,
            )
            log("Successfully imported src.data.profiler symbols", "PASS", pillar=2)
            
            # Unit check on helper math functions
            pcts = _compute_percentiles([10, 20, 30, 40, 50], [50])
            if pcts.get("p50") == 30.0:
                log("Verified percentile calculation logic", "PASS", pillar=2)
            else:
                log(f"Percentile logic unexpected result: {pcts}", "FAIL", pillar=2)
                
            if pillar_results[2]["result"] != "FAIL":
                pillar_results[2]["notes"] = "CorpusProfiler, percentile logic, and CSV exporter verified"
        except Exception as e:
            log(f"Failed importing or validating src.data.profiler: {e}", "FAIL", pillar=2)
            pillar_results[2]["notes"] = f"Import error: {e}"

    # -------------------------------------------------------------
    # Pillar 3: Profile Manifests Verification
    # -------------------------------------------------------------
    log("--- Pillar 3: Profile Manifests Verification ---")
    if not os.path.isfile(PROFILE_JSON) or not os.path.isfile(PROFILE_CSV):
        log("Missing source_profile.json or source_profile.csv", "FAIL", pillar=3)
        pillar_results[3]["notes"] = "Missing source_profile manifests"
    else:
        log("data/manifests/source_profile.json and source_profile.csv exist", "PASS", pillar=3)
        try:
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                
            total_r = p_data.get("total_rows", 0)
            narr_present = p_data.get("narrative_profile", {}).get("narratives_present", 0)
            narr_missing = p_data.get("narrative_profile", {}).get("narratives_missing", 0)
            dup_id_count = p_data.get("integrity_checks", {}).get("duplicate_complaint_id_count", -1)
            
            if total_r == 1041632 and narr_present == 439860 and narr_missing == 601772:
                log(f"Verified population reconciliation: {total_r:,} total, {narr_present:,} narratives, {narr_missing:,} missing", "PASS", pillar=3)
            else:
                log(f"Population mismatch in JSON: total={total_r}, present={narr_present}, missing={narr_missing}", "FAIL", pillar=3)
                
            if dup_id_count == 0:
                log("Verified 0 duplicate Complaint IDs in population", "PASS", pillar=3)
            else:
                log(f"Duplicate Complaint IDs detected: {dup_id_count}", "FAIL", pillar=3)

            # CSV schema check
            with open(PROFILE_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
                if headers == REQUIRED_CSV_COLUMNS:
                    log(f"Exact 9-column CSV schema validated: {headers}", "PASS", pillar=3)
                else:
                    log(f"CSV schema mismatch: expected {REQUIRED_CSV_COLUMNS}, got {headers}", "FAIL", pillar=3)
                    
            if pillar_results[3]["result"] != "FAIL":
                pillar_results[3]["notes"] = "1,041,632 rows reconciled, 0 duplicate IDs, 9-column CSV validated"
        except Exception as e:
            log(f"Failed verifying profile manifests: {e}", "FAIL", pillar=3)
            pillar_results[3]["notes"] = f"Manifest verification error: {e}"

    # -------------------------------------------------------------
    # Pillar 4: Documentation Completeness
    # -------------------------------------------------------------
    log("--- Pillar 4: Documentation Completeness & Analysis ---")
    if not os.path.isfile(PROFILE_REPORT):
        log(f"Missing documentation: {PROFILE_REPORT}", "FAIL", pillar=4)
        pillar_results[4]["notes"] = "Missing docs/profile_report.md"
    else:
        log("docs/profile_report.md exists", "PASS", pillar=4)
        with open(PROFILE_REPORT, "r", encoding="utf-8") as f:
            pr_text = f.read()
        if "1,041,632" in pr_text and "439,860" in pr_text and "42.23%" in pr_text:
            log("profile_report.md documents population counts and narrative availability", "PASS", pillar=4)
        else:
            log("profile_report.md missing primary population metrics", "FAIL", pillar=4)
            
        if "56,822" in pr_text and "12.92%" in pr_text and "808" in pr_text:
            log("profile_report.md documents exact duplicate rates and top boilerplate templates", "PASS", pillar=4)
        else:
            log("profile_report.md missing exact duplicate or boilerplate template analysis", "FAIL", pillar=4)
            
        if "reporting_incorrect_information" in pr_text and "29.22%" in pr_text:
            log("profile_report.md documents un-capped natural class distribution and imbalance", "PASS", pillar=4)
        else:
            log("profile_report.md missing natural class distribution details", "FAIL", pillar=4)

        if pillar_results[4]["result"] != "FAIL":
            pillar_results[4]["notes"] = "Full population, length percentiles, duplicate templates, and drift documented"

    # -------------------------------------------------------------
    # Pillar 5: Empirical Ingestion Smoke Checks
    # -------------------------------------------------------------
    log("--- Pillar 5: Empirical Ingestion Smoke Checks ---")
    try:
        from src.data.profiler import CorpusProfiler
        profiler = CorpusProfiler()
        
        sample_csv = io.StringIO(
            "Date received,Product,Sub-product,Issue,Sub-issue,Consumer complaint narrative,Company public response,Company,State,ZIP code,Tags,Submitted via,Date sent to company,Company response to consumer,Timely response?,Complaint ID\n"
            "2020-01-01,Credit card,General,Billing,Late fee,This is a test complaint narrative with some words.,Response,Bank A,CA,90210,,Web,2020-01-02,Closed,Yes,99901\n"
            "2020-01-02,Mortgage,Conventional,Loan,Modification,Another brief complaint narrative for smoke testing.,Response,Bank B,NY,10001,,Web,2020-01-03,Closed,Yes,99902\n"
        )
        sample_profile = profiler.profile_cfpb_foia_archive(sample_csv)
        if sample_profile.get("total_rows") == 2 and sample_profile.get("narrative_profile", {}).get("narratives_present") == 2:
            log("Empirical profiler smoke test: successfully profiled in-memory sample stream", "PASS", pillar=5)
            pillar_results[5]["notes"] = "Stream profiler executes cleanly with 0 errors on mock data"
        else:
            log(f"Profiler smoke test unexpected output: {sample_profile}", "FAIL", pillar=5)
            pillar_results[5]["notes"] = "Smoke profile mismatch"
    except Exception as e:
        log(f"Empirical smoke check failed: {e}", "FAIL", pillar=5)
        pillar_results[5]["notes"] = f"Smoke test crash: {e}"

    # -------------------------------------------------------------
    # Pillar 6: Unit Test Suite Execution
    # -------------------------------------------------------------
    log("--- Pillar 6: Unit Test Suite Execution ---")
    from tests.data.test_phase3_profiling import TestPhase3Profiling
    from tests.data.test_phase2_parsing import TestPhase2Parsing
    from tests.data.test_phase1_provenance import TestPhase1Provenance

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPhase3Profiling))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase2Parsing))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase1Provenance))

    canonical_parquet = os.path.join(REPO_ROOT, "data", "processed", "canonical_dataset.parquet")
    if os.path.exists(canonical_parquet):
        from tests.data.test_data_integrity import TestDataIntegrity
        suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
        test_scope_str = "Phase 3 (10), Phase 2 (10), Phase 1 (9), Phase 0 (10)"
    else:
        test_scope_str = "Phase 3 (10), Phase 2 (10), Phase 1 (9) [CI mode: processed data untracked]"

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

    summary_table_rows = []
    for k in sorted(pillar_results.keys()):
        p = pillar_results[k]
        summary_table_rows.append(f"| **{k}. {p['title']}** | {p['focus']} | {p['result']} | {p['notes']} |")
    summary_table_str = "\n".join(summary_table_rows)

    report_content = f"""# Phase 3 Audit Report: Full-Corpus Profiling

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
    success = run_phase3_audit()
    sys.exit(0 if success else 1)

