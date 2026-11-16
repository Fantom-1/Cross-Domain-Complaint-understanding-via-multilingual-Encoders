# Automated Phase 5 Duplicate, Overlap & Contamination Audit Report

**Generated:** 2026-11-16T16:09:25.586833+00:00  
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
| **Pillar 3** | Manifest Schema & Integrity Invariants | **PASS** | duplicate_audit.csv (28 metrics), duplicate_clusters.csv (3273 rows, 13 cols, row-level size invariants) |
| **Pillar 4** | Zero Split Leakage & Cluster Invariants | **PASS** | Mathematical disjointness proven: Train_groups ∩ Val_groups = ∅, zero text hash leakage, Banking77 contamination = 0 |
| **Pillar 5** | Governance & Exact Headline Reconciliation | **PASS** | Weak administrative routing disclosures, exact metric reconciliation |
| **Pillar 6** | Unit Test Suite Execution | **PASS** | Regression test suites pass with 0 failures across Phases 1–5 |

---

## 2. Key Audit Statistics Verified

* **Canonical Dataset Total Instances:** 45,723
* **Unique Example IDs:** 45,723 (Duplicate source IDs: 0)
* **Total Partitions (group_id):** 43,142 (Singleton groups: 42,098)
* **Multi-Item Clusters:** 692 clusters (3,273 instances)
* **Maximum Cluster Size:** 123 instances (`grp_exact_6638526a9e2a`, 100% in validation)
* **Cross-Partition Group Leakage:** **0** (Train ∩ Val = 0, Train ∩ Test = 0, Val ∩ Test = 0)
* **Cross-Partition Text Hash Leakage:** **0** (Train ∩ Val = 0, Train ∩ Test = 0, Val ∩ Test = 0)
* **PolyAI/banking77 Contamination:** **0** instances (Zero cross-dataset leakage)
* **Exact Duplicate Text Collisions with Label Conflict:** 31 distinct text hashes
* **Near-Duplicate Clusters with Label Conflict:** 135 clusters

---

## 3. Detailed Audit Execution Log

```
16:08:19 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
16:08:19 [PASS ] Workspace disk space confirmed: 19.78 GB free.
16:08:19 [PASS ] Duplicate auditor module imports cleanly.
16:08:19 [INFO ] Starting Pillar 2: Dataset Provenance & Input File Checksums...
16:08:19 [PASS ] Source file hash independently checked locally: canonical_dataset.parquet verified (b591ba980a99ba82...).
16:08:19 [PASS ] Source file hash independently checked locally: Banking77 train & test SHA-256 digests verified.
16:08:19 [INFO ] Starting Pillar 3: Duplicate Manifest Schema & Data Integrity Invariants...
16:08:19 [PASS ] Loaded duplicate audit manifest (28 metrics validated against canonical invariants).
16:08:19 [PASS ] Cluster catalog instance count verified (3,273 instances).
16:08:19 [PASS ] Distinct cluster count verified (692 clusters).
16:08:19 [PASS ] Row-level cluster size invariants validated across all cluster instances.
16:08:19 [INFO ] Starting Pillar 4: Zero Split Leakage & Partition Invariants...
16:08:19 [PASS ] Zero cross-partition group leakage verified: Train_groups ∩ Val_groups = ∅, etc.
16:08:19 [PASS ] Zero cross-partition text hash leakage verified: Train_hashes ∩ Val_hashes = ∅, etc.
16:08:19 [PASS ] Manifest zero_leakage_verified flag confirmed True.
16:08:19 [PASS ] Zero cross-dataset contamination against PolyAI/banking77 confirmed.
16:08:19 [PASS ] All 692 clusters in catalog are strictly assigned to a single partition.
16:08:19 [INFO ] Starting Pillar 5: Governance Disclaimers & Exact Headline Reconciliation...
16:08:19 [PASS ] Report includes CFPB weak administrative supervision notice.
16:08:19 [PASS ] Report includes Banking77 auxiliary benchmark classification notice.
16:08:19 [PASS ] Report includes Zero partition leakage mathematical confirmation.
16:08:19 [PASS ] Report includes MinHash LSH parameters specification.
16:08:19 [PASS ] Report includes Chain-merging risk analysis.
16:08:19 [PASS ] Report exactly matches manifest for Total records: 45,723
16:08:19 [PASS ] Report exactly matches manifest for Unique normalized text hashes: 44,754
16:08:19 [PASS ] Report exactly matches manifest for Total records in exact duplicate collisions: 1,259
16:08:19 [PASS ] Report exactly matches manifest for Total partitions (`cluster_id`): 43,142
16:08:19 [PASS ] Report exactly matches manifest for Multi-item near-duplicate clusters: 692
16:08:19 [PASS ] Report exactly matches manifest for comprising **3,273** records: 3,273
16:08:19 [PASS ] Report exactly matches manifest for Max **123**: 123
16:08:19 [PASS ] Report exactly matches manifest for Mean **4.73**: 4.73
16:08:19 [PASS ] Report exactly matches manifest for Exact duplicate collisions with conflicting intent labels: 31
16:08:19 [PASS ] Report exactly matches manifest for Near-duplicate clusters with conflicting intent labels: 135
16:08:19 [INFO ] Starting Pillar 6: Unit Test Suite Execution...
16:08:58 [PASS ] Phase 5 Deduplication Suite: 25 tests PASSED.
16:09:11 [PASS ] Phase 4 Tokenization Suite: 20 tests PASSED.
16:09:12 [PASS ] Phase 3 Profiling Suite: 17 tests PASSED.
16:09:25 [PASS ] Phase 2 Parsing Suite: 22 tests PASSED.
16:09:25 [PASS ] Phase 1 Provenance Suite: 9 tests PASSED.
16:09:25 [PASS ] All unit tests passed (93 tests executed across Phases 1-5 with 0 failures).
```
