"""Core module for Phase 5: Duplicate, Overlap, and Contamination Audit.

Provides comprehensive, auditable duplicate detection, empirical near-duplicate clustering via
MinHash LSH with verified candidate Jaccard similarity, cluster diameter/chain-merging risk quantification,
weak administrative label conflict analysis, symmetric cross-dataset contamination verification,
and cross-partition zero-leakage verification.

Mathematical Guarantees:
- Exact hashing: 64-character SHA-256 for deterministic collision identification.
- Symmetric normalization: Unicode NFC canonical normalization, lowercasing, and whitespace collapsing.
- MinHash LSH: 64 affine hash permutations with Mersenne prime P = 2^31 - 1 = 2,147,483,647.
  16 bands of 4 rows each evaluate Jaccard similarity at threshold s ~= (1/b)^(1/r) ~= (1/16)^(1/4) ~= 0.5.
- Verified Candidate Clustering: LSH candidate pairs undergo explicit Jaccard similarity evaluation;
  false-positive collisions (s < 0.50) are rejected before union-find merging.
- Cycle-free Disjoint Set Union (Union-Find) with path compression for cluster grouping.
- Partition exclusivity: Strict zero-leakage verification across train, validation, and test splits:
  Train_groups ∩ Val_groups = ∅, Train_groups ∩ Test_groups = ∅, Val_groups ∩ Test_groups = ∅.
"""

import collections
import csv
import hashlib
import json
import os
import random
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import numpy as np
except ImportError:
    np = None


def normalize_for_comparison(text: str) -> str:
    """Symmetric Unicode NFC normalization, lowercasing, and whitespace collapsing."""
    text = unicodedata.normalize("NFC", text or "")
    return " ".join(text.lower().split())


