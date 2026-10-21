# SLURM Runbook — User-Owned Environment, Safe Job Lifecycles

## Rule
Submit training with `sbatch`; the training job then proceeds independently of the SSH terminal. It can still stop due to time limit, preemption, node failure, OOM, or storage/quota issues. Use resumable checkpoints.

## Read-only preflight
Run only after logging into the authorized account:
```bash
id
whoami
pwd -P
printf 'HOME=%s\nSCRATCH=%s\n' "${HOME:-UNSET}" "${SCRATCH:-UNSET}"
df -h "$HOME"
df -i "$HOME"
quota -s 2>/dev/null || true
command -v sbatch
command -v squeue
command -v sinfo
command -v sacct
```
Only use `sinfo` and `squeue -u "$USER"` for safe initial scheduler checks. Verify partition/account/QOS/time/GPU syntax against site documentation; do not infer exact values from the specification sheet.

## Submit
1. Create the log directory before submitting (SLURM opens logs before script execution).
2. Use a new config with no null required values.
3. Validate input files and model revision.
4. Fill all `REPLACE_AFTER_VERIFICATION` directives in the template.
5. Submit:
```bash
sbatch slurm/train_baseline.sbatch
```
6. Record the returned job ID, then:
```bash
squeue -u "$USER"
sacct -j <OWN_JOB_ID> --format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES,MaxRSS
```
Inspect only the exact job's logs. Do not use broad cancellation commands.

## GPU resource syntax
The specification sheet lists `gpu:1g.24gb:8`, but that may describe capacity/count in a site-specific way. It is not the same thing as the request for one GPU. Ask site documentation or an administrator to verify whether the correct request is `--gres=gpu:1g.24gb:1`, `--gpus=...`, or another registered string. Never guess; never request all eight slices.

## Checkpoint/restart
- Each run writes to a new unique directory.
- Checkpoint model + optimizer + scheduler/RNG/trainer state often enough for walltime.
- Test resume in the pilot.
- Preserve failed-run checkpoints until a resume succeeds and user approves cleanup.
- A model-only checkpoint is not sufficient to resume optimizer state.
- Cancel only an exact, verified job ID from this project.

## Terminal closure
Do not use `nohup`, `&`, `disown` or `tmux` as a replacement for scheduled jobs. `sbatch` is the mechanism for durable execution after disconnecting.


Set `OUTPUT_ROOT` to an existing, quota-checked directory owned by your account. Do not use `/apps` or any other shared path unless the site explicitly allocates a user-owned subdirectory there. The submitted script refuses an output root owned by a different user.
