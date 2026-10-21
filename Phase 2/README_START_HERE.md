# START HERE — Complaint Baseline Tuning Pack

This pack is for an agent who starts with no context. Read the following in order:

1. `SYSTEM.md`
2. `PROJECT_BRIEF.md`
3. `PHASE_A_REVIEW_FINDINGS.md`
4. `SERVER_PROFILE_PRIVATE.md`
5. `SHARED_CLUSTER_SAFETY.md`
6. `ENVIRONMENT_AND_CONTAINER_STRATEGY.md`
7. `PHASE_B_BASELINE_ARCHITECTURE.md`
8. `BASELINE_TUNING_PLAN.md`
9. `SLURM_RUNBOOK.md`
10. `BASELINE_TRAINING_EVALUATION.md`
11. `DATA_RELEASE_GATE.md`
12. `DELIVERABLES_AND_CHECKLIST.md`
13. `REFERENCES.md`
14. `AGENT_HANDOFF_PROMPT.md`

Templates under `configs/`, `slurm/` and `container/` are not automatically safe to execute. Fill cluster-specific settings only after verifying them from the actual account and site docs.

## Key user constraint
**Do not change server configuration or system settings.** All Python packages, project dependencies, model weights, caches, logs, outputs and checkpoints must remain in a project-owned environment/container and user-owned/approved paths. Never run privileged operations, edit system configuration, install system packages, change drivers/modules/services, modify SLURM/Kubernetes settings, or affect other users.

The server-specification document is labeled confidential. `SERVER_PROFILE_PRIVATE.md` contains only a summary needed for planning and must not be committed to a public repository.

## What can start now
The agent can inspect data files/readiness and implement CPU-tested baseline code/config validation. Before GPU tuning it must verify the dataset files, exact label map, user-owned paths and scheduler/container access. Run the smallest allocated GPU smoke test first. Do not claim that training has started until there is a real SLURM job ID and log.

## Baseline implementation scaffold
`src/training/train_baseline.py` is included as a starting trainer. It deliberately fails when required config values are null, CUDA is unavailable, data hashes/manifests don't verify, or existing outputs would be overwritten. It still must be CPU-tested, reviewed against the installed Transformers version, and run through the smoke/pilot gates before tuning. Its test metrics must not be used to compare tuning trials; the agent should disable test evaluation during trial runs and evaluate test only once settings are locked.
