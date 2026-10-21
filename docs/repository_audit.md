# Repository & Environment Audit

**Date:** 2026-10-22  
**Agent:** Research Engineering Agent  
**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase A (Data Preparation & Quality Verification Only)

---

## 1. Executive Summary

This audit establishes the baseline state of the repository, operating environment, source availability, and governance constraints prior to data ingestion and processing. The project objective is to classify the intent of consumer complaint text and study domain/language generalization under rigorous experimental controls.

Per binding instructions in `SYSTEM.md` and `README_START_HERE.md`:
- **Current Scope:** Standard data preparation for a supervised intent classification baseline.
- **Strict Prohibition in Phase A:** No downloading model weights, no training, no fine-tuning, no evaluation, and no contrastive learning / retrieval / multi-task stacks until `docs/baseline_data_readiness.md` is approved and split manifests are frozen.

---

## 2. Git & Version Control State

- **Active Branch:** `main`
- **Remote URL:** `https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders.git`
- **Tracking:** `origin/main`
- **Initial Baseline Commit:** `d70d480` (*feat(init): initialize project instruction pack and Phase A specifications*)
- **Cleanliness:** Working tree clean; `.gitignore` actively ignores local data artifacts (`/data/`), model checkpoints, virtual environments, and scratch logs.
- **Commit Strategy:** Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`) applied at regular checkpoint intervals.

---

## 3. Runtime & Hardware Environment

- **Operating System:** Windows 11 (build 10.0.26100)
- **Local Storage:**
  - `D:` Drive: 42.55 GB available (primary workspace: `d:\NLP`)
  - `C:` Drive: 29.37 GB available
- **Python Runtime:** Python 3.13.9 (Anaconda environment at `C:\Users\yashk\anaconda3`)
- **Key Installed Libraries:**
  - `pandas`: 2.2.3 (Verified OK)
  - `numpy`: 2.2.2 (Verified OK)
  - `pyarrow`: 19.0.0 (Verified OK)
  - `scipy`: 1.15.1 (Verified OK)
  - `scikit-learn`: 1.6.1 (Verified OK)
  - `requests`: 2.32.3 (Verified OK)
- **Missing / Deferred Libraries:**
  - Hugging Face `datasets` / `transformers` (deferred to training phase per Phase A gate). All raw downloads and transformations in Phase A use standard HTTP streams, `pyarrow`, `pandas`, and standard library utilities (`zipfile`, `hashlib`, `csv`, `json`).

---

## 4. Directory Structure Plan

```text
d:\NLP\
├── configs/
│   ├── taxonomy.json             # Canonical project taxonomy definitions
│   └── product_canonical.json    # Canonical mapping for source domains
├── data/
│   ├── raw/                      # Immutable raw data with verified SHA-256 hashes
│   │   ├── cfpb/
│   │   └── banking77/
│   ├── interim/                  # Intermediate filtered & normalized tables
│   ├── processed/                # Canonical dataset (.parquet) & frozen train/val/test splits
│   └── manifests/                # Inventory, label mapping, split manifests, exclusion logs
├── docs/
│   ├── repository_audit.md       # (This document)
│   ├── label_taxonomy.md         # Intent label ontology and definitions
│   ├── dataset_card.md           # Formal dataset card adhering to FAIR principles
│   ├── data_preparation_methodology.md # Step-by-step pipeline documentation
│   └── baseline_data_readiness.md      # Phase A completion gate & readiness report
├── src/
│   └── data/
│       ├── __init__.py
│       ├── download.py           # Deterministic source acquisition & hash verification
│       ├── normalize.py          # Conservative normalization & redaction handling
│       ├── dedup.py              # Exact and MinHash/LSH near-duplicate grouping
│       ├── map_intents.py        # Rule-based / ontology mapping to project taxonomy
│       └── split.py              # Group-safe stratified splitting
└── tests/
    └── data/
        ├── __init__.py
        └── test_data_integrity.py# Automated schema, integrity, leakage & count tests
