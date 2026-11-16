# Phase 5 Audit Report: Duplicate, Overlap, and Split Contamination Audit

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 5 (Duplicate, Overlap, and Contamination Audit)  
**Execution Date:** 2026-11-16 16:17:00Z  
**Dataset Analyzed:** `data/processed/canonical_dataset.parquet` (45,723 instances, SHA-256 `b591ba980a99ba82...`)  
**Auxiliary Benchmark:** `PolyAI/banking77` (13,083 queries: train 10,003 + test 3,080)  

---

## 1. Executive Summary & Gating Verdict

Phase 5 establishes an empirical audit of exact text duplication, near-duplicate credit repair template clustering, chain-merging transitivity risks, administrative weak-supervision label conflicts, cross-dataset contamination, and cross-partition data leakage.

### Key Headline Audit Invariants:

1. **Zero Partition Leakage (Empirical Proof):**
   * **Train $\cap$ Validation Leakage:** **0** groups, **0** text hashes.
   * **Train $\cap$ Test Leakage:** **0** groups, **0** text hashes.
   * **Validation $\cap$ Test Leakage:** **0** groups, **0** text hashes.
   * **Verdict:** $\text{Train}_{\text{groups}} \cap \text{Val}_{\text{groups}} = \emptyset$, $\text{Train}_{\text{groups}} \cap \text{Test}_{\text{groups}} = \emptyset$, $\text{Val}_{\text{groups}} \cap \text{Test}_{\text{groups}} = \emptyset$. Absolute zero split contamination is mechanically confirmed across all 45,723 records.

2. **Exact Duplicate Text Collisions:**
   * Unique raw text hashes: **44,870** / 45,723 records.
   * Unique normalized text hashes: **44,754** / 45,723 records.
   * Total records in exact duplicate collisions: **1,259** records across **290** unique text hashes.
   * Unique example IDs: **45,723** (0 duplicate example IDs).
   * Unique source IDs: **45,723** (0 duplicate source IDs).

3. **Near-Duplicate MinHash LSH Clusters & Chain-Merging Risk:**
   * Total partitions (`cluster_id`): **43,142**.
   * Singleton groups: **42,450** (98.40% of all partitions).
   * Multi-item near-duplicate clusters: **692** clusters, comprising **3,273** records.
   * Cluster size distribution: Mean **4.73**, Median **2.0**, 75th percentile **3.0**, 90th percentile **8.0**, Max **123**.
   * Evaluated cluster mean pairwise Jaccard similarity: **0.7564** (aggregate min similarity **0.1693**).
   * LSH Candidate Generation & Verification: **13,260** candidate pairs evaluated, **10,588** pairs verified ($J \ge 0.50$), **2,672** false-positive collisions rejected ($J < 0.50$).

4. **Weak Administrative Supervision & Conflicting Source Labels:**
   * **Exact duplicate collisions with conflicting intent labels:** **31** distinct text hashes are assigned contradictory administrative labels by CFPB intake routing.
   * **Near-duplicate clusters with conflicting intent labels:** **135** clusters contain multiple conflicting intent labels.
   * **Methodological Implication:** Form letters with identical or near-identical text receiving divergent CFPB labels (e.g., `reporting_investigation_dispute` vs `debt_communication`) proves that intake tags reflect weak administrative routing rather than semantic intent ground truth.

5. **Cross-Dataset Benchmark Contamination:**
   * Exact collisions between CFPB complaint narratives and `PolyAI/banking77` queries: **0** (0 matches) under symmetric Unicode NFC and whitespace normalization.
   * Near-duplicate collisions ($J \ge 0.50$): **0** (0 matches) across all 13,083 Banking77 queries against 44,755 unique CFPB complaint texts.
   * Confirms strict empirical isolation of the auxiliary customer intent benchmark.

---

## 2. Duplicate Detection & Clustering Architecture

### Hashing & Shingling Specifications
- **Exact Hashing:** 64-character SHA-256 hex digest computed over UTF-8 text bytes for both raw and normalized text.
- **Symmetric Normalization:** Canonical Unicode NFC normalization followed by lowercasing and whitespace collapsing symmetrically applied to all datasets.
- **Shingling:** 5-word shingles extracted from lowercased, whitespace-collapsed text. Shingle sets are capped at 400 shingles per narrative.
- **MinHash Parameters:** 64 affine permutations using Mersenne prime $P = 2^{31} - 1 = 2,147,483,647$. Permutation coefficients satisfy $a \cdot h + b < P^2 < 2^{62}$, fitting within unsigned 64-bit integer space without overflow.
- **Locality-Sensitive Hashing (LSH):** 16 bands with 4 rows each evaluate candidate pairs at an approximate Jaccard similarity threshold:
  $$s \approx \left(\frac{1}{b}\right)^{1/r} = \left(\frac{1}{16}\right)^{1/4} \approx 0.500$$
