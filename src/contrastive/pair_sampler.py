"""Deterministic weakly supervised contrastive pair generation.

Pairs are generated from the training split only. CFPB intent labels are weak
administrative labels, not semantic ground truth; outputs preserve that caveat.
"""
from __future__ import annotations

import argparse
import hashlib
import random
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_TRAIN = {"example_id", "text", "label", "group_id", "domain"}
REQUIRED_CLUSTER = {"example_id", "cluster_id"}
REQUIRED_SPLIT = {"example_id", "split"}


def _stable_rng(seed: int, anchor_id: str, mode: str) -> random.Random:
    token = f"{seed}|{anchor_id}|{mode}".encode("utf-8")
    derived = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
    return random.Random(derived)


def _choose(rng: random.Random, values: list[str]) -> str:
    return values[rng.randrange(len(values))]


def generate_pairs(
    train: pd.DataFrame,
    clusters: pd.DataFrame,
    split_manifest: pd.DataFrame,
    *,
    seed: int = 20261117,
    positive_mode: str = "same-domain",
    max_pairs_per_anchor: int = 1,
) -> tuple[pd.DataFrame, dict]:
    """Create anchor/positive/negative triplets with strict train-only checks.

    positive_mode:
      - same-domain: same weak label and same product domain
      - cross-domain: same weak label and different product domain
      - mixed: alternate the two strategies by anchor's stable order
    """
    if positive_mode not in {"same-domain", "cross-domain", "mixed"}:
        raise ValueError("positive_mode must be same-domain, cross-domain, or mixed")
    if max_pairs_per_anchor < 1:
        raise ValueError("max_pairs_per_anchor must be >= 1")

    missing = REQUIRED_TRAIN - set(train.columns)
    if missing:
        raise ValueError(f"Training CSV missing columns: {sorted(missing)}")
    if REQUIRED_CLUSTER - set(clusters.columns):
        raise ValueError(f"Cluster manifest missing columns: {sorted(REQUIRED_CLUSTER - set(clusters.columns))}")
    if REQUIRED_SPLIT - set(split_manifest.columns):
        raise ValueError(f"Split manifest missing columns: {sorted(REQUIRED_SPLIT - set(split_manifest.columns))}")

    train = train.copy()
    clusters = clusters.copy()
    split_manifest = split_manifest.copy()
    for frame, name in ((train, "train"), (clusters, "cluster"), (split_manifest, "split")):
        frame["example_id"] = frame["example_id"].astype(str)
        if frame["example_id"].duplicated().any():
            raise ValueError(f"{name} manifest contains duplicate example_id values")

    if train[list(REQUIRED_TRAIN)].isna().any().any():
        raise ValueError("Training rows contain null required fields")
    if train["text"].astype(str).str.strip().eq("").any():
        raise ValueError("Training rows contain empty text")
    if train["group_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Training rows contain empty group_id")
    if train["domain"].astype(str).str.strip().eq("").any():
        raise ValueError("Training rows contain empty domain")

    split_train = set(split_manifest.loc[split_manifest["split"].eq("train"), "example_id"])
    split_non_train = set(split_manifest.loc[~split_manifest["split"].eq("train"), "example_id"])
    train_ids = set(train["example_id"])
    if train_ids != split_train:
        raise ValueError(
            f"Training CSV does not exactly match train split manifest "
            f"(missing={len(split_train - train_ids)}, extra={len(train_ids - split_train)})"
        )
    if train_ids & split_non_train:
        raise ValueError("Train IDs overlap non-training split IDs")

    cluster_ids = set(clusters["example_id"])
    all_manifest_ids = set(split_manifest["example_id"])
    if not train_ids.issubset(cluster_ids) or not cluster_ids.issubset(all_manifest_ids):
        raise ValueError(
            f"Cluster manifest must cover every train ID and contain no unknown IDs "
            f"(missing_train={len(train_ids - cluster_ids)}, unknown={len(cluster_ids - all_manifest_ids)})"
        )
    if clusters["cluster_id"].isna().any() or clusters["cluster_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Cluster manifest contains empty cluster_id values")

    train["example_id"] = train["example_id"].astype(str)
    clusters["example_id"] = clusters["example_id"].astype(str)
    clusters["cluster_id"] = clusters["cluster_id"].astype(str)
    clusters = clusters.loc[clusters["example_id"].isin(train_ids)].copy()
    train = train.merge(clusters[["example_id", "cluster_id"]], on="example_id", how="left", validate="one_to_one")
    if train["cluster_id"].isna().any():
        raise ValueError("Incomplete duplicate-cluster mapping")

    # A pair must not share either its duplicate cluster or source group.
    records = train.to_dict("records")
    by_label_domain: dict[tuple[str, str], list[dict]] = {}
    by_label: dict[str, list[dict]] = {}
    by_domain: dict[str, list[dict]] = {}
    for row in records:
        by_label_domain.setdefault((str(row["label"]), str(row["domain"])), []).append(row)
        by_label.setdefault(str(row["label"]), []).append(row)
        by_domain.setdefault(str(row["domain"]), []).append(row)

    def pick_valid(rng: random.Random, candidates: list[dict], anchor: dict, *, positive: bool) -> dict | None:
        if not candidates:
            return None
        anchor_id = str(anchor["example_id"])
        anchor_cluster = str(anchor["cluster_id"])
        anchor_group = str(anchor["group_id"])
        anchor_label = str(anchor["label"])
        for _ in range(min(80, max(1, len(candidates)))):
            candidate = candidates[rng.randrange(len(candidates))]
            if str(candidate["example_id"]) == anchor_id:
                continue
            if str(candidate["cluster_id"]) == anchor_cluster or str(candidate["group_id"]) == anchor_group:
                continue
            if positive and str(candidate["label"]) != anchor_label:
                continue
            if not positive and str(candidate["label"]) == anchor_label:
                continue
            return candidate
        # Deterministic fallback handles small/duplicate-heavy candidate pools.
        valid = [
            candidate for candidate in candidates
            if str(candidate["example_id"]) != anchor_id
            and str(candidate["cluster_id"]) != anchor_cluster
            and str(candidate["group_id"]) != anchor_group
            and ((str(candidate["label"]) == anchor_label) if positive else (str(candidate["label"]) != anchor_label))
        ]
        return valid[rng.randrange(len(valid))] if valid else None

    rows: list[dict] = []
    skipped_no_positive = 0
    skipped_no_negative = 0
    anchors_with_pairs = 0

    # Stable ordering makes mixed-mode assignment reproducible.
    records = sorted(records, key=lambda r: str(r["example_id"]))
    for anchor_index, anchor in enumerate(records):
        anchor_id = str(anchor["example_id"])
        mode = positive_mode
        if mode == "mixed":
            mode = "same-domain" if anchor_index % 2 == 0 else "cross-domain"

        same_label = by_label[str(anchor["label"])]
        if mode == "same-domain":
            positive_pool = by_label_domain.get((str(anchor["label"]), str(anchor["domain"])), [])
        else:
            positive_pool = [
                r for r in same_label if str(r["domain"]) != str(anchor["domain"])
            ]

        rng = _stable_rng(seed, anchor_id, mode)
        positive = pick_valid(rng, positive_pool, anchor, positive=True)
        if positive is None:
            skipped_no_positive += 1
            continue

        # Prefer same-domain negatives; fall back to the full train pool only
        # when the domain has no valid alternative weak label.
        negative = pick_valid(rng, by_domain.get(str(anchor["domain"]), []), anchor, positive=False)
        if negative is None:
            negative = pick_valid(rng, records, anchor, positive=False)
        if negative is None:
            skipped_no_negative += 1
            continue

        pair_count = max_pairs_per_anchor
        for pair_no in range(pair_count):
            if pair_no:
                positive = pick_valid(rng, positive_pool, anchor, positive=True) or positive
                negative = pick_valid(rng, by_domain.get(str(anchor["domain"]), []), anchor, positive=False)
                if negative is None:
                    negative = pick_valid(rng, records, anchor, positive=False) or negative
            rows.append({
                "pair_id": hashlib.sha256(
                    f"{seed}|{anchor_id}|{positive['example_id']}|{negative['example_id']}|{mode}|{pair_no}".encode()
                ).hexdigest()[:20],
                "anchor_id": anchor_id,
                "positive_id": str(positive["example_id"]),
                "negative_id": str(negative["example_id"]),
                "weak_label": str(anchor["label"]),
                "positive_label": str(positive["label"]),
                "negative_label": str(negative["label"]),
                "anchor_domain": str(anchor["domain"]),
                "positive_domain": str(positive["domain"]),
                "negative_domain": str(negative["domain"]),
                "positive_mode": mode,
                "supervision": "weak_label",
                "seed": seed,
            })
        anchors_with_pairs += 1

    result = pd.DataFrame(rows, columns=[
        "pair_id", "anchor_id", "positive_id", "negative_id", "weak_label",
        "positive_label", "negative_label", "anchor_domain", "positive_domain", "negative_domain", "positive_mode",
        "supervision", "seed",
    ])
    stats = {
        "train_rows": len(train),
        "anchors_with_pairs": anchors_with_pairs,
        "pairs": len(result),
        "skipped_no_positive": skipped_no_positive,
        "skipped_no_negative": skipped_no_negative,
        "positive_mode": positive_mode,
        "seed": seed,
        "weak_label_warning": (
            "CFPB-derived labels are weak administrative supervision, not semantic gold labels. "
            "Pairs require human relevance evaluation before semantic retrieval claims."
        ),
    }
    return result, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--clusters-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--stats-json", required=True)
    parser.add_argument("--positive-mode", choices=["same-domain", "cross-domain", "mixed"], default="same-domain")
    parser.add_argument("--seed", type=int, default=20261117)
    parser.add_argument("--max-pairs-per-anchor", type=int, default=1)
    args = parser.parse_args()

    pairs, stats = generate_pairs(
        pd.read_csv(args.train_csv, keep_default_na=False),
        pd.read_csv(args.clusters_csv, keep_default_na=False),
        pd.read_csv(args.split_manifest, keep_default_na=False),
        seed=args.seed,
        positive_mode=args.positive_mode,
        max_pairs_per_anchor=args.max_pairs_per_anchor,
    )
    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(output, index=False)
    stats_path = Path(args.stats_json)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
