# OPTIONAL TEMPLATE ONLY. Build/use only if institutional policy permits user images
# and the container can be constrained to the GPU/MIG resource allocated by SLURM.
# Do not use privileged runtime or mount broad host paths.
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip

# Versions are intentionally installed inside the image, never into the host.
# Validate the site-supported PyTorch/Transformers combination before building a
# production image. This template defaults to the site's documented CUDA 12.8 build.
RUN python3 -m pip install --no-cache-dir \
      torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128

# Pin these after compatibility testing and save the final lock file.
RUN python3 -m pip install --no-cache-dir \
      transformers accelerate datasets scikit-learn pandas pyarrow pyyaml

# Create and use an unprivileged runtime identity.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin trainee \
    && mkdir -p /workspace /job-output \
    && chown -R trainee:trainee /workspace /job-output
USER trainee
WORKDIR /workspace

# Do not bake datasets, Hub weights, credentials or private configs into this image.
# Mount code/config/data read-only where practical, and only the project output as writable.
CMD ["python3", "-c", "import torch; print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available())"]
