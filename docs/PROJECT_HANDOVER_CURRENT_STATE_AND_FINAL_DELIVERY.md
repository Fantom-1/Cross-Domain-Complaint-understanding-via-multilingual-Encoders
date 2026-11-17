# Project Handover: Current State, Controlled Execution, and Final Delivery

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Canonical repository:** https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders  
**Primary encoder:** `facebook/xlm-v-base`  
**Document purpose:** Single source of truth for the coding agent, training agent, reviewer, and project owner  
**Status date:** 17 November 2026  
**Execution mode:** Agent-led implementation and experiments; owner-controlled access and approvals

---

## 0. Operating instruction — read before changing anything

This project must be executed as a controlled research-to-deployment workflow. Do not broaden the scope, replace the dataset, change the research question, introduce new models without approval, or skip validation gates to save time.

The final application has three primary capabilities:

1. **Intent classification** — predict one of the 16 CFPB-derived complaint intent categories.
2. **Structured complaint summarization** — produce a concise, evidence-grounded summary of the complaint.
3. **Similar complaint retrieval** — retrieve relevant complaints using learned representations, with cross-domain retrieval as the principal research focus.

The main research contribution is **contrastive representation learning for cross-domain complaint understanding and retrieval using XLM-V**. The classifier and summarizer support the product. The retrieval and representation-learning experiments must remain scientifically defensible.

The agent must:
- Work only in the canonical repository named above. Do not use `AbdulMalik1287/NLP`.
- Inspect the current branch, commits, open PRs, CI, and working tree before editing.
- Preserve merged Phase 0–6 artifacts and the frozen dataset/splits.
- Treat Phase 7 as merged into `main` by PR #9, but re-run its audit and tests in the actual working environment before relying on it.
- Work in small, reviewable commits with descriptive messages.
- Never commit complaint narratives, raw datasets, checkpoints, indexes, secrets, tokens, local paths, or private server details.
- Never report a training run, validation result, deployment, or test as successful without logs and reproducible evidence.
- Stop and report blockers instead of silently improvising.

**No training or deployment is authorized by this document alone.** The project owner supplies access and explicitly approves resource-consuming jobs and deployment actions.

---

## 1. Current verified project position

### 1.1 Repository and branch state

Canonical repository:

`Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders`

At the latest repository inspection:
- `main` includes the Phase 7 merge from PR #9.
- PR #9 is closed and merged. Merge commit: `573e1587a6c4b94d09496f41ac5b291d756f560f`.
- The working feature branch `feature/contrastive-retrieval-engine` exists.
- Its inspected head was `1891859fa69b0ec1664349ec5e4977e7f687ed91`.
- The feature branch was 27 commits ahead of `main` and 0 behind at the time of comparison.
- The feature branch contains new contrastive, retrieval, summarization, API and CI changes. These changes must be reviewed and tested before merge.
- The latest feature branch commit observed was `Add duplicate-aware unsupervised SimCSE trainer`.

These values are a snapshot, not a guarantee of the current head. The agent must fetch and re-check before starting.

### 1.2 Data and research foundations

Merged phases:
- Phase 0–3: data specification, provenance, parsing/validation, profiling.
- Phase 4: XLM-V tokenizer and truncation analysis.
- Phase 5: exact/near-duplicate detection and leakage controls.
- Phase 6: weak-label taxonomy and blinded human-annotation materials.
- Phase 7: split feasibility, domain-confounding and temporal boundary audit; PR #9 merged.

Frozen baseline reported by the project:
- 45,723 CFPB complaint narratives.
- 16 administrative weak-label intent categories.
- 9 financial product domains.
- Train: 32,019.
- Validation: 6,852.
- Test: 6,852.
- English-only corpus.

Phase 5 audit reported:
- 43,142 duplicate partitions.
- 692 multi-item clusters.
- Zero cross-partition duplicate-cluster/text-hash leakage in the recorded audit.

Phase 6 produced taxonomy and blinded annotation materials, including a 320-item pilot manifest. Actual human annotation/adjudication is still required before semantic relevance claims.

Phase 7 audit artifacts report:
- 9 domains × 16 classes = 144 cells.
- 81 zero-support cells (56.25% sparsity).
- 36 continuous months from May 2018 through April 2021.
- Structural confounding for some leave-one-domain-out settings, including debt_collection and mortgage.
- Hindi/Hinglish evaluation deferred until authentic complaint data is obtained.

The agent must run the committed Phase 7 audit from a clean checkout and verify its inputs and output. A report file marked PASS is not, by itself, proof that the current checkout passes.

### 1.3 Existing supervised classifier evidence

The repository contains supervised XLM-V training/evaluation code and historical result artifacts. Historical recorded test metrics:
- Macro-F1: approximately 0.5369.
- Weighted-F1: approximately 0.5340.
- Accuracy: approximately 0.5325.
- Test rows: 6,852.

Historical run records indicate one 1g.24gb MIG allocation and approximately 15.6 GB peak VRAM. These are historical artifacts, not independently reproduced evidence in the current work session. The external checkpoint path must be located, checksum-verified, and tested before the model is treated as deployable.

There is a documentation conflict to reconcile: Phase 4 reports an XLM-V tokenizer vocabulary of 901,629, while an older README statement reportedly says 2.5M. Confirm the pinned tokenizer revision and correct documentation with evidence.

---

## 2. Research framing and non-negotiable data caveats

### 2.1 Central research question

Does contrastive fine-tuning of XLM-V produce complaint representations that improve similar-complaint retrieval, particularly across financial product domains, compared with lexical TF-IDF and frozen XLM-V representations, while preserving or improving intent classification?

### 2.2 Weak-label limitation

CFPB Product/Issue/Sub-issue mappings are administrative weak labels, not semantic ground truth.

Therefore:
- Same-label complaints are not automatically semantically equivalent.
- Different-label complaints are not automatically semantically unrelated.
- Weak-label retrieval metrics must be labelled as weak-label proxy metrics.
- Human-adjudicated semantic relevance must be evaluated separately.
- Do not claim semantic retrieval quality from weak labels alone.

### 2.3 Language limitation

The current frozen corpus is English-only. A multilingual encoder does not make the dataset multilingual. Do not claim Hindi/Hinglish complaint understanding or multilingual generalization without authentic multilingual complaint data and a suitable evaluation set. Translating CFPB English narratives is not a substitute for authentic user-generated Indian complaint text.

### 2.4 Cross-domain limitation

The class/domain matrix is sparse. Do not run or report naive all-class leave-one-domain-out evaluation where the held-out class has no training support. Report supported class-domain cells, unsupported cells, query coverage and denominators explicitly.

---

## 3. Final system scope

### Component A — Intent classifier

Input: complaint narrative.

Output:
- Predicted intent label.
- Top-k class probabilities/scores.
- Model version.
- Warning that labels originate from administrative weak supervision.

Evaluation:
- Macro-F1 is the primary metric.
- Also report accuracy, weighted-F1, per-class precision/recall/F1, support and confusion matrix.
- Compare TF-IDF + Logistic Regression with the supervised XLM-V baseline and any contrastive encoder plus classifier variant.
- Use validation for model selection; use test only after decisions are frozen.

### Component B — Structured complaint summarizer

