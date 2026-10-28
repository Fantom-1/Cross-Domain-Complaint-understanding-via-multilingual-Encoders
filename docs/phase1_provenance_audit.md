# Phase 1 Source Provenance & Release Manifest Audit Report

**Audit Type:** Automated Gated Execution  
**Execution Context:** Captured Local Snapshot (`2026-10-28 18:42:07Z`)  
**Workspace Root:** `D:\NLP`  
**Overall Verdict:** **PASSED**  

---

## 1. Multi-Pillar Invariant Evaluation

| Pillar | Inspection / Invariant Scope | Status | Details |
| :--- | :--- | :---: | :--- |
| **Storage & Preflight** | Workspace volume capacity >= 15 GB | PASS | 34.02 GB free |
| **Required Deliverables** | Presence of manifests and governance docs | PASS | Manifests and docs verified |
| **Inventory Manifest** | 20-column schema & 25 entries in `dataset_inventory.csv` | PASS | 25 entries, 0 errors |
| **Overlap & Contiguity** | 15-column schema, 24 entries, strict 1-day contiguity | PASS | 24 entries, 0 errors |
| **Cryptographic Hashes** | SHA-256 verification of cached baseline archives | PASS | 5 files verified, 0 errors |
| **Automated Test Suite** | Execution of `test_phase1_provenance` & `test_data_integrity` | PASS | 19 tests passed in test suite |

---

## 2. Invariant Checklist

- [x] **Storage Buffer:** Sufficient workspace capacity verified (34.02 GB available).
- [x] **Official Source Catalog:** Complete enumeration of all 21 CFPB FOIA narrative archive windows.
- [x] **Mathematical Partition Proof:** Contiguous date coverage (2011-12-01 to 2026-08-14) with zero pairwise ID overlap against baseline.
- [x] **Immutable Baseline Integrity:** Cryptographic SHA-256 check matches `CCDB_Export_2` reference snapshot.
- [x] **Unit Test Compliance:** Full automated test suite passes with 0 failures and 0 errors.

---

## 3. Detailed Inspection Logs

### Manifest Summary
* **`data/manifests/dataset_inventory.csv`**: 25 cataloged assets across CFPB FOIA reading room (21), active bulk feed (1), and BANKING77 (3).
* **`data/manifests/release_overlap_report.csv`**: 24 comparative releases documenting temporal duration, column counts, narrative presence, and zero overlap.
* **`docs/source_terms_and_provenance.md`**: Legal terms of use, 5 U.S.C. § 552 FOIA reading room authority, 17 U.S.C. § 105 public domain status, and August 14, 2026 policy change documentation.

### Test Results
* Ran 19 automated test cases across `tests/data/test_phase1_provenance.py` and `tests/data/test_data_integrity.py`.
* Failures: 0, Errors: 0.
