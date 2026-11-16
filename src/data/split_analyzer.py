"""Phase 7: Split Feasibility & Boundary Formulation Module.

Provides empirical analysis of:
1. Product Domain x Intent Label contingency matrix, sparsity, and domain-exclusive classes.
2. Domain transfer (cross-product generalization) feasibility and structural confounding.
3. Temporal (chronological) complaint distribution, class stability, and near-duplicate cluster spanning.
4. In-distribution group-stratified split verification and cluster-exclusivity leakage assertions.
5. Multilingual / modality scope boundaries (formal Hindi/Hinglish deferral).
"""

import collections
import csv
import os
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

# Canonical constants
CANONICAL_PARQUET_PATH = "data/processed/canonical_dataset.parquet"
CLUSTERS_CSV_PATH = "data/manifests/duplicate_clusters.csv"
SPLIT_INDOMAIN_CSV_PATH = "data/manifests/split_indomain.csv"
CLASS_DOMAIN_COVERAGE_CSV = "data/manifests/class_domain_coverage.csv"
TEMPORAL_DISTRIBUTION_CSV = "data/manifests/temporal_distribution.csv"
TEMPORAL_CLASS_DISTRIBUTION_CSV = "data/manifests/temporal_class_distribution.csv"

TOTAL_CANONICAL_ROWS = 45723
EXPECTED_CLASS_COUNT = 16
EXPECTED_DOMAIN_COUNT = 9
EXPECTED_MATRIX_CELLS = 144  # 9 x 16
EXPECTED_ZERO_CELLS = 81     # 56.25% sparsity
EXPECTED_ACTIVE_CELLS = 63   # 43.75% active

EXPECTED_TRAIN_ROWS = 32019
EXPECTED_VAL_ROWS = 6852
EXPECTED_TEST_ROWS = 6852

ALL_DOMAINS = [
    "bank_account",
    "credit_card",
    "credit_reporting",
    "debt_collection",
    "money_transfer",
    "mortgage",
    "payday_personal_loan",
    "student_loan",
    "vehicle_loan",
]

DOMAIN_EXCLUSIVE_CLASSES = {
    "closing_process": "mortgage",
    "debt_communication": "debt_collection",
    "debt_not_owed": "debt_collection",
    "debt_threats": "debt_collection",
}


