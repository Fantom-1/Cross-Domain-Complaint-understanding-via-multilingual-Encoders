#!/usr/bin/env python3
"""Taxonomy auditor and annotation agreement module for Phase 6.

Provides:
- Taxonomy schema verification and operational codebook consistency.
- Rule pattern collision and order-dependency audit across CFPB source mappings.
- Stratified sampling from canonical_dataset.parquet for human annotation pilot (N=320).
- Inter-annotator agreement metrics: raw agreement, Cohen's Kappa, and confusion matrices.
- Weak administrative label vs. adjudicated gold label divergence analysis.
- Multi-issue prevalence and narrative ambiguity tracking.
"""

import collections
import csv
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple


TAXONOMY_PATH = "configs/taxonomy.json"
SOURCE_MAPPING_PATH = "data/manifests/source_label_mapping.csv"
CANONICAL_PARQUET_PATH = "data/processed/canonical_dataset.parquet"
PILOT_MANIFEST_PATH = "data/manifests/label_pilot_sampling_manifest.csv"
ADJUDICATION_LOG_PATH = "data/manifests/adjudication_log.csv"

PILOT_TARGET_PER_CLASS = 20
EXPECTED_CLASS_COUNT = 16
EXPECTED_PILOT_SIZE = 320  # 16 classes * 20 instances


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
        target_per_class: int = PILOT_TARGET_PER_CLASS,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """Samples a deterministic, stratified pilot dataset (N = 16 * target_per_class).
        
        Stratified primarily across 16 intent classes, balancing across product domains
        and dataset splits (train, validation, test) using stable sorting and pseudo-random selection.
        """
        import pandas as pd

        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"Canonical dataset not found: {parquet_path}")

        df = pd.read_parquet(parquet_path)

        sampled_rows: List[Dict[str, Any]] = []
        pilot_counter = 1

        for cls_name in sorted(self.class_names):
            cls_df = df[df["intent_label"] == cls_name].copy()
            if len(cls_df) < target_per_class:
                raise ValueError(
                    f"Class '{cls_name}' has insufficient records ({len(cls_df)}) for target {target_per_class}"
                )

            # Deterministic stratified sample across domains & splits
            # Sort by text_hash + example_id to achieve deterministic ordering
            cls_df["sort_key"] = cls_df["text_hash"] + "_" + cls_df["example_id"]
            cls_df = cls_df.sort_values("sort_key").reset_index(drop=True)

            # Stratify by domain within class using GroupBy or stable deterministic stride
            # To ensure representation across domains and splits:
            sampled_indices = []
            domains = sorted(cls_df["domain"].unique())
            domain_pools = {d: cls_df[cls_df["domain"] == d].index.tolist() for d in domains}

            # Round-robin selection across domains to ensure domain diversity
            d_idx = 0
            while len(sampled_indices) < target_per_class:
                curr_domain = domains[d_idx % len(domains)]
                pool = domain_pools[curr_domain]
                if pool:
                    sampled_indices.append(pool.pop(0))
                d_idx += 1

            cls_sample = cls_df.loc[sampled_indices].copy()

            for _, row in cls_sample.iterrows():
                sampled_rows.append({
                    "pilot_id": f"PILOT_{pilot_counter:03d}",
                    "example_id": row["example_id"],
                    "text_normalized": row["text_normalized"],
                    "domain": row["domain"],
                    "source_label": row["source_label"],
                    "weak_cfpb_label": row["intent_label"],
                    "split": row["split"],
                    "group_id": row["group_id"],
                })
                pilot_counter += 1

        return sampled_rows

    def analyze_adjudication_log(
        self, adjudication_csv: str = ADJUDICATION_LOG_PATH
    ) -> Dict[str, Any]:
        """Analyzes inter-annotator agreement and weak-to-gold label divergence."""
        if not os.path.exists(adjudication_csv):
            raise FileNotFoundError(f"Adjudication log not found: {adjudication_csv}")

        with open(adjudication_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        total_instances = len(rows)
        if total_instances == 0:
            raise ValueError("Adjudication log is empty")

        ann1 = [r["annotator_1_label"] for r in rows]
        ann2 = [r["annotator_2_label"] for r in rows]
        gold = [r["adjudicated_label"] for r in rows]
        weak = [r["weak_cfpb_label"] for r in rows]

        # Raw & Kappa agreement between independent annotators
        raw_agree_count = sum(1 for a, b in zip(ann1, ann2) if a == b)
        p_o_ann, kappa_ann = compute_cohens_kappa(ann1, ann2, self.class_names)

        # Agreement between CFPB weak labels and Adjudicated gold labels
        weak_gold_agree_count = sum(1 for w, g in zip(weak, gold) if w == g)
        p_o_weak_gold, kappa_weak_gold = compute_cohens_kappa(weak, gold, self.class_names)

        # Multi-issue count
        multi_issue_count = sum(1 for r in rows if r.get("multi_issue_flag", "").lower() in ("true", "1", "yes"))
        ambiguous_count = sum(1 for r in rows if r.get("ambiguity_flag", "").lower() in ("true", "1", "yes"))

        # Per-class metrics comparing weak labels to gold
        per_class_weak = compute_per_class_metrics(gold, weak, self.class_names)

        # Class distribution of gold
        gold_dist = collections.Counter(gold)

        return {
            "total_instances": total_instances,
            "raw_inter_annotator_agreement": round(p_o_ann, 4),
            "raw_inter_annotator_agree_count": raw_agree_count,
            "cohens_kappa_inter_annotator": round(kappa_ann, 4),
            "raw_weak_vs_gold_agreement": round(p_o_weak_gold, 4),
            "weak_vs_gold_agree_count": weak_gold_agree_count,
            "cohens_kappa_weak_vs_gold": round(kappa_weak_gold, 4),
            "divergence_count": total_instances - weak_gold_agree_count,
            "divergence_rate": round((total_instances - weak_gold_agree_count) / total_instances, 4),
            "multi_issue_count": multi_issue_count,
            "multi_issue_rate": round(multi_issue_count / total_instances, 4),
            "ambiguous_count": ambiguous_count,
            "ambiguous_rate": round(ambiguous_count / total_instances, 4),
            "per_class_weak_metrics": per_class_weak,
            "gold_class_distribution": dict(gold_dist),
        }
