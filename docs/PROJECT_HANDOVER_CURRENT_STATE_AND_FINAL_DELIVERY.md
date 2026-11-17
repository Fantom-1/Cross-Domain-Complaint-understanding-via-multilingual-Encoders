# Project Handover: Current State, Controlled Execution, and Final Delivery

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Canonical repository:** https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders  
**Primary encoder:** `facebook/xlm-v-base`  
**Document purpose:** Single source of truth for the coding agent, training agent, reviewer, and project owner  
**Status date:** 17 November 2026

## Operating instruction

Execute this as a controlled research-to-deployment workflow. Do not broaden scope, replace the dataset, change the research question, introduce new models without approval, or skip validation gates.

Final capabilities:
1. Intent classification (16 CFPB-derived administrative weak-label categories).
2. Evidence-grounded structured complaint summarization.
3. Similar-complaint retrieval, with cross-domain retrieval as the central research focus.

The main research contribution is contrastive representation learning for cross-domain complaint understanding and retrieval using XLM-V. The application is the delivery vehicle, not the research contribution by itself.

The agent must use only the canonical repository above; never use `AbdulMalik1287/NLP`. Inspect current branch, commits, PRs, CI and working tree before edits. Preserve merged Phase 0–6 artifacts and frozen data/splits. Do not commit raw complaint narratives, datasets, checkpoints, indexes, secrets, tokens, private paths or server details. Never claim a test, training run, metric or deployment succeeded without logs and reproducible evidence.

**No training or deployment is authorized by this document alone.** The owner provides access and explicitly approves resource-consuming jobs and deployment actions.

## 1. Current verified position

### Repository snapshot

At the latest inspection:
- PR #9 (Phase 7) is closed and merged into `main`; merge commit `573e1587a6c4b94d09496f41ac5b291d756f560f`.
- Feature branch `feature/contrastive-retrieval-engine` exists.
- Inspected feature head: `1891859fa69b0ec1664349ec5e4977e7f687ed91`.
- At comparison time, the feature branch was 27 commits ahead of `main`, 0 behind.
- The feature branch contains contrastive, retrieval, summarization, API and CI changes that require complete review and tests before merge.
- Latest observed feature commit: `Add duplicate-aware unsupervised SimCSE trainer`.

This is a snapshot, not a guarantee of current branch state. Fetch and re-check before work.

### Data foundations

Merged phases:
- Phase 0–3: data specification, provenance, parsing/validation and profiling.
- Phase 4: XLM-V tokenizer/truncation analysis.
- Phase 5: exact/near-duplicate detection and leakage controls.
- Phase 6: weak-label taxonomy and blinded annotation materials.
- Phase 7: split feasibility, domain-confounding and temporal-boundary audit; PR #9 merged.

Frozen baseline reported by project:
- 45,723 CFPB narratives.
- 16 administrative weak-label intent categories.
- 9 financial product domains.
- Train 32,019; validation 6,852; test 6,852.
- English-only corpus.

Phase 5 reported 43,142 duplicate partitions, 692 multi-item clusters and zero cross-partition duplicate-cluster/text-hash leakage. Phase 6 produced taxonomy and blinded annotation materials, including a 320-item pilot manifest. Actual human annotation/adjudication remains outstanding.

Phase 7 reports 9×16=144 class-domain cells, 81 zero-support cells (56.25% sparsity), 36 continuous months from May 2018 to April 2021, and structural confounding for some leave-one-domain-out settings including debt_collection and mortgage. Hindi/Hinglish remains deferred pending authentic complaint data.

The agent must run the committed Phase 7 audit from a clean checkout and verify its inputs/output. A report marked PASS is not proof that the current checkout passes.

### Classifier history

Historical supervised XLM-V artifacts record test Macro-F1 ≈0.5369, weighted-F1 ≈0.5340, accuracy ≈0.5325 on 6,852 rows. Historical run records mention one 1g.24gb MIG allocation and approximately 15.6 GB peak VRAM. These results have not been independently reproduced in this work session. Locate and checksum-verify the external checkpoint before treating it as deployable.

Reconcile the reported tokenizer vocabulary conflict: Phase 4 reports 901,629, while an older README statement reportedly says 2.5M. Verify the pinned tokenizer revision and update docs based on evidence.

## 2. Research framing and caveats

Central question:

Does contrastive fine-tuning of XLM-V produce complaint representations that improve similar-complaint retrieval, particularly across financial product domains, compared with TF-IDF and frozen XLM-V representations, while preserving or improving intent classification?

CFPB Product/Issue/Sub-issue mappings are administrative weak labels, not semantic ground truth:
- Same-label complaints are not automatically semantically equivalent.
- Different-label complaints are not automatically unrelated.
- Weak-label retrieval metrics must be labelled proxy metrics.
- Human-adjudicated semantic relevance must be evaluated separately.

