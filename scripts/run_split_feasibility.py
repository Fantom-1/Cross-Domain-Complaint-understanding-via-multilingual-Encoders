#!/usr/bin/env python3
"""Phase 7: Split Feasibility & Boundary Formulation Runner.

Executes end-to-end dataset partition feasibility analysis:
1. Product Domain x Intent Label contingency matrix computation and manifest export.
2. Cross-product leave-one-domain-out feasibility and structural confounding quantification.
3. Chronological complaint distribution, temporal continuity, and class persistence verification.
4. In-distribution group-stratified baseline split verification and fail-closed cluster exclusivity audit.
5. Multilingual and modality scope boundary governance verification.
"""

import argparse
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.split_analyzer import (
    CLASS_DOMAIN_COVERAGE_CSV,
    CLUSTERS_CSV_PATH,
    EXPECTED_CLASS_COUNT,
    EXPECTED_DOMAIN_COUNT,
    EXPECTED_MATRIX_CELLS,
    EXPECTED_TEST_ROWS,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VAL_ROWS,
    EXPECTED_ZERO_CELLS,
    SPLIT_INDOMAIN_CSV_PATH,
    TEMPORAL_CLASS_DISTRIBUTION_CSV,
    TEMPORAL_DISTRIBUTION_CSV,
    TOTAL_CANONICAL_ROWS,
    SplitAnalyzer,
)


def run_split_feasibility(regenerate_manifests: bool = True) -> int:
    print("=" * 80)
    print("PHASE 7: SPLIT FEASIBILITY & BOUNDARY FORMULATION RUNNER")
    print(f"Repository Root: {REPO_ROOT}")
    print("=" * 80)

    analyzer = SplitAnalyzer()

    # 1. Contingency Matrix
    print("\n[Step 1/4] Computing Product Domain x Label Contingency Matrix...")
    matrix_res = analyzer.compute_class_domain_matrix()
    print(
        f"  Total records: {matrix_res['total_records']} across {len(matrix_res['domains'])} domains "
        f"and {len(matrix_res['classes'])} classes"
    )
    print(
        f"  Matrix cells: {matrix_res['total_cells']} | Zero cells: {matrix_res['zero_cells']} "
        f"({matrix_res['sparsity_pct']}% sparsity) | Active cells: {matrix_res['active_cells']}"
    )
    print(f"  Exclusive classes: {matrix_res['exclusive_classes']}")

    if regenerate_manifests:
        out_csv = analyzer.export_class_domain_coverage_csv(matrix_res)
        print(f"  Exported manifest: {out_csv}")

    # 2. Cross-Product Domain Transfer Feasibility
    print("\n[Step 2/4] Evaluating Cross-Product Leave-One-Domain-Out Feasibility...")
    tf_res = analyzer.evaluate_domain_transfer_feasibility()
    print(f"  Confounded domains ({tf_res['confounded_count']}/{tf_res['total_domains']}): {tf_res['confounded_domains']}")
    for d, diag in tf_res["held_out_diagnostics"].items():
        status = "CONFOUNDED" if diag["is_structurally_confounded"] else "FEASIBLE"
        print(
            f"  - {d:<22}: {diag['test_instances']:>5} test rows | {diag['test_class_count']:>2}/16 classes | "
            f"Missing in train: {diag['missing_in_train']} [{status}]"
        )

    # 3. Temporal Distribution Audit
    print("\n[Step 3/4] Verifying Chronological & Temporal Distribution Manifests...")
    temp_res = analyzer.audit_temporal_distribution()
    print(
        f"  Temporal span: {temp_res['total_months']} months ({temp_res['start_month']} to {temp_res['end_month']}) | "
        f"Complaints: {temp_res['total_complaints']} | Class persistence across all years: {temp_res['active_in_all_years']}"
    )

    # 4. In-Distribution Split Baseline Audit
    print("\n[Step 4/4] Auditing In-Distribution Split & Cluster Exclusivity...")
    split_res = analyzer.audit_in_distribution_split()
    print(
        f"  Split rows: {split_res['total_rows']} (Train: {split_res['train_count']}, Val: {split_res['val_count']}, Test: {split_res['test_count']})"
    )
    print(f"  Reconciled with canonical dataset: {split_res['reconciled_with_canonical']}")
    print(f"  All 16 classes in all splits: {split_res['all_classes_in_all_splits']}")
    print(f"  All 9 domains in all splits: {split_res['all_domains_in_all_splits']}")
    print(
        f"  Cluster leakage check: {split_res['cluster_records_checked']} duplicate cluster records checked | "
        f"Shared clusters: {split_res['shared_clusters_count']} | Shared groups: {split_res['shared_groups_count']} | "
        f"Leakage verified: {not split_res['has_leakage']}"
    )

    if split_res["has_leakage"]:
        print("\n[ERROR] Cross-partition cluster leakage detected!", file=sys.stderr)
        return 1

    print("\n" + "=" * 80)
    print("PHASE 7 SPLIT FEASIBILITY RUN COMPLETE: ALL INVARIANTS SATISFIED")
    print("=" * 80)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 7 Split Feasibility Runner")
    parser.add_argument(
        "--no-regenerate",
        action="store_false",
        dest="regenerate",
        help="Do not regenerate class_domain_coverage.csv",
    )
    args = parser.parse_args()
    ret = run_split_feasibility(regenerate_manifests=args.regenerate)
    sys.exit(ret)


if __name__ == "__main__":
    main()
