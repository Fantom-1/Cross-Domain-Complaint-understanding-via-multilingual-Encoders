# Automated Phase 5 Duplicate, Overlap & Contamination Audit Report

**Generated:** 2026-11-16T15:10:41.888345+00:00  
**Execution Mode:** **Captured Local Workstation Snapshot** (Full Cryptographic Source-File & Manifest Verification)  
**Repository Root:** `.` (Repo-Relative)  
**Audit Target:** Phase 5 Duplicate, Overlap & Contamination Audit (`src/data/duplicate_auditor.py`, `data/manifests/duplicate_audit.csv`, `data/manifests/duplicate_clusters.csv`, `docs/split_leakage_audit.md`)  
**Audit Status:** **PASSED**  

---

## 1. Pillar Results Summary

| Pillar | Focus Area | Status | Key Criteria |
| :---: | :--- | :---: | :--- |
| **Pillar 1** | Storage & Environment Preflight | **PASS** | >= 10.0 GB disk space, clean module import |
| **Pillar 2** | Dataset Provenance & File Checksums | **PASS** | Canonical parquet SHA-256 (`b591ba98...`), Banking77 SHA-256 bindings |
| **Pillar 3** | Manifest Schema & Integrity Invariants | **PASS** | duplicate_audit.csv (26 metrics), duplicate_clusters.csv (3625 rows, 13 cols, row-level size invariants) |
| **Pillar 4** | Zero Split Leakage & Cluster Invariants | **PASS** | Mathematical disjointness proven: Train_groups ∩ Val_groups = ∅, zero text hash leakage, Banking77 contamination = 0 |
| **Pillar 5** | Governance & Exact Headline Reconciliation | **PASS** | Weak administrative routing disclosures, exact metric reconciliation |
| **Pillar 6** | Unit Test Suite Execution | **PASS** | Regression test suites pass with 0 failures across Phases 1–5 |

---

## 2. Key Audit Statistics Verified

* **Canonical Dataset Total Instances:** 45,723
* **Unique Example IDs:** 45,723 (Duplicate source IDs: 0)
* **Total Partitions (group_id):** 42,818 (Singleton groups: 42,098)
* **Multi-Item Clusters:** 720 clusters (3,625 instances)
* **Maximum Cluster Size:** 159 instances (`grp_exact_6638526a9e2a`, 100% in validation)
* **Cross-Partition Group Leakage:** **0** (Train ∩ Val = 0, Train ∩ Test = 0, Val ∩ Test = 0)
* **Cross-Partition Text Hash Leakage:** **0** (Train ∩ Val = 0, Train ∩ Test = 0, Val ∩ Test = 0)
* **PolyAI/banking77 Contamination:** **0** instances (Zero cross-dataset leakage)
* **Exact Duplicate Text Collisions with Label Conflict:** 31 distinct text hashes
* **Near-Duplicate Clusters with Label Conflict:** 167 clusters

---

## 3. Detailed Audit Execution Log

```
15:10:08 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
15:10:08 [PASS ] Workspace disk space confirmed: 19.78 GB free.
15:10:09 [PASS ] Duplicate auditor module imports cleanly.
15:10:09 [INFO ] Starting Pillar 2: Dataset Provenance & Input File Checksums...
15:10:09 [PASS ] Source file hash independently checked locally: canonical_dataset.parquet verified (b591ba980a99ba82...).
15:10:09 [PASS ] Source file hash independently checked locally: Banking77 train & test SHA-256 digests verified.
15:10:09 [INFO ] Starting Pillar 3: Duplicate Manifest Schema & Data Integrity Invariants...
15:10:09 [PASS ] Loaded duplicate audit manifest (26 metrics validated against canonical invariants).
15:10:09 [PASS ] Cluster catalog instance count verified (3,625 instances).
15:10:09 [PASS ] Distinct cluster count verified (720 clusters).
15:10:09 [PASS ] Row-level cluster size invariants validated across all cluster instances.
15:10:09 [INFO ] Starting Pillar 4: Zero Split Leakage & Partition Invariants...
15:10:09 [PASS ] Zero cross-partition group leakage verified: Train_groups ∩ Val_groups = ∅, etc.
15:10:09 [PASS ] Zero cross-partition text hash leakage verified: Train_hashes ∩ Val_hashes = ∅, etc.
15:10:09 [PASS ] Manifest zero_leakage_verified flag confirmed True.
15:10:09 [PASS ] Zero cross-dataset contamination against PolyAI/banking77 confirmed.
15:10:09 [PASS ] All 720 clusters in catalog are strictly assigned to a single partition.
15:10:09 [INFO ] Starting Pillar 5: Governance Disclaimers & Exact Headline Reconciliation...
15:10:09 [PASS ] Report includes CFPB weak administrative supervision notice.
15:10:09 [PASS ] Report includes Banking77 auxiliary benchmark classification notice.
15:10:09 [PASS ] Report includes Zero partition leakage mathematical confirmation.
15:10:09 [PASS ] Report includes MinHash LSH parameters specification.
15:10:09 [PASS ] Report includes Chain-merging risk analysis.
15:10:09 [PASS ] Report exactly matches manifest for Total records: 45,723
15:10:09 [PASS ] Report exactly matches manifest for Unique normalized hashes: 44,755
15:10:09 [PASS ] Report exactly matches manifest for Exact duplicate instances: 1,257
15:10:09 [PASS ] Report exactly matches manifest for Total groups: 42,818
15:10:09 [PASS ] Report exactly matches manifest for Multi-item clusters: 720
15:10:09 [PASS ] Report exactly matches manifest for Multi-item instances: 3,625
15:10:09 [PASS ] Report exactly matches manifest for Max cluster size: 159
15:10:09 [PASS ] Report exactly matches manifest for Mean cluster size: 5.035
15:10:09 [PASS ] Report exactly matches manifest for Exact duplicate label conflicts: 31
15:10:09 [PASS ] Report exactly matches manifest for Near-duplicate label conflicts: 167
15:10:09 [INFO ] Starting Pillar 6: Unit Test Suite Execution...
15:10:13 [PASS ] Phase 5 Deduplication Suite: 20 tests PASSED.
15:10:27 [PASS ] Phase 4 Tokenization Suite: 20 tests PASSED.
15:10:28 [PASS ] Phase 3 Profiling Suite: 17 tests PASSED.
15:10:41 [PASS ] Phase 2 Parsing Suite: 22 tests PASSED.
15:10:41 [PASS ] Phase 1 Provenance Suite: 9 tests PASSED.
15:10:41 [PASS ] All unit tests passed (88 tests executed across Phases 1-5 with 0 failures).
```