The frozen corpus is English-only. A multilingual encoder does not make the dataset multilingual. Do not claim Hindi/Hinglish or multilingual generalization without authentic multilingual complaint data and suitable evaluation.

The class/domain matrix is sparse. Do not report naive all-class leave-one-domain-out results where held-out classes have no training support. Report supported cells, unsupported cells, query coverage and denominators.

## 3. Final system scope

### A. Intent classifier
Input complaint narrative. Output predicted intent, top-k scores, model version and weak-label warning.

Evaluation: Macro-F1 primary; accuracy, weighted-F1, per-class precision/recall/F1, support and confusion matrix. Compare TF-IDF + Logistic Regression, supervised XLM-V and any contrastive encoder plus classifier. Use validation for selection; test only after decisions are frozen.

### B. Structured summarizer
Initial deliverable is conservative, evidence-grounded structured summarization, not unsupported free-form generation.

Fields:
- Problem description.
- Customer concern.
- Timeline/events when stated.
- Requested resolution when stated.
- Supporting evidence/source sentence references.
- Short summary.
- Missing information/uncertainty notes.

Never invent dates, people, amounts, causes, commitments or resolutions. If absent, return “not stated”. Preserve chronology. Human-review factuality, coverage, chronology, omissions and usefulness. ROUGE/BERTScore are secondary if references exist.

### C. Similar complaint retrieval
Input narrative, optional product-domain filter and top-k. Output ranked complaint IDs, similarity score, domain, available intent label and whether relevance is weak-label or human-validated. Display text only where policy permits.

Compare:
1. TF-IDF cosine.
2. Frozen XLM-V.
3. SimCSE-style XLM-V.
4. Supervised contrastive XLM-V.
5. Pairwise InfoNCE XLM-V.
6. Cross-domain positive-sampling variant only for supported classes/domains.

Metrics: Precision@K, Recall@K, MRR@K, nDCG@K and query coverage. Development uses validation queries against training gallery. Final uses test queries against training gallery after model/config freeze. Do not include validation/test complaints in the training gallery for this benchmark.

### D. API
Required routes:
- `GET /health`
- `POST /predict`
- `POST /summarize`
- `POST /retrieve`
- `POST /analyze`

The API loads fixed, versioned artifacts at startup. It does not train at request time.

### E. Deployable application
Deliver backend, minimal usable frontend or API demo, Docker image/build instructions, Kubernetes Deployment/internal Service manifests subject to permissions, versioned model bundle/index, readiness checks, configuration via environment variables/secrets, privacy-safe logging, and access controls before public exposure.

## 4. AI Node preparation

The supplied internal specification describes one AI node with:
- 2 × NVIDIA RTX PRO 6000 Blackwell Server Edition physical GPUs.
- Each GPU split into eight 1g.24gb MIG instances (16 total).
- 24 CPU cores and approximately 306 GB RAM.
- Slurm 24.05.4, gpu/cpu partitions, per-node GRES string `gpu:1g.24gb:8`.
- Kubernetes, Docker and NVIDIA Container Toolkit.
- CUDA toolkit module 12.8; GPU PyTorch listed as 2.11.0+cu12.8.
- Modules including anaconda3-2025, cuda-12.8 and miniconda3.

This is one node with two physical GPUs, not evidence of two physical nodes. Verify account, QOS, quota, MIG availability, writable storage and Kubernetes permissions live. Keep confidential server details in authorized institutional channels; do not commit hostnames, access IPs, usernames, credentials or private paths.

### Read-only preflight (after approved SSH access)

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

Use project-owned Conda/venv or approved containers. Do not change shared modules, drivers, system Python, CUDA, Slurm or Kubernetes configuration. Verify actual PyTorch/CUDA compatibility inside an allocation. Pin package versions only after smoke tests.

Start with one 1g.24gb MIG slice. Measure device visibility, memory, step time, CPU/RAM, storage, checkpoint save/reload. Scale only if allowed and measured useful. Multi-GPU training requires tested DDP/process launch/distributed sampling/checkpoint coordination; requesting more GPUs does not make a single-process trainer distributed.

Separate source, environment, read-only data, logs, checkpoints, retrieval index, model bundles, images and reports. Check quotas before training. Never commit data, complaint text, weights, indexes or secrets.

## 5. Controlled stages and gates

The agent must complete each stage and report evidence before moving on. If a gate fails, stop, fix, rerun and report. No silent workarounds.

