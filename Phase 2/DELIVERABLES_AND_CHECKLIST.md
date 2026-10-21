# Acceptance Checklist

## Data gate
- [ ] Actual files, hashes, label map and split manifest verified.
- [ ] Counts reconcile, including sampling exclusion.
- [ ] Mapping status accurately describes rule-derived labels.
- [ ] Dedup algorithm docs and code match.
- [ ] Tests pass against actual processed release.
- [ ] Current limitations clearly stated.

## Environment/cluster gate
- [ ] No system/server settings changed.
- [ ] User-owned environment or approved image only.
- [ ] Paths/ownership/quotas confirmed.
- [ ] SLURM GPU request syntax verified from actual site docs.
- [ ] Actual allocated device and VRAM observed.
- [ ] Container GPU isolation confirmed if container path is used.

## Smoke/pilot gate
- [ ] Output shape matches approved class count.
- [ ] Finite loss/gradients.
- [ ] Peak allocated/reserved VRAM recorded.
- [ ] Checkpoint save/load/resume tested.
- [ ] No OOM or resource-policy violation.
- [ ] Pilot metrics not presented as baseline results.

## Tuning/final gate
- [ ] Limited sequential LR search completed using validation only.
- [ ] Trial ledger complete.
- [ ] Final settings locked before test evaluation.
- [ ] Test evaluated only after selection.
- [ ] Metrics, support, confusion matrix and error analysis saved.
- [ ] Seeds and environment recorded.
- [ ] Claims constrained to English, in-distribution data unless other data/splits exist.

## Final agent report
Phase/gate status; actual data hashes/counts; environment isolation method; GPU/MIG type and memory actually allocated; exact SLURM job IDs/states; config/model revision hashes; tuning results; final test results; limitations; any failed checks; explicit confirmation no system/server settings or other users' work were modified.
