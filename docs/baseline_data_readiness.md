# Baseline Data Readiness Report (Phase A Completion Gate)

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Author:** Research Engineering Agent  
**Date:** 2026-10-22  
**Gate Status:** **PHASE A COMPLETE — STOPPED FOR USER REVIEW & APPROVAL**  

---

## 1. Executive Summary

Phase A (Data Ingestion, Verification, Normalization, Deduplication, Taxonomy Mapping, and Leakage-Controlled Partitioning) has been executed to completion. All datasets, manifests, automated tests, and documentation artifacts have been generated deterministically.

Per `SYSTEM.md` and `README_START_HERE.md`:
> *"Dataset preparation is first; baseline training is allowed only after explicit approval of the data-readiness report and frozen manifests. Do not download model weights, load a model, train, fine-tune, or evaluate a model in Phase A."*

This document provides the full data-readiness audit and reconciliation figures required for the Phase A completion gate.

---

## 2. Source Inventory & Checksums

All source files have been acquired deterministically, verified against SHA-256 digests, and cataloged in `data/manifests/dataset_inventory.csv`:

| Dataset | Local Path | Verified SHA-256 | Records / Rows | License | Role Decision |
|---|---|---|---|---|---|
| **CFPB FOIA Narratives Archive** | `data/raw/cfpb/CCDB_Export_2_May_2018_through_April_2021.zip` | `4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45` | 1,041,632 records (439,860 narratives) | US Public Domain | `primary_eligible` (English complaint baseline) |
| **CFPB Bulk Metadata** | `data/raw/cfpb/complaints.csv.zip` | `9ae94df79f82a8e84b9b3e22bf8951f8c02489b88f5c4fa9ee32a95e1df760a1` | Metadata export | US Public Domain | `primary_eligible` (Reference metadata) |
| **BANKING77 Train** | `data/raw/banking77/train.csv` | `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b` | 10,003 queries | CC BY 4.0 | `auxiliary_only` (Query benchmark, kept distinct) |
| **BANKING77 Test** | `data/raw/banking77/test.csv` | `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` | 3,080 queries | CC BY 4.0 | `auxiliary_only` (Query benchmark, kept distinct) |
| **BANKING77 Classes** | `data/raw/banking77/categories.json` | `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63` | 77 classes | CC BY 4.0 | `auxiliary_only` |

---

## 3. Data Cleaning, Normalization & Deduplication Audit

1. **Conservative Text Normalization:**
   - Standardized Unicode to NFC across all records.
   - PII redaction runs matching `X{2,}` collapsed to single `<REDACTED>` sentinel tokens.
   - Preserved original complaint text in `text_original` and normalized text in `text_normalized`.
   - Casing, punctuation, digits, spelling variations, and negation words are strictly preserved.
2. **Deduplication & Leakage Prevention:**
   - Exact hash deduplication identified 2,791 exact duplicate texts.
   - MinHash LSH (64 permutations, 16 bands, 5-gram word shingles) clustered 5,422 near-duplicate templated form letters into unified `group_id`s.
   - A Disjoint Set Union (Union-Find) with path compression assigned all connected near-duplicates to 106,175 distinct cluster groups.

---

## 4. Count Reconciliation

Every scanned row from the raw CFPB archive is accounted for in `data/manifests/exclusion_log.csv`:

| Stage / Category | Record Count | Percentage |
|---|---|---|
| **Total Scanned Rows in Archive** | **1,041,632** | 100.0% |
| - *Excluded: Missing free-text narrative* | 601,772 | 57.8% |
| - *Total Verified Narratives in Archive* | **439,860** | **42.2%** |
| - *Excluded: Under 20 words (insufficient context)* | 19,838 | 1.9% |
| - *Eligible Narratives Sampled across 9 Domains* | 114,388 | 11.0% |
| - *Excluded: Unmapped issue/sub-issue* | 1,473 | 0.1% |
| - *Excluded: Discarded for class balance cap* | 67,192 | 6.5% |
| **Final Canonical Dataset (`canonical_dataset.parquet`)** | **45,723** | **4.4%** |

---

## 5. Frozen Partition Manifests & Class Support

The dataset was partitioned using a group-safe stratified policy (Seed 13), ensuring that duplicate/near-duplicate groups never cross partitions:

| Partition | Record Count | Percentage | Unique Groups | Group Leakage Overlap |
|---|---|---|---|---|
| **Train** (`baseline_train.csv`) | 32,019 | 70.0% | 31,521 | **0 (Zero)** |
| **Validation** (`baseline_validation.csv`) | 6,852 | 15.0% | 6,762 | **0 (Zero)** |
| **Test** (`baseline_test.csv`) | 6,852 | 15.0% | 6,756 | **0 (Zero)** |
| **Total** | **45,723** | **100.0%** | **45,039** | **0 (Zero)** |

### Per-Class Distribution Across Partitions