Initial deliverable should be a conservative, evidence-grounded structured summarizer, not an unsupported free-form generative system.

Required fields:
- Problem description.
- Customer concern.
- Timeline/events, when stated.
- Requested resolution, when stated.
- Supporting evidence/source sentence references.
- Short summary.
- Missing information and uncertainty notes.

Rules:
- Do not invent dates, people, amounts, causes, commitments or resolutions.
- Distinguish explicitly stated facts from inferred/uncertain information.
- Preserve chronology.
- If a field is absent, return “not stated” rather than hallucinating.
- Evaluate with human review for factuality, coverage, chronology, omissions and usefulness.
- ROUGE/BERTScore may be secondary if reference summaries are created; they do not replace factuality review.

### Component C — Similar complaint retrieval

Input: complaint narrative, optional product-domain filter, top-k.

Output:
- Ranked complaint IDs.
- Similarity score.
- Product domain.
- Intent label where available.
- Clear indication of whether relevance is based on weak-label or human-validated evidence.
- Complaint text only where access policy permits.

Research comparisons:
1. TF-IDF cosine similarity.
2. Frozen XLM-V embeddings.
3. SimCSE-style XLM-V.
4. Supervised contrastive XLM-V.
5. Pairwise InfoNCE XLM-V.
6. Cross-domain positive sampling variant, only for supported classes/domains.

Metrics:
- Precision@K.
- Recall@K.
- MRR@K.
- nDCG@K.
- Query coverage and support counts.

Use validation queries against training gallery for development. Once the model and configuration are locked, use test queries against training gallery for final evaluation. Do not index validation/test complaints into the training gallery for this benchmark.

### Component D — Integrated complaint analysis API

Required routes:
- `GET /health`
- `POST /predict`
- `POST /summarize`
- `POST /retrieve`
- `POST /analyze`

`/analyze` combines classifier, summarizer and retrieval responses. The API must load fixed, versioned artifacts at startup. It must not train models during a request.

### Component E — Deployable application

Deliver:
- Backend API.
- Minimal usable frontend or documented API demo.
- Docker image and reproducible build instructions.
- Kubernetes Deployment and internal Service manifests, subject to cluster permissions.
- Versioned model bundle and retrieval index.
- Health/readiness checks.
- Configuration through environment variables/secrets, never hard-coded credentials.
- Logging that avoids storing raw complaint narratives by default.
- Privacy, authorization, rate limiting and retention controls before public exposure.

---

## 4. Infrastructure preparation — AI Node

The supplied internal AI Node specification describes:
- 2 × NVIDIA RTX PRO 6000 Blackwell Server Edition physical GPUs on one node.
- Each GPU divided into eight 1g.24gb MIG instances; 16 MIG instances total.
- 24 CPU cores and approximately 306 GB host RAM.
- Slurm 24.05.4 with `gpu` and `cpu` partitions.
- Per-node Slurm GPU resource string shown as `gpu:1g.24gb:8`.
- Kubernetes and Docker are installed.
- CUDA toolkit module 12.8.
- GPU PyTorch environment listed as 2.11.0+cu12.8.
- Modules listed include `anaconda3-2025`, `cuda-12.8` and `miniconda3`.

This specification describes one node with two physical GPUs; it does not establish two separate physical nodes. Actual account access, partition/QOS, quotas, available MIG slices, writable storage and Kubernetes permissions must be checked live.

The specification is confidential/internal-use-only. Keep it in authorized institutional channels. Do not copy exact hostnames, access IPs, usernames, credentials, private filesystem details or sensitive infrastructure information into public repository documentation.

### 4.1 Read-only preflight

After the owner provides approved SSH access, the agent may run read-only inspection:

```bash
hostname
whoami
pwd
module avail
module list
sinfo -o "%P %a %l %D %G"
squeue -u "$USER"
nvidia-smi -L
nvidia-smi
df -h
quota -s
```

If permitted by administrators, check account association/QOS and storage quota. Do not inspect or alter protected system configuration without explicit administrator approval.

### 4.2 Environment policy

- Use a project-owned Conda/venv environment or an approved container.
- Do not alter system Python, shared modules, drivers, CUDA, Slurm or Kubernetes configuration.
- Verify PyTorch/CUDA compatibility inside the actual allocation.
- Pin exact package versions after a successful smoke test.
- Do not assume the listed PyTorch/Transformers versions are compatible with the repository code until imports, forward/backward and checkpoint save/reload are tested.

### 4.3 GPU allocation policy

Start with one 1g.24gb MIG slice. Measure:
- Visible device count and model name.
- Total available MIG memory.
- Peak allocated and reserved VRAM.
- Batch/sequence length and step time.
- CPU/RAM use.
- Checkpoint and output storage.
- Successful save/reload.

Scale to multiple MIG slices only if permitted and beneficial. Multi-GPU training requires an explicit tested distributed strategy such as DDP, including distributed sampler, process launch, rank handling and checkpoint coordination. Requesting multiple GPUs does not make a single-process trainer distributed.

### 4.4 Storage policy

Use administrator-approved writable project storage. Keep separate locations for:
- Source checkout.
- Project environment/container definitions.
- Read-only canonical data.
- Run logs/configs.
- Checkpoints.
- Retrieval index.
- Model release bundles.
- Deployment images/manifests.
- Reports.

Check quotas before training. Do not place large outputs on the root filesystem. Do not commit datasets, complaint text, checkpoints, indexes, credentials or environment files.

---

## 5. Strict execution stages and gates

The agent must complete each stage and report its evidence before moving to the next. If a gate fails, stop, fix the issue, rerun the gate and report the correction. Do not silently continue.

### Stage 0 — repository baseline and scope lock

Tasks:
1. Fetch latest `main` and working branch.
2. Record commit SHA, clean/dirty status, branch divergence and open PRs.
3. Inspect current implementation; do not duplicate modules.
4. Run current tests and CI.
5. Confirm Phase 7 merge and run Phase 7 audit.
6. Reconcile README/tokenizer vocabulary conflict.
7. Produce a short baseline report listing verified, failed, missing and unverified items.

Gate 0:
- Clean working tree.
- Exact commit SHA recorded.
- Current test/CI state recorded.
- Phase 7 audit run or explicit blocker documented.
- No scope drift.

### Stage 1 — server preflight and environment lock

Tasks:
1. Confirm authorized account, partition, QOS and GPU allocation.
2. Confirm available storage and quota.
3. Load approved modules.
4. Verify PyTorch/CUDA and actual MIG visibility inside Slurm.
5. Create project-owned environment/container.
6. Run tokenizer/model load, forward, backward, optimizer step, checkpoint save and reload.
7. Record environment versions and GPU memory.

Gate 1:
- One allocated MIG slice works.
- Smoke job has Slurm job ID, stdout/stderr and exit code 0.
- Checkpoint can be reloaded.
- No system configuration was changed.
- Environment lock file is committed.

### Stage 2 — frozen data release

Tasks:
1. Verify canonical dataset checksum.
2. Verify exact 45,723 IDs and split counts.
3. Verify unique IDs and allowed split values.
4. Verify duplicate-cluster catalog completeness.
5. Verify no duplicate cluster or source group crosses partitions.
6. Verify 16 labels, 9 domains and all 144 class-domain cells, including zero cells.
7. Record class/domain support per split.
8. Re-run Phase 1–7 tests and audit from clean checkout.
9. Freeze a versioned data manifest; do not overwrite original splits.

