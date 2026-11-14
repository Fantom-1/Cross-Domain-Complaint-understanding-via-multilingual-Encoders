# Comprehensive Full-Corpus Profiling Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 3 (Full-Corpus Profiling Before Filtering or Sampling)  
**Author:** Research Engineering Agent  
**Date:** 2026-11-14  
**Status:** **EMPIRICALLY VERIFIED (Developer Workstation Snapshot)**

> [!NOTE]
> **Execution Context & Verification Scope:** The comprehensive figures and tail distributions reported herein reflect empirical profiling executed on a 64-bit developer workstation (win32) directly against the full uncompressed/zipped raw FOIA archive (`CCDB_Export_2_May_2018_through_April_2021.zip`, SHA-256: `4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45`, ~55s runtime, ~140 MB peak RSS). Hosted CI runners validate committed profile manifests, schema contracts, and deterministic synthetic unit tests without re-scanning the multi-gigabyte raw archive when uncached.

---

## 1. Executive Summary

Phase 3 establishes an empirical, un-filtered, un-sampled profile of the primary reference complaint corpus (`CCDB_Export_2_May_2018_through_April_2021.zip`, 1,041,632 records) and the auxiliary query benchmark (`PolyAI/banking77`, 13,083 queries).

In accordance with `SYSTEM.md` and the *Dataset Preparation Handover*, profiling is conducted **prior to any exclusion, class capping, or reservoir sampling decisions**. This guarantees that all subsequent filtering rules (such as short-text thresholds or class balance caps) are grounded in measured population distributions rather than heuristic guesswork.

### Key Headline Findings:
1. **Total Population Traced:** 1,041,632 records across 36 calendar months (May 1, 2018 through April 30, 2021).
2. **Narrative Opt-In Rate:** 439,860 complaints contain free-text narratives (**42.23%**), while 601,772 complaints (**57.77%**) lack consumer narratives entirely.
3. **Severe Natural Class Imbalance:** In the un-capped natural population, `reporting_incorrect_information` (128,540 narratives, **29.22%**) and `reporting_investigation_dispute` (68,225 narratives, **15.51%**) comprise **44.73%** of all complaints. Conversely, `closing_process` comprises only **0.86%** (3,768 narratives).
4. **Length Distribution & Context Tail:** The median narrative length is **122 words** (675 characters). The 95th percentile is **572 words** (3,189 characters), and the 99th percentile is **1,162 words** (6,513 characters).
5. **Exact Template Duplication:** 56,822 narratives (**12.92%**) are exact textual duplicates of other complaints. The top credit-repair form template occurs **808 times** under identical text.
6. **Unique ID Integrity:** 0 duplicate complaint IDs across all 1,041,632 records (100.0% unique).

### Computational & Memory Profile:
* **Execution Architecture:** Single-pass streaming via `csv.reader` wrapping `TextIOWrapper` over zip stream (`src/data/profiler.py`).
* **Memory Footprint:** Peak RSS $\approx 140\text{ MB}$. (Retains 1,041,632 complaint IDs in `set` for duplicate ID detection, 383,038 unique SHA-256 narrative hashes in `Counter` for exact duplicate clustering, and 439,860 compact C integer array elements for exact quantile sorting. This represents an $O(N)$ retained state streaming model rather than constant $O(1)$ memory).
* **Workstation Runtime:** 54.8 seconds elapsed for all 1,041,632 records.

---

## 2. Ingestion & Temporal Date Coverage

* **Primary Archive:** `CCDB_Export_2_May_2018_through_April_2021.zip`
* **Verified SHA-256 Checksum:** `4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45`
* **Date Range:** `2018-05-01` to `2021-04-30`

