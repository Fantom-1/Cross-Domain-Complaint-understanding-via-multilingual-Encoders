#!/usr/bin/env bash
#SBATCH --job-name=cdcu-trial_lr1e5
#SBATCH --output=/apps/cdcu/logs/slurm/cdcu-trial_lr1e5-%j.out
#SBATCH --error=/apps/cdcu/logs/slurm/cdcu-trial_lr1e5-%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1g.24gb:1

set -Eeuo pipefail
umask 077

PROJECT_ROOT="/apps/cdcu"
PYTHON_BIN="/home/abdul/envs/amlc/bin/python"
export HF_HOME="/apps/cdcu/hf_cache"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TORCH_HOME="$HF_HOME/torch"
export TMPDIR="/apps/cdcu/tmp"
export XDG_CACHE_HOME="/apps/cdcu/xdg"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export PROJECT_ALLOWED_OUTPUT_ROOT="$PROJECT_ROOT/runs"
mkdir -p "$TMPDIR" "$HF_HOME" "$PROJECT_ROOT/runs"

cd "$PROJECT_ROOT"
RUN_DIR="$PROJECT_ROOT/runs/trial_lr1e5_$SLURM_JOB_ID"
mkdir -p "$RUN_DIR"

{
  echo "job_id=$SLURM_JOB_ID"
  echo "trial=trial_lr1e5"
  echo "learning_rate=1e-05"
  echo "start_utc=$(date -u +%FT%TZ)"
  echo "git_commit=b9f4207"
  echo "hostname=$(hostname)"
} | tee "$RUN_DIR/job_metadata.txt"

echo "=== STARTING trial_lr1e5 (LR=1e-05) ==="
"$PYTHON_BIN" -m src.training.train_baseline \
  --config configs/baseline_tuning_lr1e5.yaml \
  --run-dir "$RUN_DIR" \
  --learning-rate 1e-05 \
  --max-length 128 \
  --epochs 3.0

STATUS=$?
echo "end_utc=$(date -u +%FT%TZ)" | tee -a "$RUN_DIR/job_metadata.txt"
echo "exit_status=$STATUS" | tee -a "$RUN_DIR/job_metadata.txt"
exit "$STATUS"
