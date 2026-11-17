"""Build complete corpus-wide cluster manifest covering both duplicate clusters and singletons.

Ensures every example_id in the canonical dataset has an unambiguous cluster_id,
satisfying fail-closed contrastive pair sampling requirements.
"""
from __future__ import annotations

import csv
from pathlib import Path
import pandas as pd


def build_full_cluster_manifest(
    split_manifest_path: str = "data/manifests/split_indomain.csv",
    duplicate_clusters_path: str = "data/manifests/duplicate_clusters.csv",
    output_path: str = "data/manifests/full_clusters.csv",
) -> pd.DataFrame:
    splits = pd.read_csv(split_manifest_path, keep_default_na=False)
    dup_clusters = pd.read_csv(duplicate_clusters_path, keep_default_na=False)

    dup_map = dict(zip(dup_clusters["example_id"].astype(str), dup_clusters["cluster_id"].astype(str)))

    rows = []
    for eid in splits["example_id"].astype(str):
        if eid in dup_map:
            cid = dup_map[eid]
        else:
            cid = f"singleton_{eid}"
        rows.append({"example_id": eid, "cluster_id": cid})

    df = pd.DataFrame(rows)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Generated full cluster manifest: {len(df)} records ({len(dup_map)} multi-item, {len(df)-len(dup_map)} singletons) -> {out}")
    return df


if __name__ == "__main__":
    build_full_cluster_manifest()

