# Baseline Snapshot Inventory (May 2018–April 2021 Reference Release)

**Audit Date:** 2026-10-28  
**Auditor:** Automated Phase 0 Script (`scripts/audit_phase0.py`)  
**Scope:** Preserved reference baseline snapshot files, checksums, and empirical profile metrics.  
**Retention Policy:** Strictly immutable reference baseline release. Preserved as a historical benchmark.

---

## 1. Executive Summary

This inventory documents the pre-existing reference baseline dataset generated from the CFPB historical export (May 2018 through April 2021). The dataset was used to establish the initial repository baseline benchmark (`facebook/xlm-v-base` 16-class classification).

* **Total Canonical Narratives:** 45,723 records
* **Partition Split:** 32,019 train (70.0%) / 6,852 validation (15.0%) / 6,852 test (15.0%)
* **Intent Classes:** 16 classes mapped deterministically from CFPB administrative `Issue` and `Sub-issue` fields
* **Normalized Product Domains:** 9 financial domains
* **Audit Scope Status:** 27 of 27 target artifacts inspected (0 missing optional)
* **Overall Audit Verdict:** **Empirically Verified & Reconciled (100% Invariants Passed)**

---

## 2. Core Snapshot Files & Cryptographic Checksums (Reconciled)

| File Path | Format | Size (Bytes) | Size (MB) | Rows | Columns | SHA-256 Checksum |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `data/processed/canonical_dataset.parquet` | Parquet | 66,312,066 | 63.24 | 45,723 | 18 | `b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463` |
| `data/processed/baseline_train.csv` | CSV | 46,273,246 | 44.13 | 32,019 | 8 | `febbb253a9d7a3fec3caf622e811a45370a9fa16bd15583a2a7ff34d1fbfac78` |
| `data/processed/baseline_validation.csv` | CSV | 9,909,912 | 9.45 | 6,852 | 8 | `db270bbbf48841deadb3c1251863881680d419eb04513146041b79065aa49800` |
| `data/processed/baseline_test.csv` | CSV | 9,624,936 | 9.18 | 6,852 | 8 | `ffff21c815d7c54f0719094fc1aaa6e9fdfb7f75bb9c41f838fe4875507b90bb` |
| `data/processed/label_map.json` | JSON | 464 | 0.0 | 16 | N/A | `3285b5b9b5939c603dccb400a8f00f99244f5897393f51816e57dfa80bd42406` |
| `data/manifests/split_indomain.csv` | CSV | 7,463,620 | 7.12 | 45,723 | 10 | `cd84fdb294b8ea8caa7da7e532a796bc78da99013d298f36f8e32c6a1c2c2f20` |

> [!NOTE]
> All row and column counts above are dynamically read from disk using RFC 4180 CSV-aware record parsing and Parquet metadata inspect, resolving previous reporting discrepancies.

---

## 3. Independent Verification vs. Historical Repository Claims

To ensure complete empirical clarity, this audit explicitly distinguishes between properties verified directly on the disk artifacts during this run versus historical benchmark claims reported by prior phases.

### A. Properties Empirically Verified by Current Audit:
1. **Programmatic Test Execution:**  
   The integrity test suite (`tests/data/test_data_integrity.py`) was executed programmatically during this audit run:
   * **Tests executed:** 8
   * **Failures:** 0
   * **Errors:** 0
   * **Test Suite Result:** PASSED (All 8 tests succeeded)
2. **Mathematical Partition Invariants (Independently Computed & Dynamically Derived):**
   * **Example ID Exclusivity:**
     * Train $\cap$ Val: 0 overlapping IDs — **PASSED**
     * Train $\cap$ Test: 0 overlapping IDs — **PASSED**
     * Val $\cap$ Test: 0 overlapping IDs — **PASSED**
   * **Duplicate Group Leakage:**
     * Train $\cap$ Val groups: 0 shared group IDs — **PASSED**
     * Train $\cap$ Test groups: 0 shared group IDs — **PASSED**
     * Val $\cap$ Test groups: 0 shared group IDs — **PASSED**
   * **Closed-Set Label Containment:**
     * Val labels missing from Train: 0 — **PASSED**
     * Test labels missing from Train: 0 — **PASSED**
   * **Row Count Reconciliation:**
     * Train (32,019) + Val (6,852) + Test (6,852) = 45,723 vs Canonical Parquet 45,723 — **PASSED (Exact match)**

