# Shared AI Server Usage & Project Execution Instructions

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Canonical repository:** https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders  
**Primary encoder:** XLM-V (`facebook/xlm-v-base`)

## 1. Purpose

This document defines how the project team and coding agent may use the shared AI server to complete model training, fine-tuning, hyperparameter tuning, experiments and final demo deployment.

The server is **not off-limits**. It should be used actively when its GPU, memory or compute resources materially help the project. The requirement is to protect administrator-managed configuration, preinstalled systems and other users' workloads—not to impose an unnecessary restriction on project workloads.

The user's local machine remains the primary project workspace and recovery point. Work may be moved to the server when there is a clear technical or operational benefit and the required access and storage are approved.

## 2. Non-negotiable server safety rules

Do not modify, disrupt, replace or reconfigure administrator-managed systems.

### Prohibited without explicit administrator authorization

- Changing system-wide Python installations or global package environments.
- Installing, upgrading, downgrading or removing system-wide packages.
- Changing NVIDIA drivers, CUDA installations/toolkit configuration, GPU firmware or system libraries.
- Changing Slurm configuration, partitions, QOS, scheduler settings, GRES/MIG configuration or accounting.
- Changing Kubernetes cluster configuration, namespaces, RBAC, admission policies or shared services.
- Changing Docker/container runtime or NVIDIA Container Toolkit configuration.
- Modifying shared environment modules or administrator-maintained software.
- Rebooting nodes, stopping shared services or changing host/network/security configuration.
- Deleting or altering other users' files, processes, jobs or resources.
- Running broad cleanup commands against shared or system directories.
- Storing credentials in source code, Git, notebooks, shell history, logs, prompts or documentation.

If a task appears to require any of these changes, stop and ask the user to obtain administrator approval. Do not attempt a workaround that bypasses access controls.

### Allowed project-level operations, subject to account permissions and resource policy

- Creating project-owned directories in approved storage locations.
- Creating user-owned Python/Conda environments or approved containers.
- Installing compatible dependencies inside project-owned environments.
- Loading existing administrator-provided modules.
- Submitting, monitoring and cancelling the project's own Slurm jobs.
- Running training, fine-tuning, hyperparameter tuning, validation and inference workloads.
- Saving project checkpoints, logs, metrics and configuration files in approved project storage.
- Running a project-owned inference service under an approved allocation and access model.
- Copying project artifacts between the server and the user's local machine.

Use only resources and actions permitted by the user's account, cluster policy and administrator guidance. Do not assume that a listed GPU, partition, module, directory or service is available to this account until verified.

## 3. Work allocation: local-first, server-capable

The local machine is the default location for general project work. This is a default, not a hard boundary. Move work to the server when there is a clear compute, memory, storage or operational reason.

| Workstream | Default location | Server use |
|---|---|---|
| Git repository, branches and documentation | Local | Clone/checkout only when useful |
| Data collection and source provenance | Local | Only if scale or approved access requires it |
| Cleaning, normalization and profiling | Local | May offload compute-heavy stages when justified |
| Split construction and leakage audits | Local | May run reproducibility checks on server if useful |
| Contrastive pair-manifest generation | Local | May offload if resource-intensive |
| CPU baselines and general EDA | Local | Not normally required |
| GPU model training and fine-tuning | Server | Primary use |
| Hyperparameter and objective tuning | Server | Primary use |
| Training-time validation and checkpoint selection | Server | Appropriate when close to training |
| Embedding generation and index construction | Local by default | Use server when scale or memory justifies it |
| Final test evaluation and error analysis | Local by default | May use server if the selected model or workload requires it |
| API and frontend development | Local | Not normally required |
| Final inference deployment for demo | Server | Required for the agreed demo architecture |
| Reports and project documentation | Local | Transfer only if needed |
| Repository and artifact backups | Local plus independent backup | Server is not the only copy |

Do not move work merely to make the architecture look server-centric. Equally, do not avoid server compute when it is the sensible way to complete the work.

## 4. Protect the installed environment

Before using the server:

1. Inspect the modules and software already provided.
2. Confirm the approved storage locations and account quotas.
3. Confirm available partitions, GPU/MIG resources, time limits and job policies.
4. Check the existing Python, PyTorch, CUDA and Transformers versions.
5. Prefer compatible preinstalled dependencies where practical.
6. Create an isolated, project-owned environment when dependencies differ.
7. Record exact package versions and environment setup commands.
8. Do not upgrade a working environment just because a newer version exists.

Never assume that the version shown in an old project note is still installed. Verify the live environment from an approved session.

Example read-only preflight commands (run only where permitted):

```bash
hostname
whoami
pwd
module avail
module list
sinfo -o "%P %a %l %D %G"
squeue -u "$USER"
nvidia-smi -L
nvidia-smi
df -h
quota -s
```

Example Python environment check after loading administrator-provided modules:

```bash
python - <<'PY'
import sys
print("Python:", sys.version)

try:
    import torch
    print("PyTorch:", torch.__version__)
    print("Torch CUDA:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())
    print("Visible devices:", torch.cuda.device_count())
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            print(i, torch.cuda.get_device_name(i))
except Exception as exc:
    print("PyTorch check failed:", repr(exc))
PY
```

Module names in examples are not guaranteed to be available. Use the names reported by the live module system and approved by the administrator.

## 5. Storage and resource discipline

- Use approved project-owned storage; do not assume the home directory, scratch filesystem or a particular mount is suitable.
- Check available capacity and quota before downloading datasets, model weights or checkpoints.
- Keep temporary files, caches, checkpoints, logs and final artifacts in clearly separated project directories.
- Set project-specific cache locations where appropriate so large downloads do not unexpectedly fill a shared or root filesystem.
- Estimate checkpoint and dataset sizes before long runs.
- Monitor GPU memory, CPU memory, disk usage, runtime and job state.
- Request only the resources needed for the experiment.
- Do not monopolize GPUs or submit large sweeps without checking cluster policy and the user's approval.
- Use a small smoke test before expensive jobs.
- Make long jobs resumable where possible.
- Do not delete server-side files merely because a local copy appears to exist. Verify the backup first and obtain user approval before cleanup.

Suggested project directory layout (adapt only to an approved writable location):

```text
<approved-project-storage>/
  complaint-understanding/
    environments/
    runs/
      <experiment-id>/
        config/
        logs/
        checkpoints/
        metrics/
    releases/
      <release-id>/
        model/
        tokenizer/
        config/
        checksums/
    inference/
```

Do not put credentials, raw sensitive data or restricted artifacts in broadly accessible locations.

## 6. Training and tuning plan

Training and tuning are major project workstreams and must be scheduled early. Do not postpone all GPU work until the frontend or every report is finished. Local preparation and server experiments can progress in parallel.

### Stage A — Environment and smoke test

Verify:

- Approved GPU/MIG allocation and actual device visibility.
- Tokenizer and XLM-V checkpoint loading.
- Forward and backward passes.
- Mixed-precision compatibility, if used.
- Checkpoint save, reload and inference.
- Peak GPU memory and basic throughput.
- Data-loader operation and storage throughput.
- Job preemption/time-limit behavior, if relevant.

Do not begin a long experiment until the smoke test passes and its environment details are recorded.

### Stage B — Reproducible baselines

Run the agreed baseline configurations with fixed seeds and recorded data/model revisions. Preserve the existing comparison requirements:

1. TF-IDF retrieval baseline.
2. Frozen XLM-V embeddings.
3. Supervised XLM-V representation/classifier baseline.
4. Contrastively fine-tuned XLM-V variants.

Keep classification and retrieval outcomes separate. A classifier improvement does not automatically demonstrate better semantic retrieval.

### Stage C — Hyperparameter and objective tuning

Plan tuning as a sequence of controlled experiments rather than an uncontrolled sweep.

Potential tuning dimensions, subject to the approved research protocol:

- Learning rate and scheduler.
- Effective batch size and gradient accumulation.
- Maximum sequence length.
- Number of epochs and early-stopping criteria.
- Temperature and other contrastive-loss parameters.
- Positive/negative sampling strategy.
- Same-domain versus supported cross-domain positive sampling.
- Projection head and embedding dimension, if part of the model design.
- Weight decay and warm-up.
- Random seed and repeat count.

