# Complaint Understanding - Agent Instruction Pack

Read in this order: `SYSTEM.md`, `PROJECT_BRIEF.md`, `DATA_SOURCES.md`, `DATA_PREPARATION_SPEC.md`, `BASELINE_TRAINING_EVALUATION.md`, `DELIVERABLES_AND_CHECKLIST.md`, `REFERENCES.md`.

**Immediate task:** inspect the repository and existing data; verify source versions, licenses and fields; report an acquisition plan. Do not train or download model weights. Dataset preparation is first; baseline training is allowed only after explicit approval of the data-readiness report and frozen manifests.

The primary model for the later baseline is `facebook/xlm-v-base`. The current scope is standard supervised classification only. Do not implement contrastive learning, retrieval, XLM-R comparisons, or the application stack yet.
