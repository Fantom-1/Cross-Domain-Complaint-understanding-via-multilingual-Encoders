#!/usr/bin/env python3
"""Execute full-corpus profiling across all available datasets and output manifests."""

import json
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.profiler import CorpusProfiler, export_profile_csv

def main():
    print("=" * 80)
    print("PHASE 3: FULL-CORPUS PROFILING EXECUTION")
    print("=" * 80)
    
    t0 = time.time()
    profiler = CorpusProfiler()
    
    raw_archive = os.path.join(REPO_ROOT, "data", "raw", "cfpb", "CCDB_Export_2_May_2018_through_April_2021.zip")
    banking77_train = os.path.join(REPO_ROOT, "data", "raw", "banking77", "train.csv")
    banking77_test = os.path.join(REPO_ROOT, "data", "raw", "banking77", "test.csv")
    
    print(f"Profiling CFPB FOIA archive: {raw_archive}")
    cfpb_profile = profiler.profile_cfpb_foia_archive(raw_archive)
    print(f"CFPB profiling completed: {cfpb_profile['total_rows']:,} rows scanned.")
    
    print(f"Profiling BANKING77 auxiliary benchmark: {banking77_train}, {banking77_test}")
    banking77_profile = profiler.profile_banking77(banking77_train, banking77_test)
    cfpb_profile["banking77"] = banking77_profile
    
    out_json = os.path.join(REPO_ROOT, "data", "manifests", "source_profile.json")
    out_csv = os.path.join(REPO_ROOT, "data", "manifests", "source_profile.csv")
    
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(cfpb_profile, f, indent=2)
    print(f"Wrote JSON profile to: {out_json}")
    
    export_profile_csv(cfpb_profile, out_csv)
    print(f"Wrote CSV profile to: {out_csv}")
    
    elapsed = time.time() - t0
    print(f"Total profiling pipeline elapsed time: {elapsed:.2f} seconds.")
    print("=" * 80)

if __name__ == "__main__":
    main()