### Stage 0 — repository baseline and scope lock
1. Fetch latest main and feature branch.
2. Record SHA, clean/dirty status, divergence, PRs and CI.
3. Inspect implementation; do not duplicate modules.
4. Run tests and static checks.
5. Confirm Phase 7 merge and run its audit.
6. Reconcile tokenizer documentation conflict.
7. Produce verified/failed/missing/unverified report.

**Gate 0:** clean tree, exact SHA, test/CI status, Phase 7 audit evidence or blocker, no scope drift.

### Stage 1 — server preflight and environment lock
1. Confirm account, partition, QOS and GPU allocation.
2. Confirm storage and quota.
3. Load approved modules.
4. Verify PyTorch/CUDA/MIG visibility in Slurm.
5. Create project-owned environment/container.
6. Test tokenizer/model load, forward, backward, optimizer step, checkpoint save/reload.
7. Record versions and peak memory.

**Gate 1:** one MIG smoke job exits 0, job ID/logs exist, checkpoint reloads, no system changes, environment lock committed. Request owner approval before GPU submission if not already granted.

### Stage 2 — frozen data release
Verify canonical checksum, exact 45,723 IDs and split counts, unique IDs, split values, cluster completeness, no cluster/group crossing, all 16 labels and 9 domains, all 144 cells including zero cells. Re-run Phase 1–7 tests/audit. Freeze versioned manifest; do not overwrite splits.

**Gate 2:** all invariants pass, hashes recorded, immutable experiment data release.

### Stage 3 — baselines and classifier verification
Run TF-IDF + Logistic Regression. Locate historical XLM-V checkpoint, verify checkpoint/tokenizer/label-map compatibility and hashes. Reproduce validation results where possible. Historical test metrics remain labelled historical/unreproduced unless verified. Save per-class metrics and confusion matrix.

**Gate 3:** baselines reproducible or explicitly unverified; no fabricated metrics; split discipline respected.

### Stage 4 — contrastive pair generation
Generate deterministic train-only pairs. Exclude identical IDs, shared duplicate clusters and source groups. Record pair IDs, labels, domains, sampling mode, supervision type, seed and dataset version. Start with same-domain weak-label positives. Cross-domain positives only where supported. Treat weak negatives cautiously. Report pair counts by class/domain/type and inspect samples.

**Gate 4:** all IDs resolve to train; no cluster/group overlap; deterministic auditable manifest; unsupported cells not silently filled.

### Stage 5 — contrastive pilots
Minimum: SimCSE-style dropout baseline, supervised contrastive XLM-V, pairwise InfoNCE comparison. Start small. Save commit SHA, configs, seed, data/pair hashes, model revision, batch/length/temperature/objective/optimizer, loss, runtime, peak VRAM, checkpoint checksum and validation metrics. Scale only after smoke success; avoid broad sweeps.

**Gate 5:** at least one valid SimCSE and one supervised contrastive run complete, checkpoints reload, validation evaluation and run manifests exist.

### Stage 6 — retrieval benchmark
Compare TF-IDF, frozen XLM-V, SimCSE, supervised contrastive and InfoNCE if complete. Validation queries → training gallery; in-domain and feasible cross-domain separately; report query coverage/support/excluded cells. Freeze model/config, then test queries → training gallery once. Do not tune on test. Human relevance: blinded independent ratings, adjudication, agreement and separate semantic metrics.

**Gate 6:** baseline comparison, denominators and limitations documented; no unsupported cross-domain claim.

### Stage 7 — summarizer
Implement structured output with sentence traceability, explicit missing fields, and tests for short/long/malformed/contradictory/incomplete narratives. Human-review factuality, chronology, omissions and usefulness.

**Gate 7:** schema validated, reviewed sample shows no unsupported details, evaluation documented. Do not call an extractive baseline an LLM summarizer.

### Stage 8 — API/application
Define request/response schemas; load artifacts once at startup; implement all five routes; validate inputs and errors; retrieval searches across domains by default; add unit/integration tests; build minimal usable frontend/demo; verify exact release artifacts.

**Gate 8:** all endpoints pass; /analyze returns all three capabilities; no request-time training; artifact hashes verified; raw complaint text not logged by default.

### Stage 9 — container and deployment
Build approved runtime image; pin dependencies/tag; run non-root; mount model/index read-only; secrets external; test locally; deploy internal Kubernetes Service only after namespace/RBAC/storage permissions; readiness/liveness reflect actual model load; smoke-test; public ingress only after security/privacy approval.

**Gate 9:** reproducible image, exact bundle loads, rollout ready, internal smoke test and rollback/version procedure documented.

### Stage 10 — final delivery
Required: research report; data/provenance/split audit; pair-generation report; classification comparison; contrastive run manifests; retrieval report separating weak-label and human relevance; summarizer evaluation; model cards/release manifest; API docs; Docker/Kubernetes instructions; demo; clean repo/tag; reproduction handover.

