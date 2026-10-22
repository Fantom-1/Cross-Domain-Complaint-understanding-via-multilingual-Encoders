# Acceptance Checklist

## Data gate
- [x] Actual files, hashes, label map and split manifest verified (32,019 train, 6,852 val, 6,852 test; all sha256 hashes verified).
- [x] Counts reconcile, including sampling exclusion (exact match with `split_indomain.csv`).
- [x] Mapping status accurately describes rule-derived labels (16-class intent schema mapped from CFPB Issue/Sub-issue).
- [x] Dedup algorithm docs and code match.
- [x] Tests pass against actual processed release.
- [x] Current limitations clearly stated (English-only, in-distribution, rule-derived intents).

## Environment/cluster gate
- [x] No system/server settings changed.
- [x] User-owned environment or approved image only (`/home/abdul/envs/amlc`).
- [x] Paths/ownership/quotas confirmed (isolated in `/apps/cdcu` on partition with 758 GB free).
- [x] SLURM GPU request syntax verified from actual site docs (`--gres=gpu:1g.24gb:1`).
- [x] Actual allocated device and VRAM observed (NVIDIA RTX PRO 6000 Blackwell Server Edition MIG `1g.24gb`, 25.37 GB VRAM).
- [x] Container GPU isolation confirmed if container path is used (environment path isolated).

## Smoke/pilot gate
- [x] Output shape matches approved class count (16 classes).
- [x] Finite loss/gradients (loss=2.8125 in smoke test, finite=True).
- [x] Peak allocated/reserved VRAM recorded (7.84 GB in smoke, 15.6 GB in full tuning).
- [x] Checkpoint save/load/resume tested (tested in pilot Job 153 and full trials).
- [x] No OOM or resource-policy violation.
- [x] Pilot metrics not presented as baseline results.

## Tuning/final gate
- [x] Limited sequential LR search completed using validation only (Trial 1: LR=1e-5, Trial 2: LR=2e-5).
- [x] Trial ledger complete (`Phase 2/configs/tuning_trials.csv`).
- [x] Final settings locked before test evaluation (Trial 2 selected with Val Macro-F1=0.5339).
- [x] Test evaluated only after selection (Test Macro-F1=0.5369, Accuracy=53.25%).
- [x] Metrics, support, confusion matrix and error analysis saved (`Phase 2/results/`).
- [x] Seeds and environment recorded (Seed 42, Python 3.12.3, PyTorch 2.11.0+cu128).
- [x] Claims constrained to English, in-distribution data unless other data/splits exist.

## Final agent report
- [x] Phase/gate status; actual data hashes/counts; environment isolation method; GPU/MIG type and memory actually allocated; exact SLURM job IDs/states; config/model revision hashes; tuning results; final test results; limitations; any failed checks; explicit confirmation no system/server settings or other users' work were modified. Complete report available at `Phase 2/BASELINE_MODEL_HANDOVER_REPORT.md`.