Gate 2:
- All invariants pass.
- Data hash and manifest hashes recorded.
- No unreviewed data changes.
- Dataset release is immutable for the experiment series.

### Stage 3 — baselines and classifier verification

Tasks:
1. Implement/run TF-IDF + Logistic Regression baseline.
2. Locate historical XLM-V classifier checkpoint.
3. Verify checkpoint/tokenizer/label map compatibility and hashes.
4. Reproduce validation metrics where possible.
5. Evaluate test only if the historical test procedure is confirmed and the test has not been used for tuning; otherwise report historical test values as unreproduced.
6. Save classification report, per-class metrics and confusion matrix.

Gate 3:
- Baselines are reproducible or clearly marked historical/unverified.
- No fabricated metrics.
- Validation/test separation respected.

### Stage 4 — contrastive pair generation

Tasks:
1. Generate deterministic train-only pair manifest.
2. Exclude identical IDs, shared duplicate clusters and shared source groups.
3. Record anchor/positive/negative IDs, labels, domains, sampling mode, supervision type, seed and dataset version.
4. Start with same-domain weak-label positives.
5. Generate cross-domain positives only where a class is supported in multiple domains.
6. Treat weak negatives cautiously; do not automatically label every different weak class as semantically negative.
7. Report pair counts by class, domain, pair type and sampling mode.
8. Inspect samples for false positive/negative patterns.

Gate 4:
- Pair IDs resolve to training split only.
- No duplicate-cluster/group overlap.
- Pair manifest is deterministic and auditable.
- Unsupported class/domain combinations are not silently filled.

### Stage 5 — contrastive training pilots

Minimum experiments:
- SimCSE-style dropout contrastive baseline.
- Supervised contrastive XLM-V.
- Pairwise InfoNCE comparison.

Keep the first runs small. Save:
- Config and seed.
- Commit SHA.
- Dataset/pair hashes.
- Model and tokenizer revision.
- Batch size, gradient accumulation, max length, temperature, objective and optimizer.
- Training loss history.
- Runtime and peak VRAM.
- Checkpoint checksum.
- Validation retrieval metrics.

Only scale after a successful smoke test. Do not run a broad hyperparameter sweep under time pressure. Choose a small, predeclared set of experiments and justify each one.

Gate 5:
- At least one valid SimCSE run and one valid supervised contrastive run complete.
- Checkpoints reload.
- Validation evaluation completes.
- Run manifests and logs exist.

### Stage 6 — retrieval benchmark

Compare:
- TF-IDF.
- Frozen XLM-V.
- SimCSE XLM-V.
- Supervised contrastive XLM-V.
- Pairwise InfoNCE if completed.

Development protocol:
- Validation queries → training gallery.
- Report in-domain and feasible cross-domain results separately.
- Report query coverage, class/domain support and excluded unsupported cells.
- Weak-label metrics must be clearly labelled.

Final protocol:
- Freeze model/configuration using validation.
- Test queries → training gallery.
- Run test once.
- Do not tune on test results.

Human relevance:
- Use blinded annotation materials.
- Have independent raters judge query/candidate relevance.
- Adjudicate disagreements.
- Report agreement and relevance metrics separately from weak-label proxy metrics.

Gate 6:
- Baseline comparison complete.
- Metrics and denominators recorded.
- Human semantic evaluation either complete or explicitly listed as a limitation.
- No unsupported cross-domain claim.

### Stage 7 — summarizer

Tasks:
1. Implement conservative structured output.
2. Keep sentence-level source traceability.
3. Represent missing fields explicitly.
4. Test short, long, malformed, contradictory and incomplete narratives.
5. Human-review a sample for factuality, chronology, omissions and usefulness.
6. Record failure examples and limitations.

Gate 7:
- No invented details in reviewed sample.
- Output schema validated.
- Human evaluation documented.
- Do not describe an extractive baseline as an LLM summarizer.

### Stage 8 — API and application integration

Tasks:
1. Define stable request/response schemas.
2. Load classifier, contrastive encoder and index once at startup.
3. Implement `/health`, `/predict`, `/summarize`, `/retrieve`, `/analyze`.
4. Add input size/type validation and predictable errors.
5. Ensure retrieval can search across domains by default; optional filters must be explicit.
6. Return model version and relevant limitations.
7. Add unit and integration tests with small fixtures.
8. Build minimal usable frontend or an API demo client.
9. Verify the application works with the exact release artifacts.

Gate 8:
- All endpoints pass tests.
- End-to-end `/analyze` returns all three capabilities.
- No model training occurs during requests.
- Model/index paths and checksums are verified.
- No complaint data leaks into logs by default.

### Stage 9 — containerization and deployment

Tasks:
1. Build Docker image from an approved compatible runtime base.
2. Pin dependencies and image tag.
3. Run as non-root.
4. Mount model/index bundles read-only.
5. Keep secrets outside image and Git.
6. Test locally before cluster deployment.
7. Deploy internal Kubernetes Service only after namespace/RBAC/storage permissions are confirmed.
8. Add readiness/liveness probes that reflect actual model load state.
9. Verify internal service access and endpoint smoke tests.
10. Obtain privacy/security approval before any public ingress.

Gate 9:
- Image build reproducible.
- Container starts and loads exact model release.
- Kubernetes rollout ready.
- Internal endpoint smoke test passes.
- Deployment rollback/version procedure documented.

### Stage 10 — final delivery

Required outputs:
1. Research report with methods, hypotheses, experiments, results and limitations.
2. Dataset/provenance and split audit report.
3. Pair-generation audit report.
4. Classification comparison.
5. Contrastive training report and run manifests.
6. Retrieval benchmark report, separating weak-label and human relevance.
7. Summarizer evaluation report.
8. Model cards and release manifest.
9. API documentation.
10. Docker/Kubernetes deployment instructions.
11. Demo script and screenshots/video if permitted.
12. Final clean repository and tagged release.
13. Handover instructions for reproducing inference and experiments.

Gate 10:
- Every result traceable to code, config, data hash and run log.
- No unsupported claims.
- Fresh checkout can reproduce documented tests and start the application with the released artifacts.

---

## 6. Commit and pull request discipline

Use small logical commits. Suggested message format:

`<type>(<scope>): <imperative summary>`

Examples:
- `fix(data): enforce complete duplicate-cluster coverage`
- `feat(contrastive): add deterministic train-only pair sampling`
- `feat(contrastive): add supervised contrastive objective`
- `feat(contrastive): add SimCSE training pipeline`
- `feat(retrieval): add retrieval metrics and benchmark runner`
- `feat(api): add complaint analysis endpoints`
- `test(deploy): add container and service smoke tests`
- `docs(research): document experiment protocol and limitations`

Every PR must include:
- Purpose and scope.
- Commit SHA.
- Files changed.
- Commands/tests executed and actual results.
- CI run link and tested head SHA.
- Data/model hashes where relevant.
- What is implemented versus actually executed.
- Risks, limitations and remaining blockers.
- Confirmation that test data was not used for training/model selection.

Do not merge a PR because it is merely mergeable. Require CI on exact head, review, and relevant gate evidence. Do not force-push or rewrite shared history without approval.

