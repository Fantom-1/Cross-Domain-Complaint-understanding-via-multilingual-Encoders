# First Agent Task — Begin Baseline Readiness and Tuning Safely

Read all instructions.

1. Inspect the current repository, Git status, and actual availability of the raw/processed dataset on this machine. Do not download duplicate data or rewrite anything yet.
2. Perform the checks in `DATA_RELEASE_GATE.md`. Compute hashes and counts from the actual files. If not all artifacts are available, report which machine/path is missing them.
3. Review the data-label generation caveat in `PHASE_A_REVIEW_FINDINGS.md`. Report whether human mapping review exists, and whether proceeding on mapped CFPB issue categories as weak labels is defensible for the planned baseline. Do not fabricate a review.
4. Build CPU-only model/training code and configuration validation, with tests for data integrity, no test leakage, label-map class count and non-overwriting outputs.
5. Perform read-only cluster preflight. Do not edit server/system configuration. Determine the approved user-owned environment/container path and exact SLURM MIG request syntax from site docs.
6. If all gates pass, submit one small allocated GPU smoke test (batch 1, max length 128). Record the job ID, device model/memory visible to the job, BF16 availability, peak allocated/reserved memory, finite loss/gradients and exit code.
7. Only after smoke-test success, run a short pilot and then sequential LR trials `1e-5`, `2e-5`. Do not submit concurrent trials. Select settings from validation Macro-F1 only.
8. Do not test-set tune. Evaluate test only after selected config is frozen.

Do not alter host/system settings, use privileged containers, ask for all GPUs, change shared packages, affect other users, or claim the run occurred without job IDs/logs. If any gate fails, stop and report evidence and a concrete next action.
