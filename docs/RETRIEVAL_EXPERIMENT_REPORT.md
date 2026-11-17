# Retrieval Experiment Report

**Status:** Not run — template only. Do not replace Pending values with estimates.

## 1. Executive summary

- Dataset release/hash:
- Code commit:
- Evaluation run IDs:
- Primary finding:
- Does contrastive training improve retrieval over frozen XLM-V? Pending.
- Does cross-domain pair training improve feasible cross-domain retrieval? Pending.
- Do human relevance judgments support weak-label findings? Pending.

## 2. Research questions and hypotheses

Use the hypotheses in docs/CONTRASTIVE_RETRIEVAL_RESEARCH_PROTOCOL.md.

| Hypothesis | Result | Evidence |
|---|---|---|
| H1: contrastive XLM-V improves over frozen XLM-V | Pending | |
| H2: cross-domain positives improve feasible cross-domain retrieval | Pending | |
| H3: human relevance supports semantic improvement | Pending | |

## 3. Data and split audit

- Frozen dataset ID/hash:
- Train/validation/test counts:
- Duplicate-cluster manifest hash:
- Phase 7 audit commit and result:
- Pair manifest hashes:
- Confirmation no validation/test examples entered training pairs:
- Class/domain support and excluded cells:

## 4. Models and training configurations

| Model ID | Base checkpoint/revision | Objective | Pair strategy | Seed | Max length | Effective batch | Temperature | Steps/epochs | Commit |
|---|---|---|---|---|---:|---:|---:|---:|---|
| R0 TF-IDF | N/A | TF-IDF | N/A | | | | | | |
| R1 Frozen XLM-V | | None | N/A | | | | | | |
| R2 Supervised XLM-V | | Classification | Weak labels | | | | | | |
| R3 SimCSE | | SimCSE | Dropout views | | | | | | |
| R4 SupCon same-domain | | SupCon | Same-domain weak positives | | | | | | |
| R5 SupCon cross-domain | | SupCon | Supported cross-domain positives | | | | | | |
| R6 InfoNCE | | Pairwise InfoNCE | Explicit pairs | | | | | | |

## 5. Retrieval protocol

- Query split:
- Gallery split:
- Similarity function:
- Pooling and normalization:
- Top-K values:
- In-domain definition:
- Cross-domain filtering definition:
- Weak-label relevance definition:
- Human annotation protocol/version:
- Exclusions and query coverage:

## 6. Weak-label proxy results

| Model | P@5 | R@5 | P@10 | R@10 | MRR@10 | nDCG@10 | Query coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Supervised XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Pairwise InfoNCE | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

## 7. Human-adjudicated semantic retrieval

Do not populate until adjudication is complete.

- Annotation sample design:
- Number of queries/candidates:
- Raters and blinding:
- Agreement statistic and method:
- Adjudication method:
- Relevance grade definitions:

| Model | P@5 | R@5 | MRR@10 | nDCG@10 | Queries evaluated |
|---|---:|---:|---:|---:|---:|
| TF-IDF | Pending | Pending | Pending | Pending | Pending |
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending |

## 8. Cross-domain results

Provide per-domain query support, candidate gallery size, eligible query count, unsupported class/domain cells and metrics. Never collapse unsupported cells into one aggregate without disclosure.

## 9. Embedding-space diagnostics

| Model | Positive cosine mean | Negative cosine mean | Separation | NN weak-label consistency | Duplicate NN rate |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending |

## 10. Efficiency and deployment suitability

| Model | Train time | Peak VRAM | Embedding throughput | Index build time | Query latency |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| Contrastive variants | Pending | Pending | Pending | Pending | Pending |

## 11. Statistical uncertainty and robustness

- Seeds:
- Paired bootstrap method:
- Confidence intervals:
- Query-level comparison:
- Domain/class breakdown:
- Limitations if robustness tests were not run:

## 12. Error analysis

Include representative false positives, false negatives, weak-label mismatches, domain-specific errors, duplicate-related errors and unsupported cases. Keep raw complaint narratives in approved restricted storage.

## 13. Discussion and conclusion

Explicitly answer H1/H2/H3. Distinguish observed metric improvements from semantic conclusions. Discuss whether gains justify compute and operational cost.

## 14. Reproducibility appendix

- Repository URL and commit SHA:
- Environment lock/container digest:
- Dataset/split/pair manifest hashes:
- Model/tokenizer revisions:
- Training configs and seeds:
- Slurm job IDs and logs:
- Checkpoint/index checksums:
- Evaluation commands:
- CI/test run links:
- Artifact storage locations:
