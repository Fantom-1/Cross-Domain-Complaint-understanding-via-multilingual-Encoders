# Phase B Baseline Model Handover Report

**Project**: Cross-Domain Complaint Understanding via Multilingual Encoders  
**Model**: `facebook/xlm-v-base` (Sequence Classification, 16 Intent Classes)  
**Execution Date**: October 22, 2026  
**Status**: All Gates Passed — Tuning & Test Evaluation Complete  

---

## 1. Executive Summary & Final Test Results

The standard supervised baseline model `facebook/xlm-v-base` (pinned revision `68c75dd7...`) has completed sequential hyperparameter tuning and final locked evaluation on the frozen, unseen test split (`baseline_test.csv`, 6,852 examples).

### Final Benchmark Performance (Unseen Test Set)
| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Test Macro-F1** | **0.5369** (53.69%) | Primary evaluation metric across all 16 balanced intent classes |
| **Test Weighted-F1** | **0.5340** (53.40%) | F1 weighted by class support |
| **Test Accuracy** | **0.5325** (53.25%) | Exact match rate on 16-way classification (random baseline = 6.25%) |
| **Test Samples Evaluated** | **6,852** | Exact match with frozen in-domain split manifest |

---

## 2. Gate Verification & Acceptance Checklist

### A. Data Gate: Verified
- **Train Set**: 32,019 rows (`sha256: febbb253a9d7a3fec3caf622e811a45370a9fa16bd15583a2a7ff34d1fbfac78`)
- **Validation Set**: 6,852 rows (`sha256: db270bbbf48841deadb3c1251863881680d419eb04513146041b79065aa49800`)
- **Test Set**: 6,852 rows (`sha256: ffff21c815d7c54f0719094fc1aaa6e9fdfb7f75bb9c41f838fe4875507b90bb`)
- **Label Taxonomy**: 16 unique contiguous integer IDs 0..15 (`sha256: 3285b5b9b5939c603dccb400a8f00f99244f5897393f51816e57dfa80bd42406`)
- **Split Separation**: Strict disjointness verified across all splits; zero `group_id` or `example_id` leakage.

### B. Environment & Cluster Safety Gate: Verified
- **Host / Partition**: Node `anrfotd5`, SLURM partition `gpu`.
- **Allocated Device**: NVIDIA RTX PRO 6000 Blackwell Server Edition MIG instance `1g.24gb` (25.37 GB VRAM total).
- **Environment**: User-owned virtual environment `/home/abdul/envs/amlc` (Python 3.12.3, PyTorch `2.11.0+cu128`, CUDA 12.8, Transformers 5.17.0).
- **Filesystem Isolation**: Host root `/` and `/home` are at 100% capacity; all execution, scratch storage, checkpoints, and caches were strictly isolated to `/apps/cdcu` on partition `/dev/nvme1n1p1` (758 GB available).
- **Cluster Guardrail Confirmation**: No system settings, driver modules, system packages, SLURM configurations, or other users' workspaces were modified.

### C. Smoke & Pilot Gate: Verified
- **Smoke Test (Job 150)**: Passed. Pinned model revision downloaded, BF16 confirmed, forward/backward pass executed cleanly with peak allocated memory of 7.84 GB.
- **Pilot Test (Job 153)**: Passed. 41 training steps, validation evaluation throughput at 1,374 samples/sec, model serialization in 2.39 seconds (`pilot_exit=0`).

### D. Tuning Gate: Verified
- Planned sequential learning rate search executed with strict dependency chaining (`--dependency=afterok`):
  - **Trial 1 (Job 155, LR=1e-5)**: Completed 3.0 epochs (`12,009` steps). Final validation Macro-F1: **0.5142**, Accuracy: **0.5130**.
  - **Trial 2 (Job 156, LR=2e-5)**: Completed 3.0 epochs (`12,009` steps). Final validation Macro-F1: **0.5339**, Accuracy: **0.5285**.
- **Model Selection**: Trial 2 selected solely based on validation Macro-F1 (`0.5339` vs `0.5142`). The test set was locked and untouched during the entire tuning phase.

---

## 3. Per-Class Performance Breakdown

Evaluated on 6,852 unseen test complaints across all 16 intent classes:

| Intent Class | Precision | Recall | F1-Score | Test Support |
| :--- | :--- | :--- | :--- | :--- |
| `servicing_dispute` | **0.6783** | **0.7356** | **0.7058** | 450 |
| `account_access` | **0.6674** | **0.6422** | **0.6546** | 450 |
| `reporting_improper_use` | **0.6840** | **0.5955** | **0.6367** | 309 |
| `credit_terms_dispute` | 0.6349 | 0.5333 | 0.5797 | 450 |
| `application_problem` | 0.6034 | 0.5511 | 0.5761 | 450 |
| `closing_process` | 0.5903 | 0.5403 | 0.5642 | 248 |
| `fraud_or_scam` | 0.5653 | 0.5421 | 0.5535 | 439 |
| `debt_communication` | 0.5469 | 0.5224 | 0.5344 | 446 |
| `funds_availability` | 0.4859 | 0.5768 | 0.5275 | 449 |
| `payment_problem` | 0.4890 | 0.5520 | 0.5186 | 442 |
| `transaction_problem` | 0.5616 | 0.4365 | 0.4912 | 449 |
| `reporting_investigation_dispute` | 0.5938 | 0.4978 | 0.5416 | 464 |
| `reporting_incorrect_information` | 0.4670 | 0.4782 | 0.4725 | 458 |
| `account_management` | 0.4058 | 0.5326 | 0.4606 | 445 |
| `debt_not_owed` | 0.3744 | 0.4758 | 0.4190 | 454 |
| `debt_threats` | 0.3759 | 0.3341 | 0.3538 | 449 |
| **Macro Average** | **0.5453** | **0.5342** | **0.5369** | **6,852** |
| **Weighted Average** | **0.5411** | **0.5325** | **0.5340** | **6,852** |

---

## 4. Deep Error Analysis & Domain Interpretations

Analysis of the top prediction confusions in `confusion_matrix.csv` reveals critical domain patterns:

1. **`debt_threats` vs. `debt_not_owed` (112 confusions)**:
   - *Cause*: Consumers disputing collections frequently state both that they do not owe the debt AND that the collector made threats of litigation, wage garnishment, or credit ruin.
   - *Interpretation*: The underlying narratives naturally contain multi-intent signals. Forcing a single label creates unavoidable label competition between two simultaneously true statements.
2. **`transaction_problem` vs. `funds_availability` (100 confusions)**:
   - *Cause*: Deposit, checking, and transfer disputes routinely conflate unauthorized/delayed transactions with held deposits or unavailable funds.
3. **`reporting_investigation_dispute` vs. `reporting_incorrect_information` (185 mutual confusions)**:
   - *Cause*: Consumers reporting credit bureau disputes almost invariably report both the presence of inaccurate information AND the bureau's failure to conduct a proper reinvestigation.
4. **Strongest Intent Class (`servicing_dispute`, F1 = 0.7058)**:
   - Mortgage, loan, and student servicing narratives contain distinct, unambiguous terminology (escrow, forbearance, transfer of servicing, payment re-amortization) that the multilingual encoder easily discriminates.

---

## 5. Methodological Limitations

In strict adherence to the project guidelines, the following constraints must be noted for all subsequent reporting:
1. **English-Only Scope**: The CFPB training and evaluation sets are in English. While `facebook/xlm-v-base` is a multilingual model, no multilingual generalization claims can be made without cross-lingual evaluation.
2. **In-Distribution Split**: Evaluation was conducted on in-domain CFPB data partitioned by complaint group. It does not establish out-of-domain transfer to other financial or non-financial complaint corpora.
3. **Rule-Derived Taxonomy**: Labels were mapped from CFPB Issue and Sub-issue metadata using a deterministic rule engine; they are not human expert double-annotated gold standards.
4. **Per-Class Balanced Sampling**: Reservoir sampling capped classes at 3,000 complaints to prevent dominant classes from overpowering the loss. Real-world consumer complaint distributions will show higher class imbalance.

---

## 6. Handover Artifacts Directory Structure

All deliverables have been transferred locally to `Phase 2/results/` and committed to version control:

```
Phase 2/
├── results/
│   ├── test_metrics.json          # Top-level test metrics (Macro-F1, accuracy, top confusions)
│   ├── test_predictions.csv        # Row-by-row test predictions with confidence and correctness
│   ├── per_class_metrics.csv       # Precision, recall, F1, and support for all 16 classes
│   ├── confusion_matrix.csv        # 16x16 confusion matrix
│   ├── trial_lr1e5_metrics.json    # Trial 1 full training and validation history
│   └── trial_lr2e5_metrics.json    # Trial 2 full training and validation history
├── configs/
│   ├── baseline_tuning_lr1e5.yaml  # Trial 1 exact reproduction config
│   ├── baseline_tuning_lr2e5.yaml  # Trial 2 winning reproduction config
│   └── tuning_trials.csv           # Completed trial ledger with job IDs and scores
├── slurm/
│   ├── train_trial1.sbatch         # SLURM script for Job 155
│   └── train_trial2.sbatch         # SLURM script for Job 156
├── src/training/
│   ├── train_baseline.py           # Hardened trainer with Transformers 5.x compatibility
│   └── evaluate_test.py            # Standalone test evaluator with BF16 handling
└── BASELINE_MODEL_HANDOVER_REPORT.md # This document
```

On the remote cluster (`30.30.31.2`), the winning serialized model checkpoint is preserved at:
`/apps/cdcu/runs/trial_lr2e5_156/final_model/`
