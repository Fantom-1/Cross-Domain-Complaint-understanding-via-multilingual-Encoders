"""Subword Tokenization Profiling for Cross-Domain Complaint Understanding.

Phase 4 of the Data Preparation Pipeline.
Focuses on empirical token-level characterization using the frozen multilingual
encoder tokenizer (`facebook/xlm-v-base` SentencePiece unigram model, vocab 901,629).

Adheres strictly to the architectural specifications and maintainer directives:
- Keeps tokenizer measurements strictly separate from lexical whitespace-word counts.
- Reports exact subword token-length distributions (p25, p50, p75, p90, p95, p99, min, max, mean, std).
- Evaluates context window truncation coverage at critical sequence length thresholds (128, 256, 384, 512).
- Profiles subword expansion ratios (tokens per whitespace word) across partitions and taxonomy classes.
- Profiles auxiliary benchmark (Banking77) to contrast short conversational queries against long narratives.
- Maintains lightweight offline/mock fallback capability for non-GPU / minimal CI test runners.
"""

import collections
import csv
import datetime
import hashlib
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from transformers import AutoTokenizer, PreTrainedTokenizerBase
except ImportError:
    AutoTokenizer = None
    PreTrainedTokenizerBase = None

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

DEFAULT_TOKENIZER_CHECKPOINT = "facebook/xlm-v-base"
DEFAULT_CUTOFFS = [128, 256, 384, 512]
DEFAULT_PERCENTILES = [25.0, 50.0, 75.0, 90.0, 95.0, 99.0]


def to_repo_relative(path: str) -> str:
    """Converts an absolute path to a repo-relative POSIX path."""
    try:
        rel = os.path.relpath(path, REPO_ROOT)
        return rel.replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_percentiles(values: Sequence[Union[int, float]], percentiles: Sequence[float] = DEFAULT_PERCENTILES) -> Dict[str, float]:
    """Computes exact percentiles from a sequence of numeric values using linear rank interpolation."""
    if not values:
        return {f"p{int(p) if p == int(p) else p}": 0.0 for p in percentiles}
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    res = {}
    for p in percentiles:
        key = f"p{int(p) if p == int(p) else p}"
        if n == 1:
            res[key] = float(sorted_vals[0])
            continue
        rank = (p / 100.0) * (n - 1)
        lower_idx = int(math.floor(rank))
        upper_idx = int(math.ceil(rank))
        weight = rank - lower_idx
        interpolated = sorted_vals[lower_idx] * (1.0 - weight) + sorted_vals[upper_idx] * weight
        res[key] = round(float(interpolated), 2)
    return res


def compute_token_statistics(
    token_lengths: Sequence[int],
    word_lengths: Optional[Sequence[int]] = None,
    cutoffs: Sequence[int] = DEFAULT_CUTOFFS,
) -> Dict[str, Any]:
    """Computes comprehensive token length summary statistics, percentiles, truncation coverage, and expansion ratio."""
    n = len(token_lengths)
    if n == 0:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "std": 0.0,
            "percentiles": {f"p{int(p) if p == int(p) else p}": 0.0 for p in DEFAULT_PERCENTILES},
            "truncation_coverage": {},
            "subword_expansion_ratio": None,
        }

    sorted_lengths = sorted(token_lengths)
    tot = sum(sorted_lengths)
    mean_val = tot / n
    var = sum((x - mean_val) ** 2 for x in sorted_lengths) / n
    std_val = math.sqrt(var)

    pcts = compute_percentiles(sorted_lengths, DEFAULT_PERCENTILES)

    trunc_cov = {}
    for cutoff in cutoffs:
        # Binary search or count exceeding cutoff
        truncated_count = sum(1 for x in sorted_lengths if x > cutoff)
        truncated_pct = round((truncated_count / n) * 100.0, 2)
        retained_cov_pct = round(100.0 - truncated_pct, 2)
        retained_tokens = sum(min(x, cutoff) for x in sorted_lengths)
        retained_token_pct = round((retained_tokens / tot) * 100.0, 2) if tot > 0 else 100.0
        trunc_cov[str(cutoff)] = {
            "cutoff": cutoff,
            "truncated_count": truncated_count,
            "truncated_percent": truncated_pct,
            "retained_coverage_percent": retained_cov_pct,
            "retained_token_percent": retained_token_pct,
        }

    expansion_ratio = None
    if word_lengths is not None and len(word_lengths) == n:
        ratios = [t / max(w, 1) for t, w in zip(token_lengths, word_lengths)]
        r_sorted = sorted(ratios)
        r_pcts = compute_percentiles(r_sorted, [50.0, 90.0])
        expansion_ratio = {
            "mean": round(sum(ratios) / n, 3),
            "median": round(r_pcts["p50"], 3),
            "p90": round(r_pcts["p90"], 3),
            "min": round(r_sorted[0], 3),
            "max": round(r_sorted[-1], 3),
        }

    return {
        "count": n,
        "min": int(sorted_lengths[0]),
        "max": int(sorted_lengths[-1]),
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        "percentiles": pcts,
        "truncation_coverage": trunc_cov,
        "subword_expansion_ratio": expansion_ratio,
    }


