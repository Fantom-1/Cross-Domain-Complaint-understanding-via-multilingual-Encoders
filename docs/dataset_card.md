# Dataset Card: Canonical Consumer Complaint Intent Benchmark

**Dataset Name:** Canonical Consumer Complaint Intent Benchmark  
**Version:** 1.0.0  
**Date:** 2026-10-22  
**Curators:** Research Engineering Agent  
**Language:** English (`en`)  
**License:** US Public Domain (US Government Work)  

---

## 1. Dataset Summary

The **Canonical Consumer Complaint Intent Benchmark** is a curated, leakage-controlled, class-balanced dataset of authentic consumer complaints. The dataset is engineered from the official Consumer Financial Protection Bureau (CFPB) FOIA Reading Room Archive (`CCDB_Export_2_May_2018_through_April_2021.zip`) covering complaints filed between May 2018 and April 2021.

Unlike standard raw exports which suffer from severe category imbalance (>60% credit reporting) and pervasive credit-repair form letter leakage (~20%), this dataset applies:
1. Product-stratified reservoir sampling across 12 canonical financial domains.
2. Conservative Unicode NFC normalization and redaction marker standardization (`<REDACTED>`).
3. MinHash LSH near-duplicate clustering and group-exclusive partitioning to guarantee zero template leakage across splits.
4. Semantic mapping to a 16-class mutually exclusive consumer complaint intent taxonomy with uniform class capping.

---

## 2. Supported Tasks & Metrics

- **Primary Task:** Multi-Class Intent Classification (`text -> intent_label`).
- **Primary Evaluation Metric:** Macro-F1 (unweighted arithmetic mean of per-class F1 scores).
- **Secondary Metrics:** Accuracy, per-class Precision/Recall/F1, Confusion Matrix, and intra-financial domain transfer breakdown.

---

## 3. Dataset Structure

### Canonical Schema (Parquet)

| Field Name | Type | Description |
|---|---|---|
| `example_id` | string | Stable unique identifier (`cfpb_<Complaint ID>`). |
| `text_original` | string | Unaltered, raw consumer complaint narrative as submitted. |
| `text_normalized` | string | NFC normalized text with safe whitespace and `<REDACTED>` tokens. |
| `intent_label` | string | Canonical intent class (one of 16 project labels). |
| `intent_id` | int64 | Numerical class index (0 to 15). |
| `source_label` | string | Original CFPB `Issue // Sub-issue`. |
| `parent_label` | string | Original CFPB `Product` category. |
| `domain` | string | Canonical financial domain (e.g. `credit_reporting`, `debt_collection`, `mortgage`, `bank_account`). |
| `language_condition` | string | Language identifier (`en`). |
| `source_dataset` | string | Ingestion source identifier. |
| `source_version` | string | Source release/export snapshot version. |
| `source_id` | string | Original CFPB Complaint ID. |
| `group_id` | string | Cluster identifier grouping exact and near-duplicate narratives. |
| `split` | string | Assigned partition (`train`, `validation`, `test`). |
| `mapping_status` | string | Mapping audit flag (`mapped`). |
| `exclusion_reason` | string | Reason for exclusion, or `none` for retained records. |
| `source_file_sha256` | string | SHA-256 hash of the immutable source archive. |
| `text_hash` | string | SHA-256 hash of `text_normalized`. |

### Training CSV Schema (`baseline_train.csv`, `baseline_validation.csv`, `baseline_test.csv`)

| Field | Description |
|---|---|
| `example_id` | Unique identifier. |
| `text` | Normalized complaint text (`text_normalized`). |
| `label` | Target intent label (`intent_label`). |
| `intent_id` | Numerical label ID (0 to 15). |
| `domain` | Canonical financial product domain. |
| `language_condition` | Language condition (`en`). |
| `source_dataset` | Ingestion source name. |
| `group_id` | Group identifier for leakage-free evaluation. |

---

## 4. Ingestion & Preprocessing Details

### Redaction & PII Handling
CFPB scrubs direct personal identifiable information (PII) such as account numbers, phone numbers, dollar amounts, and personal names by substituting sequences of uppercase `X`s (e.g., `XXXX/XXXX/2019`, `XXXX of XXXX`). These runs are collapsed into a single `<REDACTED>` sentinel. This prevents language model tokenizers from producing degenerate subword sequences while preserving redaction context.

### Deduplication Policy
Form letters and repeated dispute templates submitted by credit repair agencies share high textual similarity with slight variations in dates or account numbers. MinHash LSH (64 permutations, 16 bands, 5-word shingles) clusters these near-duplicates into unified `group_id` partitions. The group-stratified split guarantees that no group spans across training, validation, or test sets.

---

## 5. Intent Taxonomy (16 Classes)

| ID | Class Label | Core Semantics |
|---|---|---|
| 0 | `reporting_incorrect_information` | Inaccurate, obsolete, or incorrect account reporting on credit files. |
| 1 | `reporting_investigation_dispute` | Procedural failure or delay in investigating previously filed credit disputes. |
| 2 | `reporting_improper_use` | Impermissible inquiry, unauthorized credit access, or identity monitoring failure. |
| 3 | `fraud_or_scam` | Unauthorized transactions, stolen credentials, and fraud alert mishandling. |
| 4 | `debt_not_owed` | Collection attempts for debts not owed, previously paid, or discharged. |
| 5 | `debt_threats` | Harassment, illegal legal threats, and abusive debt collection behavior. |
| 6 | `debt_communication` | Improper timing, frequency, or failure to provide debt verification notices. |
| 7 | `payment_problem` | Lenders failing to credit payments, improper fee allocation, or autopay errors. |
| 8 | `transaction_problem` | Merchant statement discrepancies, unauthorized card charges, point-of-sale errors. |
| 9 | `funds_availability` | Delayed deposit availability, unexpected account holds, or mobile wallet withdrawal freezes. |
| 10 | `account_access` | Denial of online portal access, locked login credentials, sudden account closure. |
| 11 | `account_management` | Administrative friction in opening, modifying, or maintaining ongoing account terms. |
| 12 | `servicing_dispute` | Escrow miscalculations, customer service failures, payoff quote delays, repossession. |
| 13 | `application_problem` | Misrepresentation, origination fee disputes, or processing delays during loan application. |
| 14 | `credit_terms_dispute` | Objections to arbitrary credit line reductions, APR interest rate hikes, or misleading terms. |
| 15 | `closing_process` | Settlement disclosures, unexpected closing costs, and mortgage closing delays. |

---

## 6. Known Limitations & Biases

1. **Selection Bias:** CFPB complaints are voluntary, self-reported consumer grievances. They do not represent a random sample of all consumer financial interactions or consumer demographics.
2. **Opt-in Narratives:** Only a fraction of consumers (~42%) opt-in to publishing their free-text narratives publicly.
3. **No Validity / Resolution Causality:** The intent label reflects the *consumer's stated issue*. It does not judge whether the consumer or company is legally at fault, nor does it predict resolution outcome.
4. **Language & Domain Scope:** This canonical benchmark is strictly English (`en`) within the financial sector. Claims of multilingual complaint performance (e.g. Hindi/Hinglish) cannot be made from this dataset alone without dedicated, human-annotated Indic complaint narratives.
