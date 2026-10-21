# Data Preparation Methodology

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase A (Data Preparation)  
**Author:** Research Engineering Agent  
**Date:** 2026-10-22  

---

## 1. Overview & Data Provenance

The goal of Phase A is to engineer a clean, reproducible, leakage-free, and balanced complaint-intent dataset from authentic consumer complaint narratives, adhering strictly to the specifications in `DATA_PREPARATION_SPEC.md` and `SYSTEM.md`.

### Source Verification & Ingestion
- **Primary Complaint Source:** CFPB Consumer Complaint Database FOIA Reading Room Archive (`CCDB_Export_2_May_2018_through_April_2021.zip`).
  - **URL:** `https://files.consumerfinance.gov/f/documents/CCDB_Export_2_May_2018_through_April_2021.zip`
  - **License:** US Government Public Domain.
  - **Verified SHA-256 Checksum:** `4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45`
  - **Total Scanned Rows:** 1,041,632 complaints.
  - **Total Narratives in Archive:** 439,860 verified free-text narratives (42.2% narrative availability rate).
- **Auxiliary Benchmark Source:** `PolyAI/banking77` (13,083 customer service queries across 77 intents, CC BY 4.0).
  - Maintained in `data/raw/banking77/` as a distinct auxiliary query benchmark; kept strictly isolated from complaint training.

---

## 2. Ingestion & Stratified Reservoir Sampling

To counteract the severe class imbalance documented in the repository audit (where credit reporting accounts for >60% of all narratives), streaming reservoir sampling is applied across canonical financial products:

1. **Product Canonicalization:** Historical CFPB category drift (e.g. `Credit card` vs. `Credit card or prepaid card`) is resolved via `configs/product_canonical.json`, standardizing 21 raw product names into 12 canonical domains.
2. **Per-Product Reservoir Sampling:** A reservoir cap of 15,000 narratives per canonical domain is maintained during single-pass streaming of the compressed raw CSV, ensuring that smaller products (such as student loans, mortgages, checking accounts, and money transfers) maintain balanced representation against credit reporting.
3. **Word Count Filtering:** Narratives under 20 words are excluded (logged in `data/manifests/exclusion_log.csv`) because short fragments (e.g. "please call me", "dispute this") lack sufficient semantic context for intent classification.

---

## 3. Conservative Text Normalization

Per binding rules in `SYSTEM.md`, normalization is conservative and deterministic:
- **Unicode Consistency:** Standardized to NFC (Normalization Form C).
- **Whitespace Collapsing:** Internal newline sequences, tabs, and multiple spaces are collapsed into single spaces; leading/trailing whitespace is stripped.
- **Redaction Marker Normalization:** CFPB scrubs PII by inserting runs of capital X's (e.g., `XXXX`, `XXXX/XXXX/2019`, `XXXX of XXXX`). To prevent tokenizers from generating excessive repeated subword tokens while preserving the presence of redaction, any sequence matching `X{2,}` is collapsed to a single `<REDACTED>` sentinel.
- **Integrity Preservation:** Original text is preserved immutably in `text_original`, while normalized text is stored in `text_normalized`. Casing, punctuation, digits, spelling variations, and code-switching are preserved. No stopword removal, stemming, or lemmatization is applied.

---

## 4. Deduplication & MinHash LSH Grouping

Templated form letters (frequently submitted by credit-repair agencies) constitute a major source of data leakage if identical or near-identical complaints appear across different partitions.

1. **Exact Deduplication:** Each normalized narrative is hashed with SHA-256 (`text_hash`). All identical texts receive a shared exact group ID (`grp_exact_<hash>`).
2. **MinHash LSH Near-Duplicate Clustering:**
   - 5-gram word shingles are generated for each narrative (capped at 400 shingles).
   - 64 affine hash permutations with Mersenne prime $P = 2^{61}-1$ generate a 64-dimensional signature.
   - 16 bands with 4 rows each evaluate Jaccard similarity at threshold $s \approx (1/b)^{1/r} \approx (1/16)^{1/4} \approx 0.5$.
   - Near-duplicates sharing bucket keys are merged into connected components, assigning a unified `group_id`.

---

## 5. Intent Mapping & Class Balancing

- **Project Taxonomy:** 16 canonical intent classes defined in `configs/taxonomy.json` and `docs/label_taxonomy.md`.
- **Mapping Logic:** Rule-based matching against `<issue> || <sub_issue>`.
- **Auditability:** Every mapped and unmapped category is exported to `data/manifests/source_label_mapping.csv`.
- **Uniform Intent Capping:** To guarantee balanced class support and prevent class collapse in subsequent model fine-tuning, each intent class is capped at a uniform ceiling of 3,500 examples.

---

## 6. Partitioning & Leakage Prevention Policy

The canonical dataset is partitioned into in-distribution splits:
- **Train Split:** 70%
- **Validation Split:** 15%
- **Test Split:** 15%

### Invariants Enforced:
1. **Group Exclusivity:** All records sharing a `group_id` are strictly assigned to the same partition. If a credit-repair template appears 5 times, all 5 instances remain in the same partition.
2. **Zero Leakage:** $\text{Train}_{\text{groups}} \cap \text{Val}_{\text{groups}} = \emptyset$, $\text{Train}_{\text{groups}} \cap \text{Test}_{\text{groups}} = \emptyset$, $\text{Val}_{\text{groups}} \cap \text{Test}_{\text{groups}} = \emptyset$.
3. **Closed-Set Coverage:** All labels appearing in validation and test are guaranteed to have support in the training set.
4. **Reproducibility:** Partitioning is deterministic given seed 13 and documented in `data/manifests/split_indomain.csv`.