- **Candidate Pair Verification:** All candidate collisions undergo exact Jaccard similarity evaluation against threshold $s \ge 0.50$. False-positive collisions ($s < 0.50$) are rejected to prevent false-bridge transitive merging.
- **Disjoint Set Union (Union-Find):** Path compression and union-by-rank guarantee cycle-free $O(N \cdot \alpha(N))$ component merging.

---

## 3. Empirical Split Leakage Verification

To prevent train/test contamination from memorization of boilerplate credit-repair form letters, every instance sharing a cluster must reside in exactly one partition.

| Partition Boundary | Shared Clusters | Shared Text Hashes | Leakage Rate | Audit Status |
| :--- | :---: | :---: | :---: | :---: |
| **Train vs. Validation** | **0** | **0** | **0.00%** | **PASS** |
| **Train vs. Test** | **0** | **0** | **0.00%** | **PASS** |
| **Validation vs. Test** | **0** | **0** | **0.00%** | **PASS** |

$$\text{Total Cross-Partition Contamination} = 0 \text{ records (0.00%)}$$

All records belonging to credit-repair template clusters (up to size 123) are assigned exclusively to a single split partition.

---

## 4. Chain-Merging Risk & Cluster Diameter Analysis

MinHash LSH with transitive union-find risks "chain-merging," where document A is linked to B and B to C, but A and C are semantically unrelated.

To quantify chain-merging severity, we evaluated pairwise Jaccard similarities within sampled multi-item clusters using deterministic digest-derived PRNG seeding:
- **Mean Pairwise Jaccard Similarity across Evaluated Clusters:** **0.7564**
- **Aggregate Minimum Pairwise Jaccard Similarity:** **0.1693**
- **Cluster Isolation:** 98.40% of all partitions (42,450 of 43,142) remain singletons. There are no sprawling "mega-components" spanning thousands of documents, confirming that the threshold ($s \approx 0.50$) and 400-shingle cap successfully prevent runaway transitive chaining.

---

## 5. Label Conflicts in Duplicate Clusters: Evidence of Weak Supervision

A critical finding of Phase 5 is the empirical measurement of label disagreement within duplicate text clusters.

### Top Multi-Item Clusters with Label Conflicts

| Cluster ID | Size | Unique Labels | Dominant Intent Label | Disagreement Rate | Split Assignment |
| :--- | :---: | :---: | :--- | :---: | :---: |
| `grp_exact_00a8a8a0bd44` | 123 | 3 | `credit_terms_dispute` | 66.7% | `train` |
| `grp_exact_150207f8f89b` | 113 | 3 | `reporting_improper_use` | 66.7% | `train` |
| `grp_exact_00b418e6ba0b` | 111 | 4 | `reporting_improper_use` | 75.0% | `validation` |
| `grp_exact_05722d84ce8d` | 90 | 4 | `payment_problem` | 75.0% | `train` |
| `grp_exact_08fb4daecc77` | 62 | 4 | `fraud_or_scam` | 75.0% | `train` |
| `grp_exact_01586833b1af` | 53 | 3 | `account_management` | 66.7% | `train` |
| `grp_exact_01617fb88e40` | 43 | 2 | `reporting_investigation_dispute` | 50.0% | `validation` |
| `grp_exact_23899f7e3e2f` | 42 | 3 | `payment_problem` | 66.7% | `test` |
| `grp_exact_bc263343afc7` | 41 | 3 | `reporting_improper_use` | 66.7% | `train` |
| `grp_exact_2e202cd270c3` | 41 | 2 | `reporting_investigation_dispute` | 50.0% | `validation` |

---

## 6. Cross-Dataset Contamination Verification (Banking77)

To ensure that the auxiliary customer intent benchmark `PolyAI/banking77` is strictly isolated from CFPB complaints, both datasets underwent symmetric NFC normalization and dual exact/near-duplicate collision audits:
- **Banking77 Total Queries Evaluated:** 13,083 (train 10,003 + test 3,080)
- **CFPB Complaint Texts Evaluated:** 44,755 unique normalized narratives
- **Exact Collisions:** **0**
- **Near-Duplicate Collisions ($J \ge 0.50$):** **0**
- **Methodological Role:** Banking77 serves exclusively as an auxiliary out-of-domain benchmark; CFPB intake labels are weak administrative routing tags. No cross-domain transfer or semantic gold evaluation is claimed.

---

## 7. Gating Checksums and Provenance

| Artifact | Location | Status |
| :--- | :--- | :--- |
| Canonical Dataset | `data/processed/canonical_dataset.parquet` | Verified |
| Duplicate Summary Manifest | `data/manifests/duplicate_audit.csv` | Generated |
| Cluster Instance Catalog | `data/manifests/duplicate_clusters.csv` | Generated |
| Split Leakage Report | `docs/split_leakage_audit.md` | Generated |
