# Included Trainer — Review Before Cluster Use

`src/training/train_baseline.py` is a scaffold to accelerate implementation, not a claim that it has run successfully against the user's local data or cluster. Before use:

1. Run static/syntax checks in the user's local environment.
2. Compare the installed Transformers/Trainer API with the arguments in the script.
3. Check the specific dataset manifest column names and checksums file format. The script intentionally errors if required files are missing or fail validation.
4. Keep `--evaluate-test` OFF for every LR tuning trial. Only pass it on the final locked run after the chosen configuration is frozen. Never compare trials using test results.
5. Check model head initialization warnings carefully: encoder weights must load; classifier weights may be newly initialized.
6. Validate the `num_proc`/worker choice on the cluster; start conservatively.
7. Add a focused CPU unit-test suite for validation helpers.
8. Run only within an allocated SLURM job after cluster/resource gates pass.

Do not turn off assertions to make this code run. Correct schemas/manifests or fix a justified code defect instead. Never overwrite existing runs.