class MockSentencePieceTokenizer:
    """Deterministic mock tokenizer mimicking SentencePiece subword tokenization for CI and offline unit testing."""

    def __init__(self, vocab_size: int = 901629):
        self.vocab_size = vocab_size
        self.name_or_path = "mock/xlm-v-base-sentencepiece"

    def tokenize(self, text: str) -> List[str]:
        """Splits whitespace words and decomposes punctuation and special tokens deterministically."""
        if not text:
            return []
        tokens = []
        for word in text.split():
            # Mimic SentencePiece: add prefix marker and break into 1-3 subwords
            if word.startswith("<") and word.endswith(">"):
                # E.g. <REDACTED> -> 5 tokens
                inner = word[1:-1]
                tokens.extend(["<", inner[:3], inner[3:6], inner[6:], ">"])
            elif len(word) <= 4:
                tokens.append(f" {word}")
            elif len(word) <= 8:
                tokens.extend([f" {word[:4]}", word[4:]])
            else:
                tokens.extend([f" {word[:4]}", word[4:8], word[8:]])
        return [t for t in tokens if t]

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        tokens = self.tokenize(text)
        # 1: <s>, 2: </s>
        ids = [hash(t) % (self.vocab_size - 10) + 10 for t in tokens]
        if add_special_tokens:
            return [1] + ids + [2]
        return ids

    def batch_encode_plus(self, texts: Sequence[str], add_special_tokens: bool = True) -> Dict[str, List[List[int]]]:
        return {"input_ids": [self.encode(t, add_special_tokens=add_special_tokens) for t in texts]}

    def __call__(self, texts: Union[str, Sequence[str]], add_special_tokens: bool = True, truncation: bool = False) -> Dict[str, List[List[int]]]:
        if isinstance(texts, str):
            return {"input_ids": [self.encode(texts, add_special_tokens=add_special_tokens)]}
        return self.batch_encode_plus(texts, add_special_tokens=add_special_tokens)