```

---

## 5. Candidate Source Verification Status

| Source | Role Decision | Verified License | Access Method | Schema / Notes |
|---|---|---|---|---|
| **CFPB Consumer Complaint Database** | `primary_eligible` | US Public Domain / FOIA Electronic Reading Room | Bulk ZIP: `https://files.consumerfinance.gov/ccdb/complaints.csv.zip` (Tested live: HTTP 200, Content-Length 356,704,969 bytes, Last-Modified 2026-10-21) | 18 columns including `Complaint ID`, `Product`, `Sub-product`, `Issue`, `Sub-issue`, `Consumer complaint narrative`. Primary source for English financial complaints. |
| **BANKING77** | `auxiliary_only` | CC BY 4.0 | Hugging Face Hub `PolyAI/banking77` (sha: `90d4e2ee5521c04fc1488f065b8b083658768c57`) | 13,083 customer queries, 77 fine-grained banking intents. Customer service queries, not full complaint narratives. Kept distinct. |
| **MASSIVE** | `auxiliary_only` | CC BY 4.0 | Hugging Face Hub `AmazonScience/massive` (sha: `ff6bd8e4b27c3543e4f8fe2108f32bb95a6f8740`) | Virtual assistant utterances across 51 languages. Not consumer complaints. Kept separate from complaint training. |
| **COMI-LINGUA & MUTANT** | `excluded` | CC BY 4.0 / Research Use | `https://github.com/lingo-iitgn/COMI-LINGUA` | Hindi-English code-mixed tasks (LID, NER, POS, MT). Sourced from news and speeches, not complaint narratives. Excluded from complaint intent classification. |
| **Project-Annotated Hindi/Hinglish** | `needs_review` / Uncollected | N/A | Pending collection protocol | Currently unavailable. The absence of authentic Hindi/Hinglish complaint narratives is an explicit project finding. |

---

## 6. Phase A Gate Checklist

- [x] Inspect Git status, working tree, `.gitignore`, and runtime dependencies.
- [x] Configure remote `origin` to `https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders.git` and establish `main` tracking branch.
- [x] Verify live URLs, HTTP responses, license types, and schemas for candidate sources.
- [x] Implement deterministic acquisition script and immutable raw data storage with SHA-256 recording.
- [x] Create `dataset_inventory.csv` manifest.
- [x] Execute conservative normalization and MinHash deduplication.
- [x] Construct explicit `label_taxonomy.md` and `source_label_mapping.csv`.
- [x] Build canonical dataset (`canonical_dataset.parquet`) with unified schema.
- [x] Generate leakage-safe, group-stratified in-distribution split manifests.
- [x] Execute automated test suite for schema integrity, split exclusivity, and count reconciliation.
- [x] Author `dataset_card.md`, `data_preparation_methodology.md`, and `baseline_data_readiness.md`.

---

## 7. Known Gaps Deferred to Phase B

| Gap | Description | Status |
|---|---|---|
| **Cross-domain split manifest** | `data/manifests/split_crossdomain.csv` pairing CFPB test rows with Banking77 queries for zero-shot domain transfer evaluation does not yet exist. Only `split_indomain.csv` is present. Cross-domain generalization — a core project claim — **cannot be evaluated until this manifest is created.** | **Phase B prerequisite** |
| **Hindi/Hinglish complaint data** | No authentic Hindi/Hinglish consumer complaint narratives are available. COMI-LINGUA and MUTANT are code-mixed news/speech corpora, not complaint text. Multilingual evaluation requires dedicated human-annotated complaint data. | Pending external annotation |
| **Reviewer label in `source_label_mapping.csv`** | All label decisions were made by an automated rule engine. The `reviewer` field was corrected from `"Automated Rule Engine (Reviewed)"` (misleadingly implying human sign-off) to `"automated_rule_engine"` in commit following Phase A audit. |  Corrected post-audit |
