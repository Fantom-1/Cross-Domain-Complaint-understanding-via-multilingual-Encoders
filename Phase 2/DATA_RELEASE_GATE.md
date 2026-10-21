# Data Release Gate Before Model Tuning

The repository claims the prepared release has 45,723 rows and splits 32,019/6,852/6,852, with 16 classes and eight passing tests. The raw/processed files are excluded by Git, so verify on the training machine.

Required checks:
1. Locate actual files and record size/date/owner. Do not create, overwrite or delete any data until inventory is complete.
2. Compute SHA-256 of the source archive and exported train/val/test CSVs.
3. Verify `label_map.json` equals the label-ID pairs in `configs/taxonomy.json`.
4. Compare each split CSV's example IDs and split labels row-for-row with `split_indomain.csv`.
5. Check unique IDs, nonempty text, label support, group overlap, train/val/test exclusivity and exact counts.
6. Reconcile all exclusion counts, including reservoir-sampling omissions. The existing visible exclusion log omits this stage.
7. Confirm the `source_label_mapping.csv` reviewer/status is truthful and mappings have had appropriate human audit or are described as rule-derived weak labels.
8. Ensure docs and code agree on MinHash parameters.
9. Save an immutable/versioned report with data hash and config hash.

Do not wait for a perfect held-out-domain dataset to run the in-distribution baseline, but do not call it domain generalization. If the source-mapping issue remains material, the agent must present the evidence and seek user's acceptance rather than silently claim validated gold labels.
