# Automated Phase 4 Tokenization Profiling Audit Report

**Generated:** 2026-11-15T12:19:54.599143+00:00  
**Execution Mode:** **Captured Local Workstation Snapshot** (Full Cryptographic Source-File & Checkpoint Verification)  
**Repository Root:** `.` (Repo-Relative)  
**Audit Target:** Phase 4 Subword Tokenization Profiling (`src/data/tokenization_profiler.py`, `data/manifests/tokenization_profile.json`, `data/manifests/tokenization_profile.csv`, `docs/tokenization_report.md`)  
**Overall Status:** **PASSED**

---

## 1. Executive Summary & Gating Decision

| Pillar | Focus | Result | Notes |
| :---: | :--- | :---: | :--- |
| **Pillar 1: Storage & Environment** | Disk space & profiler module | **PASS** | All verification invariants satisfied. |
| **Pillar 2: Provenance & Tokenizer Binding** | Revision, asset hashes & dataset SHA-256 bindings | **PASS** | All verification invariants satisfied. |
| **Pillar 3: Manifest Schema & CSV Reconciliation** | Fail on mock, JSON/CSV row-by-row reconciliation | **PASS** | All verification invariants satisfied. |
| **Pillar 4: Truncation & Monotonicity** | Mathematical monotonicity & truncation bounds | **PASS** | All verification invariants satisfied. |
| **Pillar 5: Governance & Headline Statistics** | Supervision disclaimers & exact markdown reconciliation | **PASS** | All verification invariants satisfied. |
| **Pillar 6: Unit Test Suite** | Regression coverage across Phases 0-4 | **PASS** | All verification invariants satisfied. |

---

## 2. Key Empirical Verification Metrics

* **Model Checkpoint:** `facebook/xlm-v-base` (SentencePiece Unigram, 901,629 vocabulary size)
* **Pinned Checkpoint Revision:** `68c75dd7733d2640b3a98114e3e94196dc543fe1`
* **Tokenizer Asset Hashes:**
  - `config.json`: `25ed3e0d067ca06706bb76a597856c9ac7ba67559d4b2cf0e3f3f5052efd47e2`
  - `sentencepiece.bpe.model`: `dbee9f6b1c2cba29b335e70d6088eea943c7d5ae55ac7dd17174760bf758e309`
  - `tokenizer.json`: `43f949ef0c0b1ac18c506551109383d4a8a2bd48956ced0cc95cfd9120d42dca`
* **Canonical Dataset Total:** 45,723 instances (Train: 32,019, Val: 6,852, Test: 6,852)
* **Canonical Checksum:** `b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463`
* **Subword Expansion Ratios:**
  - Content Subword Expansion (excl. special tokens): **1.437x mean** (median 1.350x, p90 1.810x, min 1.000x, max 11.316x)
  - Sequence Length Expansion (incl. special tokens): **1.456x mean** (median 1.370x, p90 1.830x, min 1.022x, max 11.351x)
* **Context Window Truncation Rates (Canonical Normalized):**
  - **128 tokens:** 72.27% truncated (33,042 instances) | Retained coverage: 27.73%
  - **256 tokens:** 42.34% truncated (19,360 instances) | Retained coverage: 57.66%
  - **384 tokens:** 25.49% truncated (11,655 instances) | Retained coverage: 74.51%
  - **512 tokens:** 15.96% truncated (7,298 instances)  | Retained coverage: 84.04%
* **Auxiliary Intent Benchmark (Banking77):**
  - Train (10,003 queries): Mean 15.97 tokens, 0.00% truncated at 128 tokens
  - Test (3,080 queries): Mean 14.82 tokens, 0.00% truncated at 128 tokens
* **Semantic Governance:** CFPB Issue/Sub-issue designated as weak administrative supervision; Banking77 designated auxiliary-only.

---

## 3. Detailed Audit Execution Log