class SplitAnalyzer:
    """Analyzer for dataset partitioning, cross-domain transfer, and temporal feasibility."""

    def __init__(
        self,
        parquet_path: str = CANONICAL_PARQUET_PATH,
        clusters_path: str = CLUSTERS_CSV_PATH,
        split_indomain_path: str = SPLIT_INDOMAIN_CSV_PATH,
    ):
        self.parquet_path = parquet_path
        self.clusters_path = clusters_path
        self.split_indomain_path = split_indomain_path

    def compute_class_domain_matrix(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Computes the 9 domain x 16 intent contingency matrix, cell sparsity, and marginals."""
        if df is None:
            if not os.path.exists(self.parquet_path):
                raise FileNotFoundError(f"Canonical dataset not found: {self.parquet_path}")
            df = pd.read_parquet(self.parquet_path)

        domains = sorted(df["domain"].unique())
        classes = sorted(df["intent_label"].unique())

        crosstab = pd.crosstab(df["domain"], df["intent_label"])

        # Reindex to ensure all expected domains and classes are present
        for d in ALL_DOMAINS:
            if d not in crosstab.index:
                crosstab.loc[d] = 0
        crosstab = crosstab.reindex(index=sorted(crosstab.index), columns=classes, fill_value=0)

        total_cells = len(crosstab.index) * len(crosstab.columns)
        zero_cells = int((crosstab == 0).sum().sum())
        active_cells = total_cells - zero_cells
        sparsity_pct = round((zero_cells / total_cells) * 100, 2)

        # Domain totals and shares
        domain_records = crosstab.sum(axis=1).to_dict()
        class_records = crosstab.sum(axis=0).to_dict()

        # Identify exclusive and shared classes
        exclusive_classes: Dict[str, str] = {}
        shared_classes: Dict[str, List[str]] = {}

        for c in classes:
            col = crosstab[c]
            active_doms = col[col > 0].index.tolist()
            if len(active_doms) == 1:
                exclusive_classes[c] = active_doms[0]
            else:
                shared_classes[c] = active_doms

        return {
            "crosstab": crosstab,
            "total_records": len(df),
            "domains": sorted(list(crosstab.index)),
            "classes": classes,
            "total_cells": total_cells,
            "zero_cells": zero_cells,
            "active_cells": active_cells,
            "sparsity_pct": sparsity_pct,
            "domain_records": domain_records,
            "class_records": class_records,
            "exclusive_classes": exclusive_classes,
            "shared_classes": shared_classes,
        }

    def export_class_domain_coverage_csv(
        self,
        matrix_res: Dict[str, Any],
        output_path: str = CLASS_DOMAIN_COVERAGE_CSV,
    ) -> str:
        """Exports structured machine-readable class_domain_coverage.csv manifest."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        crosstab = matrix_res["crosstab"]
        classes = matrix_res["classes"]
        total_corpus = matrix_res["total_records"]

        fieldnames = (
            ["domain"]
            + classes
            + ["total_records", "domain_share_pct", "active_classes_count", "zero_classes_count"]
        )

        rows = []
        for d in sorted(crosstab.index):
            row = {"domain": d}
            for c in classes:
                row[c] = int(crosstab.loc[d, c])
            tot = int(crosstab.loc[d].sum())
            row["total_records"] = tot
            row["domain_share_pct"] = round((tot / total_corpus) * 100, 2)
            row["active_classes_count"] = int((crosstab.loc[d] > 0).sum())
            row["zero_classes_count"] = int((crosstab.loc[d] == 0).sum())
            rows.append(row)

        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

        return output_path

    def evaluate_domain_transfer_feasibility(
        self, df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """Evaluates leave-one-domain-out transfer feasibility for each of the 9 product domains.
        
        Proves structural confounding by identifying classes present in the held-out test domain
        that have ZERO training instances in the remaining 8 domains.
        """
        if df is None:
            if not os.path.exists(self.parquet_path):
                raise FileNotFoundError(f"Canonical dataset not found: {self.parquet_path}")
            df = pd.read_parquet(self.parquet_path)

        domains = sorted(df["domain"].unique())
        all_classes = sorted(df["intent_label"].unique())

        held_out_diagnostics = {}
        confounded_domains = []

        for d in domains:
            train_sub = df[df["domain"] != d]
            test_sub = df[df["domain"] == d]

            train_classes = set(train_sub["intent_label"].unique())
            test_classes = set(test_sub["intent_label"].unique())

            missing_in_train = sorted(list(test_classes - train_classes))
            untested_classes = sorted(list(set(all_classes) - test_classes))

            is_confounded = len(missing_in_train) > 0
            if is_confounded:
                confounded_domains.append(d)

            held_out_diagnostics[d] = {
                "held_out_domain": d,
                "test_instances": len(test_sub),
                "train_instances": len(train_sub),
                "test_class_count": len(test_classes),
                "missing_in_train": missing_in_train,
                "missing_in_train_count": len(missing_in_train),
                "untested_class_count": len(untested_classes),
                "is_structurally_confounded": is_confounded,
            }

        return {
            "total_domains": len(domains),
            "confounded_domains": confounded_domains,
            "confounded_count": len(confounded_domains),
            "held_out_diagnostics": held_out_diagnostics,
        }

    def audit_in_distribution_split(
        self,
        split_csv_path: Optional[str] = None,
        clusters_csv_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Audits the in-distribution baseline split for row quotas, class representation, and zero leakage."""
        path = split_csv_path or self.split_indomain_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Split manifest not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        total_rows = len(reader)
        split_counts = collections.Counter(r["split"] for r in reader)

        # Cluster leakage audit
        cl_path = clusters_csv_path or self.clusters_path
        cluster_map: Dict[str, str] = {}
        if cl_path and os.path.exists(cl_path):
            with open(cl_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    cluster_map[r["example_id"]] = r["cluster_id"]

        splits_by_cluster = collections.defaultdict(set)
        for r in reader:
            eid = r["example_id"]
            gid = r.get("group_id", eid)
            cid = cluster_map.get(eid, gid)
            splits_by_cluster[cid].add(r["split"])

        shared_clusters = {cid: sp for cid, sp in splits_by_cluster.items() if len(sp) > 1}
        has_leakage = len(shared_clusters) > 0

        # Class support per split
        classes_by_split = collections.defaultdict(lambda: collections.Counter())
        for r in reader:
            classes_by_split[r["split"]][r["intent_label"]] += 1

        all_classes_in_all_splits = (
            len(classes_by_split["train"]) == EXPECTED_CLASS_COUNT
            and len(classes_by_split["validation"]) == EXPECTED_CLASS_COUNT
            and len(classes_by_split["test"]) == EXPECTED_CLASS_COUNT
        )

        return {
            "total_rows": total_rows,
            "train_count": split_counts.get("train", 0),
            "val_count": split_counts.get("validation", 0),
            "test_count": split_counts.get("test", 0),
            "unique_clusters": len(splits_by_cluster),
            "shared_clusters_count": len(shared_clusters),
            "has_leakage": has_leakage,
            "all_classes_in_all_splits": all_classes_in_all_splits,
            "classes_by_split": dict(classes_by_split),
        }

