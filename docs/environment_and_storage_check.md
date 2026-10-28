# Environment and Storage Pre-Flight Check (Cross-Platform)

**Audit Date:** 2026-10-28  
**Auditor:** Automated Phase 0 Script (`scripts/audit_phase0.py`)  
**Workspace Root:** `D:\NLP`  
**Git Branch:** `DATA_PREPARATION` (tracking `origin/main`)

---

## 1. Storage Quotas and Headroom (Dynamically Discovered Volumes)

| Volume Label | Mount / Root Path | Total Capacity | Used Space | Free Space | Free % | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Workspace Volume (D:) | `D:\NLP` | 200.00 GB | 165.98 GB | 34.02 GB | 17.0% | **Adequate Headroom** |
| System/Temp Volume (C:) | `C:\Users\yashk\AppData\Local\Temp` | 274.72 GB | 244.28 GB | 30.44 GB | 11.1% | **Adequate Headroom** |

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

## 2. Software and Computational Stack

| Component | Specification | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Host Operating System** | win32 (nt) | Python Platform API | Operational |
| **Package Manager** | Mamba / Conda | Environment Inspection | Operational |
| **Project Python Prefix** | `D:\NLP\env` | `sys.prefix` | Operational |
| **Python Runtime** | Python 3.12.16 | `sys.version` | Verified |
| **Core Libraries** | `pandas`, `pyarrow`, `scikit-learn`, `scipy`, `datasketch`, `transformers`, `datasets`, `tokenizers` | In-Environment Smoke Test | 100% Passed |

---

## 3. Git Hygiene and Exclusion Rules

Audit of `.gitignore` confirmed that:
* `env/` is matched and ignored (line 19) — no local environment binaries can contaminate git.
* `/data/raw/`, `/data/interim/`, `/data/processed/` are strictly ignored (lines 2–4).
* `!/data/manifests/` is explicitly retained (line 5) to ensure all checksums, provenance records, and audit logs are tracked in version control.
* Checkpoints, models, and private cluster profiles (`Phase 2/SERVER_PROFILE_PRIVATE.md`) are shielded from commits.

---

## 4. Hard Safety Safeguards Adherence

* [x] **Zero Model Training / Fine-Tuning:** No model execution scheduled or executed.
* [x] **No Cluster Activity:** Zero SLURM jobs submitted, queried, or modified.
* [x] **Privacy / Narrative Protection:** No raw narrative strings written to logs or diagnostic outputs.
* [x] **Reference Immutability:** Baseline snapshot files documented and preserved unchanged.
