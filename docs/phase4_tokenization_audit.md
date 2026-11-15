# Automated Phase 4 Tokenization Profiling Audit Report

**Generated:** 2026-11-15T10:53:51.015509+00:00  
**Repository Root:** `D:\NLP`  
**Audit Target:** Phase 4 Subword Tokenization Profiling (`src/data/tokenization_profiler.py`, `data/manifests/tokenization_profile.json`, `docs/tokenization_report.md`)  
**Overall Status:** **PASSED**

---

## 1. Executive Summary & Gating Decision

| Pillar | Focus | Result | Notes |
| :---: | :--- | :---: | :--- |
| **Pillar 1: Storage & Environment** | Disk space & profiler module | **PASS** | All verification invariants satisfied. |
| **Pillar 2: Cryptographic Provenance** | Dataset SHA-256 bindings | **PASS** | All verification invariants satisfied. |
| **Pillar 3: Manifest Integrity** | JSON & CSV schema and cardinality reconciliation | **PASS** | All verification invariants satisfied. |
| **Pillar 4: Truncation & Monotonicity** | Mathematical monotonicity & truncation bounds | **PASS** | All verification invariants satisfied. |
| **Pillar 5: Governance & Documentation** | Supervision disclaimers & empirical report | **PASS** | All verification invariants satisfied. |
| **Pillar 6: Unit Test Suite** | Regression coverage across Phases 0-4 | **PASS** | All verification invariants satisfied. |

---

## 2. Key Empirical Verification Metrics

* **Model Checkpoint:** `facebook/xlm-v-base` (SentencePiece Unigram, 901,629 vocabulary size)
* **Canonical Dataset Total:** 45,723 instances (Train: 32,019, Val: 6,852, Test: 6,852)
* **Canonical Checksum:** `b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463`
* **Canonical Subword Expansion Ratio:** 1.456x mean tokens/word (median 1.370x, p90 1.826x)
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
10:53:27 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
10:53:27 [PASS ] Workspace disk space confirmed: 20.10 GB free.
10:53:32 [PASS ] Tokenization profiler module imports cleanly.
10:53:32 [INFO ] Starting Pillar 2: Dataset Provenance & Cryptographic Binding...
10:53:32 [PASS ] Canonical dataset SHA-256 verified: b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463
10:53:32 [PASS ] Banking77 train & test SHA-256 digests verified.
10:53:32 [INFO ] Starting Pillar 3: Profile Manifests Schema & Invariant Reconciliation...
10:53:32 [PASS ] Loaded profile JSON from D:\NLP\data\manifests\tokenization_profile.json
10:53:32 [PASS ] Canonical splits perfectly reconcile to 45,723 instances.
10:53:32 [PASS ] All 16 intent classes present and reconcile exactly to 45,723 instances.
10:53:32 [PASS ] Banking77 train (10,003) and test (3,080) counts verified.
10:53:32 [PASS ] Profile CSV schema verified (21 cols, 23 rows).
10:53:32 [INFO ] Starting Pillar 4: Truncation Analysis & Monotonic Percentile Invariants...
10:53:32 [PASS ] Percentiles in normalized_overall are strictly monotonic.
10:53:32 [PASS ] Truncation rates in normalized_overall are strictly monotonic across cutoffs.
10:53:32 [PASS ] Percentiles in split_test are strictly monotonic.
10:53:32 [PASS ] Truncation rates in split_test are strictly monotonic across cutoffs.
10:53:32 [PASS ] Percentiles in split_train are strictly monotonic.
10:53:32 [PASS ] Truncation rates in split_train are strictly monotonic across cutoffs.
10:53:32 [PASS ] Percentiles in split_validation are strictly monotonic.
10:53:32 [PASS ] Truncation rates in split_validation are strictly monotonic across cutoffs.
10:53:32 [PASS ] Canonical 512-truncation rate verified: 15.96% (within [15.0%, 17.0%]).
10:53:32 [PASS ] Banking77 128-token truncation is verified at 0.00% across train and test.
10:53:32 [INFO ] Starting Pillar 5: Governance Disclaimers & Empirical Report Completeness...
10:53:32 [PASS ] Report includes CFPB Issue/Sub-issue weak administrative supervision notice.
10:53:32 [PASS ] Report includes Banking77 auxiliary benchmark classification notice.
10:53:32 [PASS ] Report includes Generalization boundary disclaimers.
10:53:32 [PASS ] Report includes Explicit model checkpoint specification.
10:53:32 [PASS ] Report includes Vocabulary size disclosure.
10:53:32 [PASS ] Report includes Exact canonical 512-token truncation rate.
10:53:32 [PASS ] Report includes Class-conditional risk breakdown for mortgage closing narratives.
10:53:32 [PASS ] Report includes Explicit subword expansion ratio analysis.
10:53:32 [INFO ] Starting Pillar 6: Unit Test Suite Execution...
10:53:51 [PASS ] All unit tests passed (63 tests executed across Phases 1-4 with 0 failures).
```
