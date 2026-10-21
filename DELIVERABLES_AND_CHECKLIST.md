# Phase Gates and Deliverables

## Phase A — current
- [ ] Inspect repository/Git status/.gitignore/dependencies and existing data.
- [ ] Verify official source URLs, revisions/configs, licenses/terms and download methods.
- [ ] Inventory/checksum every source file.
- [ ] Record actual schema, counts, examples, missingness, length, labels, domain, language/script.
- [ ] Preserve original labels; review taxonomy and source mappings.
- [ ] Audit privacy, duplicates, near-duplicates, parallel examples and leakage.
- [ ] Record exclusions with reasons.
- [ ] Build reproducible canonical dataset and scripts.
- [ ] Create a separate split manifest for each approved experiment.
- [ ] Report split sizes and class support; verify no group leakage.
- [ ] Reconcile source, retained, excluded and split totals.
- [ ] Save configs, checksums, tests and dataset card.
- [ ] Complete `docs/baseline_data_readiness.md`.
- [ ] Stop for explicit user approval before model work.

Phase A is accepted only when sources, label space, eligibility, counts, exclusions, language/domain coverage, split policy, leakage controls, limitations and test results are explained. Unknowns remain explicit.

## Phase B — after approval
- [ ] Confirm frozen data release hashes/manifests.
- [ ] Record actual Colab hardware/runtime.
- [ ] Verify XLM-V checkpoint/tokenizer compatibility.
- [ ] Confirm head size matches label map.
- [ ] Run smoke test, then baseline training.
- [ ] Train only on train; select using validation.
- [ ] Evaluate frozen test once.
- [ ] Save configs/logs/metrics/predictions/model artefacts.
- [ ] Perform error analysis and document limitations.
- [ ] No contrastive learning or retrieval.

## Required docs
`docs/repository_audit.md`, `docs/dataset_card.md`, `docs/label_taxonomy.md`, `docs/data_preparation_methodology.md`, `docs/baseline_data_readiness.md`, later `docs/baseline_results.md`, and README reproduction commands.

## Final status report
Phase/status; verified sources/revisions; files changed; actual counts and commands; label/split decisions; tests; blockers; gate status; smallest next step.