class TokenizationProfiler:
    """Profiles token length distributions and context-window truncation behavior."""

    def __init__(
        self,
        tokenizer_name_or_path: str = DEFAULT_TOKENIZER_CHECKPOINT,
        tokenizer: Optional[Any] = None,
        mock: bool = False,
        cutoffs: Sequence[int] = DEFAULT_CUTOFFS,
    ):
        self.tokenizer_name_or_path = tokenizer_name_or_path
        self.cutoffs = list(cutoffs)
        self.mock_mode = mock

        if tokenizer is not None:
            self.tokenizer = tokenizer
            self.tokenizer_type = type(tokenizer).__name__
            self.vocab_size = getattr(tokenizer, "vocab_size", None) or len(getattr(tokenizer, "get_vocab", lambda: {})())
        elif mock or AutoTokenizer is None:
            self.tokenizer = MockSentencePieceTokenizer()
            self.tokenizer_type = "MockSentencePieceTokenizer"
            self.vocab_size = 901629
            self.mock_mode = True
        else:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name_or_path)
                self.tokenizer_type = type(self.tokenizer).__name__
                self.vocab_size = self.tokenizer.vocab_size
            except Exception as e:
                # Fallback to mock if offline / not cached and network disallowed
                self.tokenizer = MockSentencePieceTokenizer()
                self.tokenizer_type = "MockSentencePieceTokenizer (Fallback)"
                self.vocab_size = 901629
                self.mock_mode = True

    def tokenize_batch(self, texts: Sequence[str], batch_size: int = 1000) -> List[int]:
        """Encodes a sequence of texts in batches and returns exact sequence lengths (including special tokens)."""
        lengths: List[int] = []
        n = len(texts)
        for i in range(0, n, batch_size):
            chunk = texts[i : i + batch_size]
            if not chunk:
                continue
            enc = self.tokenizer(chunk, add_special_tokens=True, truncation=False)
            lengths.extend(len(ids) for ids in enc["input_ids"])
        return lengths

    def profile_texts(
        self,
        texts: Sequence[str],
        word_lengths: Optional[Sequence[int]] = None,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Profiles a list of raw text strings."""
        if word_lengths is None:
            word_lengths = [len(t.split()) for t in texts]
        token_lengths = self.tokenize_batch(texts, batch_size=batch_size)
        return compute_token_statistics(token_lengths, word_lengths, cutoffs=self.cutoffs)

    def profile_dataframe(
        self,
        df: Any,
        text_column: str = "text_normalized",
        group_col: Optional[str] = None,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Profiles a DataFrame's text column, optionally grouping by a column (e.g. split or intent)."""
        if pd is None or not isinstance(df, pd.DataFrame):
            raise TypeError("pandas DataFrame is required for profile_dataframe")

        texts = df[text_column].fillna("").astype(str).tolist()
        word_lens = [len(t.split()) for t in texts]
        token_lens = self.tokenize_batch(texts, batch_size=batch_size)

        overall_stats = compute_token_statistics(token_lens, word_lens, cutoffs=self.cutoffs)

        groups_stats = {}
        if group_col and group_col in df.columns:
            # Map indices to groups
            group_series = df[group_col].values
            group_indices: Dict[str, List[int]] = collections.defaultdict(list)
            for idx, g in enumerate(group_series):
                group_indices[str(g)].append(idx)

            for g_name, indices in sorted(group_indices.items()):
                sub_tokens = [token_lens[i] for i in indices]
                sub_words = [word_lens[i] for i in indices]
                groups_stats[g_name] = compute_token_statistics(sub_tokens, sub_words, cutoffs=self.cutoffs)

        return {
            "overall": overall_stats,
            "groups": groups_stats,
        }

    def profile_canonical_dataset(
        self,
        parquet_path: str,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Profiles the canonical dataset parquet file across splits, intents, and text variations."""
        if pd is None:
            raise ImportError("pandas is required to profile parquet dataset")

        df = pd.read_parquet(parquet_path)
        sha256 = compute_sha256(parquet_path)

        # Profile text_normalized overall and by split
        split_profile = self.profile_dataframe(df, text_column="text_normalized", group_col="split", batch_size=batch_size)
        
        # Profile text_normalized by intent
        intent_profile = self.profile_dataframe(df, text_column="text_normalized", group_col="intent_label", batch_size=batch_size)

        # Profile text_original for direct comparison with text_normalized
        orig_profile = self.profile_dataframe(df, text_column="text_original", batch_size=batch_size)

        return {
            "source_parquet_path": to_repo_relative(parquet_path),
            "source_sha256": sha256,
            "total_instances": len(df),
            "text_normalized_overall": split_profile["overall"],
            "text_original_overall": orig_profile["overall"],
            "by_split": split_profile["groups"],
            "by_intent": intent_profile["groups"],
        }

    def profile_banking77(
        self,
        train_csv_path: str,
        test_csv_path: str,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Profiles the Banking77 auxiliary dataset partitions."""
        if pd is None:
            raise ImportError("pandas is required to profile Banking77")

        df_train = pd.read_csv(train_csv_path)
        df_test = pd.read_csv(test_csv_path)

        train_sha256 = compute_sha256(train_csv_path)
        test_sha256 = compute_sha256(test_csv_path)

        train_stats = self.profile_dataframe(df_train, text_column="text", batch_size=batch_size)["overall"]
        test_stats = self.profile_dataframe(df_test, text_column="text", batch_size=batch_size)["overall"]

        return {
            "train": {
                "source_path": to_repo_relative(train_csv_path),
                "source_sha256": train_sha256,
                "total_instances": len(df_train),
                "stats": train_stats,
            },
            "test": {
                "source_path": to_repo_relative(test_csv_path),
                "source_sha256": test_sha256,
                "total_instances": len(df_test),
                "stats": test_stats,
            },
        }

    def run_full_profile(
        self,
        canonical_parquet_path: str,
        banking77_dir: str,
        output_json_path: Optional[str] = None,
        output_csv_path: Optional[str] = None,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Executes full Phase 4 tokenization profiling and emits JSON & CSV manifests."""
        b77_train_path = os.path.join(banking77_dir, "train.csv")
        b77_test_path = os.path.join(banking77_dir, "test.csv")

        canonical_results = self.profile_canonical_dataset(canonical_parquet_path, batch_size=batch_size)
        banking77_results = self.profile_banking77(b77_train_path, b77_test_path, batch_size=batch_size)

        profile_manifest = {
            "metadata": {
                "pipeline_phase": "Phase 4 - Subword Tokenization Profiling",
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "tokenizer_checkpoint": self.tokenizer_name_or_path,
                "tokenizer_type": self.tokenizer_type,
                "vocab_size": self.vocab_size,
                "mock_mode": self.mock_mode,
                "cutoffs": self.cutoffs,
                "percentiles": DEFAULT_PERCENTILES,
            },
            "governance_scope": {
                "supervision_status": "CFPB Issue/Sub-issue mappings are weak administrative supervision",
                "auxiliary_benchmark": "Banking77 is an auxiliary-only intent classification benchmark",
                "generalization_boundary": "No evidence of multilingual or held-out cross-domain generalization is claimed",
                "metric_isolation": "Subword token measurements are strictly distinguished from lexical whitespace word counts",
            },
            "canonical_cfpb": canonical_results,
            "auxiliary_banking77": banking77_results,
        }

        if output_json_path:
            export_profile_json(profile_manifest, output_json_path)

        if output_csv_path:
            export_profile_csv(profile_manifest, output_csv_path)

        return profile_manifest


def export_profile_json(profile_dict: Dict[str, Any], output_path: str) -> None:
    """Exports profile dictionary to a formatted JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile_dict, f, indent=2)


def export_profile_csv(profile_dict: Dict[str, Any], output_path: str) -> None:
    """Exports a flattened summary of tokenization statistics across partitions and classes to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fieldnames = [
        "dataset",
        "partition",
        "sample_size",
        "mean_tokens",
        "std_tokens",
        "min_tokens",
        "p25_tokens",
        "p50_tokens",
        "p75_tokens",
        "p90_tokens",
        "p95_tokens",
        "p99_tokens",
        "max_tokens",
        "subword_ratio_mean",
        "subword_ratio_p50",
        "subword_ratio_p90",
        "trunc_128_pct",
        "trunc_256_pct",
        "trunc_384_pct",
        "trunc_512_pct",
        "retained_cov_512_pct",
    ]

    def _extract_row(dataset_name: str, partition_name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        p = stats.get("percentiles", {})
        tc = stats.get("truncation_coverage", {})
        r = stats.get("subword_expansion_ratio") or {}
        return {
            "dataset": dataset_name,
            "partition": partition_name,
            "sample_size": stats.get("count", 0),
            "mean_tokens": stats.get("mean", 0.0),
            "std_tokens": stats.get("std", 0.0),
            "min_tokens": stats.get("min", 0),
            "p25_tokens": p.get("p25", 0.0),
            "p50_tokens": p.get("p50", 0.0),
            "p75_tokens": p.get("p75", 0.0),
            "p90_tokens": p.get("p90", 0.0),
            "p95_tokens": p.get("p95", 0.0),
            "p99_tokens": p.get("p99", 0.0),
            "max_tokens": stats.get("max", 0),
            "subword_ratio_mean": r.get("mean", ""),
            "subword_ratio_p50": r.get("median", ""),
            "subword_ratio_p90": r.get("p90", ""),
            "trunc_128_pct": tc.get("128", {}).get("truncated_percent", 0.0),
            "trunc_256_pct": tc.get("256", {}).get("truncated_percent", 0.0),
            "trunc_384_pct": tc.get("384", {}).get("truncated_percent", 0.0),
            "trunc_512_pct": tc.get("512", {}).get("truncated_percent", 0.0),
            "retained_cov_512_pct": tc.get("512", {}).get("retained_coverage_percent", 100.0),
        }

    rows = []
    canonical = profile_dict.get("canonical_cfpb", {})

    # Overall normalized
    if "text_normalized_overall" in canonical:
        rows.append(_extract_row("CFPB Canonical", "normalized_overall", canonical["text_normalized_overall"]))
    if "text_original_overall" in canonical:
        rows.append(_extract_row("CFPB Canonical", "original_overall", canonical["text_original_overall"]))

    # Splits
    for split_name, s_stats in canonical.get("by_split", {}).items():
        rows.append(_extract_row("CFPB Canonical", f"split_{split_name}", s_stats))

    # Intents
    for intent_name, i_stats in canonical.get("by_intent", {}).items():
        rows.append(_extract_row("CFPB Canonical", f"intent_{intent_name}", i_stats))

    # Banking77
    b77 = profile_dict.get("auxiliary_banking77", {})
    if "train" in b77:
        rows.append(_extract_row("Banking77 (Auxiliary)", "train", b77["train"].get("stats", {})))
    if "test" in b77:
        rows.append(_extract_row("Banking77 (Auxiliary)", "test", b77["test"].get("stats", {})))

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

