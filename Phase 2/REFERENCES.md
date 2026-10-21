# References

## Model and architecture
- XLM-V paper: https://arxiv.org/abs/2301.10472
- Model card: https://huggingface.co/facebook/xlm-v-base
- Config: https://huggingface.co/facebook/xlm-v-base/blob/main/config.json
- Transformers XLM-V model docs: https://huggingface.co/docs/transformers/model_doc/xlm-v
- Transformers sequence-classification guide: https://huggingface.co/docs/transformers/tasks/sequence_classification

## Data sources
- CFPB complaints: https://www.consumerfinance.gov/data-research/consumer-complaints/
- CFPB narratives archive: https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/
- CFPB API release notes: https://cfpb.github.io/api/ccdb/release-notes.html
- BANKING77 card: https://huggingface.co/datasets/PolyAI/banking77
- MASSIVE paper: https://aclanthology.org/2023.acl-long.235/
- COMI-LINGUA: https://aclanthology.org/2025.findings-emnlp.422/
- Code-mixing resource page: https://lingo.iitgn.ac.in/codemixing/

## SLURM / container references
- `sbatch`: https://slurm.schedmd.com/sbatch.html
- `squeue`: https://slurm.schedmd.com/squeue.html
- `sacct`: https://slurm.schedmd.com/sacct.html
- Apptainer user guide: https://apptainer.org/docs/user/latest/
- NVIDIA supported MIG profiles: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html
- NVIDIA supported MIG GPUs: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html

NVIDIA documents up to four `1g.24gb` MIG profiles per RTX PRO 6000 Blackwell Server Edition GPU. The server sheet describes eight per physical GPU, so treat its total as unresolved and verify the actual allocation/device memory rather than requesting a guessed quantity.
