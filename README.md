# Cross-Domain Complaint Understanding via Multilingual Encoders

A reproducible benchmark for fine-grained consumer complaint classification and cross-domain intent understanding using multilingual masked language models.

---

## 1. Project Overview

This repository benchmarks multilingual pretrained encoders on real-world consumer complaints across diverse financial domains (mortgages, credit reporting, debt collection, payment systems, and bank accounts).

The initial baseline phase evaluates **`facebook/xlm-v-base`** (1B parameter multilingual model with a 2.5M vocabulary) fine-tuned for 16-class intent classification on a frozen, stratified, and deduplicated corpus derived from the Consumer Financial Protection Bureau (CFPB) complaint database.

---

## 2. Dataset and Partitioning

The dataset is partitioned into strictly disjoint subsets based on consumer complaint and narrative group identifiers. There is zero overlap across train, validation, and test splits.

- **Total Curated Narratives**: 45,723 complaint narratives
- **Training Set**: 32,019 rows (`sha256: febbb253a9d7a3fec3caf622e811a45370a9fa16bd15583a2a7ff34d1fbfac78`)
- **Validation Set**: 6,852 rows (`sha256: db270bbbf48841deadb3c1251863881680d419eb04513146041b79065aa49800`)
- **Test Set**: 6,852 rows (`sha256: ffff21c815d7c54f0719094fc1aaa6e9fdfb7f75bb9c41f838fe4875507b90bb`)
- **Label Taxonomy**: 16 intent classes mapped systematically from CFPB issue and sub-issue metadata (`configs/taxonomy.json`)

---

## 3. Hardware and Training Environment

- **Accelerator**: NVIDIA RTX PRO 6000 Blackwell Server Edition MIG instance (`1g.24gb` slice, 25.37 GB VRAM)
- **Host Stack**: Python 3.12.3, PyTorch 2.11.0+cu128, CUDA 12.8, Transformers 5.17.0
- **Precision**: BFloat16 (`bf16`) with gradient checkpointing enabled
- **Workload Scheduler**: SLURM 24.05.4 (`gpu` partition)
- **Batch Architecture**: Micro-batch size 1, gradient accumulation steps 8 (effective batch size 8)

---

## 4. Sequential Baseline Tuning

In accordance with strict empirical hygiene, model selection was conducted exclusively on validation Macro-F1. The test set remained completely locked and untouched until the final configuration was chosen.

| Trial | SLURM Job ID | Learning Rate | Epochs | Peak VRAM | Validation Macro-F1 | Validation Accuracy | Selection Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trial 1** | Job 155 | `1e-5` | 3.0 (12,009 steps) | 15.6 GB | 0.5142 | 51.30% | Completed |
| **Trial 2** | Job 156 | `2e-5` | 3.0 (12,009 steps) | 15.6 GB | **0.5339** | **52.85%** | **Selected Winner** |

**Selection Outcome**: Trial 2 demonstrated a **+1.97% Macro-F1** advantage on validation data over Trial 1. Its final checkpoint was locked for test evaluation.

---

## 5. Final Benchmark Results (Unseen Test Set)

Evaluated on the frozen, held-out test split (`data/processed/baseline_test.csv`, 6,852 rows) using the locked winning model:

| Metric | Result | Benchmark Context |
| :--- | :--- | :--- |
| **Test Macro-F1** | **`0.5369`** (53.69%) | Primary evaluation metric across all 16 balanced intent classes |
| **Test Weighted-F1** | **`0.5340`** (53.40%) | F1 weighted by class support |
| **Test Accuracy** | **`0.5325`** (53.25%) | 16-way classification accuracy (random guess baseline = 6.25%) |
| **Total Test Samples** | **6,852** | Exact match with frozen split manifest |

---

## 6. Per-Class Performance Breakdown

Evaluated across all 16 intent classes on 6,852 test examples (`Phase 2/results/per_class_metrics.csv`):

| Intent Class | Precision | Recall | F1-Score | Support |
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

## 7. Error Analysis and Key Domain Insights

Analysis of the 16x16 confusion matrix (`Phase 2/results/confusion_matrix.csv`) reveals notable semantic overlaps:

