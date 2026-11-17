# Contrastive Representation Learning for Complaint Similarity and Retrieval

## Research question and hypotheses

Does contrastive fine-tuning of XLM-V improve complaint embeddings for similar-complaint retrieval compared with TF-IDF, frozen XLM-V and supervised-classifier representations? Does cross-domain positive-pair training improve retrieval across financial product domains?

- H1: Contrastively fine-tuned XLM-V improves retrieval over frozen XLM-V.
- H2: Cross-domain positive sampling improves feasible cross-domain retrieval.
- H3: Human-adjudicated relevance provides stronger semantic evidence than CFPB weak-label proxy metrics.
- H4: Contrastive fine-tuning may affect intent classification; classification and retrieval are measured separately.

These are hypotheses, not guaranteed outcomes. Contrastive training can degrade retrieval when positives are noisy, negatives are false negatives, or the model overfits administrative labels.

## Why it may help

A frozen encoder produces pretrained vectors but is not necessarily optimized for distinctions needed in financial complaint retrieval. Contrastive training explicitly shapes the embedding space by bringing valid related pairs closer and separating selected negatives.

For normalized embeddings:

    sim(z_i,z_j) = z_i^T z_j

A supervised contrastive objective:

    L_SupCon = sum_i -1/|P(i)| sum_{p in P(i)}
               log [ exp(sim(z_i,z_p)/tau) /
                     sum_{a in A(i)} exp(sim(z_i,z_a)/tau) ]

where P(i) is the valid positive set for anchor i, A(i) is the comparison set excluding the anchor, and tau is temperature. The implementation must document its actual objective, masks, temperature, pooling and normalization. Do not call a pairwise InfoNCE or triplet loss SupCon unless it implements the stated objective.

## Weak-label warning

CFPB-derived Product/Issue/Sub-issue categories are administrative weak labels, not semantic gold labels. Same-label complaints may describe different events; different-label complaints may still be related.

Maintain two separate evaluation tracks:
1. Weak-label proxy retrieval: same administrative label is the proxy relevance signal. Label it clearly.
2. Human-adjudicated semantic retrieval: blinded query/candidate judgments, independently rated and adjudicated. This is required for semantic similarity claims.

Never merge these metrics into one score.

## Pair construction

### P0: same-domain weak-label positives
- Sample same weak-label class within the same product domain.
- Exclude identical IDs, shared duplicate clusters and shared source groups.
- Treat as a weak-label baseline and inspect samples for noise.

### P1: cross-domain weak-label positives
- Sample same weak-label class across different product domains only where that class is supported in both domains.
- Do not synthesize examples for empty class-domain cells.
- Report pair counts and supported domains per class.

### P2: human-validated semantic pairs
- Use the Phase 6 blinded annotation protocol.
- Suggested graded labels: same underlying problem, related problem, different problem, insufficient information.
- Keep human evaluation pairs held out from training.
- Use human-confirmed pairs for training only if split and annotation governance explicitly permit it.

### Negatives
- Do not assume every different weak label is a true semantic negative.
- Use conservative negatives first.
- Select hard negatives from training only and inspect likely false negatives.
- Exclude duplicate/near-duplicate and shared-source pairs.
- Memory queues are optional later work, not a first-pilot requirement.

Each pair record must include IDs, weak labels, domains, duplicate-cluster and source-group IDs, sampling mode, supervision source, confidence/adjudication status, seed, dataset version/hash and split membership. Training pairs must resolve only to the training split.

## Controlled experiment matrix

| ID | Representation | Training signal |
|---|---|---|
| R0 | TF-IDF | Lexical baseline |
| R1 | Frozen XLM-V | No task-specific contrastive training |
| R2 | Supervised classifier XLM-V representation | Weak intent labels |
| R3 | SimCSE XLM-V | Dropout views of same complaint |
| R4 | SupCon XLM-V, same-domain positives | Weak-label same-domain pairs |
| R5 | SupCon XLM-V, cross-domain positives | Supported cross-domain weak-label pairs |
| R6 | Pairwise InfoNCE/triplet | Explicit anchor-positive-negative pairs |
| R7 | Human-pair-supervised model, if feasible | Human-validated relevance pairs |

Minimum first pass: R0, R1, R3 and R4. Then R5/R6 after pair sampling and pilots pass. R7 depends on annotation capacity.

