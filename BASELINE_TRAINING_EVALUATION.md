# Baseline Fine-Tuning and Evaluation — Later Phase Only

**Do not execute until the user approves `docs/baseline_data_readiness.md` and freezes split manifests.**

## Model
Checkpoint: `facebook/xlm-v-base`. Task: single-label sequence classification. Use the associated tokenizer and a standard classification head with output dimension equal to the number of approved labels. Loss is cross-entropy. No contrastive objective, retrieval, synthetic data or auxiliary task in this baseline.

For pooled representation `h`: `logits = W h + b`; `p(y|x) = softmax(logits)`; `L_CE = -mean(log p(y_i|x_i))`. Verify the checkpoint architecture and Transformers compatibility with a small smoke test; do not assume every auto-class wrapper works without verification.

## Environment
Run in Google Colab only after data approval. Record date, runtime, GPU model and actual VRAM, CPU/RAM, Python, PyTorch, Transformers, Datasets, Tokenizers, scikit-learn and CUDA versions. Do not assume GPU availability. Pin versions after compatibility is tested. Record model revision. Keep credentials out of notebooks/logs.

## Data and training
- Load only frozen CSVs and validate their hashes/manifests.
- Tokenize using the XLM-V-associated tokenizer; record revision.
- Choose maximum length from training text profile and memory constraints; report truncation rate. Do not choose it by test results.
- Train on train only. Validation controls checkpoint/hyperparameter selection and early stopping.
- Set and record seeds; multiple seeds are preferred where feasible.
- Record class weighting/sampling choices; default to none unless justified and decided before test evaluation.
- Do not fit preprocessing or select settings using test data.

## Metrics
Primary: Macro-F1 (unweighted mean of class F1 scores).
Secondary: accuracy, per-class precision/recall/F1, confusion matrix, and domain/language Macro-F1 when support permits. Report support alongside metrics. Weighted-F1 may be supplementary, not a replacement for Macro-F1. Multiple-seed mean/std where feasible.

## Artefacts
`experiments/baseline/config.yaml`, `environment.json`, `train.log`, `metrics_by_epoch.csv`, `test_metrics.json`, `per_class_metrics.csv`, `confusion_matrix.csv` and plot, `test_predictions.csv`, `error_analysis.md`, model checkpoint/config/tokenizer where storage permits, and `docs/baseline_results.md`. Avoid sensitive raw text in public reports.

## Interpretation
Compare train/validation for overfit; read Macro-F1 with support; inspect confusions and taxonomy overlap; separate model errors from possible data/annotation errors where evidence allows; report unsupported domain/language metrics as not estimable; discuss selection bias, opt-in narratives, imbalance, ambiguity and script variation. Do not claim robustness or multilingual generalization from a single aggregate score. No claims about contrastive improvements in this phase.
