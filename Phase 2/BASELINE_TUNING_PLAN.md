# Baseline Tuning Plan — Small, Sequential, Validation-Only Search

## Experiment A: verify data
Before loading model weights, the program must validate:
- actual train/validation/test files and their recorded SHA-256 hashes;
- frozen label map and label IDs;
- unique IDs, non-empty text, valid labels;
- CSV rows exactly match `split_indomain.csv`;
- no `group_id` crosses splits;
- every validation/test label exists in train;
- split/source counts and known mapping limitations.
If checks fail, stop before model loading.

## Experiment B: GPU smoke test
Use one site-approved SLURM allocation. Start with:
- micro-batch 1;
- maximum sequence length 128;
- gradient checkpointing enabled;
- BF16 only if `torch.cuda.is_bf16_supported()` is true on the allocated device; otherwise test FP16 with finite-loss/gradient checks or FP32 if practical;
- one forward, backward and optimizer step; then release memory.
Log actual GPU name/VRAM, PyTorch/CUDA versions, peak allocated/reserved VRAM, finite loss/gradients, time per step, and exit code. No full epoch during smoke test.
If full fine-tuning does not fit, stop and present memory evidence. Do not silently change methodology.

## Experiment C: short pilot
- Start at sequence length 128 and micro-batch 1, with gradient checkpointing.
- Use a short controlled subset of the training set, preserving class variety only for throughput/memory diagnostics. Do not report pilot metric as the baseline result.
- Check checkpoint save/reload and a true training resume.
- Test sequence length 256 only if the 128-token pilot has safe memory headroom. Select final maximum length from tokenizer length statistics on train only plus validation behavior, with the truncation fraction reported.

## Experiment D: tune only the small planned search
Only after data release and smoke/pilot gates pass:
- Trial LR `1e-5`, then `2e-5`; optional `3e-5` only if resource budget permits and it is authorized.
- Same frozen split, seed `42` for comparison, same sequence length, effective batch size and precision. Change one main variable at a time.
- Up to 3 epochs per tuning trial; validation Macro-F1 selects epoch/checkpoint.
- AdamW, weight decay `0.01`, warmup ratio `0.06`, max gradient norm `1.0` as provisional starting settings.
- Use micro-batch determined by observed VRAM, likely 1 on a 24 GB MIG profile. Gradient accumulation may target effective batch 8 if stable and within walltime, but it does not reduce parameter/optimizer-state memory.
- Avoid concurrent trials and broad grid search. Use one job at a time.
- Log config hash, data hash, seed, lr, max length, micro/effective batch, accumulation steps, precision, grad-checkpointing, step/epoch, validation Macro-F1, loss, runtime, peak VRAM, checkpoint bytes, SLURM job ID, exit code.

## Experiment E: final run
- Lock tuning choice before touching test metrics.
- Train full training split, monitor validation, restore best validation checkpoint.
- If compute budget permits, use seeds `13`, `42`, `2026` sequentially; if not, clearly state the number of seeds.
- Evaluate frozen test set after config selection. Do not alter tuning based on test results.
- Report Macro-F1, accuracy, per-class metrics/support, confusion matrix, learning curves, throughput/VRAM and redacted error analysis.

## Interpret limitations
- Current corpus is reported English-only; no multilingual complaint claims.
- Current split is in-distribution; no held-out-domain claims.
- Labels are currently rule-mapped from CFPB issue/sub-issue; they are not independently annotated unless actual human audit evidence exists.
- Per-class capping changes prevalence; do not make population-level claims.