### Annual Ingestion Breakdown:
| Year | Total Complaints | Narrative Complaints | Narrative Availability Rate | Dominant Product Domain |
| :---: | :---: | :---: | :---: | :--- |
| **2018 (May–Dec)** | 163,605 | 68,912 | 42.12% | `credit_reporting` (44.06%) |
| **2019** | 277,240 | 118,328 | 42.68% | `credit_reporting` (49.98%) |
| **2020** | 444,213 | 187,411 | 42.19% | `credit_reporting` (63.87%) |
| **2021 (Jan–Apr)** | 156,574 | 65,209 | 41.65% | `credit_reporting` (58.99%) |
| **Total** | **1,041,632** | **439,860** | **42.23%** | `credit_reporting` (**56.33%**) |

> [!NOTE]
> Complaint volume surged by **+60.2%** in 2020 (444,213 complaints vs. 277,240 in 2019), corresponding with the onset of the COVID-19 pandemic and economic stimulus/forbearance disruptions. The proportion of credit reporting disputes rose from 44.06% in 2018 to 63.87% in 2020.

---

## 3. Field-Level Missingness Profile

Evaluated across all 16 fields in `CFPB_FOIA_COLUMNS` for all 1,041,632 records:

| Field Name | Non-Null Count | Null Count | Null Rate (%) | Epistemological / Regulatory Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| `Date received` | 1,041,632 | 0 | **0.00%** | Mandatory bureau intake timestamp. |
| `Product` | 1,041,632 | 0 | **0.00%** | Mandatory casework routing categorization. |
| `Sub-product` | 1,041,568 | 64 | **0.01%** | Near-universal optional subcategory. |
| `Issue` | 1,041,632 | 0 | **0.00%** | Mandatory administrative issue picklist. |
| `Sub-issue` | 928,534 | 113,098 | **10.86%** | Fine-grained detail; null when issue lacks picklist children. |
| `Consumer complaint narrative` | 439,860 | 601,772 | **57.77%** | Requires explicit affirmative opt-in consent (80 FR 15572). |
| `Company public response` | 548,417 | 493,215 | **47.35%** | Optional response chose by company from pre-set list. |
| `Company` | 1,041,632 | 0 | **0.00%** | Target financial institution name. |
| `State` | 1,018,160 | 23,472 | **2.25%** | Geographic indicator; null on non-US or withheld locations. |
| `ZIP code` | 1,041,632 | 0 | **0.00%** | Redacted 5-digit or 3-digit ZIP prefix. |
| `Tags` | 119,315 | 922,317 | **88.55%** | Demographic tags: Older American (9.0%) or Servicemember (2.4%). |
| `Submitted via` | 1,041,632 | 0 | **0.00%** | Intake channel: Web (86.7%), Referral (5.6%), Phone (4.8%). |
| `Date sent to company` | 1,041,632 | 0 | **0.00%** | Routing transmission timestamp. |
| `Company response to consumer` | 1,041,632 | 0 | **0.00%** | Mandatory disposition: Closed with explanation (78.3%). |
| `Timely response?` | 1,041,632 | 0 | **0.00%** | Statutory compliance indicator: Yes (98.6%). |
| `Complaint ID` | 1,041,632 | 0 | **0.00%** | Unique primary key (0 collisions verified). |

---

## 4. Narrative Text Length Profiling & Quantiles

Length statistics for the 439,860 free-text narratives:

### 4.1 Character & Word Length Summary Statistics:
| Metric | Character Length (`len(text)`) | Word Length (`len(text.split())`) |
| :--- | :---: | :---: |
| **Minimum** | 4 chars | 1 word |
| **Maximum** | 32,394 chars | 6,014 words |
| **Mean $\pm$ Std** | **1,056.84 $\pm$ 1,385.16** | **189.33 $\pm$ 243.28** |
| **1st Percentile (p1)** | 49.0 chars | 8.0 words |
| **5th Percentile (p5)** | 118.0 chars | 21.0 words |
| **10th Percentile (p10)** | 182.0 chars | 32.0 words |
| **25th Percentile (p25)** | 359.0 chars | 64.0 words |
| **50th Percentile (Median)** | **675.0 chars** | **122.0 words** |
| **75th Percentile (p75)** | 1,256.0 chars | 226.0 words |
| **90th Percentile (p90)** | 2,211.0 chars | 398.0 words |
| **95th Percentile (p95)** | 3,189.0 chars | 572.0 words |
| **99th Percentile (p99)** | 6,513.41 chars | 1,162.41 words |