Use validation data for tuning and model selection. Do not use final test results to choose hyperparameters, sampling rules, checkpoints or thresholds.

Start with a small, informative search. Expand only when results justify it and compute/time budgets permit. Record unsuccessful runs as well as successful ones.

### Stage D — Final training

For each accepted configuration, record:

- Experiment ID and source commit.
- Dataset version and cryptographic hash.
- Split and pair-manifest versions/hashes.
- Base model and tokenizer identifiers/revisions.
- Full configuration and random seed.
- Environment/package versions.
- Slurm job ID and resource allocation.
- Start/end time, runtime and exit status.
- Training and validation metrics.
- Peak GPU memory and relevant throughput.
- Checkpoint paths and checksums.

Use resumable checkpoints and preserve the configuration needed to reproduce each run.

### Stage E — Model selection and final evaluation

- Select models using predeclared validation criteria.
- Keep the test set untouched until the configuration is locked.
- Evaluate the final selected model on the test set once the protocol is frozen.
- Report classification and retrieval metrics separately.
- Report in-domain and feasible cross-domain retrieval separately.
- Identify unsupported class/domain combinations rather than inventing coverage.
- Label CFPB administrative weak-label metrics as proxy metrics.
- Keep human-adjudicated semantic relevance results separate from weak-label results.
- Do not claim semantic retrieval improvement solely because contrastive loss decreases.

## 7. Experiment tracking and failure recovery

Every training or tuning run must have a unique experiment ID and a saved configuration.

Maintain:

- Machine-readable config.
- Source commit SHA.
- Dataset and manifest hashes.
- Logs and metrics.
- Checkpoints at sensible intervals.
- Exit status and failure reason.
- Resource usage.
- A short result summary and next action.

If a job fails:

1. Preserve its logs and failure state.
2. Identify whether the failure is code, data, environment, quota, scheduler, storage or resource related.
3. Do not change global server settings to work around it.
4. Make the smallest project-local correction.
5. Rerun the smoke test if the environment or training path changed.
6. Resume from a verified checkpoint where appropriate.
7. Record the failed run; do not silently overwrite it.

Do not claim that a job, experiment or deployment succeeded without checking its actual exit status and outputs.

## 8. Data, privacy and research integrity

- Follow the dataset's licence, terms, privacy requirements and approved storage policy.
- Do not publish raw complaint narratives or restricted data in GitHub, public logs or demo responses.
- Keep secrets and credentials out of code, prompts, notebooks, logs and documentation.
- Do not use validation or test examples to train the model or construct the training gallery.
- For retrieval development, use validation queries against the training gallery.
- For final retrieval evaluation, use test queries against the training gallery after the model/configuration is locked.
- Do not treat every same-label complaint as a valid semantic positive or every different-label complaint as a valid semantic negative.
- Keep duplicate clusters and source-group exclusions consistent with the approved leakage protocol.
- Record provenance and preprocessing decisions.

## 9. Artifact transfer and backup policy

The server is a compute and deployment resource, not the only home of project assets. The local machine is the primary recovery point.

### Back up source code

Maintain:

1. A normal local working clone.
2. A full Git mirror preserving all refs and history.
3. A verified Git bundle.
4. A separate external/offline copy.
5. Git LFS payloads separately when Git LFS is used.

Example:

```bash
git clone --mirror \
  https://github.com/Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders.git \
  complaint-project-mirror.git

cd complaint-project-mirror.git
git remote update --prune
git bundle create ../complaint-project-all-refs.bundle --all
git bundle verify ../complaint-project-all-refs.bundle
```

If Git LFS is used, fetch and back up its objects separately. A Git bundle does not contain Git LFS payloads.

### Back up model and experiment artifacts

For every accepted checkpoint/release, transfer and preserve as applicable:

- Model weights and model configuration.
- Tokenizer files and pinned tokenizer revision.
- Training configuration and random seeds.
- Source commit SHA.
- Dataset/split/pair-manifest identifiers and hashes.
- Sanitized training logs and metrics.
- Evaluation outputs and model-selection record.
- Retrieval index and metadata, if part of the release.
- Checksums for all transferred files.

