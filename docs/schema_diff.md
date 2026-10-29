# Comprehensive Schema Diff, Null Rates, and Parsing Diagnostics

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 2 (Robust Parsing & Schema Diff)  
**Document:** Schema Diff & Parsing Invariant Audit  
**Date:** 2026-10-29  

---

## 1. Executive Summary

This document provides a comparative schema diff across all ingested data formats (CFPB FOIA Reading Room archives, CFPB active daily bulk exports, and auxiliary `PolyAI/banking77` benchmarks). It documents empirical null rates measured across 19,615,623 total raw records, details the critical August 14, 2026 schema shift, and specifies the streaming parser architecture designed to handle multi-line text and platform-specific overflow constraints.

---

## 2. Comparative Schema Architecture Matrix

The table below contrasts the 16-column FOIA Reading Room schema against the 15-column active bulk export schema and the 2-column auxiliary query benchmark. All null percentages are measured empirically from full-file streaming scans.

| Column Index | Field Name | CFPB FOIA Archives (`CCDB_Export_1`–`21`) | CFPB Active Bulk (`complaints.csv.zip`) | PolyAI / banking77 (`train.csv` / `test.csv`) | Null Rate in Baseline Export 2 (1,041,632 rows) | Null Rate in Active Bulk (18,560,908 rows) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `Date received` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 2 | `Product` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 3 | `Sub-product` | Present | Present | Absent | 0.01% (64) | 1.27% (235,275) |
| 4 | `Issue` | Present | Present | Absent | 0.00% (0) | 0.00% (6) |
| 5 | `Sub-issue` | Present | Present | Absent | 10.86% (113,098) | 5.08% (943,559) |
| 6 | **`Consumer complaint narrative`** | **Present** | **ABSENT (DROPPED)** | Absent | 57.77% (601,772) | **100.00% (N/A)** |
| 7 | `Company public response` | Present | Present | Absent | 47.35% (493,215) | 44.87% (8,327,693) |
| 8 | `Company` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 9 | `State` | Present | Present | Absent | 2.25% (23,472) | 0.34% (63,399) |
| 10 | `ZIP code` | Present | Present | Absent | 0.00% (0) | 0.02% (3,227) |
| 11 | `Tags` | Present | Present | Absent | 88.55% (922,317) | 95.56% (17,736,737) |
| 12 | `Submitted via` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 13 | `Date sent to company` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 14 | `Company response to consumer` | Present | Present | Absent | 0.00% (0) | 0.00% (21) |
| 15 | `Timely response?` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| 16 | `Complaint ID` | Present | Present | Absent | 0.00% (0) | 0.00% (0) |
| -- | `text` | Absent | Absent | **Present** | N/A | N/A (0.00% in 13,083 rows) |
| -- | `category` | Absent | Absent | **Present** | N/A | N/A (0.00% in 13,083 rows) |

---

## 3. Structural Findings & Schema Discrepancies

### 3.1 The August 14, 2026 Narrative Deprecation
* **Observation:** The CFPB ceased public publication of newly submitted consumer complaint narratives on August 14, 2026.
* **Schema Consequence:** The active bulk feed `complaints.csv.zip` dropped column 6 (`Consumer complaint narrative`) entirely. Consequently, rows in `complaints.csv` have 15 columns rather than 16 columns.
* **Downstream Research Guardrail:** The active bulk export is formally ineligible for text-based NLP classification models. The 21 static FOIA Reading Room archives remain the exclusive authoritative source for authentic consumer narrative text.

### 3.2 High-Cardinality Field Variations
* **Tags ($88.55\%$ to $95.56\%$ null):** Only populated when a consumer qualifies for special demographic protections (`Older American`, `Servicemember`). Null is not missing data; it signifies general public submission.
* **Sub-Issue ($5.08\%$ to $10.86\%$ null):** Many administrative categories do not offer sub-issue picklists, or consumers bypass optional granular categorization. Mappings must handle empty strings cleanly by falling back to `Issue`.

---

## 4. Parser Architecture & Edge-Case Engineering

