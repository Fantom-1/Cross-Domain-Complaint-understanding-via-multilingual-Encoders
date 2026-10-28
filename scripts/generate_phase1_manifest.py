#!/usr/bin/env python3
"""Programmatically generate Phase 1 manifests:
1. data/manifests/dataset_inventory.csv (20 columns per DATA_PREPARATION_SPEC.md)
2. data/manifests/release_overlap_report.csv

Captures verified provenance for all 21 CFPB FOIA narrative archive windows,
the bulk complaints daily feed, and the auxiliary BANKING77 benchmark.

Strictly distinguishes empirically observed properties from unverified/reported
properties of unfetched archives, and documents consumer narrative submission terms.
"""

import csv
import json
import os
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_DIR = os.path.join(REPO_ROOT, "data", "manifests")
RAW_CFPB_DIR = os.path.join(REPO_ROOT, "data", "raw", "cfpb")
RAW_BANKING77_DIR = os.path.join(REPO_ROOT, "data", "raw", "banking77")

CFPB_FOIA_BASE_URL = "https://files.consumerfinance.gov/f/documents/"
CFPB_READING_ROOM_URL = "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/"
CFPB_TERMS_URL = "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/"

# Clear legal categorization: Bureau metadata vs. Consumer-authored narrative submissions
CFPB_GOV_LICENSE = "Public Domain (US Government Work for Bureau Metadata); User-Consented Public Record (Narratives)"
CFPB_LICENSE_STATUS_NOTES = "Bureau metadata is a US Government Work. Consumer-authored narratives are third-party submissions disclosed pursuant to affirmative opt-in consumer consent (80 FR 15572) and FOIA reading room rules; downstream commercial reuse terms require verification."

CC_BY_4_LICENSE = "CC BY 4.0"
CC_BY_4_URL = "https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE"

# The 21 contiguous historical FOIA export windows established by CFPB
CFPB_EXPORT_WINDOWS = [
    (1, "CCDB_Export_1_December_2011_through_April_2018.zip", "2011-12-01", "2018-04-30", "December 2011 through April 2018"),
    (2, "CCDB_Export_2_May_2018_through_April_2021.zip", "2018-05-01", "2021-04-30", "May 2018 through April 2021"),
    (3, "CCDB_Export_3_May_2021_through_October_2022.zip", "2021-05-01", "2022-10-31", "May 2021 through October 2022"),
    (4, "CCDB_Export_4_November_2022_through_August_2023.zip", "2022-11-01", "2023-08-31", "November 2022 through August 2023"),
    (5, "CCDB_Export_5_September_2023_through_March_2024.zip", "2023-09-01", "2024-03-31", "September 2023 through March 2024"),
    (6, "CCDB_Export_6_April_2024_through_July_2024.zip", "2024-04-01", "2024-07-31", "April 2024 through July 2024"),
    (7, "CCDB_Export_7_August_2024_through_October_2024.zip", "2024-08-01", "2024-10-31", "August 2024 through October 2024"),
    (8, "CCDB_Export_8_November_2024_through_December_2024.zip", "2024-11-01", "2024-12-31", "November 2024 through December 2024"),
    (9, "CCDB_Export_9_January_2025_through_February_2025.zip", "2025-01-01", "2025-02-28", "January 2025 through February 2025"),
    (10, "CCDB_Export_10_March_2025_through_April_2025.zip", "2025-03-01", "2025-04-30", "March 2025 through April 2025"),
    (11, "CCDB_Export_11_May_2025_through_June_2025.zip", "2025-05-01", "2025-06-30", "May 2025 through June 2025"),
    (12, "CCDB_Export_12_July_2025_through_August_2025.zip", "2025-07-01", "2025-08-31", "July 2025 through August 2025"),
    (13, "CCDB_Export_13_September_2025_through_October_2025.zip", "2025-09-01", "2025-10-31", "September 2025 through October 2025"),
    (14, "CCDB_Export_14_November_2025_through_December_2025.zip", "2025-11-01", "2025-12-31", "November 2025 through December 2025"),
    (15, "CCDB_Export_15_January_2026_through_February_2026.zip", "2026-01-01", "2026-02-28", "January 2026 through February 2026"),
    (16, "CCDB_Export_16_March_2026.zip", "2026-03-01", "2026-03-31", "March 2026"),
    (17, "CCDB_Export_17_April_2026.zip", "2026-04-01", "2026-04-30", "April 2026"),
    (18, "CCDB_Export_18_May_2026.zip", "2026-05-01", "2026-05-31", "May 2026"),
    (19, "CCDB_Export_19_June_2026.zip", "2026-06-01", "2026-06-30", "June 2026"),
    (20, "CCDB_Export_20_July_2026.zip", "2026-07-01", "2026-07-31", "July 2026"),
    (21, "CCDB_Export_21_August_2026.zip", "2026-08-01", "2026-08-14", "August 2026"),
]

