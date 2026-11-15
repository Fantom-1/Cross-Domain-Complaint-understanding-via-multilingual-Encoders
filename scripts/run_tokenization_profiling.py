#!/usr/bin/env python3
"""CLI Runner: Subword Tokenization Profiling for Canonical & Auxiliary Datasets.

Executes Phase 4 empirical profiling using the frozen `facebook/xlm-v-base` tokenizer:
- Tokenizes full canonical dataset (45,723 narratives) across splits and intent classes.
- Tokenizes Banking77 auxiliary partitions (10,003 train, 3,080 test queries).
- Generates `data/manifests/tokenization_profile.json` (full hierarchical manifest).
- Generates `data/manifests/tokenization_profile.csv` (summary tabular manifest).
"""

import argparse
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.tokenization_profiler import (
    DEFAULT_TOKENIZER_CHECKPOINT,
    TokenizationProfiler,
)

CANONICAL_PARQUET_DEFAULT = os.path.join(REPO_ROOT, "data", "processed", "canonical_dataset.parquet")
BANKING77_DIR_DEFAULT = os.path.join(REPO_ROOT, "data", "raw", "banking77")
OUTPUT_JSON_DEFAULT = os.path.join(REPO_ROOT, "data", "manifests", "tokenization_profile.json")
OUTPUT_CSV_DEFAULT = os.path.join(REPO_ROOT, "data", "manifests", "tokenization_profile.csv")


def main():
    parser = argparse.ArgumentParser(description="Run Phase 4 Subword Tokenization Profiling")
    parser.add_argument("--canonical-parquet", default=CANONICAL_PARQUET_DEFAULT, help="Path to canonical_dataset.parquet")
    parser.add_argument("--banking77-dir", default=BANKING77_DIR_DEFAULT, help="Directory containing Banking77 train.csv and test.csv")
    parser.add_argument("--output-json", default=OUTPUT_JSON_DEFAULT, help="Path for output JSON manifest")
    parser.add_argument("--output-csv", default=OUTPUT_CSV_DEFAULT, help="Path for output CSV manifest")
    parser.add_argument("--tokenizer", default=DEFAULT_TOKENIZER_CHECKPOINT, help="Tokenizer checkpoint name or path")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for tokenizer encoding")
    parser.add_argument("--mock", action="store_true", help="Force mock tokenizer mode for fast verification")
    args = parser.parse_args()

    print("=" * 80)
    print("PHASE 4: SUBWORD TOKENIZATION PROFILING RUNNER")
    print(f"Tokenizer Checkpoint: {args.tokenizer} (mock={args.mock})")
    print(f"Canonical Dataset:   {args.canonical_parquet}")
    print(f"Banking77 Directory: {args.banking77_dir}")
    print(f"Output JSON:         {args.output_json}")
    print(f"Output CSV:          {args.output_csv}")
    print("=" * 80)

    t0 = time.time()
    profiler = TokenizationProfiler(
        tokenizer_name_or_path=args.tokenizer,
        mock=args.mock,
    )
    print(f"Tokenizer loaded in {time.time() - t0:.2f}s (Type: {profiler.tokenizer_type}, Vocab: {profiler.vocab_size:,})")

    t1 = time.time()
    manifest = profiler.run_full_profile(
        canonical_parquet_path=args.canonical_parquet,
        banking77_dir=args.banking77_dir,
        output_json_path=args.output_json,
        output_csv_path=args.output_csv,
        batch_size=args.batch_size,
    )
    duration = time.time() - t1

    canon_overall = manifest["canonical_cfpb"]["text_normalized_overall"]
    print("\n--- Canonical CFPB Profile Summary (Normalized Texts) ---")
    print(f"Total Rows:     {canon_overall['count']:,}")
    print(f"Mean Tokens:    {canon_overall['mean']:.2f} (std: {canon_overall['std']:.2f})")
    print(f"Median Tokens:  {canon_overall['percentiles']['p50']}")
    print(f"P90 Tokens:     {canon_overall['percentiles']['p90']}")
    print(f"P95 Tokens:     {canon_overall['percentiles']['p95']}")
    print(f"P99 Tokens:     {canon_overall['percentiles']['p99']}")
    print(f"Subword Ratio:  {canon_overall['subword_expansion_ratio']['mean']}x tokens/word")
    print("\nTruncation Coverage at Cutoffs:")
    for cutoff, info in canon_overall["truncation_coverage"].items():
        print(f"  Cutoff {cutoff:>3}: {info['truncated_count']:>5} truncated ({info['truncated_percent']:>5.2f}%) | "
              f"Coverage: {info['retained_coverage_percent']:>5.2f}% (Token volume retained: {info['retained_token_percent']:>5.2f}%)")

    b77_train = manifest["auxiliary_banking77"]["train"]["stats"]
    b77_test = manifest["auxiliary_banking77"]["test"]["stats"]
    print(f"\n--- Banking77 Auxiliary Intent Summary ---")
    print(f"Train (N={b77_train['count']:,}): Mean Tokens = {b77_train['mean']:.2f}, Max = {b77_train['max']}, 128-Cutoff Trunc = {b77_train['truncation_coverage']['128']['truncated_percent']:.2f}%")
    print(f"Test  (N={b77_test['count']:,}): Mean Tokens = {b77_test['mean']:.2f}, Max = {b77_test['max']}, 128-Cutoff Trunc = {b77_test['truncation_coverage']['128']['truncated_percent']:.2f}%")

    print("\n" + "=" * 80)
    print(f"Profiling successfully completed in {duration:.2f}s.")
    print(f"Manifest written to: {args.output_json}")
    print(f"Summary CSV written to: {args.output_csv}")
    print("=" * 80)


if __name__ == "__main__":
    main()

