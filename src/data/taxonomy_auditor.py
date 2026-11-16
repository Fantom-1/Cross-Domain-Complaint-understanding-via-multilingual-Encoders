#!/usr/bin/env python3
"""Taxonomy auditor and annotation agreement module for Phase 6.

Provides:
- Taxonomy schema verification and operational codebook consistency.
- Rule pattern collision and order-dependency audit across CFPB source mappings.
- Stratified sampling from canonical_dataset.parquet for pilot annotation (N=320)
  enforcing strict per-class domain x split quotas (14 train, 3 val, 3 test)
  and zero near-duplicate cluster re-sampling (320 distinct clusters).
- Blinded annotation instrument generation for independent human raters.
- Provenance auditing to distinguish genuine human adjudication from synthetic simulation.
- Inter-annotator agreement metrics: observed agreement, Cohen's Kappa, and confusion matrices.
"""

import collections
import csv
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple


TAXONOMY_PATH = "configs/taxonomy.json"
SOURCE_MAPPING_PATH = "data/manifests/source_label_mapping.csv"
CANONICAL_PARQUET_PATH = "data/processed/canonical_dataset.parquet"
CLUSTERS_CSV_PATH = "data/manifests/duplicate_clusters.csv"
PILOT_MANIFEST_PATH = "data/manifests/label_pilot_sampling_manifest.csv"
RATER_1_SHEET_PATH = "data/annotation/rater_1_blinded_sheet.csv"
RATER_2_SHEET_PATH = "data/annotation/rater_2_blinded_sheet.csv"
ADJUDICATION_TEMPLATE_PATH = "data/annotation/adjudication_template.csv"
SYNTHETIC_SIMULATION_PATH = "data/manifests/synthetic_pilot_simulation.csv"

PILOT_TARGET_PER_CLASS = 20
EXPECTED_CLASS_COUNT = 16
EXPECTED_PILOT_SIZE = 320  # 16 classes * 20 instances
SPLIT_QUOTAS = {"train": 14, "validation": 3, "test": 3}

PROVENANCE_HUMAN = "human_adjudicated"
PROVENANCE_SYNTHETIC = "synthetic_rule_simulation"


def load_taxonomy(path: str = TAXONOMY_PATH) -> Dict[str, Any]:
    """Loads and validates the taxonomy configuration JSON."""
    with open(path, "r", encoding="utf-8") as f:
        tax = json.load(f)
    if "classes" not in tax or len(tax["classes"]) != EXPECTED_CLASS_COUNT:
        raise ValueError(f"Taxonomy must contain exactly {EXPECTED_CLASS_COUNT} classes")
    return tax


def compute_cohens_kappa(
    rater1: List[str],
    rater2: List[str],
    labels: Optional[List[str]] = None
) -> Tuple[float, float]:
    """Computes observed agreement (Po) and Cohen's Kappa (kappa) between two raters.
    
    Returns:
        (observed_agreement, kappa)
    """
    if len(rater1) != len(rater2):
        raise ValueError("Rater predictions must have identical length")
    n = len(rater1)
    if n == 0:
        return 1.0, 1.0

    if labels is None:
        labels = sorted(list(set(rater1) | set(rater2)))

    # Observed agreement
    agree_count = sum(1 for a, b in zip(rater1, rater2) if a == b)
    p_o = agree_count / n

    # Expected agreement by chance
    count1 = collections.Counter(rater1)
    count2 = collections.Counter(rater2)

    p_e = sum((count1[lbl] / n) * (count2[lbl] / n) for lbl in labels)

    if p_e >= 1.0:
        kappa = 1.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return p_o, kappa


