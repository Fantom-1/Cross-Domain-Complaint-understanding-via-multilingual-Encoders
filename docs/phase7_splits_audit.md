# Phase 7 Audit Report: Split Feasibility & Boundary Formulation

**Generated At:** 2026-11-16T19:16:36.457794+00:00  
**Execution Mode:** **Captured Local Workstation Snapshot** (Full Cryptographic Source-File & Manifest Verification)  
**Repository Root:** `.` (Repo-Relative)  
**Audit Target:** Phase 7 Split Feasibility & Boundary Formulation (`docs/split_feasibility.md`, `data/manifests/class_domain_coverage.csv`, `data/manifests/temporal_distribution.csv`, `data/manifests/temporal_class_distribution.csv`, `data/manifests/split_indomain.csv`)  
**Audit Status:** **PASSED**  

---

## 1. Pillar Results Summary

| Pillar | Focus Area | Status | Key Criteria |
| :---: | :--- | :---: | :--- |
| **Pillar 1** | Storage & Environment Preflight | **PASS** | >= 10.0 GB disk space, clean module import |
| **Pillar 2** | Dataset Provenance & File Checksums | **PASS** | Canonical parquet SHA-256 (`b591ba98...`), in-domain split and temporal manifests |
| **Pillar 3** | Contingency Matrix Invariants | **PASS** | 9 domains x 16 classes (144 cells, 81 zero cells = 56.25% sparsity, 45,723 records) |
| **Pillar 4** | Domain Transfer Confounding Audit | **PASS** | 4 exclusive classes; confounding proof for debt_collection and mortgage hold-outs |
| **Pillar 5** | Chronological & Temporal Stability | **PASS** | 36 continuous months (2018-05 to 2021-04), 16 classes supported across all 4 years |
| **Pillar 6** | In-Distribution Baseline Invariants | **PASS** | 32,019 train, 6,852 val, 6,852 test; 0 shared clusters across all split boundaries |
| **Pillar 7** | Governance & Exact Reconciliation | **PASS** | Official baseline adoption, confounding proof, Hindi/Hinglish deferral verified |
| **Pillar 8** | Unit Test Suite Execution | **PASS** | Unit and regression test suites pass with 0 failures across Phases 1–7 |

---

## 2. Key Audit Statistics Verified

* **Canonical Dataset Total Instances:** 45,723
* **Product Domains:** 9 domains (`bank_account`, `credit_card`, `credit_reporting`, `debt_collection`, `money_transfer`, `mortgage`, `payday_personal_loan`, `student_loan`, `vehicle_loan`)
* **Intent Classes:** 16 classes
* **Contingency Matrix Sparsity:** **81 / 144 zero cells** (**56.25% sparsity**)
* **Domain-Exclusive Classes:** **4 classes** (`closing_process` $\rightarrow$ `mortgage`; `debt_communication`, `debt_not_owed`, `debt_threats` $\rightarrow$ `debt_collection`)
* **Leave-One-Domain-Out Feasibility:** Proven **structurally confounded** for `debt_collection` and `mortgage` (0 training instances for held-out classes)
* **Chronological Span:** **36 continuous months** (May 2018 through April 2021), averaging 1,270 records/month
* **Temporal Class Support:** All 16 classes actively supported across 2018, 2019, 2020, and 2021
* **Official In-Distribution Baseline:** **32,019 train**, **6,852 val**, **6,852 test**
* **Near-Duplicate Cluster Leakage:** **0 shared clusters** between any split pairs
* **Multilingual Scope Boundary:** **Hindi/Hinglish formally deferred/blocked** from Phase A baseline (zero authentic Indian complaints in CFPB)

---

## 3. Detailed Audit Execution Log

```
19:14:50 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
19:14:50 [PASS ] Workspace disk space confirmed: 19.59 GB free.
19:14:50 [PASS ] SplitAnalyzer module imports cleanly and initializes with default paths.
19:14:50 [INFO ] Starting Pillar 2: Dataset Provenance & Input File Checksums...
19:14:50 [PASS ] Source file hash verified locally: canonical_dataset.parquet (b591ba980a99ba82...).
19:14:50 [PASS ] Baseline split manifest exists: split_indomain.csv.
19:14:50 [PASS ] Required artifact verified: Class-Domain Coverage Manifest.
19:14:50 [PASS ] Required artifact verified: Temporal Monthly Distribution Manifest.
19:14:50 [PASS ] Required artifact verified: Temporal Class Distribution Manifest.
19:14:50 [PASS ] Required artifact verified: Split Feasibility Report.
19:14:50 [INFO ] Starting Pillar 3: Product Domain x Label Contingency Matrix Invariants...
19:14:50 [PASS ] Contingency matrix verified: 9 domains x 16 classes (144 cells, 81 zero cells = 56.25% sparsity, 45723 total records).
19:14:50 [INFO ] Starting Pillar 4: Domain Transfer Confounding & Exclusivity Audit...
19:14:51 [PASS ] Domain transfer confounding proof verified: leave-one-domain-out structurally confounded for debt_collection and mortgage.
19:14:51 [INFO ] Starting Pillar 5: Chronological Distribution & Near-Duplicate Spanning Audit...
19:14:51 [PASS ] Temporal manifests verified: 36 continuous months (2018-05 to 2021-04), 45723 complaints, 16 classes active in all 4 years.
19:14:51 [INFO ] Starting Pillar 6: In-Distribution Baseline Split Invariants...
19:14:51 [PASS ] Baseline split manifest verified: 45723 records (32019 train / 6852 val / 6852 test, 0 shared clusters across all boundaries).
19:14:51 [INFO ] Starting Pillar 7: Governance Disclaimers & Exact Headline Reconciliation...
19:14:51 [PASS ] Report satisfies all governance disclosures: official in-domain baseline adoption, domain confounding proof, and Hindi/Hinglish deferral.
19:14:51 [INFO ] Starting Pillar 8: Unit Test Suite Execution...
19:16:36 [PASS ] All 133 unit tests in test_phase*.py passed with 0 failures.
```
