# Final Project Reports Directory

This directory contains the final compiled Markdown (`.md`) reports for the **Cross-Domain Complaint Understanding (CDCU)** project on branch `feature/contrastive-retrieval-engine`.

## Index of Reports

| Report File | Scope & Summary |
|---|---|
| **[FINAL_COMPREHENSIVE_PROJECT_REPORT.md](FINAL_COMPREHENSIVE_PROJECT_REPORT.md)** | **The Complete Master Final Report**: Data pipelines, CFPB FOIA provenance, text preprocessing, XLM-V 778.5M architecture details, Blackwell GPU parallel fine-tuning, empirical validation (+34.86% over frozen XLM-V), locked test evaluation, and production deployment. |
| **[RETRIEVAL_EXPERIMENT_REPORT.md](RETRIEVAL_EXPERIMENT_REPORT.md)** | **Empirical Experiment Report**: Full metric tables (P@10, R@10, MRR@10, NDCG@10) across Lexical TF-IDF (R0), Frozen XLM-V (R1), SimCSE (R2), and SupCon (R4), plus loss progression and early-stopping audit. |
| **[DATA_PROVENANCE_AND_LEGAL_TERMS.md](DATA_PROVENANCE_AND_LEGAL_TERMS.md)** | **Legal & Provenance Report**: CFPB FOIA Electronic Reading Room terms, 17 U.S.C. § 105 bureau metadata status, 80 FR 15572 consumer opt-in consent disclosures, and PII de-identification standards. |
| **[DATA_PREPARATION_METHODOLOGY.md](DATA_PREPARATION_METHODOLOGY.md)** | **Data Preprocessing Report**: Multi-line CSV parser, malformed line handling, BOM stripping, text sanitization, and `<REDACTED>` token normalization. |
| **[SPLITS_AND_LEAKAGE_AUDIT.md](SPLITS_AND_LEAKAGE_AUDIT.md)** | **Split Feasibility & Partition Hygiene**: Proof of atomic duplicate-cluster grouping (`data/manifests/full_clusters.csv`) and zero group leakage across Train (32,019), Val (6,852), and Test (6,852). |
| **[TAXONOMY_CODEBOOK.md](TAXONOMY_CODEBOOK.md)** | **Taxonomy & Mapping Standards**: Unified taxonomy definition across 9 financial domains, weak administrative routing labels vs. human truth, and cross-domain pair mining rules. |

