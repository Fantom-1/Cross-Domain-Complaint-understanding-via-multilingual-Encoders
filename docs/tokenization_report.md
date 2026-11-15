# Comprehensive Subword Tokenization Profiling & Truncation Analysis Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 4 (Subword Tokenization Profiling)  
**Author:** Research Engineering Agent  
**Date:** 2026-11-15  
**Status:** **EMPIRICALLY VERIFIED (Developer Workstation Snapshot)**  

> [!IMPORTANT]
> **Governance & Scope Boundary Notice:**
> 1. **Weak Administrative Supervision:** CFPB Issue and Sub-issue categories are recorded as administrative routing designations by financial institutions and regulators, not ground-truth semantic intent labels. They serve as weak supervision signals and must be evaluated with appropriate calibration.
> 2. **Auxiliary Benchmark Status:** The `PolyAI/banking77` dataset is incorporated strictly as an auxiliary cross-dataset intent classification benchmark. It does not constitute a held-out evaluation of cross-domain complaint generalization.
> 3. **Generalization Scope:** No claims of multilingual or held-out cross-domain generalization are substantiated by the findings in this phase.
> 4. **Metric Isolation:** Subword token length distributions reported here reflect the frozen SentencePiece tokenizer (`facebook/xlm-v-base`) and are strictly distinguished from lexical whitespace-word counts reported in Phase 3.

---

## 1. Executive Summary

Phase 4 establishes an empirical subword tokenization profile of the frozen canonical complaint dataset (`canonical_dataset.parquet`, 45,723 instances) and the auxiliary intent benchmark (`PolyAI/banking77`, 13,083 queries).

While Phase 3 profiled character and whitespace-word distributions, modern transformer architectures process text through subword tokenization vocabularies. Subword expansion ratios, boundary segmentation, and sequence truncation behavior dictate model capacity, memory consumption ($O(L^2)$ attention complexity), and information loss.

### Key Headline Findings:

1. **Frozen Tokenizer Properties:**
   * Model Checkpoint: `facebook/xlm-v-base`
   * Tokenizer Architecture: SentencePiece Unigram model with byte fallback (`XLMRobertaTokenizer`)
   * Vocabulary Size: **901,629 tokens** (multilingual coverage across 100+ languages)
2. **Subword Expansion Ratio:**
   * On normalized English complaint narratives, the mean subword expansion ratio is **1.456 tokens per whitespace word** (median $1.370\times$, 90th percentile $1.826\times$).
   * For the un-normalized narratives, the expansion ratio is $1.244\times$. The `<REDACTED>` sentinel normalization maps variable-length sequences of PII redactions (`X{2,}`) into a 5-subword token sequence (`[' <', 'RED', 'ACTE', 'D', '>']`), preventing vocabulary explosion from arbitrary alphanumeric masking while preserving structural privacy signals.
3. **Severe Truncation Risk at Standard Context Windows:**
   * At the standard transformer maximum sequence length of **512 tokens**, **15.96% of complaints (7,298 out of 45,723) are truncated**.
   * At a **256-token context window**, **42.34% of complaints (19,360 out of 45,723) are truncated**.
   * At a **128-token context window**, **72.27% of complaints (33,042 out of 45,723) are truncated**.
   * This proves empirically that lexical whitespace word counts significantly underestimate token sequence length: while the 90th percentile of whitespace words is 457 words, subword expansion pushes the **90th percentile of token length to 665 tokens**, extending well beyond the standard 512-token limit.
4. **Split Invariance:**
   * Token length distributions across splits are virtually identical:
     - `train` ($N=32,019$): Median = 216 tokens, p90 = 668 tokens, 512-truncation = **15.99%**
     - `validation` ($N=6,852$): Median = 220 tokens, p90 = 665 tokens, 512-truncation = **16.46%**
     - `test` ($N=6,852$): Median = 219 tokens, p90 = 649 tokens, 512-truncation = **15.34%**
   * This confirms that the stratified splitting methodology from Phase 1/2 introduced zero length or truncation bias across partitions.
5. **Class-Conditional Truncation Skew:**
   * **Highest Truncation Risk:** `closing_process` complaints exhibit a median of **338 tokens**, a 90th percentile of **1,065 tokens**, and a **30.89% truncation rate at 512 tokens** (nearly 1 in 3 complaints truncated).
   * **Lowest Truncation Risk:** `debt_communication` exhibits a median of **154 tokens**, a 90th percentile of **462 tokens**, and only an **8.07% truncation rate at 512 tokens**.
   * Highly technical, document-heavy disputes (`application_problem`, `payment_problem`, `closing_process`) carry disproportionate information loss under standard head truncation.