def compute_per_class_metrics(
    gold: List[str],
    pred: List[str],
    labels: List[str]
) -> Dict[str, Dict[str, float]]:
    """Computes precision, recall, and F1 per class."""
    metrics = {}
    for lbl in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lbl and p == lbl)
        fp = sum(1 for g, p in zip(gold, pred) if g != lbl and p == lbl)
        fn = sum(1 for g, p in zip(gold, pred) if g == lbl and p != lbl)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        support = sum(1 for g in gold if g == lbl)
        metrics[lbl] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    return metrics


class TaxonomyAuditor:
    """Audits taxonomy rules, mapping collisions, and pilot adjudication results."""

    def __init__(self, taxonomy_path: str = TAXONOMY_PATH):
        self.taxonomy = load_taxonomy(taxonomy_path)
        self.classes = self.taxonomy["classes"]
        self.class_names = [c["intent_label"] for c in self.classes]
        self.label_to_id = {c["intent_label"]: c["intent_id"] for c in self.classes}

    def audit_source_mapping_collisions(
        self, mapping_path: str = SOURCE_MAPPING_PATH
    ) -> Dict[str, Any]:
        """Audits CFPB source label mappings for rule overlaps and order dependencies."""
        if not os.path.exists(mapping_path):
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(mapping_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        total_mappings = len(reader)
        mapped_count = sum(1 for r in reader if r["mapping_status"] == "mapped")
        unmapped_count = sum(1 for r in reader if r["mapping_status"] == "unmapped")

        collisions: List[Dict[str, Any]] = []

        for row in reader:
            s_label = row["source_label"].lower()
            matching_classes: List[Dict[str, str]] = []

            for cls in self.classes:
                for pat in cls["rule_patterns"]:
                    if pat.lower() in s_label:
                        matching_classes.append({
                            "intent_label": cls["intent_label"],
                            "pattern": pat
                        })

            distinct_intents = sorted(list(set(m["intent_label"] for m in matching_classes)))
            if len(distinct_intents) > 1:
                collisions.append({
                    "source_label": row["source_label"],
                    "assigned_label": row["project_intent_label"],
                    "matching_intents": distinct_intents,
                    "matched_patterns": matching_classes,
                })

        return {
            "total_mappings": total_mappings,
            "mapped_count": mapped_count,
            "unmapped_count": unmapped_count,
            "collision_count": len(collisions),
            "collisions": collisions,
        }

    def sample_stratified_pilot(
        self,
        parquet_path: str = CANONICAL_PARQUET_PATH,
        clusters_csv_path: Optional[str] = CLUSTERS_CSV_PATH,
        split_quotas: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """Samples a deterministic, stratified pilot dataset (N = 320).
        
        Enforces:
        1. Exactly 20 records per class across all 16 weak-label strata (derived from administrative metadata, not human-validated semantic classes).
        2. Strict split quotas per class: 14 train, 3 validation, 3 test (224 train, 48 val, 48 test total across the 16 weak-label strata).
        3. Round-robin domain rotation within each split pool (not fixed domain x split cell quotas).
        4. Near-duplicate cluster exclusivity: at most 1 instance per cluster_id (320 unique clusters).
        """
        import pandas as pd

        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"Canonical dataset not found: {parquet_path}")

        quotas = split_quotas or SPLIT_QUOTAS
        target_per_class = sum(quotas.values())

        df = pd.read_parquet(parquet_path)

        # Load cluster map if available for cluster-exclusive sampling
        cluster_map: Dict[str, str] = {}
        if clusters_csv_path and os.path.exists(clusters_csv_path):
            with open(clusters_csv_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    cluster_map[r["example_id"]] = r["cluster_id"]

        # Assign effective cluster (cluster_id if multi-item, else group_id/hash)
        effective_clusters = []
        for eid, gid in zip(df["example_id"], df["group_id"]):
            effective_clusters.append(cluster_map.get(eid, gid))
        df["effective_cluster"] = effective_clusters

        # Deterministic sorting
        if "text_hash" in df.columns:
            df["sort_key"] = df["text_hash"] + "_" + df["example_id"]
        else:
            df["sort_key"] = df["example_id"]
        df = df.sort_values("sort_key").reset_index(drop=True)

        seen_clusters: Set[str] = set()
        sampled_rows: List[Dict[str, Any]] = []
        pilot_counter = 1

        for cls_name in sorted(self.class_names):
            cls_df = df[df["intent_label"] == cls_name]
            for split_name, quota in quotas.items():
                s_df = cls_df[cls_df["split"] == split_name]
                domains = sorted(s_df["domain"].unique())
                domain_pools = {d: s_df[s_df["domain"] == d] for d in domains}

                allocated = 0
                d_idx = 0
                max_attempts = len(s_df) * 2
                attempt = 0

                while allocated < quota and attempt < max_attempts:
                    d = domains[d_idx % len(domains)]
                    pool = domain_pools[d]

                    for idx, row in pool.iterrows():
                        cid = row["effective_cluster"]
                        if cid not in seen_clusters:
                            seen_clusters.add(cid)
                            sampled_rows.append({
                                "pilot_id": f"PILOT_{pilot_counter:03d}",
                                "example_id": row["example_id"],
                                "text_normalized": row["text_normalized"],
                                "domain": row["domain"],
                                "source_label": row["source_label"],
                                "weak_cfpb_label": row["intent_label"],
                                "split": row["split"],
                                "group_id": row["group_id"],
                                "cluster_id": cid,
                            })
                            pilot_counter += 1
                            allocated += 1
                            domain_pools[d] = pool.drop(idx)
                            break
                    d_idx += 1
                    attempt += 1

                if allocated < quota:
                    raise ValueError(
                        f"Unable to fulfill quota for class '{cls_name}' split '{split_name}': allocated {allocated}/{quota}"
                    )

        return sampled_rows

    def generate_blinded_annotation_sheets(
        self,
        sampled_rows: List[Dict[str, Any]],
        output_dir: str = "data/annotation",
    ) -> Tuple[str, str, str]:
        """Generates separate blinded annotation sheets for two human raters and an adjudication template.
        
        Strictly strips all CFPB metadata (weak_cfpb_label, source_label, domain, split) to guarantee
        that human raters evaluate narratives completely blind to administrative picklists.
        """
        os.makedirs(output_dir, exist_ok=True)
        r1_path = os.path.join(output_dir, "rater_1_blinded_sheet.csv")
        r2_path = os.path.join(output_dir, "rater_2_blinded_sheet.csv")
        adj_tmpl_path = os.path.join(output_dir, "adjudication_template.csv")

        # Blinded columns: ONLY text and identification, blank annotation fields
        blinded_fieldnames = [
            "pilot_id",
            "example_id",
            "text_normalized",
            "annotator_label",
            "confidence_1_to_5",
            "secondary_labels",
            "multi_issue_flag",
            "ambiguity_flag",
            "rationale",
        ]

        for path in [r1_path, r2_path]:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                writer = csv.DictWriter(f, fieldnames=blinded_fieldnames)
                writer.writeheader()
                for r in sampled_rows:
                    writer.writerow({
                        "pilot_id": r["pilot_id"],
                        "example_id": r["example_id"],
                        "text_normalized": r["text_normalized"],
                        "annotator_label": "",
                        "confidence_1_to_5": "",
                        "secondary_labels": "",
                        "multi_issue_flag": "",
                        "ambiguity_flag": "",
                        "rationale": "",
                    })

        # Adjudication template - complete narrative preserved without truncation
        adj_fieldnames = [
            "pilot_id",
            "example_id",
            "text_normalized",
            "rater_1_label",
            "rater_2_label",
            "raw_agreement",
            "adjudicated_label",
            "adjudication_status",
            "secondary_labels",
            "multi_issue_flag",
            "ambiguity_flag",
            "adjudication_notes",
        ]
        with open(adj_tmpl_path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=adj_fieldnames)
            writer.writeheader()
            for r in sampled_rows:
                writer.writerow({
                    "pilot_id": r["pilot_id"],
                    "example_id": r["example_id"],
                    "text_normalized": r["text_normalized"],
                    "rater_1_label": "",
                    "rater_2_label": "",
                    "raw_agreement": "",
                    "adjudicated_label": "",
                    "adjudication_status": "",
                    "secondary_labels": "",
                    "multi_issue_flag": "",
                    "ambiguity_flag": "",
                    "adjudication_notes": "",
                })

        return r1_path, r2_path, adj_tmpl_path

    def audit_annotation_provenance(self, file_path: str) -> Dict[str, Any]:
        """Audits the provenance and integrity of an adjudication / simulation file.
        
        Fails closed: requires an explicit recognized provenance tag across every row,
        rejecting missing, unrecognized, mixed, or inconsistent provenance values.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        if not reader:
            raise ValueError(f"File is empty: {file_path}")

        valid_provenances = {PROVENANCE_SYNTHETIC, PROVENANCE_HUMAN}

        row_provenances = set()
        for idx, row in enumerate(reader, start=1):
            if "provenance" not in row:
                raise ValueError(f"Missing required 'provenance' column in file: {file_path}")
            prov = row["provenance"].strip()
            if not prov:
                raise ValueError(f"Row {idx} has missing or empty 'provenance' value in {file_path}")
            if prov not in valid_provenances:
                raise ValueError(
                    f"Row {idx} has unrecognized provenance '{prov}' in {file_path}. Allowed: {sorted(valid_provenances)}"
                )
            row_provenances.add(prov)

        if len(row_provenances) > 1:
            raise ValueError(f"Mixed/inconsistent provenance detected in {file_path}: {sorted(row_provenances)}")

        unique_provenance = row_provenances.pop()
        first_row = reader[0]
        has_ann1 = bool(first_row.get("annotator_1_label") or first_row.get("rater_1_label"))
        has_ann2 = bool(first_row.get("annotator_2_label") or first_row.get("rater_2_label"))
        has_adj = bool(first_row.get("adjudicated_label"))

        return {
            "file_path": file_path,
            "row_count": len(reader),
            "provenance": unique_provenance,
            "is_synthetic": unique_provenance == PROVENANCE_SYNTHETIC,
            "is_human": unique_provenance == PROVENANCE_HUMAN,
            "has_raters": has_ann1 and has_ann2 and has_adj,
        }

    def compute_agreement_from_raters(
        self,
        rater1: List[str],
        rater2: List[str],
        gold: Optional[List[str]] = None,
        weak: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Computes inter-rater agreement and weak-to-gold divergence strictly from independent rater inputs."""
        n = len(rater1)
        if n == 0 or len(rater2) != n:
            raise ValueError("Rater lists must be non-empty and of equal length")

        po, kappa = compute_cohens_kappa(rater1, rater2, self.class_names)
        res = {
            "total_instances": n,
            "raw_inter_annotator_agreement": round(po, 4),
            "raw_inter_annotator_agree_count": sum(1 for a, b in zip(rater1, rater2) if a == b),
            "cohens_kappa_inter_annotator": round(kappa, 4),
        }

        if gold and weak and len(gold) == n and len(weak) == n:
            po_wg, kappa_wg = compute_cohens_kappa(weak, gold, self.class_names)
            res.update({
                "raw_weak_vs_gold_agreement": round(po_wg, 4),
                "weak_vs_gold_agree_count": sum(1 for w, g in zip(weak, gold) if w == g),
                "cohens_kappa_weak_vs_gold": round(kappa_wg, 4),
                "divergence_count": sum(1 for w, g in zip(weak, gold) if w != g),
                "divergence_rate": round(sum(1 for w, g in zip(weak, gold) if w != g) / n, 4),
                "per_class_weak_metrics": compute_per_class_metrics(gold, weak, self.class_names),
            })

        return res
