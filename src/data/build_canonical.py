"""End-to-end reproducible pipeline for building the canonical complaint intent dataset.

Adheres strictly to DATA_PREPARATION_SPEC.md and SYSTEM.md:
- Streams raw CFPB FOIA archive zip without bloating RAM.
- Applies conservative normalization while preserving text_original.
- Removes template duplication and near-duplicate leakage via MinHash LSH.
- Maps raw issues/sub-issues to the 16-intent project taxonomy.
- Caps dominant classes to prevent class collapse.
- Partitions into group-safe, leakage-free train/val/test splits.
- Exports canonical_dataset.parquet, split CSVs, label map, and manifests.
"""

import argparse
import collections
import csv
import io
import json
import os
import random
import sys
import time
import zipfile
import pandas as pd

# Ensure repository root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.dedup import assign_duplicate_groups, compute_text_hash
from src.data.map_intents import IntentMapper
from src.data.normalize import normalize_complaint_text, word_count
from src.data.split import group_stratified_split, export_split_manifest

RAW_ZIP_PATH = "data/raw/cfpb/CCDB_Export_2_May_2018_through_April_2021.zip"
RAW_FILE_SHA256 = "4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45"
PRODUCT_MAP_PATH = "configs/product_canonical.json"
TAXONOMY_PATH = "configs/taxonomy.json"

