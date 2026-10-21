# Environment and Container Strategy

## Preference order
1. **User-owned Python environment** under an approved quota-aware path, with dependencies installed only into that prefix.
2. **User-built container image** if the site's policy supports running it under SLURM and the allocated MIG GPU is safely passed through.
3. Stop and request administrator guidance if neither method is permitted without a system change. Do not create a system-level workaround.

## User-owned environment
Use an explicit project prefix, never global `pip` or the system Python. First inspect the allowed Python/Conda options and existing user environment. Save an environment snapshot. Decide the PyTorch build only after confirming the site's driver, CUDA runtime, and the Python version. Install Transformers, Accelerate, Datasets, scikit-learn, pandas, PyYAML and other required packages inside the project prefix.

Do not blindly install or upgrade PyTorch if the environment already has a functional GPU build. Do not share the environment across projects. Keep `requirements-lock.txt` or an equivalent export in the project. The environment directory itself should generally be excluded from Git.

## Container option
`container/Dockerfile` is an optional template. It builds an unprivileged runtime image with project libraries. It does not change host settings. Use only when the site allows a user's image to be built and used under SLURM. The site administrator must confirm whether Docker is permitted and how scheduler-assigned MIG devices are passed into containers. Do not use `--gpus all`.

If using a local build and moving it to the cluster, transfer the image through approved storage, record SHA-256/digest, and verify it. Do not bake raw datasets, model weights, tokens or private credentials into image layers.

## Caches and data
After confirming user-owned storage and quota, set:
- `HF_HOME=$PROJECT_USER_STORAGE/hf`
- `HF_DATASETS_CACHE=$PROJECT_USER_STORAGE/hf-datasets`
- `TORCH_HOME=$PROJECT_USER_STORAGE/torch`
- `TMPDIR=$PROJECT_USER_STORAGE/tmp`
- `XDG_CACHE_HOME=$PROJECT_USER_STORAGE/xdg`

These are examples, not literal paths. Create paths only after checking ownership/quota. Ensure permissions are restrictive if data access rules require them. Never use another user's or global shared writable cache.