---

## 7. Agent progress report format

At the end of every stage, the agent must send this report:

### Stage report
- Stage:
- Branch:
- Commit SHA:
- Working tree clean?:
- Objective:
- Files changed:
- Commands executed:
- Tests executed:
- CI run and exact tested SHA:
- GPU allocation/job ID, if applicable:
- Runtime and peak VRAM, if applicable:
- Artifacts/log paths:
- Evidence links:
- Passed criteria:
- Failed criteria:
- Known risks:
- Next proposed action:

Use exactly one of these statuses:
- **PASS** — all gate criteria satisfied with evidence.
- **BLOCKED** — cannot proceed safely; describe the blocker and the minimum resolution.
- **PARTIAL** — some criteria pass; list what remains.
- **NOT RUN** — no execution evidence exists.

Never use “done” when code is merely written. Distinguish:
- Implemented.
- Unit-tested.
- Integration-tested.
- Executed on GPU.
- Evaluated.
- Deployed.

---

## 8. Review protocol for the project owner and reviewer

The owner provides the agent access and approves training/deployment actions. The reviewer checks the repository and evidence at each milestone.

Review in this order:
1. Exact commit and diff.
2. Whether changes fit the approved scope.
3. Data leakage and split discipline.
4. Correctness of model objective and pair construction.
5. Tests and CI on the exact commit.
6. Reproducibility of commands/configs.
7. Runtime and memory evidence.
8. Evaluation validity and honest claims.
9. Security/privacy of data and artifacts.
10. Deployment readiness and rollback.

When reviewing a PR:
- Inspect the complete diff, not just the PR description.
- Inspect tests for meaningful assertions and failure cases.
- Check for empty/stub files, hard-coded paths, hidden assumptions, swallowed exceptions and fail-open behavior.
- Check that metrics are calculated from saved predictions and correct labels.
- Check that train/validation/test boundaries are enforced in code, not only in documentation.
- Check that retrieval gallery/query split is correct.
- Check that checkpoint/tokenizer/label map versions match.
- Check that API routes actually load and use the intended artifacts.
- Ask for a reproducible command and log when claims cannot be verified from CI.

Do not issue broad instructions such as “improve the code.” Give the agent a precise file/function-level correction, expected behavior, regression test and acceptance condition.

---

## 9. Collaboration and progress-check cadence

The agent works on the repository and server under the owner's authorization. The owner shares progress updates, PR links, commit SHAs, CI runs, logs and experiment reports here.

At each check-in, the reviewer will:
1. Refresh the repository state and inspect new commits/PRs.
2. Compare the changes against this handover and current stage gate.
3. Identify blockers, regression risks and scope drift.
4. Give precise, prioritized instructions to the agent.
5. State whether the stage is PASS, PARTIAL or BLOCKED.
6. Approve the next stage only when the evidence supports it.

The reviewer will not assume progress between check-ins or claim to be monitoring the repository continuously. A review is triggered when the owner asks for one or shares new progress. If the owner says something is going wrong, first inspect evidence and isolate the failure; do not immediately redesign the whole system.

### Priority labels for review findings

- **P0 — Stop:** data leakage, incorrect test usage, security/privacy exposure, destructive data change, wrong repository, invalid scientific claim.
- **P1 — Fix before next stage:** incorrect objective, invalid pair construction, broken training/evaluation, missing checkpoint provenance, failing CI.
- **P2 — Fix before release:** API edge cases, weak observability, packaging defects, incomplete documentation.
- **P3 — Improvement:** non-blocking refactor, speed or usability improvement.

Every review finding should include:
- Priority.
- File/function or exact location.
- Evidence/reason.
- Required change.
- Regression test.
- Acceptance condition.

---

## 10. Explicit out-of-scope items unless approved

- Changing the frozen baseline dataset or split.
- Adding new intent classes or changing the taxonomy.
- Replacing XLM-V with another encoder as the primary model.
- Claiming multilingual performance without authentic multilingual data.
- Claiming semantic retrieval success using only weak labels.
- Naive all-domain leave-one-domain-out evaluation despite structural confounding.
- Large hyperparameter sweeps without a predeclared plan.
- Training on validation/test data.
- Public deployment or public complaint-data exposure.
- Modifying system/server configuration.
- Committing raw data, checkpoints, indexes, secrets or confidential server details.
- Building unrelated dashboards/features that do not support the research question or required demo.

---

## 11. First instructions to the agent

Do not start full training immediately.

**First task: baseline and server readiness report.**

1. Fetch the latest repository state and report branch/commit/PR/CI status.
2. Confirm PR #9 Phase 7 merge is present in `main`.
3. Inspect the contrastive/retrieval/API implementation branch and report exact changed files.
4. Run current unit tests and static checks without modifying shared infrastructure.
5. Run Phase 7 audit from a clean checkout and attach logs.
6. Inspect the training scripts for actual model loading, loss computation, backward pass, optimizer, checkpoint save/reload and deterministic configuration.
7. Confirm authorized AI Node account, Slurm partition/QOS, MIG allocation and writable storage.
8. Run read-only server preflight.
9. Request approval before submitting even a smoke GPU job if the owner has not already authorized it.
10. Return the Stage 0 and Stage 1 reports. Do not proceed to full training until the owner/reviewer accepts them.

After acceptance, proceed sequentially through Stages 2–10. If a failure occurs, stop at that gate and propose the smallest safe correction.

---

## 12. Definition of final success

The project is complete only when:
- The three capabilities work together in the application.
- The classifier is evaluated against a lexical baseline.
- Contrastive training is reproducible and compared with frozen XLM-V and TF-IDF retrieval.
- Cross-domain retrieval claims are restricted to supported class/domain settings.
- Human semantic relevance evidence is reported, or its absence is explicitly stated as a limitation.
- The summarizer is demonstrably evidence-grounded and human-reviewed.
- The API and frontend/demo work from a versioned model bundle.
- Docker/Kubernetes deployment instructions are tested in the authorized environment.
- CI, tests, run logs, hashes, reports and model release metadata are available.
- A new authorized user can follow the handover and reproduce the application.

**Final principle:** move quickly by reducing unnecessary experiments and preventing rework—not by skipping data validation, weakening evaluation, or making claims without evidence.


---

## 13. Research extension: contrastive learning for complaint embedding quality and retrieval

This section is a mandatory part of the research plan and final report. It makes explicit that the project is not merely adding a retrieval endpoint: it is testing whether contrastive learning improves the geometry and usefulness of complaint embeddings.

### 13.1 Research hypothesis

**Primary hypothesis (H1):** Fine-tuning XLM-V with a carefully constructed contrastive objective will improve the quality of complaint embeddings for nearest-neighbour retrieval compared with frozen XLM-V embeddings.

**Cross-domain hypothesis (H2):** Training with valid cross-domain positive complaint pairs will improve retrieval of related complaints from a different financial product domain, where the available data supports that comparison.

**Semantic-validity hypothesis (H3):** Improvements measured on human-adjudicated relevance judgments will agree with, or provide a more reliable account than, improvements measured using CFPB weak-label relevance proxies.

**Classification hypothesis (H4, secondary):** Contrastive fine-tuning may preserve or improve intent classification, but classification improvement is not required for a retrieval improvement. The two outcomes must be measured separately.