### 4.2 Cutoff Analysis & Truncation Implications:
* **Short Fragments:**
  * $< 10$ words: 5,988 records (**1.36%**) — typical fragments: *"Fraud alert"*, *"Please call me"*, *"Dispute"*.
  * $< 20$ words: 19,838 records (**4.51%**) — provides empirical justification for the Phase 0 20-word cutoff.
  * $< 50$ words: 78,550 records (**17.86%**).
* **Long Narratives & Truncation Risks:**
  * $> 500$ words: 28,239 records (**6.42%**).
  * $> 1,000$ words: 6,076 records (**1.38%**).
  * $> 2,000$ words: 991 records (**0.23%**).

> [!NOTE]
> **Subword Tokenization Deferral:** Sequence length distributions reported here reflect character and whitespace-word metrics exclusively. Exact subword token length distributions are model- and tokenizer-dependent (e.g., SentencePiece unigram for XLM-V / InfoXLM vs. BPE for RoBERTa) and are deferred to Phase 4 / Phase B tokenization pipelines using the frozen tokenizer checkpoints. Whitespace-word percentiles ($p50 = 122$, $p90 = 398$, $p95 = 572$, $p99 = 1,162$) provide lexical length baseline metrics, but do not imply exact 512-subword token coverage.

---

## 5. Text Formatting & Encoding Anomalies

Empirical inspection across all 439,860 consumer narratives:

* **Multi-Line Narratives:** 161,588 records (**36.74%**) contain embedded line breaks (`\n` or `\r\n`). Standard naive line-by-line parsers break on more than a third of the dataset, confirming the necessity of `src/data/parser.py`.
* **Redaction Markers:** 354,015 records (**80.48%**) contain runs of `XX` or `XXXX` inserted by CFPB automated de-identification filters.
* **Control Characters:** 8 records contain non-printable control characters ($< 32$, excluding tab/newline/carriage return), all of which are safely sanitized during normalization.
* **Leading/Trailing Whitespace Padding:** 0 records exhibit trailing whitespace after parsing.

---

## 6. Exact Duplication & Boilerplate Form Letters

* **Total Narratives:** 439,860
* **Unique Text Hashes (SHA-256):** 383,038
* **Exact Duplicate Narratives:** 56,822 (**12.92%** duplicate rate)

### Top Repeated Form Letter Templates:
| Rank | SHA-256 Digest Prefix | Occurrences | Domain | Template Characterization |
| :---: | :--- | :---: | :---: | :--- |
| 1 | `a6cc69e13672aa69...` | **808** | `credit_reporting` | Credit repair agency boilerplate template asserting dispute rights under FCRA § 611. |
| 2 | `253c5745239ac5f2...` | **552** | `credit_reporting` | Automated credit bureau inquiry dispute template. |
| 3 | `b1d7a77374dd98e2...` | **522** | `credit_reporting` | Pre-written identity theft affidavit dispute letter. |
| 4 | `95f49642e8b0cd07...` | **499** | `debt_collection` | Debt validation request template citing FDCPA 15 U.S.C. § 1692g. |
| 5 | `67fad14d27527047...` | **400** | `credit_reporting` | Standardized bureau late-payment removal demand letter. |

> [!WARNING]
> If exact and near duplicates are not clustered into unified group identifiers (`group_id`), identical credit repair boilerplate will inevitably contaminate train, validation, and test partitions, resulting in severe data leakage.

---

## 7. Natural Un-Capped Class Distribution

