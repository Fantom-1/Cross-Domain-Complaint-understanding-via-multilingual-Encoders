# Container use notes

This directory contains an optional Dockerfile. Do not build/run it on the cluster until the site's policy confirms user images can be used by SLURM and a single allocated MIG device is safely exposed to the container.

Never run privileged Docker, never use `--gpus all`, and never mount broad host directories. A host installation of Docker Engine does not prove that a user has permission to use Docker or that GPU constraints are inherited from SLURM.

If Docker execution cannot be safely constrained, use a dedicated user-owned Python environment under SLURM instead. Do not modify the daemon, NVIDIA toolkit, SLURM config or other system settings.
