# Shared Cluster Safety and No-System-Change Rules

## Absolute prohibition
This project must not modify the host/system configuration in any way. No root/sudo, OS package installs, global pip/Conda, driver/CUDA changes, system modules installation, changes to SLURM/Kubernetes/container service configuration, global shell startup files, firewall, daemon settings, permissions, or shared package environments.

All dependencies must live in a user-owned environment or inside the user's own image. Runtime containers must not be privileged.

## Read-only preflight
Use only site-approved, read-only checks such as `id`, `pwd -P`, `df -h`, `df -i`, `quota -s` if available, `sinfo`, `squeue -u "$USER"`, and help/docs. Do not issue GPU jobs until the resource syntax and path policies are confirmed. Avoid exposing internal hostnames/account identifiers in public artefacts.

## Ownership and path rules
- Confirm project checkout path and ownership.
- Keep environments, caches, datasets if allowed, logs and checkpoints under user-owned or explicitly allocated project storage.
- Check quota/inodes and scratch retention before writing.
- Never modify other users' files, processes, caches or outputs.
- Use unique run directories keyed by config hash/job ID; do not overwrite existing results.
- Do not use `rm -rf` on variables, wildcards, or paths you have not just inspected.
- Do not upload raw complaint text or internal server details to a public repo.

## Environment/container rules
- Preferred: a dedicated user-owned venv or Conda environment in the project/user storage, with installed packages confined to that prefix.
- Alternative: build an image locally or in an approved user-space build environment, pin its digest, and run only through the site's approved container integration under the SLURM allocation.
- Do not assume rootless Docker works or that a Docker daemon permits GPU workloads. The installed Docker Engine alone does not grant permission to use it.
- Never use `docker run --privileged`, `--network host`, broad host mounts (`/`, `/home`, `/root`, `/etc`), or `--gpus all`.
- Do not configure or restart a container runtime, Kubernetes, SLURM, or the NVIDIA toolkit.
- If the site's scheduler/container policy cannot safely constrain the container to the assigned MIG GPU, use an approved user-space environment under SLURM instead.
- Use the site-provided driver only; never install a driver in an environment/container.
- Any module load, if site documentation permits it, may only affect that job/process environment; never change module files or global config. Prefer the user's isolated environment and documented site-supported runtime.
- Set `HF_HOME`, `HF_DATASETS_CACHE`, `TORCH_HOME`, `TMPDIR`, and `XDG_CACHE_HOME` to project/user-owned paths after quota checks. Set `TRANSFORMERS_CACHE` only if supported by the pinned library.
- Keep tokens/secrets out of scripts, images, notebooks and logs.

## Scheduler rules
- GPU training only through a verified SLURM allocation, never directly on login/head nodes.
- One MIG allocation initially; no multi-GPU or concurrent sweep unless explicitly supported and measured.
- Do not bypass SLURM/cgroups/MIG resource limits.
- Do not use `pkill`, broad `killall`, `nvidia-smi --gpu-reset`, `scancel -u`, or broad job cancellation. Only manage a specific verified project job ID.
- Use `sbatch` for jobs that should survive terminal closure. Check status via `squeue -u "$USER"` and completed state via `sacct -j <own_jobid>`.
- Checkpoint frequently, test restore/resume, and expect wall-time limits/preemption/OOM to be possible.

## Memory/throughput safeguards
- The MIG profile is reported as 24 GB, but this must be confirmed inside the allocation.
- Start with micro-batch 1 and max length 128 for the first measured training-step pilot; test length 256 only after memory headroom is observed.
- Use BF16 only if the allocated device and PyTorch runtime report support. Otherwise evaluate FP16 or FP32 safely.
- Use gradient checkpointing and avoid concurrent trials. Gradient accumulation changes effective batch size, not parameter/optimizer-state memory.
- Log `torch.cuda.max_memory_allocated()` and `max_memory_reserved()` inside the allocated job.


## Output/checkpoint path rule
The SLURM template requires an existing writable user-owned `OUTPUT_ROOT`. Set `PROJECT_ALLOWED_OUTPUT_ROOT` to that verified path in the job. Keep source code in the repository and heavy checkpoints/logs/caches in the approved storage area if the repository/home quota is limited. Never use a shared application path merely because it is writable.
