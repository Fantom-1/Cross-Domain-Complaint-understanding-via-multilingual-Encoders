# Environment and Storage Pre-Flight Check

**Audit Date:** 2026-10-28  
**Auditor:** Automated Phase 0 Script (`scripts/audit_phase0.py`)  
**Workspace Root:** `D:\NLP`  
**Git Branch:** `DATA_PREPARATION` (tracking `origin/main`)

---

## 1. Storage Quotas and Headroom

| Drive | Total Capacity | Used Space | Free Space | Free % | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `D:` (Workspace & Data) | 200.00 GB | 165.81 GB | 34.19 GB | 17.1% | **Adequate Headroom** |
| `C:` (System & Conda Base) | 274.72 GB | 244.36 GB | 30.36 GB | 11.1% | **Adequate Headroom** |

### Storage Budget Analysis:
1. **Existing Raw Data:**
   * `data/raw/cfpb/CCDB_Export_2_May_2018_through_April_2021.zip`: ~157.0 MB (Compressed)
   * `data/raw/cfpb/complaints.csv.zip`: ~340.2 MB (Compressed)
   * `data/raw/banking77/`: ~1.0 MB
2. **Existing Processed Data:**
   * `canonical_dataset.parquet`: ~63.2 MB
   * Split CSVs (`baseline_train.csv`, `baseline_val.csv`, `baseline_test.csv`): ~63.0 MB total
3. **Mamba Local Environment:**
   * `D:\NLP\env`: ~1.85 GB (Python 3.12 + core data science libraries)
4. **Projected Archive Ingestion Buffer (Phases 1–3):**
   * If newer CFPB historical archive dumps through August 2026 are ingested, compressed archives range from 1.5 GB to 4.5 GB.
   * Streaming decompression and chunked parsing will require 10–18 GB transient disk space.
   * Current free disk space on `D:` (34.19 GB) provides a **safe 1.9x to 3x safety margin** for staged processing, provided raw zip files are not duplicated uncompressed in multiple locations.

> [!IMPORTANT]
> To prevent disk exhaustion, the data pipeline must strictly use streaming RFC 4180 parsing or chunked iterators instead of extracting entire uncompressed multi-gigabyte CSVs into multiple directories.

---

## 2. Software and Computational Stack

| Component | Specification | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Host Operating System** | Windows (PowerShell Shell) | Platform API | Operational |
| **Package Manager** | Mamba 2.4.0 (Conda 26.1.1) | `mamba --version` | Operational |
| **Project Python Prefix** | `D:\NLP\env` (Isolated user-owned prefix) | `sys.prefix` | Operational |
| **Python Runtime** | Python 3.12.16 | `python --version` | Verified |
| **Core Libraries** | `pandas` 3.1.0, `pyarrow` 26.0.0, `scikit-learn` 1.9.1, `scipy` 1.18.1, `datasketch` 2.0.0, `pyyaml` 6.0.3, `tqdm` 4.70.1, `requests` 2.34.2 | Smoke Test Import | 100% Passed |

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
