# Environment Setup — No Host/System Changes

## Preferred route: user-owned environment
Create a dedicated environment at a verified user-owned path. The exact Python command depends on what is already installed and permitted; do not assume `conda`, `micromamba` or `venv` is available without inspection. Installing packages into this environment must not alter system Python or a shared Conda base.

Before changing the environment:
1. Record the current Python, OS, installed packages, environment paths and quotas.
2. Check whether a usable user-specific environment already exists.
3. Decide the compatible Python/PyTorch/Transformers combination.
4. Create a new prefix under approved storage; never reuse a shared environment.
5. Install only inside that prefix.
6. Run CPU tests and a GPU smoke test in a SLURM allocation.
7. Export a lock/freeze file and environment report.

Do not blindly upgrade PyTorch. The server spec lists PyTorch `2.11.0+cu12.8` as a preconfigured build, but your own environment must be independently verified.

## Container route
`container/Dockerfile` is optional. Build it in a permitted location (a personal workstation or approved build environment) and test that the cluster's existing Docker/SLURM integration respects GPU allocation. Do not assume access to the daemon. Do not change Docker daemon config or request administrator privileges. Do not use `--gpus all`.

## Cache paths
Use explicitly approved user-owned paths for model/cache/temp files. The following are variable examples, not literal paths:
- `HF_HOME`
- `HF_DATASETS_CACHE`
- `TORCH_HOME`
- `TMPDIR`
- `XDG_CACHE_HOME`

Check disk/inode quota before creating them. Do not place large checkpoints on a small home filesystem.