| Intent ID | Intent Label | Train | Validation | Test | Total |
|---|---|---|---|---|---|
| 0 | `reporting_incorrect_information` | 2,113 | 429 | 458 | 3,000 |
| 1 | `reporting_investigation_dispute` | 2,093 | 443 | 464 | 3,000 |
| 2 | `reporting_improper_use` | 1,441 | 312 | 309 | 2,062 |
| 3 | `fraud_or_scam` | 2,105 | 456 | 439 | 3,000 |
| 4 | `debt_not_owed` | 2,092 | 454 | 454 | 3,000 |
| 5 | `debt_threats` | 2,103 | 448 | 449 | 3,000 |
| 6 | `debt_communication` | 2,085 | 469 | 446 | 3,000 |
| 7 | `payment_problem` | 2,113 | 445 | 442 | 3,000 |
| 8 | `transaction_problem` | 2,102 | 449 | 449 | 3,000 |
| 9 | `funds_availability` | 2,101 | 450 | 449 | 3,000 |
| 10 | `account_access` | 2,099 | 451 | 450 | 3,000 |
| 11 | `account_management` | 2,106 | 449 | 445 | 3,000 |
| 12 | `servicing_dispute` | 2,101 | 449 | 450 | 3,000 |
| 13 | `application_problem` | 2,100 | 450 | 450 | 3,000 |
| 14 | `credit_terms_dispute` | 2,101 | 449 | 450 | 3,000 |
| 15 | `closing_process` | 1,164 | 249 | 248 | 1,661 |
| **Total** | | **32,019** | **6,852** | **6,852** | **45,723** |

---

## 6. Automated Data Integrity Verification

Automated test suite (`tests/data/test_data_integrity.py`) executed:
- `test_01_canonical_schema_and_columns`: **PASSED** (all 18 canonical columns present with valid types)
- `test_02_unique_example_ids`: **PASSED** (45,723 unique IDs, zero collisions)
- `test_03_non_empty_text`: **PASSED** (zero nulls, all normalized texts > 10 characters)
- `test_04_taxonomy_and_label_map_integrity`: **PASSED** (strict 1-to-1 match with `configs/taxonomy.json`)
- `test_05_closed_set_evaluation_coverage`: **PASSED** (100% of validation and test labels exist in training)
- `test_06_zero_group_leakage`: **PASSED** (0 groups shared across train, val, test)
- `test_07_split_exclusivity`: **PASSED** (train, val, test partitions mutually disjoint)
- `test_08_count_reconciliation`: **PASSED** (Canonical parquet count == Train + Val + Test)

**Execution Result:** `Ran 8 tests in 1.048s — OK`.

---

## 7. Multilingual & Indic Gap Assessment

Per `SYSTEM.md` and `PROJECT_BRIEF.md`:
- CFPB narratives provide real English financial complaints, but contain **0.00% Devanagari or Hindi/Hinglish complaint text**.
- `PolyAI/banking77` provides English banking queries, not complaints.
- Resources like `COMI-LINGUA` and `MUTANT` provide code-mixed news/speech tokens for POS/NER/LID, not consumer complaint intent labels.
- **Explicit Finding:** To evaluate genuine Hindi or Hinglish complaint understanding, dedicated human-annotated complaint narratives are required. The current dataset readiness permits a rigorous, leakage-free English baseline (`facebook/xlm-v-base`), but cannot substantiate Hindi/Hinglish claims without external annotation.

---

## 8. Phase A Deliverables Checklist

- [x] `docs/repository_audit.md` (Git state, remote tracking, environment baseline)
- [x] `docs/label_taxonomy.md` (16-class intent taxonomy & confusable boundaries)
- [x] `docs/data_preparation_methodology.md` (Complete pipeline documentation)
- [x] `docs/dataset_card.md` (Formal dataset card)
- [x] `docs/baseline_data_readiness.md` (This gate report)
- [x] `configs/taxonomy.json` & `configs/product_canonical.json`
- [x] `data/manifests/dataset_inventory.csv`
- [x] `data/manifests/source_label_mapping.csv`
- [x] `data/manifests/split_indomain.csv`
- [x] `data/manifests/exclusion_log.csv`
- [x] `data/processed/canonical_dataset.parquet` (45,723 rows)
- [x] `data/processed/baseline_train.csv`, `baseline_validation.csv`, `baseline_test.csv`
- [x] `data/processed/label_map.json`
- [x] `src/data/download.py`, `normalize.py`, `dedup.py`, `map_intents.py`, `split.py`, `build_canonical.py`
- [x] `tests/data/test_data_integrity.py` (8 automated tests passing)

---

## 9. Gate Status: Stopped for User Approval

Phase A is complete. As mandated by `SYSTEM.md` (§ Phase A completion gate):
> **No model weights have been downloaded, and no fine-tuning or evaluation will take place until the user explicitly reviews and approves this Data Readiness Report.**