To guarantee deterministic, leak-free, and crash-resistant ingestion across multi-gigabyte archives, `src/data/parser.py` implements four core safeguards:

### 4.1 Multi-Line Narrative Handling (36.74% of Narratives)
In `CCDB_Export_2`, **161,588 out of 439,860 narratives (36.74%)** contain internal newline sequences (`\r`, `\n`).
* **Vulnerability:** Naive line-oriented parsers (e.g. `line.split(",")` or iterating lines with a basic loop) treat each paragraph as a new record, corrupting over 160,000 complaints and throwing subsequent field mappings out of alignment.
* **Implementation:** The streaming parser utilizes Python's standard `csv.reader` over an `io.TextIOWrapper` stream configured with `newline=""`. This properly preserves multi-line RFC 4180 CSV strings within single yielded record dictionaries.

### 4.2 Embedded Quotations & Comma Delimiters (11.97% of Narratives)
In `CCDB_Export_2`, **52,641 narratives (11.97%)** contain internal quotation marks and escaped quotes (`""`).
* **Implementation:** Standard quote-doubling parsing rules are strictly enforced. Internal commas, punctuation, and escaped quotation marks are parsed as literal text without splitting record cells.

### 4.3 Platform-Specific `csv.field_size_limit` Overflow on Windows
* **Vulnerability:** On 64-bit Linux/macOS, Python integers up to 64-bit fit in C `long` (`sys.maxsize = 9,223,372,036,854,775,807`). However, on 64-bit Windows, the MSVC LLP64 data model defines C `long` as **32-bit** (maximum value $2^{31}-1 = 2{,}147{,}483{,}647$).
* Calling `csv.field_size_limit(sys.maxsize)` on Windows crashes immediately with:
  ```
  OverflowError: Python int too large to convert to C long
  ```
* **Implementation:** `src/data/parser.py` enforces a portable ceiling:
  ```python
  SAFE_FIELD_SIZE_LIMIT = min(sys.maxsize, 2147483647)
  csv.field_size_limit(SAFE_FIELD_SIZE_LIMIT)
  ```
  This accommodates massive consumer narratives while guaranteeing seamless execution across Windows, Linux (CI), and macOS.

### 4.4 Constant-Memory Streaming
* Loading `CCDB_Export_2` (1.1 GB uncompressed) or `complaints.csv` (5.6 GB uncompressed) directly into Pandas via `pd.read_csv()` requires 4–12 GB of contiguous RAM, violating storage and memory budgets.
* `stream_complaints()` reads directly from the compressed `.zip` stream via `io.TextIOWrapper`, maintaining $\mathcal{O}(1)$ memory consumption throughout ingestion.

---

## 5. Empirical Parsing Quality & Diagnostic Audit

Full empirical scans were executed across all available local datasets using `src/data/parser.py`. The results are recorded in [`data/manifests/parse_errors.csv`](file:///d:/NLP/data/manifests/parse_errors.csv):

| Archive Scanned | Target File | Total Records | Valid Records | Parse Errors | Multiline Narratives | Quoted Narratives | Parse Error Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CCDB_Export_2_May_2018_through_April_2021.zip` | `CCDB_Export_2_May_2018_through_April_2021.csv` | 1,041,632 | 1,041,632 | 0 | 161,588 | 52,641 | **0.00%** |
| `complaints.csv.zip` | `complaints.csv` | 18,560,908 | 18,560,908 | 0 | 0 (narrative dropped) | 0 | **0.00%** |
| `banking77` | `train.csv` | 10,003 | 10,003 | 0 | 0 | 0 | **0.00%** |
| `banking77` | `test.csv` | 3,080 | 3,080 | 0 | 0 | 0 | **0.00%** |
| **Total Empirical Validation** | -- | **19,615,623** | **19,615,623** | **0** | **161,588** | **52,641** | **0.00%** |

> [!NOTE]
> All 19,615,623 scanned records across all files parsed with **zero column count mismatches, zero unescaped delimiter errors, and zero decoding crashes**.
