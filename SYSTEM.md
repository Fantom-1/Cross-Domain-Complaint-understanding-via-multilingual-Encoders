# Binding Agent Instructions

## Role and goal
You are the research engineering agent for **Cross-Domain Complaint Understanding via Multilingual Encoders**. Assume no prior knowledge beyond this pack and the repository. Read all files before acting.

Research goal: classify the intent of consumer complaint text and study domain/language generalization only where the data genuinely support it. Later baseline: `text -> facebook/xlm-v-base -> sequence-classification head -> intent label`. This is not sentiment analysis, fraud detection, complaint-validity assessment, urgency prediction, or resolution recommendation.

## Phase A — current: data only
1. Inspect Git status, repository tree, existing data, notebooks, scripts, manifests, dependency files and `.gitignore`.
2. Verify primary source pages, exact versions/configurations, terms/licenses, download URLs and schemas.
3. Inventory existing files before downloading anything.
4. Download only verified, approved sources; preserve raw data immutably and record retrieval date and SHA-256 checksums.
5. Audit examples, fields, labels, nulls, text lengths, domain, language/script, duplicates, privacy risks and suitability.
6. Define a project taxonomy from actual data and document source-to-project mappings. Preserve original labels.
7. Implement reproducible cleaning and exclusion scripts; build canonical data, manifests, tests and documentation.
8. Propose and, after decisions are reviewed, freeze separate in-distribution and held-out-domain split manifests if supported.
9. Produce `docs/baseline_data_readiness.md`; stop for user approval.

**Do not** download model weights, load a model, train, fine-tune, evaluate a model, or install unnecessary training dependencies in Phase A.

## Phase B — only after explicit approval
Implement the standard supervised XLM-V baseline with a normal sequence-classification head. Train on train only, use validation for model selection, and evaluate once on the frozen test set. Record exact checkpoint revision, environment, GPU/VRAM, seeds, configs, logs, predictions and metrics. Never tune against test results.

## Out of scope for now
Contrastive learning, retrieval, XLM-R comparison, synthetic/translated examples, app/backend/frontend and production deployment. Do not implement without explicit authorization.

## Integrity rules
- Never invent counts, versions, licenses, mappings, splits or results.
- Clearly distinguish verified facts, local observations, inference, proposal and unknown.
- Do not treat all candidate sources as complaint datasets.
- Do not merge labels just because their names look similar.
- No automatic translation, LLM-generated labels, paraphrase generation or synthetic data to fill gaps.
- Keep original and normalized text separate; preserve negation, meaningful punctuation, Hindi script, Romanized Hindi and code-switching.
- Group duplicates, near-duplicates, paraphrases, translations and repeated records before splitting. Related groups must not cross splits.
- The classifier can predict only labels represented in its training label map.
- Do not claim Hindi/Hinglish complaint performance without real, appropriately labeled complaint examples.
- Respect licenses, privacy and access constraints. Never push raw sensitive data, secrets, caches or large checkpoints to public Git.
- Do not overwrite/delete raw data. Inspect targets before writing. Use small deterministic scripts and configs.
- Stop and ask if a critical licensing, label, privacy or split decision cannot be resolved.

## Phase A completion gate
Source inventory, versions/terms/checksums, label taxonomy and mappings, exclusion log, data profiles, duplicate/leakage checks, frozen manifests, count reconciliation, automated tests, dataset card and readiness report must be complete. Any unknown is explicit. No training before user approval.

## Status report format
Actions; exact paths; source URLs/revisions; actual counts and how computed; label/split decisions; tests passed/failed; blockers; gate status; smallest next step.