Verify checksums after transfer. Keep at least one independent backup separate from the working copy. Use access-controlled or encrypted storage where required.

Do not commit large model checkpoints, raw complaint narratives, private indexes or credentials to ordinary Git unless the repository's storage and access policy explicitly permits it.

### Backup cadence

- Refresh the Git mirror and bundle after accepted merges or important repository milestones.
- Back up each accepted checkpoint and final release after transfer and checksum verification.
- Back up final evaluation reports, manifests and release metadata.
- Periodically test recovery by cloning or restoring into a separate test location.
- Do not delete server copies automatically after backup.

## 10. Final inference deployment and demo architecture

The intended demo architecture is:

```text
Local React frontend
        |
        v
Local API / orchestration layer
        |
        v
Approved SSH port forward
        |
        v
Server inference API
        |
        +--> Intent classifier
        +--> Complaint embedding / retrieval encoder
        +--> Vector index and metadata
        +--> Structured summarizer
```

The local application remains usable and developed locally. The final selected inference model and required inference components are deployed to the server for the demo.

Deployment requirements:

- Use an approved project-owned environment/container.
- Bind the inference service to loopback unless the administrator explicitly approves another exposure model.
- Prefer an owner-initiated SSH tunnel; do not expose an unapproved public endpoint.
- Confirm whether the service must run inside a Slurm allocation and respect its time limit.
- Provide documented startup, health-check, log inspection and shutdown commands.
- Keep model files and index versioned as a release.
- Verify the deployed model checksum against the locally accepted release.
- Test the full request/response path from the local frontend.
- Do not assume a Slurm job or inference service persists after its allocation expires.
- Do not leave abandoned GPU jobs or services running.

Illustrative tunnel command (replace placeholders only with administrator-approved values):

```bash
ssh -N -L 8000:127.0.0.1:8000 <APPROVED_USER>@<APPROVED_HOST>
```

Never place passwords, private keys or tokens in this document or in the repository.

## 11. Approval gates

Obtain the user's approval before:

- Starting a long or expensive training/tuning sweep.
- Using unusually large GPU/CPU/storage allocations.
- Downloading or copying large datasets/model artifacts to the server.
- Creating a persistent service or deploying the demo.
- Deleting project data, checkpoints, logs or environments.
- Changing the agreed data, evaluation or research protocol.

Obtain administrator approval before any action affecting core configuration, shared services, system-wide software or other users.

Routine project-owned work within an already approved allocation and policy can proceed without treating every command as a new approval event.

## 12. Definition of done

The server workstream is complete only when:

- The training environment and exact dependencies are documented.
- Smoke tests pass.
- Baseline, tuning and final experiments have reproducible records.
- Accepted models are selected using validation data.
- Final test evaluation is performed under the frozen protocol.
- Accepted checkpoints and release artifacts are transferred and checksum-verified.
- Independent backups exist and restoration has been tested.
- The inference service is deployed under the approved access model.
- The local demo connects successfully through the approved tunnel.
- Startup, health-check, troubleshooting and shutdown steps are documented.
- No administrator-managed configuration or preinstalled system has been modified.

## 13. Agent operating instructions

The coding agent must:

1. Treat the canonical repository above as the only project repository for this work.
2. Never substitute the older `AbdulMalik1287/NLP` repository.
3. Preserve existing project decisions and research protocol unless the user approves a change.
4. Inspect live server state before relying on historical environment notes.
5. Use isolated, project-owned environments and approved storage.
6. Protect administrator-managed systems and other users' workloads.
7. Prepare training and tuning early enough to accommodate queue delays, failed runs and reruns.
8. Make experiments reproducible and resumable.
9. Keep source code and backups on the user's local machine and independent backup locations.
10. Report exact commit SHA, changed files, commands, test results, job IDs, resource usage, artifact paths and checksums.
11. Distinguish verified results from historical notes, estimates and assumptions.
12. Stop and ask before destructive actions, policy exceptions or changes to core infrastructure.

**Operating principle:** Use the server productively; isolate project changes; preserve the shared environment; make experiments reproducible; and keep verified backups outside the server.