Below is the natural population distribution of consumer complaint narratives under weak administrative matching rules (`configs/taxonomy.json`), evaluated across all 439,860 narratives:

| Intent ID | Intent Label | Raw Narrative Count | Natural Share (%) | Baseline Capped Count | Capping Compression Ratio |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 0 | `reporting_incorrect_information` | **128,540** | **29.22%** | 3,000 | 42.8 : 1 |
| 1 | `reporting_investigation_dispute` | **68,225** | **15.51%** | 3,000 | 22.7 : 1 |
| 7 | `payment_problem` | 35,804 | 8.14% | 3,000 | 11.9 : 1 |
| 4 | `debt_not_owed` | 27,170 | 6.18% | 3,000 | 9.1 : 1 |
| 2 | `reporting_improper_use` | 24,124 | 5.48% | 2,062 | 11.7 : 1 |
| 6 | `debt_communication` | 22,673 | 5.15% | 3,000 | 7.6 : 1 |
| 3 | `fraud_or_scam` | 19,728 | 4.49% | 3,000 | 6.6 : 1 |
| 8 | `transaction_problem` | 18,862 | 4.29% | 3,000 | 6.3 : 1 |
| 5 | `debt_threats` | 18,489 | 4.20% | 3,000 | 6.2 : 1 |
| 11 | `account_management` | 16,444 | 3.74% | 3,000 | 5.5 : 1 |
| 14 | `credit_terms_dispute` | 14,916 | 3.39% | 3,000 | 5.0 : 1 |
| 12 | `servicing_dispute` | 13,478 | 3.06% | 3,000 | 4.5 : 1 |
| 13 | `application_problem` | 8,961 | 2.04% | 3,000 | 3.0 : 1 |
| 9 | `funds_availability` | 8,737 | 1.99% | 3,000 | 2.9 : 1 |
| 10 | `account_access` | 7,758 | 1.76% | 3,000 | 2.6 : 1 |
| 15 | `closing_process` | 3,768 | **0.86%** | 1,661 | 2.3 : 1 |
| -- | `unmapped` | 2,183 | **0.50%** | Excluded | N/A |
| **Total** | | **439,860** | **100.00%** | **45,723** | **9.6 : 1** |

---

## 8. Auxiliary Benchmark Profile (`PolyAI/banking77`)

Evaluated on `data/raw/banking77/train.csv` (10,003 rows) and `test.csv` (3,080 rows):

| Dimension | `banking77/train.csv` | `banking77/test.csv` |
| :--- | :---: | :---: |
| **Total Query Records** | 10,003 | 3,080 |
| **Number of Classes** | 77 | 77 |
| **Null Rate** | **0.00%** (0 nulls) | **0.00%** (0 nulls) |
| **Mean Character Length** | 59.48 chars | 54.23 chars |
| **Mean Word Count** | 11.95 words | 10.95 words |
| **Word Length Range (Min–Max)** | 2 – 79 words | 2 – 69 words |
| **Class Balance (Min–Max Support)** | 35 – 187 queries / class | 40 queries / class |

> [!IMPORTANT]
> The auxiliary benchmark queries average **11.95 words**, compared to **189.33 words** for CFPB complaint narratives. They represent single-turn intent questions (e.g. *"how do I transfer funds?"*), not authentic consumer complaint narratives detailing grievances and institutional disputes. They must remain strictly isolated from complaint training.

---

## 9. Conclusion & Phase 3 Audit Verdict

Phase 3 profiling confirms that the underlying population characteristics are fully documented and quantified:
* Missingness rates, multi-line prevalence, and quote rates reconcile with parser specifications.
* Natural class distributions and length tails provide clear quantitative guidance for sequence length and sampling policies in subsequent phases.
* The complete profile is versioned in [`data/manifests/source_profile.json`](file:///d:/NLP/data/manifests/source_profile.json) and [`data/manifests/source_profile.csv`](file:///d:/NLP/data/manifests/source_profile.csv).

