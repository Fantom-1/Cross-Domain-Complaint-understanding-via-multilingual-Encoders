# Agent Handoff Prompt — Copy/Paste

Read `README_START_HERE.md` and all instruction files. You have no prior context.

We want to begin the standard supervised `facebook/xlm-v-base` baseline tuning now, but only safely. First verify the actual existing prepared data release against the claims in `PHASE_A_REVIEW_FINDINGS.md` and `DATA_RELEASE_GATE.md`. Do not overwrite the data. If labels/manifests/hashes do not reconcile or the mapping decisions are materially unreliable, stop and present evidence.

Implement a reproducible baseline training/evaluation entry point and config in the repository, using the classification head output dimension from the frozen label map. Run CPU checks first. Then complete read-only cluster preflight and use only a project-owned environment or an approved user container. Do not modify any server/system settings or shared environments; no sudo/root, system installs, driver/module changes, SLURM/Kubernetes changes, privileged containers, broad mounts, `--gpus all`, GPU reset, or commands affecting other users.

Use SLURM for GPU jobs, verify the actual MIG resource syntax rather than guessing, and run one small smoke test (batch 1, length 128) before a short pilot. Measure VRAM and test checkpoint/restart. Only then run the limited sequential LR tuning described in `BASELINE_TUNING_PLAN.md`. Keep all outputs, caches, environments, logs and checkpoints in approved user-owned paths. Do not claim the job started without a real job ID and logs.

Do not implement contrastive learning, retrieval, XLM-R, LoRA, frozen embeddings, quantization, optimizer alternatives or distributed training without separate approval. Do not use test metrics to select tuning settings. If the actual environment/container route cannot be used without host changes, stop and report the blocker.


Before training, confirm that the SLURM `OUTPUT_ROOT` already exists, is writable, is user-owned, and has enough disk/inode quota. Keep checkpoints and caches out of the repo if needed; the script only allows external output when `PROJECT_ALLOWED_OUTPUT_ROOT` is explicitly set.
