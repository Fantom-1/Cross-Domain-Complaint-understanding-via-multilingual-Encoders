# Phase A Review — Known Issues from the Public Repository

This is a static review of public repository files, not an independent examination of ignored raw/processed data. The files in `.gitignore` such as `data/processed/*.csv` and `canonical_dataset.parquet` must be verified on the actual training machine.

## Figures claimed by `docs/baseline_data_readiness.md`
The report claims 1,041,632 rows in the CFPB 2018-05 to 2021-04 archive, 439,860 narrative rows, 45,723 final records, 16 labels, and splits of 32,019 / 6,852 / 6,852. It reports eight data tests passed. These remain repository claims until compared with actual files.

## Items the agent must verify/fix or explicitly accept as limitations
1. `docs/repository_audit.md` contains unchecked preparation tasks while `docs/baseline_data_readiness.md` declares Phase A complete.
2. Data files are ignored by Git; GitHub does not establish they exist or match the report on the cluster.
3. Exclusion log lacks an explicit reservoir-sampling omission category. Reconcile all rows and explain sampling omissions.
4. `src/data/map_intents.py` maps labels by ordered substring rules against CFPB issue/sub-issue metadata. Mapping is weakly supervised/source-taxonomy mapping, not human annotation. “Automated Rule Engine (Reviewed)” is not adequate evidence of human review.
5. Mapping patterns may overlap and be order-dependent. Audit rule collisions and class samples. If changed, create a new versioned release.
6. Visible manifest is in-distribution only. Do not claim held-out-domain performance.
7. `docs/data_preparation_methodology.md` says the MinHash prime is `2^61-1`, while `src/data/dedup.py` uses `2^31-1`. Align documentation with code; confirm grouping implementation behavior.
8. Download routine has a path that can remove an existing target before rename. Do not rerun acquisition on the cluster until safe no-clobber behavior is verified.
9. Existing tests do not fully reconcile raw/source/exclusion counts and the split manifest row-for-row against exported CSVs.
10. The capped class distribution is not a naturally representative population distribution. Report this limitation.
11. Inventory metadata should distinguish archive coverage/release from retrieval date and revision/hash.
12. All source hashes, processed-file hashes, label-map identity, split CSV rows, manifest assignments, group leakage and outputs must be independently verified.

## Gate decision
Do not launch full tuning until the available dataset release passes these checks or unresolved issues are explicitly documented and the user approves the risk. Do not silently rebuild or overwrite existing data. This baseline's current supported scope is English CFPB complaint classification on an in-distribution split.
