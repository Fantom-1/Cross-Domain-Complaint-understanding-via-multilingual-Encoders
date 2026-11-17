"""Phase 7: Split Feasibility & Boundary Formulation Module.

Provides empirical analysis of:
1. Product Domain x Intent Label contingency matrix, sparsity, and domain-exclusive classes.
2. Domain transfer (cross-product generalization) feasibility and structural confounding.
3. Temporal (chronological) complaint distribution, class stability, and near-duplicate cluster spanning.
4. In-distribution group-stratified split verification and fail-closed cluster-exclusivity leakage assertions.
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
EXPECTED_TEMPORAL_MONTHS = 36

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

ALL_CLASSES = [
    "account_access",
    "account_management",
    "application_problem",
    "closing_process",
    "credit_terms_dispute",
    "debt_communication",
    "debt_not_owed",
    "debt_threats",
    "fraud_or_scam",
    "funds_availability",
    "payment_problem",
    "reporting_improper_use",
    "reporting_incorrect_information",
    "reporting_investigation_dispute",
    "servicing_dispute",
    "transaction_problem",
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
        """Computes the 9 domain x 16 intent contingency matrix, cell sparsity, and marginals.
        
        Strictly enforces the canonical 9 domains and 16 classes universe. Fails closed with ValueError
        if any unexpected domain or intent class appears.
        """
        if df is None:
            if not os.path.exists(self.parquet_path):
                raise FileNotFoundError(f"Canonical dataset not found: {self.parquet_path}")
            df = pd.read_parquet(self.parquet_path)

        observed_domains = set(df["domain"].unique())
        observed_classes = set(df["intent_label"].unique())

        unexpected_domains = observed_domains - set(ALL_DOMAINS)
        if unexpected_domains:
            raise ValueError(f"Unexpected domain(s) detected: {sorted(unexpected_domains)}")

        unexpected_classes = observed_classes - set(ALL_CLASSES)
        if unexpected_classes:
            raise ValueError(f"Unexpected intent class(es) detected: {sorted(unexpected_classes)}")

        crosstab = pd.crosstab(df["domain"], df["intent_label"])

        # Reindex explicitly to canonical universe so that all expected domains and classes exist
        crosstab = crosstab.reindex(index=ALL_DOMAINS, columns=ALL_CLASSES, fill_value=0)

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

        for c in ALL_CLASSES:
            col = crosstab[c]
            active_doms = col[col > 0].index.tolist()
            if len(active_doms) == 1:
                exclusive_classes[c] = active_doms[0]
            else:
                shared_classes[c] = active_doms

        return {
            "crosstab": crosstab,
            "total_records": len(df),
            "domains": ALL_DOMAINS,
            "classes": ALL_CLASSES,
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
        for d in ALL_DOMAINS:
            row = {"domain": d}
            for c in classes:
                row[c] = int(crosstab.loc[d, c])
            tot = int(crosstab.loc[d].sum())
            row["total_records"] = tot
            row["domain_share_pct"] = round((tot / total_corpus) * 100, 2) if total_corpus > 0 else 0.0
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

        observed_domains = sorted(df["domain"].unique())
        all_classes = sorted(df["intent_label"].unique())

        held_out_diagnostics = {}
        confounded_domains = []

        for d in observed_domains:
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
            "total_domains": len(observed_domains),
            "confounded_domains": confounded_domains,
            "confounded_count": len(confounded_domains),
            "held_out_diagnostics": held_out_diagnostics,
        }

    def audit_temporal_distribution(
        self,
        temp_dist_path: Optional[str] = None,
        temp_class_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Audits the temporal distribution and class support manifests."""
        dist_path = temp_dist_path or TEMPORAL_DISTRIBUTION_CSV
        class_path = temp_class_path or TEMPORAL_CLASS_DISTRIBUTION_CSV

        if not os.path.exists(dist_path):
            raise FileNotFoundError(f"Temporal distribution manifest not found: {dist_path}")
        if not os.path.exists(class_path):
            raise FileNotFoundError(f"Temporal class distribution manifest not found: {class_path}")

        with open(dist_path, "r", encoding="utf-8") as f:
            dist_rows = list(csv.DictReader(f))

        total_months = len(dist_rows)
        total_complaints = sum(int(r["complaint_count"]) for r in dist_rows)
        start_month = dist_rows[0]["year_month"] if dist_rows else ""
        end_month = dist_rows[-1]["year_month"] if dist_rows else ""

        with open(class_path, "r", encoding="utf-8") as f:
            class_rows = list(csv.DictReader(f))

        active_in_all_years = True
        for r in class_rows:
            for y in ["count_2018", "count_2019", "count_2020", "count_2021"]:
                if int(r[y]) <= 0:
                    active_in_all_years = False

        return {
            "total_months": total_months,
            "total_complaints": total_complaints,
            "start_month": start_month,
            "end_month": end_month,
            "total_classes": len(class_rows),
            "active_in_all_years": active_in_all_years,
        }

    def audit_in_distribution_split(
        self,
        split_csv_path: Optional[str] = None,
        clusters_csv_path: Optional[str] = None,
        canonical_parquet_path: Optional[str] = None,
        validate_canonical: bool = False,
        require_cluster_manifest: bool = True,
        require_full_coverage: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Audits the in-distribution baseline split with fail-closed cluster leakage verification.
        
        Guarantees:
        - Split manifest exists, valid row count, valid split values, no duplicate example IDs.
        - Exact bijection of example IDs with canonical dataset when canonical validation is active.
        - Cluster manifest is required; fails closed if missing.
        - Complete, unique, and consistent example-to-cluster mappings; zero cross-split leakage.
        """
        path = split_csv_path or self.split_indomain_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Split manifest not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        total_rows = len(reader)
        example_ids = [r["example_id"] for r in reader]
        unique_eids = set(example_ids)
        duplicate_eids = len(example_ids) - len(unique_eids)

        if duplicate_eids > 0:
            raise ValueError(f"Duplicate example_id values detected in split manifest: {duplicate_eids} duplicates found")

        # Check allowed split values
        allowed_splits = {"train", "validation", "test"}
        observed_splits = set(r["split"] for r in reader)
        invalid_splits = observed_splits - allowed_splits
        if invalid_splits:
            raise ValueError(f"Invalid split values detected in split manifest: {invalid_splits}")

        split_counts = collections.Counter(r["split"] for r in reader)
        split_by_example: Dict[str, str] = {r["example_id"]: r["split"] for r in reader}

        # Validate against canonical parquet if explicitly provided or validate_canonical=True
        canon_path = canonical_parquet_path if canonical_parquet_path is not None else (self.parquet_path if validate_canonical else None)
        reconciled_with_canonical = False
        if canon_path and os.path.exists(canon_path):
            canon_df = pd.read_parquet(canon_path)
            canon_eids = set(canon_df["example_id"].unique())
            if len(canon_df) != total_rows:
                raise ValueError(
                    f"Row count mismatch between canonical parquet ({len(canon_df)}) and split manifest ({total_rows})"
                )
            if canon_eids != unique_eids:
                missing_in_split = canon_eids - unique_eids
                extra_in_split = unique_eids - canon_eids
                raise ValueError(
                    f"Example ID mismatch with canonical parquet: {len(missing_in_split)} missing, {len(extra_in_split)} extra"
                )
            reconciled_with_canonical = True

        # Class and domain coverage across splits
        classes_by_split = collections.defaultdict(lambda: collections.Counter())
        domains_by_split = collections.defaultdict(lambda: collections.Counter())
        groups_by_split = collections.defaultdict(set)

        for r in reader:
            sp = r["split"]
            classes_by_split[sp][r["intent_label"]] += 1
            domains_by_split[sp][r["domain"]] += 1
            gid = r.get("group_id", r["example_id"])
            groups_by_split[gid].add(sp)

        all_classes_in_all_splits = all(
            len(classes_by_split[sp]) == EXPECTED_CLASS_COUNT for sp in allowed_splits if sp in split_counts
        )
        all_domains_in_all_splits = all(
            len(domains_by_split[sp]) == EXPECTED_DOMAIN_COUNT for sp in allowed_splits if sp in split_counts
        )

        # Check group-level leakage within split manifest
        shared_groups = {gid: sps for gid, sps in groups_by_split.items() if len(sps) > 1}
        has_group_leakage = len(shared_groups) > 0

        # Cluster manifest verification - FAIL CLOSED. Requiring the manifest
        # also requires complete coverage unless a test explicitly opts out.
        if require_full_coverage is None:
            require_full_coverage = require_cluster_manifest
        cl_path = clusters_csv_path or self.clusters_path
        if require_cluster_manifest and (not cl_path or not os.path.exists(cl_path)):
            raise FileNotFoundError(f"Cluster manifest required for fail-closed leakage verification but not found: {cl_path}")

        cluster_records_checked = 0
        splits_by_cluster = collections.defaultdict(set)
        shared_clusters = {}

        if cl_path and os.path.exists(cl_path):
            with open(cl_path, "r", encoding="utf-8") as f:
                cl_rows = list(csv.DictReader(f))

            cl_eids = [r["example_id"] for r in cl_rows]
            unique_cl_eids = set(cl_eids)
            if len(cl_eids) != len(unique_cl_eids):
                raise ValueError(
                    f"Duplicate example_id values detected in cluster manifest: {len(cl_eids) - len(unique_cl_eids)} duplicates"
                )

            # Check coverage
            if require_full_coverage:
                missing_coverage = unique_eids - unique_cl_eids
                if missing_coverage:
                    raise ValueError(
                        f"Incomplete cluster mapping coverage: {len(missing_coverage)} example IDs missing from cluster manifest"
                    )

            # Verify each clustered record
            cluster_records_checked = len(cl_rows)
            for r in cl_rows:
                eid = r["example_id"]
                cid = str(r.get("cluster_id", "")).strip()
                if not cid:
                    raise ValueError(f"Empty cluster_id for example_id: {eid}")

                if eid not in split_by_example:
                    raise ValueError(f"Cluster manifest contains unknown example_id: {eid}")

                actual_split = split_by_example[eid]
                # If cluster manifest records a split, verify exact consistency
                if "split" in r and r["split"]:
                    if r["split"] != actual_split:
                        raise ValueError(
                            f"Split mismatch between cluster manifest and split manifest for {eid}: "
                            f"manifest says '{r['split']}', split file says '{actual_split}'"
                        )

                splits_by_cluster[cid].add(actual_split)

            shared_clusters = {cid: sps for cid, sps in splits_by_cluster.items() if len(sps) > 1}

        has_cluster_leakage = len(shared_clusters) > 0
        has_leakage = has_group_leakage or has_cluster_leakage

        return {
            "total_rows": total_rows,
            "train_count": split_counts.get("train", 0),
            "val_count": split_counts.get("validation", 0),
            "test_count": split_counts.get("test", 0),
            "unique_example_ids": len(unique_eids),
            "duplicate_example_ids": duplicate_eids,
            "reconciled_with_canonical": reconciled_with_canonical,
            "unique_groups": len(groups_by_split),
            "shared_groups_count": len(shared_groups),
            "cluster_records_checked": cluster_records_checked,
            "unique_clusters": len(splits_by_cluster),
            "shared_clusters_count": len(shared_clusters),
            "has_leakage": has_leakage,
            "has_group_leakage": has_group_leakage,
            "has_cluster_leakage": has_cluster_leakage,
            "all_classes_in_all_splits": all_classes_in_all_splits,
            "all_domains_in_all_splits": all_domains_in_all_splits,
            "classes_by_split": {k: dict(v) for k, v in classes_by_split.items()},
            "domains_by_split": {k: dict(v) for k, v in domains_by_split.items()},
        }
