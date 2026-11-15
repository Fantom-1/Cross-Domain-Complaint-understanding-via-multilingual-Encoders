"""Subword Tokenization Profiling for Cross-Domain Complaint Understanding.

Phase 4 of the Data Preparation Pipeline.
Focuses on empirical token-level characterization using the frozen multilingual
encoder tokenizer (`facebook/xlm-v-base` SentencePiece unigram model, vocab 901,629).

Adheres strictly to architectural specifications and maintainer review directives:
- Tokenizer checkpoint pinned to exact immutable commit revision `68c75dd7733d2640b3a98114e3e94196dc543fe1`.
- Records cryptographic digests of tokenizer assets (`sentencepiece.bpe.model`, `tokenizer.json`, `config.json`).
- Strict fail-closed error handling: mock fallback is an explicit opt-in for unit tests only.
- Strict segregation of content subword expansion ratios from special-token-inclusive sequence lengths.
- Evaluates context window truncation coverage at critical sequence length thresholds (128, 256, 384, 512).
- Profiles auxiliary benchmark (Banking77) to contrast short conversational queries against long narratives.
- Deterministic cross-process mock tokenizer mapping using digest-based hashing.
"""

import collections
import csv
import datetime
import hashlib
import json
import math
import os
import platform
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import transformers
    from transformers import AutoTokenizer, PreTrainedTokenizerBase
except ImportError:
    transformers = None
    AutoTokenizer = None
    PreTrainedTokenizerBase = None

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

DEFAULT_TOKENIZER_CHECKPOINT = "facebook/xlm-v-base"
DEFAULT_TOKENIZER_REVISION = "68c75dd7733d2640b3a98114e3e94196dc543fe1"
DEFAULT_CUTOFFS = [128, 256, 384, 512]
DEFAULT_PERCENTILES = [25.0, 50.0, 75.0, 90.0, 95.0, 99.0]

EXPECTED_TOKENIZER_ASSETS = {
    "config.json": "25ed3e0d067ca06706bb76a597856c9ac7ba67559d4b2cf0e3f3f5052efd47e2",
    "sentencepiece.bpe.model": "dbee9f6b1c2cba29b335e70d6088eea943c7d5ae55ac7dd17174760bf758e309",
    "tokenizer.json": "43f949ef0c0b1ac18c506551109383d4a8a2bd48956ced0cc95cfd9120d42dca",
}


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


