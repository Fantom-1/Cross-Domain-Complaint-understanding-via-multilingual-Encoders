#!/usr/bin/env bash
# Read-only checks only. No install, GPU allocation, data modification or system change.
set -u
echo "== identity =="; id; whoami; pwd -P
echo "== paths =="; printf 'HOME=%s\nSCRATCH=%s\n' "${HOME:-UNSET}" "${SCRATCH:-UNSET}"
echo "== disk =="; df -h "$HOME" 2>&1 || true; df -i "$HOME" 2>&1 || true
echo "== quota =="; quota -s 2>&1 || true
echo "== commands =="; for c in sbatch squeue sinfo sacct python python3 conda micromamba docker apptainer; do command -v "$c" 2>/dev/null || true; done
echo "== scheduler visible partitions =="; sinfo 2>&1 || true
echo "== own jobs =="; squeue -u "$USER" 2>&1 || true
echo "NOTE: this script intentionally does not query/reset GPU state or modify system settings."