# Verified remote archive HTTP HEAD metadata captured on 2026-10-28
ARCHIVE_HEAD_METADATA = {
    1: {"content_length": 134688697, "etag": "4322bea4529773b527229b095f15f76d-17", "last_modified": "Mon, 14 Sep 2026 14:24:32 GMT"},
    2: {"content_length": 164598156, "etag": "6c2d21f0134772464bd9499e6c560169-20", "last_modified": "Mon, 14 Sep 2026 14:40:57 GMT"},
    3: {"content_length": 128680448, "etag": "4c6fa2ad66ed1e33a76d0a24ca6ad4ec-16", "last_modified": "Mon, 14 Sep 2026 14:45:43 GMT"},
    4: {"content_length": 115518181, "etag": "a734627ce73e2d7594b4938bf31aa2be-14", "last_modified": "Mon, 14 Sep 2026 14:46:45 GMT"},
    5: {"content_length": 100880669, "etag": "040d90016f24539c01ffe9b55bf8e706-13", "last_modified": "Mon, 14 Sep 2026 14:47:22 GMT"},
    6: {"content_length": 77142558, "etag": "d1ff1833b2429dd3ca06c7b5de80f688-10", "last_modified": "Mon, 14 Sep 2026 14:47:50 GMT"},
    7: {"content_length": 71365591, "etag": "b883535f9e0212db319428f04fedf765-9", "last_modified": "Mon, 14 Sep 2026 14:48:14 GMT"},
    8: {"content_length": 52563546, "etag": "f726e577a998166f1aa3a18b226934e5-7", "last_modified": "Mon, 14 Sep 2026 14:49:06 GMT"},
    9: {"content_length": 75475199, "etag": "c5d7e04d0614988b8da675b804931c5b-9", "last_modified": "Mon, 14 Sep 2026 14:50:18 GMT"},
    10: {"content_length": 65679901, "etag": "fccd79d313e472e1e5eaef81ff5748df-8", "last_modified": "Mon, 14 Sep 2026 14:32:52 GMT"},
    11: {"content_length": 71089209, "etag": "61a5b67e0f80bc2b88b209c1fa41738c-9", "last_modified": "Mon, 14 Sep 2026 14:33:15 GMT"},
    12: {"content_length": 80257322, "etag": "42aaebff986e744ee7d74dbef61aa9a5-10", "last_modified": "Mon, 14 Sep 2026 14:33:59 GMT"},
    13: {"content_length": 64219488, "etag": "549b95ab1bde9348f6979a07ab4f68d3-9", "last_modified": "Mon, 14 Sep 2026 14:34:18 GMT"},
    14: {"content_length": 60906208, "etag": "d0130937b6385e0b4d613d1a11296fbf-8", "last_modified": "Mon, 14 Sep 2026 14:34:35 GMT"},
    15: {"content_length": 35133648, "etag": "4f9f04d082dd844e3b029873314c2d2e-5", "last_modified": "Mon, 14 Sep 2026 14:34:51 GMT"},
    16: {"content_length": 21034448, "etag": "6ac549b716b7143b26c9329b333d1ce8-3", "last_modified": "Mon, 14 Sep 2026 14:35:04 GMT"},
    17: {"content_length": 21903673, "etag": "c9033c2e0227134c617bd8e88efe963d-3", "last_modified": "Mon, 14 Sep 2026 14:37:12 GMT"},
    18: {"content_length": 20061596, "etag": "f00f0013e82c5ade5142443c789a24d7-3", "last_modified": "Mon, 14 Sep 2026 14:37:28 GMT"},
    19: {"content_length": 18719277, "etag": "e66efb93a9fd4fd26ac55940393914d5-3", "last_modified": "Mon, 14 Sep 2026 14:37:46 GMT"},
    20: {"content_length": 16174780, "etag": "079663adb15ab64c6e4625cffceddbaa-3", "last_modified": "Mon, 14 Sep 2026 14:52:26 GMT"},
    21: {"content_length": 10501839, "etag": "a2424e938aca714765befe95a35e7b14-2", "last_modified": "Mon, 14 Sep 2026 14:42:09 GMT"},
}

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
    "notes",
]

OVERLAP_COLUMNS = [
    "release_id",
    "source_name",
    "file_name",
    "source_url",
    "window_start_date",
    "window_end_date",
    "window_duration_days",
    "compressed_size_bytes",
    "has_narratives",
    "column_count",
    "export2_id_overlap_count",
    "export2_id_overlap_pct",
    "overlap_relationship",
    "role_decision",
    "notes",
]


def build_inventory_rows():
    rows = []

    # 1. BANKING77 components (empirically inspected)
    b77_train = {
        "source_dataset": "BANKING77",
        "source_url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv",
        "local_path": "data/raw/banking77/train.csv",
        "file_name": "train.csv",
        "file_format": "csv",
        "source_version": "current_snapshot",
        "release_date": "2020-03-01",
        "retrieval_date": "2026-10-21",
        "license": CC_BY_4_LICENSE,
        "license_url": CC_BY_4_URL,
        "checksum_sha256": "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b",
        "rows": "10003",
        "columns": "2",
        "split": "original_train",
        "language": "en",
        "domain": "banking",
        "role_decision": "auxiliary_only",
        "decision_rationale": "Fine-grained customer service banking intent queries, but not consumer complaint narratives.",
        "status": "verified_acquired",
        "notes": "Immutably archived in data/raw/banking77 (839,073 bytes, RFC 4180 verified: 10,003 records vs 10,016 lines due to embedded newlines).",
    }
    b77_test = {
        "source_dataset": "BANKING77",
        "source_url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv",
        "local_path": "data/raw/banking77/test.csv",
        "file_name": "test.csv",
        "file_format": "csv",
        "source_version": "current_snapshot",
        "release_date": "2020-03-01",
        "retrieval_date": "2026-10-21",
        "license": CC_BY_4_LICENSE,
        "license_url": CC_BY_4_URL,
        "checksum_sha256": "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d",
        "rows": "3080",
        "columns": "2",
        "split": "original_test",
        "language": "en",
        "domain": "banking",
        "role_decision": "auxiliary_only",
        "decision_rationale": "Fine-grained customer service banking intent queries, but not consumer complaint narratives.",
        "status": "verified_acquired",
        "notes": "Immutably archived in data/raw/banking77 (239,961 bytes, RFC 4180 verified: 3,080 records vs 3,084 lines).",
    }
    b77_cat = {
        "source_dataset": "BANKING77",
        "source_url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/categories.json",
        "local_path": "data/raw/banking77/categories.json",
        "file_name": "categories.json",
        "file_format": "json",
        "source_version": "current_snapshot",
        "release_date": "2020-03-01",
        "retrieval_date": "2026-10-21",
        "license": CC_BY_4_LICENSE,
        "license_url": CC_BY_4_URL,
        "checksum_sha256": "53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63",
        "rows": "77",
        "columns": "N/A",
        "split": "all",
        "language": "en",
        "domain": "banking",
        "role_decision": "auxiliary_only",
        "decision_rationale": "77 fine-grained class taxonomy definitions.",
        "status": "verified_acquired",
        "notes": "Immutably archived in data/raw/banking77 (2,036 bytes).",
    }
    rows.extend([b77_train, b77_test, b77_cat])

    # 2. CFPB Active Daily Bulk Dump (complaints.csv.zip, empirically inspected)
    cfpb_bulk = {
        "source_dataset": "CFPB Consumer Complaint Database (Active Daily Feed)",
        "source_url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
        "local_path": "data/raw/cfpb/complaints.csv.zip",
        "file_name": "complaints.csv.zip",
        "file_format": "csv.zip",
        "source_version": "live_daily_snapshot",
        "release_date": "2026-10-28",
        "retrieval_date": "2026-10-21",
        "license": "Public Domain (US Government Work)",
        "license_url": CFPB_READING_ROOM_URL,
        "checksum_sha256": "9ae94df79f82a8e84b9b3e22bf8951f8c02489b88f5c4fa9ee32a95e1df760a1",
        "rows": "unknown",
        "columns": "15 (observed)",
        "split": "all",
        "language": "en",
        "domain": "finance",
        "role_decision": "ineligible_lacks_narratives",
        "decision_rationale": "Bulk complaint tracking feed across 5.6 GB uncompressed CSV; empirically confirmed that 'Consumer complaint narrative' column was dropped following CFPB August 2026 cessation of live narrative publication. Ineligible for narrative modeling.",
        "status": "verified_acquired",
        "notes": "Archived in data/raw/cfpb (356,704,969 bytes). Contains 15 observed columns; lacks consumer narrative text entirely.",
    }
    rows.append(cfpb_bulk)

    # 3. All 21 CFPB FOIA Narrative Archive Windows
    for num, fname, start_d, end_d, window_label in CFPB_EXPORT_WINDOWS:
        url = CFPB_FOIA_BASE_URL + fname
        meta = ARCHIVE_HEAD_METADATA.get(num, {})
        size_b = meta.get("content_length", 0)

        if num == 2:
            # Local reference baseline (empirically inspected)
            local_path = f"data/raw/cfpb/{fname}"
            sha256 = "4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45"
            rows_str = "1041632 (measured)"
            cols_str = "16 (observed)"
            role = "primary_eligible"
            status = "verified_acquired"
            notes = f"Primary project reference baseline snapshot. Official CFPB FOIA archive containing 439,860 verified consumer complaint narratives across 1,041,632 records (782.8 MB uncompressed). Verified SHA-256: {sha256}. {CFPB_LICENSE_STATUS_NOTES}"
            retrieval_date = "2026-10-21"
            rationale = "Authentic consumer complaints filed with CFPB with unedited narratives across 9 financial products (May 2018 - Apr 2021)."
        else:
            # Unfetched remote archives (distinguish observed vs unverified)
            local_path = "unfetched"
            sha256 = "unfetched"
            rows_str = "unverified_unfetched"
            cols_str = "16 (reported, unverified)"
            role = "primary_eligible"
            status = "unfetched_remote_archive"
            notes = f"Official CFPB FOIA reading room archive ({window_label}). HTTP 200 verified ({size_b:,} bytes compressed). Last-Modified: {meta.get('last_modified', 'unknown')}. ETag: {meta.get('etag', 'unknown')}. Schema and record counts unverified until fetched. {CFPB_LICENSE_STATUS_NOTES}"
            retrieval_date = "unfetched"
            rationale = f"Eligible historical consumer complaint narratives for temporal shift evaluation ({window_label}). Unfetched to preserve disk budget."

        row = {
            "source_dataset": "CFPB Consumer Complaint Database (FOIA Narratives Archive)",
            "source_url": url,
            "local_path": local_path,
            "file_name": fname,
            "file_format": "csv.zip",
            "source_version": f"export_window_{num}",
            "release_date": "2026-09-14",
            "retrieval_date": retrieval_date,
            "license": CFPB_GOV_LICENSE,
            "license_url": CFPB_TERMS_URL,
            "checksum_sha256": sha256,
            "rows": rows_str,
            "columns": cols_str,
            "split": "all",
            "language": "en",
            "domain": "finance",
            "role_decision": role,
            "decision_rationale": rationale,
            "status": status,
            "notes": notes,
        }
        rows.append(row)

    return rows


def build_overlap_rows():
    rows = []

    # 1. 21 FOIA Archives
    for num, fname, start_d, end_d, window_label in CFPB_EXPORT_WINDOWS:
        url = CFPB_FOIA_BASE_URL + fname
        meta = ARCHIVE_HEAD_METADATA.get(num, {})
        size_b = meta.get("content_length", 0)

        d1 = datetime.strptime(start_d, "%Y-%m-%d")
        d2 = datetime.strptime(end_d, "%Y-%m-%d")
        duration_days = (d2 - d1).days + 1

        if num == 2:
            overlap_count = "1041632 (measured)"
            overlap_pct = "100.00% (measured)"
            relationship = "reference_baseline_active"
            role = "reference_baseline_active"
            has_narr = "True (observed)"
            col_count = "16 (observed)"
            notes = "Active project reference baseline. Contains 1,041,632 total complaint records, 439,860 verified narrative records, yielding 45,723 canonical instances across 9 product domains."
        else:
            overlap_count = "unmeasured_unfetched"
            overlap_pct = "unmeasured_unfetched"
            relationship = "temporally_disjoint_window_id_overlap_unmeasured"
            role = "primary_eligible_unfetched"
            has_narr = "reported_unverified"
            col_count = "unverified_unfetched"
            notes = f"Chronologically disjoint calendar window ({window_label}). Temporal overlap is 0 days by window dates. Empirical record-ID overlap against Export 2 is unmeasured because file remains unfetched to preserve disk budget."

        row = {
            "release_id": f"CCDB_Export_{num:02d}",
            "source_name": "CFPB Consumer Complaint Database FOIA Archive",
            "file_name": fname,
            "source_url": url,
            "window_start_date": start_d,
            "window_end_date": end_d,
            "window_duration_days": duration_days,
            "compressed_size_bytes": size_b,
            "has_narratives": has_narr,
            "column_count": col_count,
            "export2_id_overlap_count": overlap_count,
            "export2_id_overlap_pct": overlap_pct,
            "overlap_relationship": relationship,
            "role_decision": role,
            "notes": notes,
        }
        rows.append(row)

    # 2. CFPB Active Daily Bulk Dump (empirically inspected)
    cfpb_bulk_row = {
        "release_id": "CCDB_Bulk_Complaints",
        "source_name": "CFPB Consumer Complaint Database (Active Bulk Feed)",
        "file_name": "complaints.csv.zip",
        "source_url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
        "window_start_date": "2011-12-01",
        "window_end_date": "2026-10-28",
        "window_duration_days": (datetime(2026, 10, 28) - datetime(2011, 12, 1)).days + 1,
        "compressed_size_bytes": 356704969,
        "has_narratives": "False (observed)",
        "column_count": "15 (observed)",
        "export2_id_overlap_count": "measured_superset_contains_export2_ids",
        "export2_id_overlap_pct": "measured_superset_contains_export2_ids",
        "overlap_relationship": "metadata_only_superset",
        "role_decision": "ineligible_lacks_narratives",
        "notes": "Full database metadata superset across 5.6 GB uncompressed CSV. Empirically verified to contain Export 2 IDs (e.g. Complaint ID 3109824), but lacks 'Consumer complaint narrative' column entirely (15 columns vs 16 in FOIA archives). Ineligible for narrative modeling.",
    }
    rows.append(cfpb_bulk_row)

    # 3. BANKING77 components (empirically inspected)
    b77_train_row = {
        "release_id": "BANKING77_Train",
        "source_name": "PolyAI BANKING77",
        "file_name": "train.csv",
        "source_url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv",
        "window_start_date": "N/A",
        "window_end_date": "N/A",
        "window_duration_days": "N/A",
        "compressed_size_bytes": 839073,
        "has_narratives": "False (observed)",
        "column_count": "2 (observed)",
        "export2_id_overlap_count": "0 (isolated)",
        "export2_id_overlap_pct": "0.00%",
        "overlap_relationship": "isolated_benchmark",
        "role_decision": "auxiliary_only",
        "notes": "10,003 fine-grained banking intent queries across 77 categories. Completely isolated from CFPB complaint data; zero ID overlap.",
    }
    b77_test_row = {
        "release_id": "BANKING77_Test",
        "source_name": "PolyAI BANKING77",
        "file_name": "test.csv",
        "source_url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv",
        "window_start_date": "N/A",
        "window_end_date": "N/A",
        "window_duration_days": "N/A",
        "compressed_size_bytes": 239961,
        "has_narratives": "False (observed)",
        "column_count": "2 (observed)",
        "export2_id_overlap_count": "0 (isolated)",
        "export2_id_overlap_pct": "0.00%",
        "overlap_relationship": "isolated_benchmark",
        "role_decision": "auxiliary_only",
        "notes": "3,080 fine-grained banking intent queries across 77 categories. Completely isolated from CFPB complaint data; zero ID overlap.",
    }
    rows.extend([b77_train_row, b77_test_row])

    return rows


def main():
    os.makedirs(MANIFEST_DIR, exist_ok=True)

    # Generate dataset_inventory.csv
    inventory_path = os.path.join(MANIFEST_DIR, "dataset_inventory.csv")
    inv_rows = build_inventory_rows()
    with open(inventory_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        writer.writerows(inv_rows)
    print(f"Generated {inventory_path} with {len(inv_rows)} entries.")

    # Generate release_overlap_report.csv
    overlap_path = os.path.join(MANIFEST_DIR, "release_overlap_report.csv")
    overlap_rows = build_overlap_rows()
    with open(overlap_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OVERLAP_COLUMNS)
        writer.writeheader()
        writer.writerows(overlap_rows)
    print(f"Generated {overlap_path} with {len(overlap_rows)} entries.")


if __name__ == "__main__":
    main()