def resolve_tokenizer_asset_path(
    repo_id: str = DEFAULT_TOKENIZER_CHECKPOINT,
    filename: str = "",
    revision: str = DEFAULT_TOKENIZER_REVISION,
    search_dirs: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Resolves local cached or stored file path for a tokenizer asset at a pinned revision.
    
    Resolution order:
    1. Direct filesystem check inside search_dirs if provided.
    2. Direct filesystem check if repo_id is a local directory or file path.
    3. Hugging Face hub cache via try_to_load_from_cache.
    4. Direct snapshot search in standard HF_HUB_CACHE snapshots.
    5. Fallback via hf_hub_download.
    """
    if not filename:
        return None

    if search_dirs:
        for sdir in search_dirs:
            if sdir and os.path.isdir(sdir):
                candidate = os.path.join(sdir, filename)
                if os.path.isfile(candidate):
                    return os.path.abspath(candidate)

    if os.path.exists(repo_id):
        if os.path.isdir(repo_id):
            candidate = os.path.join(repo_id, filename)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        elif os.path.isfile(repo_id) and os.path.basename(repo_id) == filename:
            return os.path.abspath(repo_id)

    # Try huggingface_hub try_to_load_from_cache
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(repo_id, filename, revision=revision)
        if cached and os.path.isfile(cached):
            return os.path.abspath(cached)
    except Exception:
        pass

    # Direct snapshot directory check in standard cache
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
        org_repo = repo_id.replace("/", "--")
        candidate = os.path.join(HF_HUB_CACHE, f"models--{org_repo}", "snapshots", revision, filename)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    except Exception:
        pass

    # Fallback to hf_hub_download
    try:
        from huggingface_hub import hf_hub_download
        downloaded = hf_hub_download(repo_id=repo_id, filename=filename, revision=revision)
        if downloaded and os.path.isfile(downloaded):
            return os.path.abspath(downloaded)
    except Exception:
        pass

    return None


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
    sequence_lengths: Sequence[int],
    content_lengths: Optional[Sequence[int]] = None,
    word_lengths: Optional[Sequence[int]] = None,
    cutoffs: Sequence[int] = DEFAULT_CUTOFFS,
) -> Dict[str, Any]:
    """Computes comprehensive token length summary statistics, percentiles, truncation coverage, and expansion ratios.

    Parameters:
        sequence_lengths: Full token sequence lengths including special tokens (<s> ... </s>) for context-window analysis.
        content_lengths: Token lengths strictly excluding special-token overhead for pure subword expansion ratio analysis.
        word_lengths: Lexical whitespace-split word counts.
        cutoffs: Context window thresholds to evaluate truncation against.
    """
    n = len(sequence_lengths)
    if n == 0:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "std": 0.0,
            "percentiles": {f"p{int(p) if p == int(p) else p}": 0.0 for p in DEFAULT_PERCENTILES},
            "truncation_coverage": {},
            "content_subword_ratio": None,
            "sequence_subword_ratio": None,
        }

    sorted_lengths = sorted(sequence_lengths)
    tot = sum(sorted_lengths)
    mean_val = tot / n
    var = sum((x - mean_val) ** 2 for x in sorted_lengths) / n
    std_val = math.sqrt(var)

    pcts = compute_percentiles(sorted_lengths, DEFAULT_PERCENTILES)

    trunc_cov = {}
    for cutoff in cutoffs:
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

    content_ratio = None
    seq_ratio = None
    if word_lengths is not None and len(word_lengths) == n:
        # 1. Content-token expansion ratio (strictly excludes special tokens)
        if content_lengths is None:
            # By default subtract 2 for <s> and </s> if not provided
            content_lens = [max(0, s - 2) for s in sequence_lengths]
        else:
            content_lens = list(content_lengths)

        c_ratios = [c / max(w, 1) for c, w in zip(content_lens, word_lengths)]
        c_sorted = sorted(c_ratios)
        c_pcts = compute_percentiles(c_sorted, [50.0, 90.0])
        content_ratio = {
            "mean": round(sum(c_ratios) / n, 3),
            "median": round(c_pcts["p50"], 3),
            "p90": round(c_pcts["p90"], 3),
            "min": round(c_sorted[0], 3),
            "max": round(c_sorted[-1], 3),
        }

        # 2. Sequence-level expansion ratio (inclusive of special tokens)
        s_ratios = [s / max(w, 1) for s, w in zip(sequence_lengths, word_lengths)]
        s_sorted = sorted(s_ratios)
        s_pcts = compute_percentiles(s_sorted, [50.0, 90.0])
        seq_ratio = {
            "mean": round(sum(s_ratios) / n, 3),
            "median": round(s_pcts["p50"], 3),
            "p90": round(s_pcts["p90"], 3),
            "min": round(s_sorted[0], 3),
            "max": round(s_sorted[-1], 3),
        }

    return {
        "count": n,
        "min": int(sorted_lengths[0]),
        "max": int(sorted_lengths[-1]),
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        "percentiles": pcts,
        "truncation_coverage": trunc_cov,
        "content_subword_ratio": content_ratio,
        "sequence_subword_ratio": seq_ratio,
    }


class MockSentencePieceTokenizer:
    """Deterministic mock tokenizer mimicking SentencePiece subword tokenization for CI and offline unit testing.

    Uses an MD5-digest mapping to generate strictly deterministic, process-independent token IDs.
    """

    def __init__(self, vocab_size: int = 901629):
        self.vocab_size = vocab_size
        self.name_or_path = "mock/xlm-v-base-sentencepiece"
        self.bos_token_id = 1
        self.eos_token_id = 2

    def _token_to_id(self, token: str) -> int:
        """Deterministic integer ID mapping using MD5 digest, immune to PYTHONHASHSEED randomization."""
        digest = hashlib.md5(token.encode("utf-8")).digest()
        val = int.from_bytes(digest[:4], "big")
        return (val % (self.vocab_size - 10)) + 10

    def tokenize(self, text: str) -> List[str]:
        """Splits whitespace words and decomposes punctuation and special tokens deterministically."""
        if not text:
            return []
        tokens = []
        for word in text.split():
            if word.startswith("<") and word.endswith(">"):
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
        ids = [self._token_to_id(t) for t in tokens]
        if add_special_tokens:
            return [self.bos_token_id] + ids + [self.eos_token_id]
        return ids

    def batch_encode_plus(self, texts: Sequence[str], add_special_tokens: bool = True) -> Dict[str, List[List[int]]]:
        return {"input_ids": [self.encode(t, add_special_tokens=add_special_tokens) for t in texts]}

    def __call__(self, texts: Union[str, Sequence[str]], add_special_tokens: bool = True, truncation: bool = False) -> Dict[str, List[List[int]]]:
        if isinstance(texts, str):
            return {"input_ids": [self.encode(texts, add_special_tokens=add_special_tokens)]}
        return self.batch_encode_plus(texts, add_special_tokens=add_special_tokens)


class TokenizationProfiler:
    """Profiles token length distributions, content subword expansion ratios, and context-window truncation."""

    def __init__(
        self,
        tokenizer_name_or_path: str = DEFAULT_TOKENIZER_CHECKPOINT,
        revision: str = DEFAULT_TOKENIZER_REVISION,
        tokenizer: Optional[Any] = None,
        mock: bool = False,
        cutoffs: Sequence[int] = DEFAULT_CUTOFFS,
        asset_search_dir: Optional[str] = None,
    ):
        self.tokenizer_name_or_path = tokenizer_name_or_path
        self.revision = revision
        self.cutoffs = list(cutoffs)
        self.mock_mode = mock
        self.tokenizer_asset_hashes: Dict[str, str] = {}

        if tokenizer is not None:
            self.tokenizer = tokenizer
            self.tokenizer_type = type(tokenizer).__name__
            self.vocab_size = getattr(tokenizer, "vocab_size", None) or len(getattr(tokenizer, "get_vocab", lambda: {})())
        elif mock:
            self.tokenizer = MockSentencePieceTokenizer()
            self.tokenizer_type = "MockSentencePieceTokenizer"
            self.vocab_size = 901629
            self.mock_mode = True
        else:
            # Production profiling mode: fail-closed if dependencies or checkpoint fail
            if AutoTokenizer is None:
                raise RuntimeError(
                    "Production tokenization profiling requires the 'transformers' library. "
                    "Pass mock=True explicitly if running in a minimal test environment."
                )

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    tokenizer_name_or_path,
                    revision=revision,
                )
                self.tokenizer_type = type(self.tokenizer).__name__
                self.vocab_size = self.tokenizer.vocab_size

                # Extract and record independently verified asset hashes from physical files on disk
                self._record_checkpoint_asset_hashes(search_dir=asset_search_dir)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load production tokenizer '{tokenizer_name_or_path}' at revision '{revision}': {e}. "
                    f"Production profiling fails closed to prevent silent mock generation. "
                    f"Pass mock=True explicitly only in unit tests."
                ) from e

    def _record_checkpoint_asset_hashes(self, search_dir: Optional[str] = None) -> None:
        """Resolves physical tokenizer assets on disk, computes their SHA-256 digests, and validates them."""
        self.tokenizer_asset_hashes.clear()
        search_dirs = []
        if search_dir:
            search_dirs.append(search_dir)
        if hasattr(self.tokenizer, "name_or_path") and os.path.isdir(str(self.tokenizer.name_or_path)):
            search_dirs.append(str(self.tokenizer.name_or_path))

        for filename, expected_hash in EXPECTED_TOKENIZER_ASSETS.items():
            actual_path = resolve_tokenizer_asset_path(
                repo_id=self.tokenizer_name_or_path,
                filename=filename,
                revision=self.revision,
                search_dirs=search_dirs,
            )
            if not actual_path or not os.path.isfile(actual_path):
                raise RuntimeError(
                    f"Required physical tokenizer asset '{filename}' could not be located on disk "
                    f"for checkpoint '{self.tokenizer_name_or_path}' at revision '{self.revision}'. "
                    f"Production profiling fails closed."
                )

            computed_h = compute_sha256(actual_path)
            if computed_h != expected_hash:
                raise RuntimeError(
                    f"Cryptographic hash mismatch for physical asset '{filename}' at '{actual_path}': "
                    f"computed {computed_h} != expected {expected_hash}"
                )

            self.tokenizer_asset_hashes[filename] = computed_h

    def tokenize_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 1000,
        add_special_tokens: bool = True,
    ) -> List[int]:
        """Encodes texts in batches and returns sequence lengths."""
        if batch_size <= 0:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size}")

        lengths: List[int] = []
        n = len(texts)
        for i in range(0, n, batch_size):
            chunk = texts[i : i + batch_size]
            if not chunk:
                continue
            enc = self.tokenizer(chunk, add_special_tokens=add_special_tokens, truncation=False)
            lengths.extend(len(ids) for ids in enc["input_ids"])
        return lengths

    def profile_texts(
        self,
        texts: Sequence[str],
        word_lengths: Optional[Sequence[int]] = None,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Profiles a list of raw text strings, computing both full sequence lengths and content token lengths."""
        if word_lengths is None:
            word_lengths = [len(t.split()) for t in texts]

        # 1. Full sequence lengths (with <s> ... </s>) for context window truncation
        seq_lengths = self.tokenize_batch(texts, batch_size=batch_size, add_special_tokens=True)

        # 2. Content lengths (without special tokens) for pure content subword expansion
        content_lengths = self.tokenize_batch(texts, batch_size=batch_size, add_special_tokens=False)

        return compute_token_statistics(
            sequence_lengths=seq_lengths,
            content_lengths=content_lengths,
            word_lengths=word_lengths,
            cutoffs=self.cutoffs,
        )

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

        if text_column not in df.columns:
            raise KeyError(f"text_column '{text_column}' not found in DataFrame columns: {list(df.columns)}")

        texts = df[text_column].fillna("").astype(str).tolist()
        word_lens = [len(t.split()) for t in texts]

        # Sequence lengths (special tokens included)
        seq_lens = self.tokenize_batch(texts, batch_size=batch_size, add_special_tokens=True)
        # Content lengths (special tokens excluded)
        content_lens = self.tokenize_batch(texts, batch_size=batch_size, add_special_tokens=False)

        overall_stats = compute_token_statistics(
            sequence_lengths=seq_lens,
            content_lengths=content_lens,
            word_lengths=word_lens,
            cutoffs=self.cutoffs,
        )

        groups_stats = {}
        if group_col and group_col in df.columns:
            group_series = df[group_col].values
            group_indices: Dict[str, List[int]] = collections.defaultdict(list)
            for idx, g in enumerate(group_series):
                group_indices[str(g)].append(idx)

            for g_name, indices in sorted(group_indices.items()):
                sub_seqs = [seq_lens[i] for i in indices]
                sub_contents = [content_lens[i] for i in indices]
                sub_words = [word_lens[i] for i in indices]
                groups_stats[g_name] = compute_token_statistics(
                    sequence_lengths=sub_seqs,
                    content_lengths=sub_contents,
                    word_lengths=sub_words,
                    cutoffs=self.cutoffs,
                )

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

        split_profile = self.profile_dataframe(df, text_column="text_normalized", group_col="split", batch_size=batch_size)
        intent_profile = self.profile_dataframe(df, text_column="text_normalized", group_col="intent_label", batch_size=batch_size)
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
                "tokenizer_revision": self.revision,
                "tokenizer_type": self.tokenizer_type,
                "vocab_size": self.vocab_size,
                "transformers_version": getattr(transformers, "__version__", "unknown") if transformers else "none",
                "tokenizer_asset_hashes": self.tokenizer_asset_hashes,
                "mock_mode": self.mock_mode,
                "environment": {
                    "platform": platform.platform(),
                    "python_version": sys.version.split()[0],
                },
                "cutoffs": self.cutoffs,
                "percentiles": DEFAULT_PERCENTILES,
            },
            "governance_scope": {
                "supervision_status": "CFPB Issue/Sub-issue mappings are weak administrative supervision",
                "auxiliary_benchmark": "Banking77 is an auxiliary-only intent classification benchmark",
                "generalization_boundary": "No evidence of multilingual or held-out cross-domain generalization is claimed",
                "metric_isolation": "Subword token measurements are strictly distinguished from lexical whitespace word counts",
                "ratio_definition": "content_subword_ratio strictly excludes special tokens (<s>, </s>); sequence_subword_ratio includes special tokens.",
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
    """Exports a flattened summary of tokenization statistics across partitions and classes to CSV.

    Emits both content-subword ratios (excluding special tokens) and sequence-subword ratios.
    """
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
        "content_ratio_mean",
        "content_ratio_p50",
        "content_ratio_p90",
        "content_ratio_min",
        "content_ratio_max",
        "seq_ratio_mean",
        "seq_ratio_p50",
        "seq_ratio_p90",
        "trunc_128_pct",
        "trunc_256_pct",
        "trunc_384_pct",
        "trunc_512_pct",
        "retained_cov_512_pct",
    ]

    def _extract_row(dataset_name: str, partition_name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        p = stats.get("percentiles", {})
        tc = stats.get("truncation_coverage", {})
        cr = stats.get("content_subword_ratio") or {}
        sr = stats.get("sequence_subword_ratio") or {}
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
            "content_ratio_mean": cr.get("mean", ""),
            "content_ratio_p50": cr.get("median", ""),
            "content_ratio_p90": cr.get("p90", ""),
            "content_ratio_min": cr.get("min", ""),
            "content_ratio_max": cr.get("max", ""),
            "seq_ratio_mean": sr.get("mean", ""),
            "seq_ratio_p50": sr.get("median", ""),
            "seq_ratio_p90": sr.get("p90", ""),
            "trunc_128_pct": tc.get("128", {}).get("truncated_percent", 0.0),
            "trunc_256_pct": tc.get("256", {}).get("truncated_percent", 0.0),
            "trunc_384_pct": tc.get("384", {}).get("truncated_percent", 0.0),
            "trunc_512_pct": tc.get("512", {}).get("truncated_percent", 0.0),
            "retained_cov_512_pct": tc.get("512", {}).get("retained_coverage_percent", 100.0),
        }

    rows = []
    canonical = profile_dict.get("canonical_cfpb", {})

    if "text_normalized_overall" in canonical:
        rows.append(_extract_row("CFPB Canonical", "normalized_overall", canonical["text_normalized_overall"]))
    if "text_original_overall" in canonical:
        rows.append(_extract_row("CFPB Canonical", "original_overall", canonical["text_original_overall"]))

    for split_name, s_stats in canonical.get("by_split", {}).items():
        rows.append(_extract_row("CFPB Canonical", f"split_{split_name}", s_stats))

    for intent_name, i_stats in canonical.get("by_intent", {}).items():
        rows.append(_extract_row("CFPB Canonical", f"intent_{intent_name}", i_stats))

    b77 = profile_dict.get("auxiliary_banking77", {})
    if "train" in b77:
        rows.append(_extract_row("Banking77 (Auxiliary)", "train", b77["train"].get("stats", {})))
    if "test" in b77:
        rows.append(_extract_row("Banking77 (Auxiliary)", "test", b77["test"].get("stats", {})))

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
