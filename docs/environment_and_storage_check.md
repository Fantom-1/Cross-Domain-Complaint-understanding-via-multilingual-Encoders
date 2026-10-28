# Environment and Storage Pre-Flight Check — Captured Local Audit Snapshot

**Audit Date:** 2026-10-28  
**Auditor:** Automated Phase 0 Script (`scripts/audit_phase0.py`)  
**Workspace Root:** `D:\NLP`  
**Git Branch:** `DATA_PREPARATION` (Tracking: `origin/DATA_PREPARATION`)

> [!NOTE]
> **Document Status: Captured Local Workstation Execution Snapshot**  
> This artifact represents a local audit snapshot dynamically generated on the developer workstation. In accordance with the Phase 0 data protocol, reproducibility evidence can be regenerated locally using the following commands:
> ```powershell
> mamba run -p D:\NLP\env python scripts/audit_phase0.py
> mamba run -p D:\NLP\env python -m unittest tests/data/test_data_integrity.py
> ```

---

## 1. Storage Quotas and Headroom (Dynamically Discovered Volumes)

| Volume Label | Mount / Root Path | Total Capacity | Used Space | Free Space | Free % | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Workspace Volume (D:) | `D:\NLP` | 200.00 GB | 165.98 GB | 34.02 GB | 17.0% | **Adequate Headroom** |
| System/Temp Volume (C:) | `C:\Users\yashk\AppData\Local\Temp` | 274.72 GB | 244.84 GB | 29.88 GB | 10.9% | **Adequate Headroom** |

### Storage Budget Analysis:
1. **Existing Raw Data:**
   * `data/raw/cfpb/CCDB_Export_2_May_2018_through_April_2021.zip`: ~157.0 MB (Compressed)
   * `data/raw/cfpb/complaints.csv.zip`: ~340.2 MB (Compressed)
   * `data/raw/banking77/`: ~1.0 MB
2. **Existing Processed Data:**
   * `canonical_dataset.parquet`: ~63.2 MB
   * Split CSVs (`baseline_train.csv`, `baseline_val.csv`, `baseline_test.csv`): ~63.0 MB total
3. **Mamba Local Environment:**
   * Isolated user prefix: ~2.2 GB (Python 3.12 + data science libraries + Hugging Face stack)
4. **Projected Archive Ingestion Buffer (Phases 1–3):**
   * If newer CFPB historical archive dumps through August 2026 are ingested, compressed archives range from 1.5 GB to 4.5 GB.
   * Streaming decompression and chunked parsing will require 10–18 GB transient disk space.
   * Current free disk space on workspace volume (34.02 GB) provides a **safe operating margin** for staged processing, provided raw zip files are not duplicated uncompressed in multiple locations.

> [!IMPORTANT]
> To prevent disk exhaustion, the data pipeline must strictly use streaming RFC 4180 parsing or chunked iterators instead of extracting entire uncompressed multi-gigabyte CSVs into multiple directories.

---

## 2. Software and Computational Stack (Live Smoke-Test Verified)

| Component | Specification | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Host Operating System** | win32 (nt) | Python Platform API | Operational |
| **Package Manager** | Mamba / Conda | Environment Inspection | Operational |
| **Project Python Prefix** | `D:\NLP\env` | `sys.prefix` | Operational |
| **Python Runtime** | Python 3.12.16 | `sys.version` | Verified |
| **Library: `pandas`** | `3.1.0` | In-Memory Import Check | Verified (v3.1.0) |
| **Library: `pyarrow`** | `26.0.0` | In-Memory Import Check | Verified (v26.0.0) |
| **Library: `sklearn`** | `1.9.1` | In-Memory Import Check | Verified (v1.9.1) |
| **Library: `scipy`** | `1.18.1` | In-Memory Import Check | Verified (v1.18.1) |
| **Library: `datasketch`** | `2.0.0` | In-Memory Import Check | Verified (v2.0.0) |
| **Library: `transformers`** | `5.21.0` | In-Memory Import Check | Verified (v5.21.0) |
| **Library: `datasets`** | `5.1.0` | In-Memory Import Check | Verified (v5.1.0) |
| **Library: `tokenizers`** | `0.23.3` | In-Memory Import Check | Verified (v0.23.3) |

* **Overall Library Smoke Test Result:** **100% Passed (All 8 libraries verified)**

---

## 3. Git Hygiene and Exclusion Rules (Dynamically Inspected from `.gitignore`)

| Pattern Rule | Description | Found in `.gitignore` | Line Number | Status |
| :--- | :--- | :---: | :---: | :---: |
| `env/` | Environment isolation | Yes | Line 17 | **PASSED** |
| `/data/raw/` | Raw data exclusion | Yes | Line 2 | **PASSED** |
| `/data/interim/` | Interim data exclusion | Yes | Line 3 | **PASSED** |
| `/data/processed/` | Processed data exclusion | Yes | Line 4 | **PASSED** |
| `!/data/manifests/` | Manifest tracking exemption | Yes | Line 5 | **PASSED** |

---

## 4. Hard Safety Safeguards Adherence

* [x] **Zero Model Training / Fine-Tuning:** No model execution scheduled or executed.
* [x] **No Cluster Activity:** Zero SLURM jobs submitted, queried, or modified.
* [x] **Privacy / Narrative Protection:** No raw narrative strings written to logs or diagnostic outputs.
* [x] **Reference Immutability:** Baseline snapshot files documented and preserved unchanged.