Keep split, query/gallery sets, preprocessing, truncation, pooling, normalization, similarity function, candidate eligibility and K values fixed across comparisons. Select models using validation only.

## Retrieval evaluation protocol

Development: validation queries -> training gallery.

Final: test queries -> training gallery, once model/configuration is frozen. Do not tune on test results or put validation/test examples into training pair manifests or the training gallery.

Evaluate separately:
- In-domain retrieval.
- Cross-domain retrieval, where candidate domain differs from query domain.

Report Precision@1/@5/@10, Recall@5/@10, MRR@10, nDCG@5/@10 where graded relevance exists, query coverage, query count, gallery size, relevant candidates, per-domain/per-class support, and unsupported/excluded cells.

State whether cross-domain filtering is applied to the gallery before ranking or after ranking; use one protocol consistently.

## Embedding diagnostics

Retrieval ranking metrics are primary. Also report:
- Positive and negative pair cosine similarity distributions.
- Positive-negative separation.
- Nearest-neighbour weak-label consistency (diagnostic only).
- Nearest-neighbour domain distribution.
- Embedding norm distribution.
- Duplicate/near-duplicate nearest-neighbour rate.
- Optional UMAP/t-SNE for qualitative inspection only.

Do not treat increased same-label cosine similarity as proof of semantic improvement.

## Statistical robustness

Use identical queries and galleries for paired model comparisons. Where feasible, compute paired bootstrap confidence intervals for metric differences and repeat selected final experiments across multiple seeds. If time prevents this, state the limitation. Inspect false-positive and false-negative retrieval cases.

## Required result tables

All values must come from actual saved predictions and run artifacts. Until then, leave them Pending.

### Weak-label proxy retrieval

| Model | P@5 | R@5 | P@10 | R@10 | MRR@10 | nDCG@10 | Query coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Supervised XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Pairwise InfoNCE | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

### Human-adjudicated semantic retrieval

Use the same model rows only after human judgments are available. Include graded nDCG, rater agreement, adjudicated query count and confidence intervals if calculated. Never copy weak-label proxy scores into this table.

### Embedding diagnostics

| Model | Positive cosine mean | Negative cosine mean | Separation | NN weak-label consistency | Duplicate NN rate |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending |

### Efficiency

| Model | Train time | Peak VRAM | Embedding throughput | Index build time | Query latency |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| Contrastive variants | Pending | Pending | Pending | Pending | Pending |

## Required report interpretation

Answer:
1. Did contrastive learning improve over frozen XLM-V?
2. Did it improve over TF-IDF?
3. Did it improve over supervised-classifier representations?
4. Which objective worked best, and on which track?
5. Did same-domain and cross-domain pair sampling differ?
6. Did gains hold on human semantic relevance or only weak-label proxies?
7. Which domains/classes improved, regressed or were unsupported?
8. What happened to classification performance?
9. What were compute cost and inference latency?
10. What failure modes and limitations remain?

A negative result is valid if the experiment is controlled and reported honestly.

## Promotion rule

Do not promote a checkpoint because training loss decreased. Promote it for retrieval only if data gates pass, validation retrieval improves or provides a justified trade-off against frozen XLM-V, unsupported cells are not hidden, semantic claims are supported by human judgments, artifacts are reproducible, and latency/memory fit deployment constraints.

If weak-label metrics improve but human semantic metrics do not, do not claim improved semantic similarity; investigate weak-label overfitting and revise pair construction.

## Required artifacts and acceptance gate

Required:
- docs/RETRIEVAL_EXPERIMENT_REPORT.md
- docs/EMBEDDING_ANALYSIS_REPORT.md
- reports/retrieval/<run_id>/run_manifest.json
- reports/retrieval/<run_id>/metrics.json
- Privacy-approved ranked prediction artifacts and logs in approved institutional storage.

Do not commit complaint narratives, large embeddings/checkpoints, private indexes or secrets.

Accept the contrastive retrieval contribution only when at least one SimCSE and one supervised contrastive run complete and reload; TF-IDF/frozen/contrastive models share the same evaluation protocol; weak-label and human semantic metrics are separated; in-domain and feasible cross-domain results are separated; diagnostics and failure cases are documented; metrics trace to saved predictions and run manifests; and H1/H2/H3 are marked supported, unsupported or inconclusive based on evidence.
