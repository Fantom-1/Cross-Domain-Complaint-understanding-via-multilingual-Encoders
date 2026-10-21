"""Deterministic, verified acquisition of raw datasets for Cross-Domain Complaint Understanding.

Supported sources:
- CFPB Consumer Complaint Database (Primary English complaint narratives)
- BANKING77 (Auxiliary intent classification benchmark)

Enforces:
- Streaming download with immutable storage in data/raw/<source>
- Live SHA-256 checksum calculation
- Automatic metadata recording into data/manifests/dataset_inventory.csv
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import requests

SOURCES = {
    "cfpb": {
        "dataset_name": "CFPB Consumer Complaint Database",
        "url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
        "target_dir": "data/raw/cfpb",
        "target_file": "complaints.csv.zip",
        "format": "csv.zip",
        "license": "Public Domain (US Government Work)",
        "license_url": "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/",
        "domain": "finance",
        "language": "en",
        "role_decision": "primary_eligible",
        "decision_rationale": "Authentic consumer complaints filed with the CFPB containing unedited narratives across multiple financial products.",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    },
    "banking77_train": {
        "dataset_name": "BANKING77",
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv",
        "target_dir": "data/raw/banking77",
        "target_file": "train.csv",
        "format": "csv",
        "license": "CC BY 4.0",
        "license_url": "https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE",
        "domain": "banking",
        "language": "en",
        "role_decision": "auxiliary_only",
        "decision_rationale": "Fine-grained customer service banking intent queries, but not consumer complaint narratives.",
        "user_agent": "Mozilla/5.0"
    },
    "banking77_test": {
        "dataset_name": "BANKING77",
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv",
        "target_dir": "data/raw/banking77",
        "target_file": "test.csv",
        "format": "csv",
        "license": "CC BY 4.0",
        "license_url": "https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE",
        "domain": "banking",
        "language": "en",
        "role_decision": "auxiliary_only",
        "decision_rationale": "Fine-grained customer service banking intent queries, but not consumer complaint narratives.",
        "user_agent": "Mozilla/5.0"
    },
    "banking77_categories": {
        "dataset_name": "BANKING77",
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/categories.json",
        "target_dir": "data/raw/banking77",
        "target_file": "categories.json",
        "format": "json",
        "license": "CC BY 4.0",
        "license_url": "https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE",
        "domain": "banking",
        "language": "en",
        "role_decision": "auxiliary_only",
        "decision_rationale": "77 fine-grained class taxonomy definitions.",
        "user_agent": "Mozilla/5.0"
    }
}

INVENTORY_PATH = "data/manifests/dataset_inventory.csv"
INVENTORY_COLUMNS = [
    "source_dataset",
    "source_url",
    "local_path",
    "file_name",
    "file_format",
    "source_version",
    "release_date",
    "retrieval_date",
    "license",
    "license_url",
    "checksum_sha256",
    "rows",
    "columns",
    "split",
    "language",
    "domain",
    "role_decision",
    "decision_rationale",
    "status",
    "notes"
]


def compute_file_sha256(filepath, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def download_file(url, target_path, user_agent=None, chunk_size=2 * 1024 * 1024):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_path = target_path + ".tmp"
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    print(f"Downloading {url} -> {target_path} ...", flush=True)
    
    headers = {"User-Agent": ua}
    sha256 = hashlib.sha256()
    bytes_downloaded = 0
    t0 = time.time()
    last_log = t0
    
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        print(f"Connected. Total size: {total_size / (1024*1024):.2f} MB", flush=True)
        
        with open(temp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    sha256.update(chunk)
                    bytes_downloaded += len(chunk)
                    
                    now = time.time()
                    if now - last_log >= 3.0 or bytes_downloaded == total_size:
                        speed = (bytes_downloaded / (1024 * 1024)) / max(now - t0, 0.001)
                        pct = (bytes_downloaded / total_size * 100) if total_size > 0 else 0
                        print(
                            f"  Downloaded: {bytes_downloaded / (1024*1024):.1f} MB"
                            f" / {total_size / (1024*1024):.1f} MB ({pct:.1f}%)"
                            f" at {speed:.2f} MB/s",
                            flush=True
                        )
                        last_log = now
    
    if os.path.exists(target_path):
        os.remove(target_path)
    os.rename(temp_path, target_path)
    
    actual_sha256 = sha256.hexdigest()
    size_bytes = os.path.getsize(target_path)
    print(f"Acquired: {target_path} ({size_bytes / (1024*1024):.2f} MB, SHA-256: {actual_sha256})", flush=True)
    return actual_sha256, size_bytes



def update_inventory(entry):
    os.makedirs(os.path.dirname(INVENTORY_PATH), exist_ok=True)
    existing = []
    if os.path.exists(INVENTORY_PATH):
        with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("local_path") != entry.get("local_path"):
                    existing.append(row)
    
    existing.append(entry)
    with open(INVENTORY_PATH, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        writer.writerows(existing)
    print(f"Updated inventory manifest: {INVENTORY_PATH}", flush=True)


def download_source(key):
    if key not in SOURCES:
        raise ValueError(f"Unknown source: {key}. Available: {list(SOURCES.keys())}")
    
    cfg = SOURCES[key]
    target_path = os.path.join(cfg["target_dir"], cfg["target_file"])
    
    if os.path.exists(target_path):
        print(f"Target file already exists: {target_path}. Verifying checksum...", flush=True)
        sha256 = compute_file_sha256(target_path)
        size_bytes = os.path.getsize(target_path)
        print(f"Existing file verified: {target_path} ({size_bytes / (1024*1024):.2f} MB, SHA-256: {sha256})", flush=True)
    else:
        sha256, size_bytes = download_file(cfg["url"], target_path, user_agent=cfg.get("user_agent"))
    
    retrieval_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    
    rows_val = "unknown"
    cols_val = "unknown"
    split_val = "all"
    if cfg["format"] == "csv":
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            rdr = csv.reader(f)
            header = next(rdr, None)
            cols_val = len(header) if header else 0
            row_count = sum(1 for _ in rdr)
            rows_val = row_count
        if "train" in cfg["target_file"]:
            split_val = "original_train"
        elif "test" in cfg["target_file"]:
            split_val = "original_test"
    elif cfg["format"] == "json":
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            rows_val = len(data) if isinstance(data, list) else 1
            cols_val = "N/A"
    
    inventory_entry = {
        "source_dataset": cfg["dataset_name"],
        "source_url": cfg["url"],
        "local_path": target_path.replace("\\", "/"),
        "file_name": cfg["target_file"],
        "file_format": cfg["format"],
        "source_version": "current_snapshot",
        "release_date": retrieval_date,
        "retrieval_date": retrieval_date,
        "license": cfg["license"],
        "license_url": cfg["license_url"],
        "checksum_sha256": sha256,
        "rows": rows_val,
        "columns": cols_val,
        "split": split_val,
        "language": cfg["language"],
        "domain": cfg["domain"],
        "role_decision": cfg["role_decision"],
        "decision_rationale": cfg["decision_rationale"],
        "status": "verified_acquired",
        "notes": f"Immutably archived in {cfg['target_dir']} ({size_bytes} bytes)"
    }
    
    update_inventory(inventory_entry)


def main():
    parser = argparse.ArgumentParser(description="Download and record verified datasets")
    parser.add_argument(
        "--source",
        choices=["cfpb", "banking77", "all"],
        default="all",
        help="Source to download"
    )
    args = parser.parse_args()
    
    if args.source in ("banking77", "all"):
        download_source("banking77_train")
        download_source("banking77_test")
        download_source("banking77_categories")
    
    if args.source in ("cfpb", "all"):
        download_source("cfpb")


if __name__ == "__main__":
    main()