**Gate 10:** every result traceable to code/config/data hash/log; no unsupported claims; fresh authorized checkout can run tests and start application with release artifacts.

## 6. Commit and PR discipline

Format: `<type>(<scope>): <imperative summary>`

Examples:
- `fix(data): enforce complete duplicate-cluster coverage`
- `feat(contrastive): add deterministic train-only pair sampling`
- `feat(contrastive): add supervised contrastive objective`
- `feat(retrieval): add retrieval metrics and benchmark runner`
- `feat(api): add complaint analysis endpoints`
- `test(deploy): add container and service smoke tests`
- `docs(research): document experiment protocol and limitations`

Every PR includes purpose, scope, commit SHA, changed files, actual commands/results, CI link and tested SHA, hashes, implemented-vs-executed distinction, limitations and confirmation test data was not used for training/model selection. Do not merge just because GitHub says mergeable. Require CI on exact head and review. Do not rewrite shared history without approval.

## 7. Mandatory agent progress report

At the end of each stage, report:

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
- Artifact/log paths:
- Evidence links:
- Passed criteria:
- Failed criteria:
- Known risks:
- Next proposed action:

Use only:
- **PASS** — all gate criteria satisfied with evidence.
- **BLOCKED** — cannot proceed safely; describe blocker and minimum resolution.
- **PARTIAL** — some criteria pass; list remaining items.
- **NOT RUN** — no execution evidence.

Distinguish implemented, unit-tested, integration-tested, executed on GPU, evaluated and deployed.

## 8. Review protocol

Owner supplies agent access and approves training/deployment. Owner shares progress, PR links, commit SHAs, CI runs, logs and experiment reports here.

At each requested check-in, reviewer:
1. Refreshes repository state and inspects new commits/PRs.
2. Compares changes with this handover and current gate.
3. Identifies blockers, regressions and scope drift.
4. Gives precise prioritized instructions.
5. States PASS/PARTIAL/BLOCKED.
6. Recommends next stage only when evidence supports it.

The reviewer does not claim continuous background monitoring. A review is triggered when the owner asks or shares progress.

Priority labels:
- **P0 Stop:** leakage, test misuse, security/privacy exposure, destructive data change, wrong repo, invalid scientific claim.
- **P1 Before next stage:** incorrect objective/pairs, broken training/evaluation, missing provenance, failing CI.
- **P2 Before release:** API edge cases, observability, packaging, docs.
- **P3 Improvement:** non-blocking refactor/speed/usability.

Every finding must include priority, file/function, evidence, required change, regression test and acceptance condition. Avoid vague “improve code” instructions.

## 9. Out of scope without approval

- Changing frozen data/splits or taxonomy.
- Replacing XLM-V as primary encoder.
- Multilingual claims without authentic multilingual data.
- Semantic retrieval claims from weak labels alone.
- Naive all-domain leave-one-domain-out despite confounding.
- Large unplanned hyperparameter sweeps.
- Training/model selection on validation/test data.
- Public deployment or public complaint-data exposure.
- System/server configuration changes.
- Committing raw data, checkpoints, indexes, secrets or confidential server details.
- Unrelated product features.

## 10. First instruction to the agent

**Do not start full training immediately. First produce the baseline and server readiness report.**

1. Fetch latest repo state; report branch/commit/PR/CI.
2. Confirm Phase 7 merge in main.
3. Inspect contrastive/retrieval/API branch and list exact files.
4. Run tests/static checks without changing shared infrastructure.
5. Run Phase 7 audit from clean checkout and attach logs.
6. Inspect trainers for model loading, loss, backward, optimizer, checkpoint save/reload and deterministic config.
7. Confirm authorized AI Node account, Slurm partition/QOS, MIG and writable storage.
8. Run read-only server preflight.
9. Ask for approval before GPU smoke submission if not already authorized.
10. Return Stage 0 and Stage 1 reports. Do not begin full training until accepted.

Then proceed sequentially through Stages 2–10. If any failure occurs, stop at that gate and propose the smallest safe correction.

## 11. Definition of final success

The three capabilities work together; classifier is compared with lexical baseline; contrastive training is reproducible and compared with frozen XLM-V and TF-IDF; cross-domain claims respect support; human semantic relevance is reported or explicitly limited; summarizer is evidence-grounded and human-reviewed; API and demo use a versioned model bundle; Docker/Kubernetes instructions are tested in the authorized environment; CI, run logs, hashes, reports and release metadata exist; a new authorized user can reproduce inference.

**Move quickly by reducing unnecessary experiments and preventing rework—not by skipping validation or making claims without evidence.**