These are hypotheses to test, not expected or guaranteed outcomes. Contrastive learning can make embeddings worse if positive pairs are noisy, negatives are false negatives, or the training objective overfits administrative labels.

### 13.2 Why contrastive learning could improve retrieval

A frozen encoder maps a complaint to a vector based on its pretrained multilingual representation. Those vectors may encode general semantic information, but they have not necessarily been optimized for the distinctions that matter in financial complaints.

Contrastive learning adds a task-specific signal:
- Bring an anchor complaint and a valid positive complaint closer in embedding space.
- Separate the anchor from selected negative complaints.
- Learn representations that make relevant neighbours rank higher under cosine similarity or another fixed similarity function.

For normalized embeddings \(z_i\) and \(z_j\), cosine similarity is:

\[
\operatorname{sim}(z_i,z_j)=z_i^\top z_j
\]

A supervised contrastive objective can be written as:

\[
\mathcal{L}_{SupCon}
=
\sum_{i \in I}
-\frac{1}{|P(i)|}
\sum_{p \in P(i)}
\log
\frac{\exp(\operatorname{sim}(z_i,z_p)/\tau)}
{\sum_{a \in A(i)}
\exp(\operatorname{sim}(z_i,z_a)/\tau)}
\]

where:
- \(I\) is the set of anchors in a batch.
- \(P(i)\) is the set of valid positives for anchor \(i\).
- \(A(i)\) is the set of comparison examples other than the anchor itself.
- \(\tau\) is the temperature parameter.

The implementation must document its exact loss, positive/negative masks, normalization and temperature. Do not describe a pairwise InfoNCE or triplet implementation as SupCon unless its actual computation matches the stated objective.

### 13.3 The critical issue: what counts as a positive complaint?

The dataset's 16 CFPB-derived categories are weak administrative labels. They are useful for constructing initial experiments, but they do not prove semantic equivalence.

Example: two complaints with the same administrative intent may describe different underlying events. Conversely, two complaints with different mapped labels may describe related customer problems.

Therefore, use a staged supervision policy:

**P0 — conservative weak-label baseline**
- Sample positives from the same weak-label class and same product domain.
- Exclude same example IDs, exact/near-duplicate clusters and shared source groups.
- Use this only as a weak-label proxy experiment.
- Inspect sampled pairs manually to estimate noise.

**P1 — cross-domain weak-label experiment**
- Sample same-weak-label positives from different product domains only where that class is supported in both domains.
- Do not manufacture examples for empty class-domain cells.
- Report pair counts and supported domains for every class.
- Keep this experiment separate from same-domain positive sampling.

**P2 — human-validated semantic positives**
- Use the blinded Phase 6 annotation process to label query/candidate pairs.
- Prefer graded relevance judgments such as: same underlying problem, related problem, different problem, insufficient information.
- Use independently rated and adjudicated pairs for evaluation.
- Only use human-confirmed training pairs for model training if the annotation protocol and split assignment explicitly allow it. Keep evaluation pairs held out.

**Negative sampling policy**
- Do not automatically treat every different weak label as a reliable semantic negative.
- Begin with conservative negatives and record their source and confidence.
- Hard negatives must be selected from training data only and manually/semantically checked where feasible.
- Avoid negatives that are duplicates, paraphrases or plausible related complaints.
- A memory queue is optional future work, not a prerequisite for the first controlled experiment.

Every pair/triplet manifest must record:
- Pair/triplet ID.
- Anchor, positive and negative example IDs.
- Weak labels and product domains.
- Duplicate-cluster IDs and source-group IDs.
- Sampling strategy and supervision source.
- Confidence or adjudication status, if available.
- Random seed and dataset release/hash.
- Split membership and creation timestamp.

All training pairs must resolve exclusively to the training split. Validation and test examples must never enter the contrastive training pair manifest.

### 13.4 Controlled experiment matrix

Run the following comparison with a common data protocol and fixed retrieval evaluation:

| ID | Encoder / training | Training signal | Question answered |
|---|---|---|---|
| R0 | TF-IDF | Lexical term overlap | How strong is a simple lexical baseline? |
| R1 | Frozen XLM-V | No task-specific contrastive training | What does pretrained semantic representation provide? |
| R2 | Supervised classifier XLM-V representation | 16 weak intent labels | Are classification-oriented representations useful for retrieval? |
| R3 | SimCSE-style XLM-V | Dropout views of the same complaint | Does unsupervised sentence-level contrastive training help? |
| R4 | SupCon XLM-V, same-domain positives | Weak-label pairs within product domain | Does conservative weak supervision help within-domain retrieval? |
| R5 | SupCon XLM-V, cross-domain positives | Weak-label pairs across supported domains | Does cross-domain pair construction improve transfer? |
| R6 | Pairwise InfoNCE / triplet variant | Explicit anchor-positive-negative samples | Does the alternative objective perform differently? |
| R7 | Human-pair-supervised variant, if feasible | Human-validated relevance pairs | Does stronger semantic supervision improve retrieval? |

Minimum first-pass experiments are R0, R1, R3 and R4. R5 and R6 follow after the pair sampler and first pilots pass. R7 depends on annotation capacity. Do not start all experiments simultaneously.

For fair comparisons:
- Use the same frozen training/validation/test split.
- Use the same query and gallery sets.
- Use the same text preprocessing and truncation policy unless truncation is the explicit ablation.
- Use the same embedding pooling and normalization policy where applicable.
- Keep retrieval similarity function fixed for the primary comparison.
- Record checkpoint selection using validation only.
- Use identical candidate eligibility rules and top-K values.
- Report model size, encoding throughput, index build time and query latency as operational measures.

### 13.5 Retrieval evaluation protocol

**Development:** validation complaints are queries; training complaints are the gallery.

**Final evaluation:** test complaints are queries; training complaints are the gallery. Freeze all model and retrieval choices before this evaluation. Do not tune on test results.

Run two distinct retrieval tracks:

1. **Weak-label proxy retrieval**
   - A candidate with the same weak CFPB label is treated as relevant for the proxy metric.
   - Report this explicitly as weak-label relevance.
   - It measures label-consistent neighbourhood structure, not verified semantic equivalence.

2. **Human-adjudicated semantic retrieval**
   - Use blinded human relevance judgments for query/candidate pairs.
   - Report graded relevance and adjudication protocol.
   - This is the evidence needed for claims about semantic complaint similarity.

For both tracks, report:
- Precision@1, @5 and @10.
- Recall@5 and @10.
- MRR@10.
- nDCG@5 and @10 for graded relevance where labels support it.
- Query coverage: fraction of eligible queries with at least one relevant candidate.
- Number of queries, gallery size and relevant candidates.
- Results by product domain and intent class where support permits.
- In-domain and cross-domain results separately.
- Unsupported or excluded class-domain cells and their counts.

Cross-domain retrieval must require the candidate's product domain to differ from the query's domain. Do not accidentally include same-domain candidates in the cross-domain metric. State whether the gallery is filtered before ranking or results are filtered after ranking; use one consistent, documented protocol.

### 13.6 Embedding-space diagnostics

Retrieval ranking metrics are primary. Also report diagnostics that help explain *why* an embedding model changes:

- Mean/median cosine similarity for positive pairs.
- Mean/median cosine similarity for negative pairs.
- Positive-negative similarity separation.
- Nearest-neighbour label consistency (clearly marked as weak-label diagnostic).
- Nearest-neighbour product-domain distribution.
- Embedding norm distribution before/after normalization.
- Duplicate/near-duplicate nearest-neighbour rate.
- Optional visualization (UMAP/t-SNE) for qualitative inspection only; never use a plot as proof of improved semantic structure.

Calculate these diagnostics on validation data and/or a dedicated held-out human-judged set. Do not use test diagnostics to choose models. Avoid interpreting a larger same-label cosine similarity as semantic improvement without human relevance evidence.

### 13.7 Statistical comparison and robustness

Where feasible:
- Use paired bootstrap resampling over the same query set to estimate confidence intervals for differences in MRR/nDCG/Recall.
- Compare models on identical queries and candidate galleries.
- Report random seeds and variability across at least multiple seeds for the selected final configuration if compute allows.
- Report per-domain/per-class support; do not hide sparse cells in a single aggregate.
- Inspect failure cases, especially false positives caused by weak labels and false negatives caused by related complaints carrying different weak labels.

If the schedule does not permit multiple seeds or confidence intervals, state that limitation rather than implying statistical significance.

### 13.8 Required result tables in the final report

**Table A — Retrieval performance (weak-label proxy)**

| Model | P@5 | R@5 | P@10 | R@10 | MRR@10 | nDCG@10 | Query coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Supervised XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Pairwise InfoNCE | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

**Table B — Human-adjudicated semantic retrieval**

Use the same model rows, but fill only after human relevance judgments are collected. Include graded nDCG where applicable, rater agreement, adjudicated query count and confidence intervals if computed. Never copy weak-label metrics into this table.

**Table C — Cross-domain retrieval by query domain**

| Model | Query domain | Eligible queries | Cross-domain candidate count | R@5 | R@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|---:|---:|
| Each evaluated model | Each supported domain | Pending | Pending | Pending | Pending | Pending | Pending |

Include only supported settings and explicitly list unsupported settings with the reason.

**Table D — Embedding diagnostics**

| Model | Positive cosine mean | Negative cosine mean | Separation | NN weak-label consistency | Duplicate NN rate |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| SimCSE XLM-V | Pending | Pending | Pending | Pending | Pending |
| SupCon same-domain | Pending | Pending | Pending | Pending | Pending |
| SupCon cross-domain | Pending | Pending | Pending | Pending | Pending |

**Table E — Efficiency**

| Model | Train time | Peak VRAM | Embedding throughput | Index build time | Query latency |
|---|---:|---:|---:|---:|---:|
| Frozen XLM-V | Pending | Pending | Pending | Pending | Pending |
| Each contrastive model | Pending | Pending | Pending | Pending | Pending |

All values remain `Pending` until generated from actual run artifacts. Do not fill tables with expected or illustrative numbers.

### 13.9 Required interpretation in the final research report

The report must answer all of these questions:

1. Did contrastive learning improve retrieval over frozen XLM-V?
2. Did it improve over TF-IDF?
3. Did it improve over the supervised classifier representation?
4. Which objective performed best, and on which evaluation track?
5. Did same-domain and cross-domain positive sampling behave differently?
6. Did gains hold on human-adjudicated semantic relevance, or only on weak-label proxy metrics?
7. Which domains/classes improved, regressed or were unsupported?
8. Did classification quality change after contrastive fine-tuning?
9. What was the compute cost and inference latency?
10. What failure modes remain, and what can the evidence legitimately support?

A valid conclusion may be that contrastive learning did not improve retrieval under the current weak-label construction. That is a useful research result if the experiment is controlled and reported honestly.

### 13.10 Decision rule for model promotion

Do not promote a contrastive checkpoint just because training loss decreases.

Promote it for retrieval only if:
- It passes data/split/leakage checks.
- It beats or provides a justified trade-off against frozen XLM-V on the predeclared validation retrieval metrics.
- It does not rely on unsupported class/domain cells.
- Its human-adjudicated semantic results, when available, support the intended claim.
- Its checkpoint and training manifest are reproducible.
- It meets application latency and memory constraints.

If weak-label metrics improve but human semantic metrics do not, do not claim improved semantic similarity. Investigate label overfitting and revise pair construction.

### 13.11 Required repository artifacts

The agent must add/update these documents and artifacts as experiments progress:

- `docs/CONTRASTIVE_RETRIEVAL_RESEARCH_PROTOCOL.md` — hypotheses, objectives, pair construction, metrics and split policy.
- `docs/RETRIEVAL_EXPERIMENT_REPORT.md` — result tables, figures, interpretation, limitations and exact run references.
- `docs/EMBEDDING_ANALYSIS_REPORT.md` — embedding diagnostics and qualitative failure analysis.
- `reports/retrieval/<run_id>/run_manifest.json` — immutable run metadata.
- `reports/retrieval/<run_id>/metrics.json` — machine-readable metrics.
- `reports/retrieval/<run_id>/predictions.parquet` or a privacy-approved equivalent — query/candidate rankings and relevance targets, without unnecessary raw text.
- `reports/retrieval/<run_id>/logs/` — training/evaluation logs where repository policy permits.

Do not commit private complaint text or large embeddings/checkpoints. Keep large artifacts in approved storage and reference them by immutable IDs and checksums.

### 13.12 Acceptance gate for the contrastive retrieval contribution

The contrastive retrieval contribution is accepted only when:
- At least one SimCSE and one supervised contrastive run have completed and reload successfully.
- Frozen XLM-V and TF-IDF retrieval baselines are evaluated on the same query/gallery protocol.
- Contrastive models are evaluated using the same protocol.
- Weak-label and human-adjudicated retrieval results are clearly separated.
- In-domain and feasible cross-domain results are separately reported.
- Embedding diagnostics and failure cases are included.
- Result tables are populated only from reproducible run outputs.
- The report states whether H1/H2/H3 were supported, not supported or inconclusive.

Until these criteria are met, describe the work as an implemented experiment or pilot, not as a demonstrated improvement.


---

# Shared cluster training, artifact handling and audit protocol

**Priority: mandatory.** The research cluster is shared. Every agent action must be non-interfering, quota-aware, attributable, reproducible and reversible. These instructions apply to data preparation, training, validation, evaluation, indexing and demo inference.

## 1. Credential and access security

- Never place passwords, private keys, tokens, SSH config containing secrets, or credential-bearing command lines in this repository, Markdown handovers, logs, notebooks, screenshots, issue comments or experiment manifests.
- A password was inadvertently included in a chat message. Treat it as compromised: the account owner must change/rotate it immediately through the approved process. Do not reuse it or copy it into agent instructions. If password authentication is allowed, use the institution's approved secret-entry mechanism; never pass the password as a command-line argument or environment variable.
- Prefer an owner-provisioned SSH key with a passphrase and restrictive permissions, subject to cluster policy. Do not generate, upload, install or authorize a key without the account owner's explicit approval.
- The coding agent must not attempt to log in until the owner has separately supplied access through an approved secure channel and confirmed authorization. This document deliberately contains no host, username or password.
- Never use sshpass, plaintext credential files, shell history entries containing secrets, or automated password prompts recorded by terminal logs.
- Do not print environment variables wholesale, inspect unrelated users' processes/files, or copy credentials into GitHub Actions.
- If a secret is found in tracked files or logs: stop, restrict access, notify the owner, rotate/revoke it, remove it from the current working tree and arrange history remediation. A new commit deleting the text does not erase it from Git history.