### B. Historical Repository Claims (Unverified Baseline Context):
The following figures represent **prior repository reports from earlier training runs**, not independently re-trained or reproduced results in this phase:
* **Model Benchmark:** `facebook/xlm-v-base` sequential fine-tuning reported Macro-F1 of 0.53686, weighted F1 of 0.53395, and accuracy of 0.53255 on `baseline_test.csv` (Trial 2, lr=2e-5, epoch 3).
* **Hardware Environment:** Prior logs report an NVIDIA RTX PRO 6000 Blackwell MIG instance (`1g.24gb` slice) under SLURM Job 156.
* **Disclaimer:** These model performance claims have not been re-evaluated or reproduced in this data-preparation phase; they remain context metrics for future comparative experiments.

---

## 4. Class Distribution Across Partitions

| Intent Label | Total Rows | Train (70%) | Val (15%) | Test (15%) | Train % | Val % | Test % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 3,000 | 2,099 | 451 | 450 | 70.0% | 15.0% | 15.0% |
| `account_management` | 3,000 | 2,106 | 449 | 445 | 70.2% | 15.0% | 14.8% |
| `application_problem` | 3,000 | 2,100 | 450 | 450 | 70.0% | 15.0% | 15.0% |
| `closing_process` | 1,661 | 1,164 | 249 | 248 | 70.1% | 15.0% | 14.9% |
| `credit_terms_dispute` | 3,000 | 2,101 | 449 | 450 | 70.0% | 15.0% | 15.0% |
| `debt_communication` | 3,000 | 2,085 | 469 | 446 | 69.5% | 15.6% | 14.9% |
| `debt_not_owed` | 3,000 | 2,092 | 454 | 454 | 69.7% | 15.1% | 15.1% |
| `debt_threats` | 3,000 | 2,103 | 448 | 449 | 70.1% | 14.9% | 15.0% |
| `fraud_or_scam` | 3,000 | 2,105 | 456 | 439 | 70.2% | 15.2% | 14.6% |
| `funds_availability` | 3,000 | 2,101 | 450 | 449 | 70.0% | 15.0% | 15.0% |
| `payment_problem` | 3,000 | 2,113 | 445 | 442 | 70.4% | 14.8% | 14.7% |
| `reporting_improper_use` | 2,062 | 1,441 | 312 | 309 | 69.9% | 15.1% | 15.0% |
| `reporting_incorrect_information` | 3,000 | 2,113 | 429 | 458 | 70.4% | 14.3% | 15.3% |
| `reporting_investigation_dispute` | 3,000 | 2,093 | 443 | 464 | 69.8% | 14.8% | 15.5% |
| `servicing_dispute` | 3,000 | 2,101 | 449 | 450 | 70.0% | 15.0% | 15.0% |
| `transaction_problem` | 3,000 | 2,102 | 449 | 449 | 70.1% | 15.0% | 15.0% |

---

## 5. Product Domain Distribution (Reconciled: 9 Domains)

The baseline corpus covers **9** normalized product domains:

| Domain | Row Count | Percentage |
| :--- | :---: | :---: |
| `debt_collection` | 9,714 | 21.25% |
| `credit_reporting` | 6,319 | 13.82% |
| `credit_card` | 6,245 | 13.66% |
| `bank_account` | 5,874 | 12.85% |
| `mortgage` | 5,079 | 11.11% |
| `money_transfer` | 4,584 | 10.03% |
| `vehicle_loan` | 3,122 | 6.83% |
| `student_loan` | 2,737 | 5.99% |
| `payday_personal_loan` | 2,049 | 4.48% |

---

## 6. Narrative Text Length Statistics (Normalized Text)

* **Word Count Percentiles:**
  * Minimum: 20 words
  * 25th Percentile: 84 words
  * Median: 152 words
  * Mean: 225.4 words
  * 75th Percentile: 272 words
  * 90th Percentile: 457 words
  * 95th Percentile: 652 words
  * 99th Percentile: 1220 words
  * Maximum: 6014 words

---

## 7. Known Scientific Limitations of Baseline

1. **Weak Labels:** Intent classes were derived via deterministic rule-matching from administrative CFPB bureau issues. They are not human-adjudicated semantic gold intents.
2. **In-Distribution Split:** The split was sampled across the entire May 2018–April 2021 window uniformly, meaning it does not evaluate temporal generalization or cross-domain transfer.
3. **English-Only:** No multilingual or code-switched (Hindi/Hinglish) complaints are represented.
