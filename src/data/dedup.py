"""Deduplication and near-duplicate grouping using exact hashing and MinHash LSH.

Requirements from DATA_PREPARATION_SPEC.md:
- Detect exact duplicates via text hash.
- Detect near-duplicate templated text (credit-repair form letters) via MinHash LSH.
- Assign stable group_id so all related examples stay within the same split partition.
- Uses Disjoint Set Union (Union-Find) with path compression to prevent cycles.
"""

import hashlib
import random
from typing import Dict, List, Set, Tuple


def compute_text_hash(text: str) -> str:
    """Computes a deterministic 64-character SHA-256 hash of the normalized text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_shingles(text: str, k: int = 5) -> Set[str]:
    """Generates k-word shingles from lowercased text."""
    words = text.lower().split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


class UnionFind:
    """Disjoint Set Union (Union-Find) with path compression. Strictly cycle-free."""

    def __init__(self):
        self.parent = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            return item
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        curr = item
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, x: str, y: str):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y


class MinHasher:
    """Vectorized, overflow-safe MinHash implementation.
    
    Uses Mersenne prime P = 2^31 - 1 = 2147483647.
    Products a * h + b < P^2 < 2^62, safely fitting within uint64 without overflow.
    """

    Mersenne_P = (1 << 31) - 1  # 2147483647

    def __init__(self, n_perm: int = 64, bands: int = 16, seed: int = 13):
        assert n_perm % bands == 0, "n_perm must be divisible by bands"
        self.n_perm = n_perm
        self.bands = bands
        self.rows = n_perm // bands
        
        rng = random.Random(seed)
        self.a = [rng.randrange(1, self.Mersenne_P) for _ in range(n_perm)]
        self.b = [rng.randrange(0, self.Mersenne_P) for _ in range(n_perm)]
        
        try:
            import numpy as np
            self.np = np
            self.a_np = np.array(self.a, dtype=np.uint64)
            self.b_np = np.array(self.b, dtype=np.uint64)
            self.p_np = np.uint64(self.Mersenne_P)
        except ImportError:
            self.np = None

    def _hash_val(self, s: str) -> int:
        return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=4).digest(), "big") % self.Mersenne_P

    def signature(self, shingles: Set[str]) -> List[int]:
        if not shingles:
            return None
        h_vals = [self._hash_val(s) for s in shingles]
        if self.np is not None:
            np = self.np
            h_arr = np.array(h_vals, dtype=np.uint64)
            m = (self.a_np[:, None] * h_arr[None, :] + self.b_np[:, None]) % self.p_np
            return m.min(axis=1).tolist()
        return [min((a * x + b) % self.Mersenne_P for x in h_vals) for a, b in zip(self.a, self.b)]

    def band_hashes(self, signature: List[int]) -> List[str]:
        return [
            hashlib.blake2b(
                (",".join(map(str, signature[b * self.rows : (b + 1) * self.rows]))).encode(),
                digest_size=8
            ).hexdigest()
            for b in range(self.bands)
        ]


def assign_duplicate_groups(
    records: List[Dict],
    n_perm: int = 64,
    bands: int = 16,
    max_shingles: int = 400
) -> Tuple[List[Dict], Dict]:
    """Identifies exact and near-duplicates and tags each record with group_id.
    
    Guarantees:
    - Stable, deterministic cluster group IDs.
    - O(N * alpha(N)) union-find without recursion or cycles.
    """
    exact_hash_to_group = {}
    exact_duplicates_count = 0
    near_duplicates_count = 0
    
    # 1. Exact duplicate identification
    for r in records:
        h = compute_text_hash(r["text_normalized"])
        r["text_hash"] = h
        if h not in exact_hash_to_group:
            exact_hash_to_group[h] = f"grp_exact_{h[:12]}"
        else:
            exact_duplicates_count += 1
        r["group_id"] = exact_hash_to_group[h]

    # 2. MinHash LSH near-duplicate clustering via Disjoint Set Union
    uf = UnionFind()
    minhasher = MinHasher(n_perm=n_perm, bands=bands)
    bucket_to_primary_group = {}
    
    for r in records:
        grp = r["group_id"]
        sh = compute_shingles(r["text_normalized"])
        if len(sh) > max_shingles:
            sh = set(sorted(sh)[:max_shingles])
        
        sig = minhasher.signature(sh)
        if sig is None:
            continue
        
        b_keys = minhasher.band_hashes(sig)
        for k in b_keys:
            if k in bucket_to_primary_group:
                other_grp = bucket_to_primary_group[k]
                if uf.find(grp) != uf.find(other_grp):
                    uf.union(grp, other_grp)
                    near_duplicates_count += 1
            else:
                bucket_to_primary_group[k] = grp

    # 3. Finalize canonical group_id via path-compressed find
    for r in records:
        r["group_id"] = uf.find(r["group_id"])

    stats = {
        "total_records": len(records),
        "unique_groups": len(set(r["group_id"] for r in records)),
        "exact_duplicates": exact_duplicates_count,
        "near_duplicate_links": near_duplicates_count
    }
    return records, stats
