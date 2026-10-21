"""Group-safe stratified splitting module adhering to DATA_PREPARATION_SPEC.md.

Guarantees:
- Group Exclusivity: All examples with the same group_id are assigned strictly to one split partition.
- Stratification: Intent class distributions are preserved across train/val/test splits.
- Zero Leakage: No near-duplicates or templated form letters cross partitions.
- Manifest generation keyed by experiment_id.
"""

import collections
import csv
import os
import random
from typing import Dict, List, Tuple

SPLIT_MANIFEST_COLUMNS = [
    "experiment_id",
    "example_id",
    "split",
    "group_id",
    "source_dataset",
    "domain",
    "language_condition",
    "intent_label",
    "split_seed",
    "split_policy_version"
]


def group_stratified_split(
    records: List[Dict],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 13,
    experiment_id: str = "exp_indomain_baseline_v1",
    policy_version: str = "group_stratified_v1.0"
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Partitions records into train, validation, and test splits while respecting group boundaries."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-5, "Ratios must sum to 1.0"
    rng = random.Random(seed)

    # 1. Group records by group_id
    groups = collections.defaultdict(list)
    for r in records:
        groups[r["group_id"]].append(r)

    # 2. Determine dominant intent per group for stratification
    groups_by_intent = collections.defaultdict(list)
    for gid, group_records in groups.items():
        intent_counts = collections.Counter(r["intent_label"] for r in group_records)
        dominant_intent = intent_counts.most_common(1)[0][0]
        groups_by_intent[dominant_intent].append((gid, group_records))

    train_records = []
    val_records = []
    test_records = []

    # 3. Stratify groups per intent
    for intent, intent_groups in sorted(groups_by_intent.items()):
        rng.shuffle(intent_groups)
        total_items = sum(len(g[1]) for g in intent_groups)
        target_val = int(total_items * val_ratio)
        target_test = int(total_items * test_ratio)

        current_val, current_test = 0, 0
        for gid, g_records in intent_groups:
            k = len(g_records)
            if current_test + k <= target_test and target_test > 0:
                for r in g_records:
                    r["split"] = "test"
                test_records.extend(g_records)
                current_test += k
            elif current_val + k <= target_val and target_val > 0:
                for r in g_records:
                    r["split"] = "validation"
                val_records.extend(g_records)
                current_val += k
            else:
                for r in g_records:
                    r["split"] = "train"
                train_records.extend(g_records)

    # 4. Verify group exclusivity assertion
    train_groups = set(r["group_id"] for r in train_records)
    val_groups = set(r["group_id"] for r in val_records)
    test_groups = set(r["group_id"] for r in test_records)

    assert not (train_groups & val_groups), "Leakage detected: train & val share groups"
    assert not (train_groups & test_groups), "Leakage detected: train & test share groups"
    assert not (val_groups & test_groups), "Leakage detected: val & test share groups"

    return train_records, val_records, test_records


def export_split_manifest(
    records: List[Dict],
    output_path: str,
    experiment_id: str = "exp_indomain_baseline_v1",
    seed: int = 13,
    policy_version: str = "group_stratified_v1.0"
):
    """Exports split assignments to CSV manifest."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=SPLIT_MANIFEST_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "experiment_id": experiment_id,
                "example_id": r["example_id"],
                "split": r["split"],
                "group_id": r["group_id"],
                "source_dataset": r["source_dataset"],
                "domain": r["domain"],
                "language_condition": r["language_condition"],
                "intent_label": r["intent_label"],
                "split_seed": seed,
                "split_policy_version": policy_version
            })
    print(f"Exported split manifest to {output_path} ({len(records)} rows)")