6. **Auxiliary Domain Discontinuity (`PolyAI/banking77`):**
   * Banking77 queries average **15.97 tokens** (train, max 98) and **14.82 tokens** (test, max 80).
   * **0.00% of Banking77 queries are truncated at 128 tokens** (100.00% coverage).
   * This empirically demonstrates the radical domain and structural divergence between short, single-sentence conversational utterances and long, multi-paragraph legalistic consumer complaints.

---

## 2. Tokenizer Architecture & Environment Setup

All tokenization metrics were empirically computed using the frozen baseline encoder checkpoint:

* **Tokenizer Checkpoint:** `facebook/xlm-v-base`
* **Library Version:** HuggingFace `transformers 5.21.0`
* **Algorithm:** SentencePiece Unigram Language Model
* **Vocabulary Dimension:** 901,629 tokens
* **Special Tokens:**
  * `<s>` (id: 1, Beginning of Sequence)
  * `</s>` (id: 2, End of Sequence / Delimiter)
  * `<unk>` (id: 3, Unknown Token)
  * `<pad>` (id: 0, Padding Token)
  * `<mask>` (id: 901628, Masking Token)
* **Special Token Overhead:** Exactly 2 tokens added per sequence (`<s> ... </s>`).
* **Workstation Ingestion Throughput:** ~4,500 texts/sec under multi-threaded Python execution.

---

## 3. Canonical Dataset Token Length Distribution

Evaluated on `data/processed/canonical_dataset.parquet` (SHA-256: `b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463`, $N=45,723$):

### 3.1 Distributional Summary Across Partitions:

| Partition | Instances | Min | P25 | P50 (Median) | P75 | P90 | P95 | P99 | Max | Mean | Std Dev |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall (Normalized)** | 45,723 | 22 | 119.0 | 217.0 | 389.0 | 665.0 | 931.0 | 1,764.1 | 12,673 | 323.75 | 394.82 |
| **Overall (Original)** | 45,723 | 22 | 104.0 | 188.0 | 333.0 | 561.0 | 789.0 | 1,499.6 | 8,049 | 276.76 | 328.30 |
| **Train Partition** | 32,019 | 22 | 119.0 | 216.0 | 388.0 | 668.0 | 944.0 | 1,801.9 | 12,673 | 325.02 | 405.79 |
| **Validation Partition**| 6,852 | 22 | 118.0 | 220.0 | 398.0 | 664.9 | 924.0 | 1,776.5 | 8,184 | 325.87 | 400.78 |
| **Test Partition** | 6,852 | 22 | 121.0 | 219.0 | 390.0 | 648.8 | 895.4 | 1,619.0 | 4,187 | 315.69 | 331.68 |

> [!NOTE]
> The split partitions exhibit statistically indistinguishable token length quantiles. The median sequence length across all three partitions varies by at most 4 tokens (216 to 220 tokens), and the 90th percentile varies by less than 20 tokens (648.8 to 668.0 tokens).

---

## 4. Context Window Truncation Analysis

In standard sequence classification setups, texts exceeding the maximum context window $L_{max}$ are truncated (typically using head truncation, retaining the first $L_{max}-2$ tokens plus special tokens `<s>` and `</s>`).

The table below details the exact empirical truncation rates across sequence length cutoffs $L \in \{128, 256, 384, 512\}$:

### 4.1 Canonical Dataset Truncation Coverage ($N = 45,723$):

| Cutoff ($L$) | Truncated Instances | Truncation Rate (%) | Retained Coverage (%) | Token Volume Retained (%) | Primary Information Loss Implication |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **128** | 33,042 | **72.27%** | **27.73%** | 35.44% | **Catastrophic Truncation:** Nearly 3 out of 4 complaints lose their core narrative context, resolution demands, and concluding evidence. |
| **256** | 19,360 | **42.34%** | **57.66%** | 57.61% | **High Truncation:** Over 42% of complaints truncated; fine-grained details of multi-party financial disputes discarded. |
| **384** | 11,655 | **25.49%** | **74.51%** | 70.71% | **Moderate Truncation:** 1 in 4 complaints truncated; captures 70.7% of total token volume. |
| **512** | 7,298 | **15.96%** | **84.04%** | 78.77% | **Standard Baseline Limit:** Retains 84.04% of complete narratives and 78.77% of total token volume; 15.96% truncated. |