1. **`debt_threats` vs `debt_not_owed` (198 mutual confusions)**: Debt collection complaints frequently contain multiple simultaneous grievances: the consumer states that they do not owe the balance and that the collector used harassing or unlawful threats. Single-label assignment introduces label competition on composite grievances.
2. **`transaction_problem` vs `funds_availability` (100 confusions)**: Unauthorized, delayed, or disputed transactions directly result in held balances and account lockouts, causing overlap between banking operational classes.
3. **`reporting_investigation_dispute` vs `reporting_incorrect_information` (185 mutual confusions)**: Credit reporting complaints almost universally combine allegations of inaccurate data with disputes over inadequate bureau investigations.
4. **Distinct Domain Separation (`servicing_dispute`, F1 = 0.7058)**: Mortgage and loan servicing complaints exhibit specialized terminology (escrow shortages, forbearance agreements, servicing transfers) that the model classifies with high fidelity.

---

## 8. Limitations and Scope

1. **Monolingual Focus**: The dataset is composed of English-language narratives from the CFPB database. Multilingual encoder capabilities (`xlm-v-base`) provide a strong feature foundation, but non-English generalization requires dedicated evaluation in future phases.
2. **In-Distribution Partitions**: The split is partitioned by complaint and narrative group identifiers. Cross-domain transfer to corporate or non-financial complaints remains to be evaluated.
3. **Derived Ground Truth**: Intent labels are established via systematic rules mapped from CFPB issue and sub-issue categories, rather than multi-annotator human consensus.

---

## 9. Repository Structure

```
├── configs/
│   ├── taxonomy.json                  # 16-class intent taxonomy and keyword patterns
│   └── product_canonical.json         # CFPB product canonical mappings
├── data/
│   ├── manifests/
│   │   ├── split_indomain.csv         # Frozen split manifest (train, validation, test)
│   │   ├── dataset_inventory.csv      # Dataset metadata and source inventory
│   │   ├── exclusion_log.csv          # Filter and deduplication exclusion accounting
│   │   └── checksums.csv              # Cryptographic SHA-256 verification manifest
│   └── processed/                     # Processed CSV splits and label map (generated)
├── Phase 2/
│   ├── BASELINE_MODEL_HANDOVER_REPORT.md  # Detailed experimental handover report
│   ├── DELIVERABLES_AND_CHECKLIST.md      # Completed acceptance checklist
│   ├── configs/
│   │   ├── baseline_tuning_lr1e5.yaml     # Trial 1 configuration
│   │   ├── baseline_tuning_lr2e5.yaml     # Trial 2 winning configuration
│   │   └── tuning_trials.csv              # Completed tuning ledger
│   ├── results/
│   │   ├── test_metrics.json              # Top-level test evaluation summary
│   │   ├── test_predictions.csv           # Row-level test predictions and confidences
│   │   ├── per_class_metrics.csv          # Per-class precision, recall, and F1
│   │   ├── confusion_matrix.csv           # Full 16x16 confusion matrix
│   │   ├── trial_lr1e5_metrics.json       # Trial 1 training history
│   │   └── trial_lr2e5_metrics.json       # Trial 2 training history
│   ├── slurm/
│   │   ├── train_trial1.sbatch            # SLURM submission script for Trial 1
│   │   └── train_trial2.sbatch            # SLURM submission script for Trial 2
│   └── src/training/
│       ├── train_baseline.py              # Main training script (Transformers 5.x compatible)
│       └── evaluate_test.py               # Standalone test-set evaluation script
├── docs/
│   ├── dataset_card.md                # Detailed dataset card
│   ├── label_taxonomy.md              # Taxonomy documentation
│   └── data_preparation_methodology.md# Data preparation and deduplication methodology
└── monitor_live.py                    # Live training progress monitor script
```

---

## 10. Reproduction and Quickstart

### Local Setup
```bash
git clone https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders.git
cd Cross-Domain-Complaint-understanding-via-multilingual-Encoders
pip install -r requirements.txt  # or install torch, transformers, datasets, scikit-learn, pyyaml
```

### Reproduce Test Evaluation
To run inference and compute test set metrics using the winning model checkpoint:
```bash
python "Phase 2/src/training/evaluate_test.py" \
  --model-path "path/to/final_model" \
  --data-dir "data/processed" \
  --out-dir "Phase 2/results"
```