## 2. Hard safety boundaries

The agent may perform read-only inspection first. It must stop and request owner approval before:
- creating persistent directories on cluster storage;
- copying datasets, checkpoints, indexes or containers to the cluster;
- installing packages or creating environments on shared storage;
- submitting any Slurm job, including smoke tests;
- starting a persistent process or network service;
- creating Kubernetes resources or opening a port/tunnel;
- changing permissions, quotas, retention or storage policy;
- deleting, overwriting, moving or cleaning any existing artifact.

Never:
- use sudo or privileged containers;
- modify system Python, global packages, drivers, CUDA, modules, Slurm or Kubernetes configuration;
- use another user's directories, caches, processes, allocations or credentials;
- run training on a login node;
- use broad cleanup commands or wildcard deletion, recursive chmod/chown;
- kill processes by broad name/pattern;
- consume all available CPUs, memory, GPUs, disk or shared filesystem bandwidth;
- run multiple training jobs concurrently unless the owner and scheduler allocation explicitly permit it;
- assume that an installed Docker/Kubernetes command means permission to use the service.

No action may interfere with other people's workloads. If resource ownership or a path is ambiguous, stop.

## 3. Preflight: read-only inspection

Run only after approved account access, and save output in an owner-approved local/private project record with secrets redacted. Do not dump sensitive environment variables.

Suggested checks:
- whoami, hostname, pwd
- module avail and module list
- sinfo -o "%P %a %l %D %G"
- squeue -u "$USER"
- nvidia-smi -L and nvidia-smi only where permitted
- df -h for approved mount points
- quota -s if available and permitted
- inspect repository git status, branch and commit
- confirm approved project storage, project quota, retention policy and scratch policy with the administrator

Do not inspect other users' home directories or process command lines. Do not infer a writable path from df; obtain the approved path from the administrator/owner.

Record:
- inspection timestamp and timezone;
- account identity (no credentials);
- repository URL, branch and commit;
- approved partition/QOS and resource limits;
- approved storage mount and quota;
- module/environment versions;
- GPU/MIG visibility from within an authorized allocation;
- outstanding permission or quota questions.

## 4. Environment isolation and loading

Use only an environment owned by this project in an approved project location, or an administrator-provided immutable container/environment. Do not alter shared base environments.

Before creating an environment:
1. Confirm the permitted location and quota.
2. Inspect repository dependency files and lock files.
3. Confirm the Python/CUDA/PyTorch compatibility matrix with the project tests and cluster-supported modules.
4. Ask before downloading large model weights or package caches.
5. Pin dependencies and record exact versions.

A possible module-loading pattern, only if the administrator confirms these exact modules are approved for the account:

    module load anaconda3-2025
    module load cuda-12.8

Do not blindly execute this if module names differ. Do not install another CUDA toolkit or PyTorch build over a working shared installation.

Set project-specific cache/temp locations only after their directories have been approved and created:
- HF_HOME
- TRANSFORMERS_CACHE if required by the pinned Transformers version
- TORCH_HOME
- XDG_CACHE_HOME
- TMPDIR

Never point caches at another user's home or a shared global cache for writes. Do not set these variables to guessed paths. Do not print tokens or secrets when inspecting environment configuration.

Before any GPU work, verify from inside the approved allocation:
- Python version;
- Python package versions for torch, transformers, tokenizers, accelerate and relevant project dependencies;
- torch.cuda.is_available();
- visible device count and device name;
- CUDA runtime reported by PyTorch;
- a small allocation/forward/backward smoke test using a synthetic batch.

Do not assume host nvidia-smi visibility means the scheduled job has GPU access. The job's visible devices and Slurm allocation are authoritative.

## 5. Storage layout, quotas and artifact lifecycle

Use only administrator-approved project-owned paths. Keep source checkout, immutable source data, run outputs, checkpoints, retrieval index, logs and temporary cache logically separate.

Required safeguards:
- record free space and quota before and after each stage;
- estimate checkpoint, optimizer-state, cache and log growth before launching;
- keep raw data read-only;
- never edit the frozen dataset or split manifests in place;
- use unique run directories; never reuse a completed run directory;
- write outputs to a temporary file in the same project-owned filesystem, verify it, then atomically rename into its final run path;
- preserve the last known-good checkpoint until the new checkpoint passes load/evaluation checks;
- use explicit retention limits approved by the owner;
- do not delete intermediate artifacts automatically;
- do not write large embeddings/checkpoints to Git or the repository checkout;
- do not put temporary files in /tmp unless policy and capacity are confirmed.

Before a run, record estimated disk requirements. If quota/free space is insufficient or unknown, do not launch.

## 6. Dataset and leakage controls

- Treat the frozen dataset, split manifest and duplicate-cluster catalog as immutable inputs.
- Verify expected file hashes and row counts before training.
- Run Phase 7 split feasibility and duplicate/leakage audits from a clean checkout.
- Verify no duplicate cluster, complaint ID, narrative hash or source group crosses partitions according to the committed protocol.
- Fit preprocessing, vocabulary/statistical transforms and pair samplers on training data only.
- Build contrastive training pairs from train only. Validation/test examples must never enter training pairs, queues, hard-negative mining, normalization fitting or training gallery.
- Validation queries retrieve against the training gallery. Final test queries retrieve against the training gallery after the model/config is frozen.
- Keep human semantic evaluation items held out from model development unless an explicit annotation/training protocol permits otherwise.
- CFPB labels are weak administrative labels. Report weak-label proxy metrics separately from human-adjudicated semantic relevance.
- Do not claim multilingual complaint performance from this English-only corpus.

If any leakage check fails or cannot be reproduced, stop training and report the exact failing artifact and evidence.

## 7. Controlled training sequence

Do not launch the complete experiment matrix at once. Execute one gated stage at a time.

### Gate A — clean checkout and software tests
- Fetch the intended branch and record exact commit SHA.
- Confirm clean working tree and no secrets.
- Run formatting, lint, type checks and unit tests supported by the repository.
- Run data schema, split, duplicate and Phase 7 audits.
- Save complete test output and exit codes.
- Resolve failures before GPU allocation.

### Gate B — CPU data and pair-manifest validation
- Generate deterministic pair manifests from training data only.
- Exclude duplicate-cluster and shared-source pairs.
- Record anchor/positive/negative IDs, labels, domains, sampling mode, supervision source, seed, dataset hash and split.
- Check counts, nulls, invalid IDs, class/domain support and false-negative risk.
- Review a privacy-approved sample of pair metadata; do not export complaint text unnecessarily.
- Verify every referenced record belongs to train.

### Gate C — approved GPU smoke test
Only after explicit owner approval and scheduler allocation:
- request one conservative approved MIG slice, initially 1g.24gb if confirmed available;
- request only the minimum permitted CPU and RAM;
- use a synthetic batch first;
- verify model/tokenizer loading, forward pass, loss, backward pass, optimizer step, checkpoint save, checkpoint reload and deterministic inference;
- measure peak allocated/reserved VRAM, host RAM, step time and throughput;
- terminate the job normally and verify it no longer runs.