PROCESSED_DIR = "data/processed"
MANIFEST_DIR = "data/manifests"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_canonical_dataset(
    zip_path: str = RAW_ZIP_PATH,
    out_dir: str = PROCESSED_DIR,
    manifest_dir: str = MANIFEST_DIR,
    per_product_sample: int = 15000,
    cap_per_intent: int = 3500,
    min_words: int = 20,
    seed: int = 13,
    max_scan_rows: int = 0
):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(manifest_dir, exist_ok=True)
    
    product_cfg = load_json(PRODUCT_MAP_PATH)
    product_map = product_cfg["map"]
    product_fallback = product_cfg.get("fallback", "other")
    
    mapper = IntentMapper(TAXONOMY_PATH)
    
    exclusion_log_path = os.path.join(manifest_dir, "exclusion_log.csv")
    exclusion_counts = collections.Counter()
    
    print("=" * 70, flush=True)
    print("PHASE A: CANONICAL DATASET PREPARATION PIPELINE", flush=True)
    print("=" * 70, flush=True)
    print(f"Source Archive: {zip_path}", flush=True)
    print(f"Random Seed: {seed} | Cap Per Intent: {cap_per_intent} | Min Words: {min_words}", flush=True)
    
    # -------------------------------------------------------------
    # Step 1: Reservoir sampling across products while streaming zip
    # -------------------------------------------------------------
    print("\n[Step 1/5] Streaming raw archive and reservoir sampling across products...", flush=True)
    rng = random.Random(seed)
    product_reservoirs = collections.defaultdict(list)
    product_seen_counts = collections.Counter()
    
    total_scanned = 0
    missing_narrative_count = 0
    too_short_count = 0
    
    t0 = time.time()
    with zipfile.ZipFile(zip_path) as z:
        csv_name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(csv_name) as raw:
            text_io = io.TextIOWrapper(raw, encoding="utf-8", newline="", errors="replace")
            reader = csv.DictReader(text_io)
            
            for row in reader:
                total_scanned += 1
                if max_scan_rows and total_scanned > max_scan_rows:
                    break
                
                raw_text = (row.get("Consumer complaint narrative") or "").strip()
                if not raw_text:
                    missing_narrative_count += 1
                    continue
                
                wc = word_count(raw_text)
                if wc < min_words:
                    too_short_count += 1
                    continue
                
                raw_prod = (row.get("Product") or "").strip()
                canon_prod = product_map.get(raw_prod, product_fallback)
                product_seen_counts[canon_prod] += 1
                
                complaint_id = (row.get("Complaint ID") or f"row_{total_scanned}").strip()
                item = {
                    "source_id": complaint_id,
                    "text_original": raw_text,
                    "product_raw": raw_prod,
                    "domain": canon_prod,
                    "sub_product": (row.get("Sub-product") or "").strip(),
                    "issue": (row.get("Issue") or "").strip(),
                    "sub_issue": (row.get("Sub-issue") or "").strip(),
                    "date_received": (row.get("Date received") or "")[:10]
                }
                
                bucket = product_reservoirs[canon_prod]
                if len(bucket) < per_product_sample:
                    bucket.append(item)
                else:
                    j = rng.randrange(product_seen_counts[canon_prod])
                    if j < per_product_sample:
                        bucket[j] = item
                
                if total_scanned % 150000 == 0:
                    current_eligible = sum(len(b) for b in product_reservoirs.values())
                    print(
                        f"  Scanned {total_scanned:,} rows | Sampled eligible: {current_eligible:,} | Elapsed: {time.time()-t0:.1f}s",
                        flush=True
                    )

    exclusion_counts["missing_narrative"] = missing_narrative_count
    exclusion_counts["too_short_under_20_words"] = too_short_count
    
    sampled_records = [rec for bucket in product_reservoirs.values() for rec in bucket]
    rng.shuffle(sampled_records)
    
    # Track rows that passed both filters but were probabilistically displaced
    # during reservoir sampling (cap = per_product_sample per domain).
    eligible_count = sum(product_seen_counts.values())
    reservoir_not_selected_count = eligible_count - len(sampled_records)
    exclusion_counts["reservoir_not_selected"] = reservoir_not_selected_count
    
    print(
        f"  Completed scan: {total_scanned:,} rows scanned | "
        f"Eligible (post-filter): {eligible_count:,} | "
        f"Reservoir-not-selected: {reservoir_not_selected_count:,} | "
        f"{len(sampled_records):,} candidates sampled across {len(product_reservoirs)} domains.",
        flush=True
    )
    
    # -------------------------------------------------------------
    # Step 2: Conservative normalization
    # -------------------------------------------------------------
    print("\n[Step 2/5] Performing conservative text normalization...", flush=True)
    for r in sampled_records:
        r["text_normalized"] = normalize_complaint_text(r["text_original"])

    # -------------------------------------------------------------
    # Step 3: Exact and MinHash near-duplicate clustering
    # -------------------------------------------------------------
    print("\n[Step 3/5] Exact and MinHash LSH near-duplicate grouping...", flush=True)
    clustered_records, dedup_stats = assign_duplicate_groups(sampled_records, n_perm=64, bands=16)
    print(
        f"  Total records: {dedup_stats['total_records']:,} | Unique cluster groups: {dedup_stats['unique_groups']:,} | Exact duplicates: {dedup_stats['exact_duplicates']:,} | Near-duplicate links: {dedup_stats['near_duplicate_links']:,}",
        flush=True
    )

    # -------------------------------------------------------------
    # Step 4: Taxonomy intent mapping & balanced capping
    # -------------------------------------------------------------
    print("\n[Step 4/5] Mapping issues to project taxonomy and balancing intent classes...", flush=True)
    mapped_by_intent = collections.defaultdict(list)
    unmapped_count = 0
    
    for r in clustered_records:
        intent_label, intent_id, status = mapper.map_cfpb_issue(r["issue"], r["sub_issue"])
        if status == "mapped" and intent_label:
            r["intent_label"] = intent_label
            r["intent_id"] = intent_id
            r["mapping_status"] = "mapped"
            r["exclusion_reason"] = "none"
            mapped_by_intent[intent_label].append(r)
        else:
            unmapped_count += 1
            r["mapping_status"] = "unmapped"
            r["exclusion_reason"] = "unmapped_issue"
    
    exclusion_counts["unmapped_issue"] = unmapped_count
    
    # Cap each intent class to cap_per_intent
    final_canonical_rows = []
    dropped_for_cap_count = 0
    
    for intent_label, records_list in sorted(mapped_by_intent.items()):
        rng.shuffle(records_list)
        if len(records_list) > cap_per_intent:
            dropped_for_cap_count += len(records_list) - cap_per_intent
            kept = records_list[:cap_per_intent]
        else:
            kept = records_list
        final_canonical_rows.extend(kept)
    
    exclusion_counts["dropped_for_class_balance_cap"] = dropped_for_cap_count
    rng.shuffle(final_canonical_rows)
    
    # -------------------------------------------------------------
    # Step 5: Group-safe stratified partition & export
    # -------------------------------------------------------------
    print("\n[Step 5/5] Partitioning into group-safe train/val/test splits...", flush=True)
    
    # Assign example_id
    for i, r in enumerate(final_canonical_rows):
        r["example_id"] = f"cfpb_{r['source_id']}"
        r["source_dataset"] = "CFPB Consumer Complaint Database"
        r["source_version"] = "FOIA Export 2 (2018-05 to 2021-04)"
        r["source_file_sha256"] = RAW_FILE_SHA256
        r["source_label"] = f"{r['issue']} // {r['sub_issue']}" if r["sub_issue"] else r["issue"]
        r["parent_label"] = r["product_raw"]
        r["language_condition"] = "en"
    
    train_rows, val_rows, test_rows = group_stratified_split(
        final_canonical_rows,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=seed,
        experiment_id="exp_indomain_baseline_v1"
    )
    
    print(
        f"  Partition counts: Train={len(train_rows):,} ({len(train_rows)/len(final_canonical_rows)*100:.1f}%), "
        f"Validation={len(val_rows):,} ({len(val_rows)/len(final_canonical_rows)*100:.1f}%), "
        f"Test={len(test_rows):,} ({len(test_rows)/len(final_canonical_rows)*100:.1f}%)",
        flush=True
    )
    
    # Verify group exclusivity
    train_groups = set(r["group_id"] for r in train_rows)
    val_groups = set(r["group_id"] for r in val_rows)
    test_groups = set(r["group_id"] for r in test_rows)
    assert not (train_groups & val_groups), "Leakage detected between train and val"
    assert not (train_groups & test_groups), "Leakage detected between train and test"
    assert not (val_groups & test_groups), "Leakage detected between val and test"
    print("  Verified: ZERO group leakage across train/validation/test partitions.", flush=True)

    # Export Parquet canonical dataset
    df_canonical = pd.DataFrame(final_canonical_rows)
    canonical_columns = [
        "example_id",
        "text_original",
        "text_normalized",
        "intent_label",
        "intent_id",
        "source_label",
        "parent_label",
        "domain",
        "language_condition",
        "source_dataset",
        "source_version",
        "source_id",
        "group_id",
        "split",
        "mapping_status",
        "exclusion_reason",
        "source_file_sha256",
        "text_hash"
    ]
    df_canonical = df_canonical[canonical_columns]
    parquet_path = os.path.join(out_dir, "canonical_dataset.parquet")
    df_canonical.to_parquet(parquet_path, index=False)
    print(f"\nSaved canonical dataset: {parquet_path} ({len(df_canonical):,} rows)", flush=True)
    
    # Export baseline CSVs
    training_cols = [
        "example_id",
        "text_normalized",
        "intent_label",
        "intent_id",
        "domain",
        "language_condition",
        "source_dataset",
        "group_id"
    ]
    for split_name, split_data in [("train", train_rows), ("validation", val_rows), ("test", test_rows)]:
        csv_file = os.path.join(out_dir, f"baseline_{split_name}.csv")
        df_split = pd.DataFrame(split_data)[training_cols].rename(columns={"text_normalized": "text", "intent_label": "label"})
        df_split.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"Saved split CSV: {csv_file} ({len(df_split):,} rows)", flush=True)
    
    # Export label_map.json
    label_map = {c["intent_label"]: c["intent_id"] for c in mapper.classes}
    label_map_path = os.path.join(out_dir, "label_map.json")
    with open(label_map_path, "w", encoding="utf-8") as f:
        json.dump(label_map, f, indent=2)
    print(f"Saved label map: {label_map_path}", flush=True)
    
    # Export manifests
    split_manifest_path = os.path.join(manifest_dir, "split_indomain.csv")
    export_split_manifest(final_canonical_rows, split_manifest_path, seed=seed)
    
    mapper.export_source_label_mapping(os.path.join(manifest_dir, "source_label_mapping.csv"))
    
    # Export exclusion log — every scanned row is now accounted for.
    # Sum: missing_narrative + too_short + reservoir_not_selected + unmapped_issue
    #      + dropped_for_class_balance_cap + final_canonical == total_scanned.
    with open(exclusion_log_path, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.writer(f)
        writer.writerow(["exclusion_reason", "count", "rationale"])
        writer.writerow(["missing_narrative", exclusion_counts["missing_narrative"], "Row did not contain a free-text complaint narrative."])
        writer.writerow(["too_short_under_20_words", exclusion_counts["too_short_under_20_words"], "Complaint narrative contained fewer than 20 words."])
        writer.writerow(["reservoir_not_selected", exclusion_counts["reservoir_not_selected"], "Narrative passed word-count filter but was probabilistically displaced during per-product reservoir sampling (cap 15,000 per domain)."])
        writer.writerow(["unmapped_issue", exclusion_counts["unmapped_issue"], "Complaint issue/sub-issue did not align with 16-class project taxonomy."])
        writer.writerow(["dropped_for_class_balance_cap", exclusion_counts["dropped_for_class_balance_cap"], "Surplus examples discarded to enforce uniform class cap."])
    print(f"Saved exclusion log: {exclusion_log_path}", flush=True)
    
    print("\n" + "=" * 70, flush=True)
    print("DATASET PREPARATION COMPLETED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default=RAW_ZIP_PATH)
    parser.add_argument("--out-dir", default=PROCESSED_DIR)
    parser.add_argument("--manifest-dir", default=MANIFEST_DIR)
    parser.add_argument("--per-product", type=int, default=15000)
    parser.add_argument("--cap-per-intent", type=int, default=3500)
    parser.add_argument("--min-words", type=int, default=20)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-scan", type=int, default=0)
    args = parser.parse_args()
    
    build_canonical_dataset(
        zip_path=args.zip,
        out_dir=args.out_dir,
        manifest_dir=args.manifest_dir,
        per_product_sample=args.per_product,
        cap_per_intent=args.cap_per_intent,
        min_words=args.min_words,
        seed=args.seed,
        max_scan_rows=args.max_scan
    )