```
12:19:22 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
12:19:22 [PASS ] Workspace disk space confirmed: 20.10 GB free.
12:19:26 [PASS ] Tokenization profiler module imports cleanly.
12:19:26 [INFO ] Starting Pillar 2: Dataset Provenance, Tokenizer Checkpoint & Asset Hashes...
12:19:27 [PASS ] Source file hash independently checked locally: canonical_dataset.parquet verified (b591ba980a99ba82...).
12:19:27 [PASS ] Source file hash independently checked locally: Banking77 train & test SHA-256 digests verified.
12:19:27 [PASS ] Physical tokenizer asset independently checked locally: 'config.json' SHA-256 verified (25ed3e0d067ca067...).
12:19:27 [PASS ] Physical tokenizer asset independently checked locally: 'sentencepiece.bpe.model' SHA-256 verified (dbee9f6b1c2cba29...).
12:19:27 [PASS ] Physical tokenizer asset independently checked locally: 'tokenizer.json' SHA-256 verified (43f949ef0c0b1ac1...).
12:19:27 [PASS ] Manifest pinned tokenizer revision verified: 68c75dd7733d2640b3a98114e3e94196dc543fe1.
12:19:27 [PASS ] Manifest cryptographic binding to tokenizer asset 'config.json' verified (25ed3e0d067ca067...).
12:19:27 [PASS ] Manifest cryptographic binding to tokenizer asset 'sentencepiece.bpe.model' verified (dbee9f6b1c2cba29...).
12:19:27 [PASS ] Manifest cryptographic binding to tokenizer asset 'tokenizer.json' verified (43f949ef0c0b1ac1...).
12:19:27 [PASS ] Manifest cryptographic binding to canonical dataset verified (b591ba980a99ba82...).
12:19:27 [PASS ] Manifest cryptographic binding to Banking77 partitions verified.
12:19:27 [INFO ] Starting Pillar 3: Profile Manifests Schema & Row-by-Row CSV Reconciliation...
12:19:27 [PASS ] Loaded profile JSON from data/manifests/tokenization_profile.json
12:19:27 [PASS ] Verified production execution: mock_mode is False.
12:19:27 [PASS ] Canonical splits perfectly reconcile to 45,723 instances.
12:19:27 [PASS ] All 16 intent classes present and reconcile exactly to 45,723 instances.
12:19:27 [PASS ] Banking77 train (10,003) and test (3,080) counts verified.
12:19:27 [PASS ] Profile CSV schema verified (26 cols, 23 rows).
12:19:27 [PASS ] All 23 rows in CSV reconciled row-by-row against JSON manifest within numeric tolerance.
12:19:27 [INFO ] Starting Pillar 4: Truncation Analysis & Monotonic Percentile Invariants...
12:19:27 [PASS ] Percentiles in normalized_overall are strictly monotonic.
12:19:27 [PASS ] Truncation rates in normalized_overall are strictly monotonic across cutoffs.
12:19:27 [PASS ] Percentiles in split_test are strictly monotonic.
12:19:27 [PASS ] Truncation rates in split_test are strictly monotonic across cutoffs.
12:19:27 [PASS ] Percentiles in split_train are strictly monotonic.
12:19:27 [PASS ] Truncation rates in split_train are strictly monotonic across cutoffs.
12:19:27 [PASS ] Percentiles in split_validation are strictly monotonic.
12:19:27 [PASS ] Truncation rates in split_validation are strictly monotonic across cutoffs.
12:19:27 [PASS ] Canonical 512-truncation rate verified: 15.96% (within [15.0%, 17.0%]).
12:19:27 [PASS ] Banking77 128-token truncation is verified at 0.00% across train and test.
12:19:27 [INFO ] Starting Pillar 5: Governance Disclaimers & Exact Headline Metric Reconciliation...
12:19:27 [PASS ] Report includes CFPB Issue/Sub-issue weak administrative supervision notice.
12:19:27 [PASS ] Report includes Banking77 auxiliary benchmark classification notice.
12:19:27 [PASS ] Report includes Generalization boundary disclaimers.
12:19:27 [PASS ] Report includes Explicit model checkpoint specification.
12:19:27 [PASS ] Report includes Pinned tokenizer revision specification.
12:19:27 [PASS ] Report includes Vocabulary size disclosure.
12:19:27 [PASS ] Report exactly matches manifest for Content expansion ratio mean: 1.437
12:19:27 [PASS ] Report exactly matches manifest for Content expansion ratio median: 1.350
12:19:27 [PASS ] Report exactly matches manifest for Content expansion ratio p90: 1.810
12:19:27 [PASS ] Report exactly matches manifest for Content expansion ratio maximum: 11.316
12:19:27 [PASS ] Report exactly matches manifest for Sequence expansion ratio mean: 1.456
12:19:27 [PASS ] Report exactly matches manifest for Sequence expansion ratio maximum: 11.351
12:19:27 [PASS ] Report exactly matches manifest for 512-token truncation rate: 15.96%
12:19:27 [PASS ] Report exactly matches manifest for 256-token truncation rate: 42.34%
12:19:27 [PASS ] Report exactly matches manifest for 128-token truncation rate: 72.27%
12:19:27 [PASS ] All headline metrics in documentation reconcile with machine-readable manifest.
12:19:27 [INFO ] Starting Pillar 6: Unit Test Suite Execution...
12:19:54 [PASS ] All unit tests passed (68 tests executed across Phases 1-4 with 0 failures).
```