No full dataset epoch during the smoke test.

### Gate D — baseline and pilot training
Run sequentially, not concurrently:
1. TF-IDF retrieval baseline (CPU).
2. Frozen XLM-V embedding baseline.
3. SimCSE pilot.
4. Same-domain supervised contrastive pilot.
5. Cross-domain supervised contrastive pilot only if class/domain support and pair audits pass.
6. Pairwise InfoNCE/triplet only if it adds a distinct, justified comparison.
7. Classifier evaluation independently.

Use a small, deterministic pilot before full training. Do not launch a full run until the pilot's loss, gradients, memory, throughput, validation path and checkpoint reload are verified.

### Gate E — full training
For each run:
- use one scheduler allocation at a time unless additional parallelism is explicitly approved;
- record run ID, git commit, config hash, data/split/pair manifest hashes, model/tokenizer revision, seed, job ID and resource request;
- record start/end times, exit code, stdout/stderr paths, loss history, validation metrics, GPU/CPU/RAM/disk usage and checkpoint hashes;
- checkpoint at documented intervals and preserve a last-known-good checkpoint;
- use early stopping/model selection on validation only;
- never evaluate the test set repeatedly to select hyperparameters;
- if a job is preempted or fails, record the failure and resume only from a verified compatible checkpoint;
- do not silently change config mid-run.

### Gate F — evaluation and final test
- Compare TF-IDF, frozen XLM-V, classifier representations and contrastive variants with identical query/gallery definitions.
- Report in-domain and feasible cross-domain results separately.
- Report Precision@K, Recall@K, MRR@10, nDCG@K where relevant, query coverage, per-domain/class support and excluded cells.
- Keep weak-label proxy and human semantic metrics separate.
- Use validation for selection. Run final test evaluation once after locking the model/configuration.
- Save predictions/metrics and manifests with hashes; restrict access to raw complaint text.
- Include error analysis and confidence intervals where feasible.
- Do not promote a model based only on lower training loss or higher weak-label consistency.

## 8. Slurm job submission controls

The agent must inspect the site's Slurm policy and use the approved partition, QOS, account, time limit, memory and GPU resource syntax. Do not guess scheduler flags or request resources beyond authorization.

Before submission, present the exact proposed job script and resource request to the owner for approval. Use a unique job name and run ID. The job script must:
- fail fast with strict shell error handling;
- print job ID, host, timestamp, commit and non-secret environment versions;
- use only the approved project working/output directories;
- never echo credentials or all environment variables;
- set conservative CPU thread limits where appropriate;
- write logs to the run-specific directory;
- record the exit status;
- avoid automatic deletion or broad cleanup;
- terminate only its own child processes on normal scheduler termination.

After submission, record job ID, requested resources, actual allocation, exit state and log locations. Cancel only the exact job ID owned by this project and only after owner authorization or an established approved cancellation policy.

## 9. Testing requirements

Every stage must include:
- unit tests for changed code;
- integration tests for data/model/API boundaries;
- regression tests for discovered bugs;
- reproducibility check from a clean checkout;
- checkpoint save/reload test;
- resource and failure-path tests where applicable.

Specific ML checks:
- loss is finite;
- gradients are finite and non-zero where expected;
- optimizer updates parameters;
- train/validation/test boundaries are enforced;
- pair sampler is deterministic for a fixed seed;
- duplicate/source exclusions work;
- embedding dimensions, normalization and similarity are consistent;
- index IDs map to the correct metadata;
- no test data enters training or gallery;
- validation/test predictions are generated from the intended checkpoint.

Specific app checks:
- startup fails clearly if artifacts are missing or mismatched;
- readiness does not report healthy before all required models/indexes load;
- input size and request rate are bounded;
- errors do not expose stack traces, paths, secrets or complaint contents;
- no raw input text is logged;
- service can stop and restart without retraining;
- API tests use synthetic or approved redacted fixtures.

## 10. Logging, provenance and audit trail

Every run must have a unique immutable run directory, for example:

    runs/<run_id>/
      run_manifest.json
      config.yaml
      environment.txt
      git.txt
      data_audit.json
      pair_audit.json
      train.log
      validation_metrics.json
      test_metrics.json
      resource_usage.json
      checkpoint_manifest.json
      checksums.sha256
      tests.log
      status.json

The exact location must be approved. This is a schema, not permission to create a path.

run_manifest.json must record:
- run ID and purpose;
- UTC start/end times;
- repository, branch and exact commit SHA;
- dirty/clean working-tree status;
- Python and dependency versions;
- CUDA/PyTorch/Transformers versions;
- model and tokenizer IDs/revisions;
- dataset, split and pair-manifest hashes;
- config hash and random seeds;
- Slurm job ID, partition/QOS and allocated resources;
- command used to launch;
- output artifact paths and checksums;
- metrics and test status;
- exit code and failure reason, if any.

Logs must not contain passwords, tokens, private keys, raw complaint narratives, unnecessary personal data or unrestricted environment dumps. Use structured, timestamped logs. Record metrics and identifiers rather than complaint content. Keep access permissions restrictive and retention consistent with institutional policy.

## 11. Git and commit discipline

- Work only in the designated project repository and approved feature branch.
- Never commit credentials, raw complaint data, private metadata, checkpoints, vector indexes, caches, logs containing sensitive content or generated datasets.
- Maintain .gitignore and scan staged changes for secrets and large files before every commit.
- Commit source, tests, configs, documentation, schemas and small reproducibility manifests.
- Record the commit SHA in every experiment manifest.
- Use small, reviewable commits with descriptive messages.
- Do not force-push, rewrite shared branch history, delete branches or merge PRs without owner approval.
- Do not report a commit/merge unless GitHub confirms its exact SHA.
- Every PR must include changed files, rationale, tests run, data impact, resource impact, privacy impact and rollback instructions.

## 12. Stop conditions and incident response

Immediately stop the current project job and notify the owner if:
- the allocation differs from what was approved;
- unexpected GPU/CPU/RAM/disk usage appears;
- quota or filesystem pressure is observed;
- a process appears to affect another user's workload;
- any path is outside approved project storage;
- secrets or raw complaint text appear in logs, commits or public outputs;
- split leakage or data corruption is detected;
- the job hangs, repeatedly restarts or exceeds its approved wall time;
- an unexpected permission or ownership change is encountered.

Stop only the project's own job/process by its exact scheduler job ID or PID. Never kill an unknown process. Preserve relevant non-sensitive logs, record the incident and do not retry until the cause is understood and the owner approves.

## 13. Stage report and approval gates

After each gate, return:
1. PASS / PARTIAL / BLOCKED.
2. Exact commit SHA and changed files.
3. Commands executed and exit codes.
4. Tests/audits and their outputs.
5. Job IDs and resource usage, if a job was approved.
6. Data/split/pair-manifest hashes.
7. Artifact paths and checksums.
8. Failures, risks and corrective action.
9. Storage usage before/after.
10. Explicit next action requiring approval.

The agent must not advance to full training, test-set evaluation, persistent serving or Kubernetes deployment without owner review at the corresponding gate.

**Default rule: inspect first, propose exact action, wait for approval, execute narrowly, verify, record, then stop.**