### 4.2 Truncation Rates Across Partitions:

| Cutoff | Train Truncated (%) | Validation Truncated (%) | Test Truncated (%) |
| :---: | :---: | :---: | :---: |
| **128 tokens** | 72.18% | 72.12% | 72.81% |
| **256 tokens** | 42.03% | 43.18% | 42.98% |
| **384 tokens** | 25.31% | 26.23% | 25.58% |
| **512 tokens** | **15.99%** | **16.46%** | **15.34%** |

---

## 5. Subword Expansion & Lexical Comparison

### 5.1 Subword Expansion Ratio ($Tokens / Words$):

For each complaint narrative, the subword expansion ratio is defined as:
$$\rho = \frac{\text{len}(\text{input\_ids})}{\max(\text{len}(\text{text.split()}), 1)}$$

* **Mean Expansion Ratio:** **1.456 tokens/word**
* **Median Expansion Ratio:** **1.370 tokens/word**
* **90th Percentile Expansion:** **1.826 tokens/word**
* **Minimum Expansion:** 1.050 tokens/word
* **Maximum Expansion:** 4.120 tokens/word (observed in documents containing unformatted account strings, legal citations, and dollar amount tables).

### 5.2 Redaction Marker Impact:

* In `text_original`, redaction runs appear as un-normalized strings of uppercase `X` (e.g. `XXXX`, `XXXX/XXXX/2019`). XLM-V SentencePiece tokenizes `XXXX` into repetitive `X` subword units.
* In `text_normalized`, runs of `X{2,}` are collapsed into `<REDACTED>`.
* SentencePiece tokenizes `<REDACTED>` into 5 tokens:
  `[' <', 'RED', 'ACTE', 'D', '>']` (IDs: `[3322, 51458, 891792, 234, 2009]`).
* While `<REDACTED>` increases token length slightly over a bare 4-character `XXXX`, it **standardizes privacy boundaries** and prevents the tokenizer from encountering unbounded out-of-vocabulary runs of masked digits.

---

## 6. Class-Conditional Subword Profiling

The table below breaks down subword sequence length and truncation exposure across all 16 intent classes in the taxonomy:

| Intent Class | Support | Mean Tokens | P50 (Med) | P90 | Mean Words | Tokens/Word Ratio | Truncation @ 512 (%) | Truncation @ 256 (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 3,000 | 318.09 | 222.0 | 634.2 | 233.2 | 1.374 | 15.17% | 42.57% |
| `account_management` | 3,000 | 357.97 | 257.0 | 718.6 | 252.5 | 1.426 | 18.33% | 50.20% |
| `application_problem` | 3,000 | 396.37 | 269.0 | 820.2 | 282.8 | 1.407 | 22.50% | 51.70% |
| `closing_process` | 1,661 | 517.32 | 338.0 | 1,065.0 | 354.0 | 1.473 | **30.89%** | **64.18%** |
| `credit_terms_dispute`| 3,000 | 324.04 | 245.5 | 632.1 | 231.8 | 1.410 | 14.93% | 47.43% |
| `debt_communication` | 3,000 | 244.10 | 154.0 | 462.0 | 174.6 | 1.413 | **8.07%** | **28.07%** |
| `debt_not_owed` | 3,000 | 243.24 | 171.5 | 496.0 | 168.3 | 1.477 | 9.17% | 32.07% |
| `debt_threats` | 3,000 | 321.31 | 212.0 | 639.0 | 221.9 | 1.464 | 15.23% | 41.37% |
| `fraud_or_scam` | 3,000 | 326.36 | 206.0 | 663.0 | 225.4 | 1.466 | 16.87% | 40.63% |
| `funds_availability` | 3,000 | 324.45 | 220.0 | 652.0 | 234.4 | 1.390 | 15.97% | 43.47% |
| `payment_problem` | 3,000 | 400.17 | 275.0 | 832.2 | 276.9 | 1.442 | 22.50% | 53.60% |
| `reporting_improper_use` | 2,062 | 248.04 | 155.0 | 511.9 | 150.8 | **1.676** | 9.99% | 28.56% |
| `reporting_incorrect_information` | 3,000 | 261.14 | 163.0 | 550.1 | 167.0 | **1.608** | 11.47% | 30.00% |
| `reporting_investigation_dispute` | 3,000 | 231.38 | 150.0 | 485.2 | 159.2 | 1.465 | 8.97% | 26.73% |
| `servicing_dispute` | 3,000 | 364.78 | 258.0 | 721.1 | 255.4 | 1.421 | 19.80% | 50.50% |
| `transaction_problem`| 3,000 | 363.95 | 264.0 | 718.0 | 251.8 | 1.460 | 20.33% | 51.83% |

### Key Class-Specific Observations:

1. **Mortgage Closing Narratives:** `closing_process` is significantly longer than any other category ($p50=338$, $p90=1,065$). More than **30.8% of closing complaints exceed 512 tokens**. Mortgage escrows, deed transfers, and closing disclosures require extensive factual exposition by consumers.
2. **Credit Reporting Subword Explosion:** `reporting_improper_use` and `reporting_incorrect_information` exhibit the highest subword expansion ratios ($1.676$ and $1.608$ tokens/word). This is driven by dense sequences of credit bureau identifiers (Equifax, Experian, TransUnion), account numbers, dates, and balance figures.
3. **Debt Collection Brevity:** `debt_communication`, `debt_not_owed`, and `reporting_investigation_dispute` have median lengths between 150 and 172 tokens, with under 10% truncation at 512 tokens.

---

## 7. Auxiliary Benchmark Profiling (`PolyAI/banking77`)

Evaluated on `data/raw/banking77/train.csv` (SHA-256: `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`) and `data/raw/banking77/test.csv` (SHA-256: `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`):

| Partition | Instances | Min | P25 | P50 (Median) | P75 | P90 | P95 | P99 | Max | Mean | Std Dev | Truncation @ 128 (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Banking77 Train** | 10,003 | 4 | 11.0 | 13.0 | 17.0 | 27.0 | 36.0 | 52.0 | 98 | 15.97 | 9.18 | **0.00%** |
| **Banking77 Test** | 3,080 | 4 | 10.0 | 13.0 | 16.0 | 23.0 | 31.0 | 46.2 | 80 | 14.82 | 7.84 | **0.00%** |

### Structural Comparison: CFPB Complaints vs. Banking77 Queries:

```
CFPB Complaints (Normalized):
[=========================================================================>] (Mean: 323.8 tokens, P90: 665.0, Max: 12,673)
Truncation @ 512: 15.96% | Truncation @ 128: 72.27%

Banking77 Queries:
[===>] (Mean: 15.97 tokens, P90: 27.0, Max: 98)
Truncation @ 512: 0.00%  | Truncation @ 128: 0.00%
```

> [!WARNING]
> This extreme structural divergence underlines why Banking77 must be treated **strictly as an auxiliary intent classification benchmark**. Transferring or adapting representations learned on short dialogue utterances to multi-paragraph complaint narratives entails a profound distributional shift in sequence length, syntax, syntactic complexity, and vocabulary density.

---

## 8. Downstream Modeling Recommendations

Based on these empirical findings, subsequent modeling phases must account for:

1. **Context Window Configuration:**
   * Setting $L_{max} = 512$ provides **84.04% full-narrative coverage** and retains **78.77% of total token volume**.
   * Setting $L_{max} = 256$ cuts sequence length and quadratic attention cost by $4\times$, but **truncates 42.34% of complaints**.
   * Setting $L_{max} = 128$ is **unacceptable for CFPB complaints**, truncating over 72% of narratives.
2. **Truncation Strategy:**
   * Standard head truncation retains narrative background and opening facts, but discards concluding demands, regulatory assertions, and institutional dispute outcomes.
   * A head-tail truncation strategy (e.g. first 384 tokens + last 126 tokens + special tokens) should be explored in downstream phases to capture both introductory complaint context and final dispute resolution requests.
3. **Class-Aware Evaluation:**
   * Because `closing_process` has a 30.89% truncation rate at 512 tokens, evaluation metrics should monitor class-conditional performance as a function of narrative length to identify whether long-document categories suffer disproportionately from truncation.

---

## 9. Manifest & Provenance Reference

* **Full Profile Manifest:** `data/manifests/tokenization_profile.json`
* **Tabular Summary Manifest:** `data/manifests/tokenization_profile.csv`
* **Source Parquet Digest:** `b591ba980a99ba820ec8e42676cba75afa0ee2222725e1917ea8d94036e0c463`
* **Banking77 Train Digest:** `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`
* **Banking77 Test Digest:** `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`
* **Automated Audit Script:** `scripts/audit_phase4.py`
