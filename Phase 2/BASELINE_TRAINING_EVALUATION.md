# Baseline Training and Evaluation Protocol

## Frozen baseline
`facebook/xlm-v-base` + standard sequence classification head + cross-entropy; no contrastive learning/retrieval/auxiliary task. Full encoder fine-tuning is the default. Output count derives from the frozen label map.

## Data contract
- Read only versioned frozen train/validation/test files.
- Verify checksums and split-manifest parity on every run.
- Input text only; target integer from `intent_id`.
- Preserve example IDs for predictions.
- No train/test overlap and no shared `group_id` crossing splits.
- Fit/choose nothing using test.

## Training
- Use the site-approved user-owned environment or approved user container only.
- Use a pinned model revision and associated tokenizer revision.
- `max_length` comes from training-text length profile and a real memory pilot; model config currently says 514 position embeddings, normally cap around 512 including special tokens unless pinned config indicates otherwise.
- Use validation Macro-F1 for best checkpoint and early stopping.
- Record seed, learning rate, optimizer, precision, micro-batch, accumulation, max length, epochs, gradient checkpointing, package versions, device, peak VRAM, data/model/code hashes and job ID.
- No concurrent hyperparameter trials by default.
- Do not silently switch full fine-tuning to another method if it OOMs.

## Primary/secondary metrics
Primary: Macro-F1 (unweighted mean per-class F1).
Secondary: accuracy, per-class precision/recall/F1/support, confusion matrix and learning curves. Report domain/language breakdowns only if dataset supports them. Report mean/std if multiple final seeds run.

## Required outputs
- `experiments/baseline/configs/`
- `experiments/baseline/trial_ledger.csv`
- `experiments/baseline/environment.json`
- `experiments/baseline/metrics_by_epoch.csv`
- `experiments/baseline/test_metrics.json`
- `experiments/baseline/per_class_metrics.csv`
- `experiments/baseline/confusion_matrix.csv` and image
- `experiments/baseline/test_predictions.csv` using IDs/labels, not raw private text
- `experiments/baseline/error_analysis.md`
- `docs/cluster_preflight.md`
- `docs/baseline_results.md`
- resumable checkpoints at approved storage path

## Interpretation
Distinguish an in-distribution baseline from domain generalization. Describe weak supervision via metadata mapping, the English-only scope, class capping, source selection bias and class confusion. Do not claim multilingual performance or contrastive improvements.