def compute_sha256(text: str) -> str:
    """Computes a deterministic 64-character SHA-256 hex digest of the UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_word_shingles(text: str, k: int = 5) -> Set[str]:
    """Generates k-word shingles from lowercased text with whitespace collapsing."""
    words = text.lower().split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Computes exact Jaccard similarity between two sets of shingles: |A ∩ B| / |A ∪ B|."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


class UnionFind:
    """Disjoint Set Union (Union-Find) with path compression. Strictly cycle-free."""

    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        # Path compression
        curr = item
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, x: str, y: str) -> bool:
        """Merges components containing x and y. Returns True if a new union occurred."""
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
        return True


class MinHasher:
    """Vectorized, overflow-safe MinHash implementation for near-duplicate candidate detection.

    Uses Mersenne prime P = 2^31 - 1 = 2,147,483,647.
    Products a * h + b < P^2 < 2^62, safely fitting within uint64 without overflow.
    """

    Mersenne_P = (1 << 31) - 1  # 2147483647

    def __init__(self, n_perm: int = 64, bands: int = 16, seed: int = 13):
        assert n_perm % bands == 0, f"n_perm ({n_perm}) must be divisible by bands ({bands})"
        self.n_perm = n_perm
        self.bands = bands
        self.rows = n_perm // bands
        self.seed = seed

        rng = random.Random(seed)
        self.a = [rng.randrange(1, self.Mersenne_P) for _ in range(n_perm)]
        self.b = [rng.randrange(0, self.Mersenne_P) for _ in range(n_perm)]

        if np is not None:
            self.a_np = np.array(self.a, dtype=np.uint64)
            self.b_np = np.array(self.b, dtype=np.uint64)
            self.p_np = np.uint64(self.Mersenne_P)

    def _hash_shingle(self, s: str) -> int:
        return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=4).digest(), "big") % self.Mersenne_P

    def signature(self, shingles: Set[str]) -> Optional[List[int]]:
        if not shingles:
            return None
        h_vals = [self._hash_shingle(s) for s in shingles]
        if np is not None:
            h_arr = np.array(h_vals, dtype=np.uint64)
            m = (self.a_np[:, None] * h_arr[None, :] + self.b_np[:, None]) % self.p_np
            return m.min(axis=1).tolist()
        return [min((a * x + b) % self.Mersenne_P for x in h_vals) for a, b in zip(self.a, self.b)]

    def band_hashes(self, signature: List[int]) -> List[str]:
        return [
            hashlib.blake2b(
                (",".join(map(str, signature[b * self.rows : (b + 1) * self.rows]))).encode(),
                digest_size=8,
            ).hexdigest()
            for b in range(self.bands)
        ]


class DuplicateAuditor:
    """Performs rigorous empirical duplicate, overlap, cluster, and contamination audits."""

    def __init__(
        self,
        n_perm: int = 64,
        bands: int = 16,
        seed: int = 13,
        max_shingles: int = 400,
        jaccard_threshold: float = 0.50,
    ):
        self.n_perm = n_perm
        self.bands = bands
        self.seed = seed
        self.max_shingles = max_shingles
        self.jaccard_threshold = jaccard_threshold
        self.minhasher = MinHasher(n_perm=n_perm, bands=bands, seed=seed)

    def audit_records(
        self,
        records: List[Dict[str, Any]],
        auxiliary_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Runs the complete multi-pillar duplicate, cluster, conflict, and leakage audit.

        Parameters:
        - records: List of complaint dictionaries (expected keys: example_id, text_normalized,
          group_id, split, intent_label, source_label, domain).
        - auxiliary_records: Optional auxiliary benchmark queries (e.g. Banking77) to evaluate
          cross-dataset contamination.

        Returns:
        - Dictionary of audit results and summary statistics.
        """
        total_records = len(records)
        example_ids = set()
        duplicate_example_ids = 0

        source_ids = set()
        duplicate_source_ids = 0

        raw_hashes = set()
        norm_hashes = set()

        # Track hash frequencies and exact groups
        exact_map: Dict[str, str] = {}
        unique_shingles: Dict[str, Set[str]] = {}
        norm_hash_to_records = collections.defaultdict(list)

        for r in records:
            # Example ID uniqueness
            eid = r["example_id"]
            if eid in example_ids:
                duplicate_example_ids += 1
            example_ids.add(eid)

            # Explicit source_id tracking with missing-field policy
            if "source_id" in r and r["source_id"] is not None:
                sid = str(r["source_id"]).strip()
                if sid in source_ids:
                    duplicate_source_ids += 1
                source_ids.add(sid)

            # Raw text hash
            raw_txt = r.get("text_original", r.get("text_normalized", ""))
            raw_h = compute_sha256(raw_txt)
            raw_hashes.add(raw_h)

            # Symmetrically normalized text hash
            norm_txt = normalize_for_comparison(r["text_normalized"])
            norm_h = compute_sha256(norm_txt)
            norm_hashes.add(norm_h)
            norm_hash_to_records[norm_h].append(r)

            if norm_h not in exact_map:
                exact_map[norm_h] = f"grp_exact_{norm_h[:12]}"
                sh = compute_word_shingles(norm_txt, k=5)
                if len(sh) > self.max_shingles:
                    sh = set(sorted(sh)[: self.max_shingles])
                unique_shingles[norm_h] = sh

            r["text_hash"] = norm_h
            r["exact_group_id"] = exact_map[norm_h]

        # 1. Exact duplicates analysis
        exact_colliding_hashes = {h: recs for h, recs in norm_hash_to_records.items() if len(recs) > 1}
        exact_duplicate_instances = sum(len(recs) for recs in exact_colliding_hashes.values())
        exact_duplicate_hash_count = len(exact_colliding_hashes)

        # Check label consistency in exact duplicates
        exact_conflicts = 0
        exact_conflicted_details = []
        for h, recs in exact_colliding_hashes.items():
            labels = {r.get("intent_label") for r in recs}
            if len(labels) > 1:
                exact_conflicts += 1
                exact_conflicted_details.append({
                    "text_hash": h,
                    "count": len(recs),
                    "labels": list(labels),
                    "sample_text": recs[0]["text_normalized"][:150],
                })

        # 2. MinHash LSH indexing on unique texts
        lsh_buckets = collections.defaultdict(list)
        for h, sh in unique_shingles.items():
            sig = self.minhasher.signature(sh)
            if sig is not None:
                for b_idx, b_hash in enumerate(self.minhasher.band_hashes(sig)):
                    lsh_buckets[(b_idx, b_hash)].append(h)

        # Candidate pairs generation
        candidate_pairs = set()
        for members in lsh_buckets.values():
            if len(members) > 1:
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        h1 = min(members[i], members[j])
                        h2 = max(members[i], members[j])
                        candidate_pairs.add((h1, h2))

        # Union-Find initialized with exact groups
        uf = UnionFind()
        for h in sorted(unique_shingles.keys()):
            uf.find(exact_map[h])

        # Candidate Jaccard verification: reject false bridges (s < threshold)
        # Processed in strictly deterministic sorted order
        sorted_candidate_pairs = sorted(candidate_pairs)
        verified_candidate_pairs = 0
        rejected_candidate_pairs = 0
        for h1, h2 in sorted_candidate_pairs:
            sim = jaccard_similarity(unique_shingles[h1], unique_shingles[h2])
            if sim >= self.jaccard_threshold:
                verified_candidate_pairs += 1
                uf.union(exact_map[h1], exact_map[h2])
            else:
                rejected_candidate_pairs += 1

        # Derive canonical cluster ID from the lexicographically minimum text hash in each connected component
        component_hashes = collections.defaultdict(list)
        for h in unique_shingles.keys():
            root = uf.find(exact_map[h])
            component_hashes[root].append(h)

        canonical_cluster_ids = {}
        for root, hashes in component_hashes.items():
            min_h = min(hashes)
            canonical_cluster_ids[root] = f"grp_exact_{min_h[:12]}"

        # Assign final verified canonical cluster_id to each record
        for r in records:
            root = uf.find(r["exact_group_id"])
            r["cluster_id"] = canonical_cluster_ids[root]

        # Cluster analysis on verified clusters
        cluster_to_records = collections.defaultdict(list)
        for r in records:
            cid = r["cluster_id"]
            cluster_to_records[cid].append(r)

        total_groups = len(cluster_to_records)
        singleton_groups = sum(1 for recs in cluster_to_records.values() if len(recs) == 1)
        multi_item_groups = {cid: recs for cid, recs in cluster_to_records.items() if len(recs) > 1}
        multi_item_cluster_count = len(multi_item_groups)
        multi_item_instance_count = sum(len(recs) for recs in multi_item_groups.values())

        cluster_sizes = [len(recs) for recs in multi_item_groups.values()]
        max_cluster_size = max(cluster_sizes) if cluster_sizes else 0
        mean_cluster_size = float(np.mean(cluster_sizes)) if cluster_sizes and np else (sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0.0)
        median_cluster_size = float(np.median(cluster_sizes)) if cluster_sizes and np else 0.0
        p75_cluster_size = float(np.percentile(cluster_sizes, 75)) if cluster_sizes and np else 0.0
        p90_cluster_size = float(np.percentile(cluster_sizes, 90)) if cluster_sizes and np else 0.0

        # Label conflicts in multi-item clusters
        group_conflicts = 0
        group_conflict_details = []
        for cid, recs in multi_item_groups.items():
            labels = {r.get("intent_label") for r in recs}
            if len(labels) > 1:
                group_conflicts += 1
                group_conflict_details.append({
                    "cluster_id": cid,
                    "cluster_size": len(recs),
                    "unique_labels": len(labels),
                    "labels": list(labels),
                    "splits": list({r.get("split") for r in recs}),
                })

        # 3. Partition / Split Leakage Verification
        train_clusters = set()
        val_clusters = set()
        test_clusters = set()

        train_hashes = set()
        val_hashes = set()
        test_hashes = set()

        for r in records:
            cid = r["cluster_id"]
            h = r["text_hash"]
            sp = r.get("split")
            if sp == "train":
                train_clusters.add(cid)
                train_hashes.add(h)
            elif sp == "validation":
                val_clusters.add(cid)
                val_hashes.add(h)
            elif sp == "test":
                test_clusters.add(cid)
                test_hashes.add(h)

        train_val_group_leakage = len(train_clusters.intersection(val_clusters))
        train_test_group_leakage = len(train_clusters.intersection(test_clusters))
        val_test_group_leakage = len(val_clusters.intersection(test_clusters))

        train_val_hash_leakage = len(train_hashes.intersection(val_hashes))
        train_test_hash_leakage = len(train_hashes.intersection(test_hashes))
        val_test_hash_leakage = len(val_hashes.intersection(test_hashes))

        total_group_leakage = train_val_group_leakage + train_test_group_leakage + val_test_group_leakage
        total_hash_leakage = train_val_hash_leakage + train_test_hash_leakage + val_test_hash_leakage
        zero_leakage_verified = (total_group_leakage == 0) and (total_hash_leakage == 0)

        # 4. Cross-dataset contamination check (Banking77) with symmetric normalization & LSH near-duplicate verification
        banking77_exact_contamination = 0
        banking77_near_contamination = 0
        banking77_contaminated_samples = []

        if auxiliary_records:
            cfpb_norm_hash_set = set(unique_shingles.keys())
            # For each auxiliary query, symmetrically normalize
            for aux_r in auxiliary_records:
                aux_raw = aux_r.get("text", aux_r.get("text_normalized", ""))
                aux_norm = normalize_for_comparison(aux_raw)
                aux_h = compute_sha256(aux_norm)

                # Check exact collision
                if aux_h in cfpb_norm_hash_set:
                    banking77_exact_contamination += 1
                    banking77_contaminated_samples.append({
                        "type": "exact",
                        "aux_text": aux_norm,
                        "text_hash": aux_h,
                    })

                # Check near-duplicate collision via LSH candidate lookup
                aux_sh = compute_word_shingles(aux_norm, k=5)
                if len(aux_sh) > self.max_shingles:
                    aux_sh = set(sorted(aux_sh)[: self.max_shingles])
                aux_sig = self.minhasher.signature(aux_sh)
                if aux_sig is not None:
                    aux_cand_hashes = set()
                    for b_idx, b_hash in enumerate(self.minhasher.band_hashes(aux_sig)):
                        if (b_idx, b_hash) in lsh_buckets:
                            aux_cand_hashes.update(lsh_buckets[(b_idx, b_hash)])

                    for cand_h in aux_cand_hashes:
                        sim = jaccard_similarity(aux_sh, unique_shingles[cand_h])
                        if sim >= self.jaccard_threshold:
                            banking77_near_contamination += 1
                            banking77_contaminated_samples.append({
                                "type": "near_duplicate",
                                "similarity": sim,
                                "aux_text": aux_norm,
                                "cfpb_text_hash": cand_h,
                            })

        # 5. Build cluster catalog records for manifest
        cluster_catalog_rows = []
        for cid, recs in multi_item_groups.items():
            label_counts = collections.Counter(r.get("intent_label") for r in recs)
            dominant_label, dominant_cnt = label_counts.most_common(1)[0]
            dominant_pct = round(100.0 * dominant_cnt / len(recs), 2)
            has_conflict = len(label_counts) > 1
            is_exact = len({r["text_hash"] for r in recs}) == 1

            for r in recs:
                cluster_catalog_rows.append({
                    "cluster_id": cid,
                    "example_id": r["example_id"],
                    "text_hash": r["text_hash"],
                    "cluster_size": len(recs),
                    "intent_label": r.get("intent_label", ""),
                    "source_label": r.get("source_label", ""),
                    "domain": r.get("domain", ""),
                    "split": r.get("split", ""),
                    "is_exact_duplicate_group": is_exact,
                    "has_label_conflict": has_conflict,
                    "cluster_label_count": len(label_counts),
                    "dominant_label": dominant_label,
                    "dominant_label_pct": dominant_pct,
                })

        summary = {
            "total_records": total_records,
            "unique_example_ids": len(example_ids),
            "duplicate_example_ids": duplicate_example_ids,
            "unique_source_ids": len(source_ids) if source_ids else (len(example_ids) if not duplicate_source_ids else 0),
            "duplicate_source_ids": duplicate_source_ids,
            "unique_raw_hashes": len(raw_hashes),
            "unique_normalized_hashes": len(norm_hashes),
            "exact_duplicate_instances": exact_duplicate_instances,
            "exact_duplicate_hash_count": exact_duplicate_hash_count,
            "exact_clusters_with_label_conflict": exact_conflicts,
            "total_groups": total_groups,
            "singleton_groups": singleton_groups,
            "multi_item_clusters": multi_item_cluster_count,
            "multi_item_instances": multi_item_instance_count,
            "max_cluster_size": max_cluster_size,
            "mean_cluster_size": round(mean_cluster_size, 3),
            "median_cluster_size": round(median_cluster_size, 3),
            "p75_cluster_size": round(p75_cluster_size, 3),
            "p90_cluster_size": round(p90_cluster_size, 3),
            "group_clusters_with_label_conflict": group_conflicts,
            "train_val_group_leakage": train_val_group_leakage,
            "train_test_group_leakage": train_test_group_leakage,
            "val_test_group_leakage": val_test_group_leakage,
            "train_val_hash_leakage": train_val_hash_leakage,
            "train_test_hash_leakage": train_test_hash_leakage,
            "val_test_hash_leakage": val_test_hash_leakage,
            "zero_leakage_verified": zero_leakage_verified,
            "banking77_contamination_count": banking77_exact_contamination + banking77_near_contamination,
            "banking77_exact_contamination": banking77_exact_contamination,
            "banking77_near_contamination": banking77_near_contamination,
            "lsh_candidate_pairs_evaluated": len(candidate_pairs),
            "lsh_verified_pairs": verified_candidate_pairs,
            "lsh_rejected_false_bridges": rejected_candidate_pairs,
        }

        return {
            "summary": summary,
            "cluster_catalog": cluster_catalog_rows,
            "exact_conflicts": exact_conflicted_details,
            "group_conflicts": group_conflict_details,
            "banking77_contaminated_samples": banking77_contaminated_samples,
        }

    def compute_cluster_diameters(
        self,
        records: List[Dict[str, Any]],
        sample_clusters: int = 50,
        max_pairs_per_cluster: int = 200,
    ) -> Dict[str, Any]:
        """Calculates pairwise Jaccard similarity and diameter statistics for multi-item clusters.

        Quantifies chain-merging risk: if a cluster has high diameter (low minimum pairwise similarity),
        it indicates transitive chaining where disparate texts are chained together.
        Uses stable digest-derived PRNG seeding for cross-process determinism.
        """
        group_to_shingles = collections.defaultdict(list)
        for r in records:
            cid = r.get("cluster_id", r.get("group_id"))
            norm_t = normalize_for_comparison(r.get("text_normalized", ""))
            sh = compute_word_shingles(norm_t)
            if len(sh) > self.max_shingles:
                sh = set(sorted(sh)[: self.max_shingles])
            group_to_shingles[cid].append((r["example_id"], sh))

        multi_groups = [g for g, items in group_to_shingles.items() if len(items) > 1]
        
        # Sort deterministically by cluster size descending, then cluster_id
        multi_groups.sort(key=lambda g: (-len(group_to_shingles[g]), g))
        sampled_groups = multi_groups[:sample_clusters]

        cluster_stats = []
        all_min_similarities = []
        all_mean_similarities = []

        for grp in sampled_groups:
            # Sort items deterministically by example_id
            items = sorted(group_to_shingles[grp], key=lambda x: x[0])
            n_items = len(items)
            pair_similarities = []

            if n_items <= 20:
                for i in range(n_items):
                    for j in range(i + 1, n_items):
                        s = jaccard_similarity(items[i][1], items[j][1])
                        pair_similarities.append(s)
            else:
                # Stable digest-derived PRNG seeding for cross-process reproducibility
                grp_digest = hashlib.sha256(str(grp).encode("utf-8")).digest()
                grp_seed_int = int.from_bytes(grp_digest[:4], "big")
                rng = random.Random(self.seed + grp_seed_int)
                for _ in range(max_pairs_per_cluster):
                    i, j = rng.sample(range(n_items), 2)
                    s = jaccard_similarity(items[i][1], items[j][1])
                    pair_similarities.append(s)

            if pair_similarities:
                min_sim = float(np.min(pair_similarities)) if np else min(pair_similarities)
                mean_sim = float(np.mean(pair_similarities)) if np else sum(pair_similarities) / len(pair_similarities)
                max_sim = float(np.max(pair_similarities)) if np else max(pair_similarities)
                all_min_similarities.append(min_sim)
                all_mean_similarities.append(mean_sim)

                cluster_stats.append({
                    "cluster_id": grp,
                    "size": n_items,
                    "min_pairwise_jaccard": round(min_sim, 4),
                    "mean_pairwise_jaccard": round(mean_sim, 4),
                    "max_pairwise_jaccard": round(max_sim, 4),
                })

        overall_min = float(np.min(all_min_similarities)) if all_min_similarities and np else (min(all_min_similarities) if all_min_similarities else 0.0)
        overall_mean = float(np.mean(all_mean_similarities)) if all_mean_similarities and np else (sum(all_mean_similarities) / len(all_mean_similarities) if all_mean_similarities else 0.0)

        return {
            "evaluated_clusters": len(cluster_stats),
            "aggregate_min_jaccard": round(overall_min, 4),
            "aggregate_mean_jaccard": round(overall_mean, 4),
            "cluster_diameter_samples": cluster_stats[:10],
        }
