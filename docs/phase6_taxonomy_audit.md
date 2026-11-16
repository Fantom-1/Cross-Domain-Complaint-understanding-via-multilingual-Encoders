# Automated Phase 6 Label Taxonomy & Human Annotation Audit Report

**Generated:** 2026-11-16T17:00:57.420382+00:00  
**Execution Mode:** **Captured Local Workstation Snapshot** (Full Cryptographic Source-File & Manifest Verification)  
**Repository Root:** `.` (Repo-Relative)  
**Audit Target:** Phase 6 Label Taxonomy & Pilot Adjudication (`docs/taxonomy_codebook.md`, `data/manifests/source_label_mapping.csv`, `data/manifests/label_pilot_sampling_manifest.csv`, `data/manifests/adjudication_log.csv`, `docs/annotation_agreement.md`)  
**Audit Status:** **PASSED**  

---

## 1. Pillar Results Summary

| Pillar | Focus Area | Status | Key Criteria |
| :---: | :--- | :---: | :--- |
| **Pillar 1** | Storage & Environment Preflight | **PASS** | >= 10.0 GB disk space, clean module import |
| **Pillar 2** | Dataset Provenance & File Checksums | **PASS** | Canonical parquet SHA-256 (`b591ba98...`), taxonomy JSON, source mapping manifest |
| **Pillar 3** | Taxonomy Codebook & Schema Invariants | **PASS** | 16 classes documented with positive inclusions, negative exclusions, and multi-issue policy |
| **Pillar 4** | Source Mapping & Collision Audit | **PASS** | 221 CFPB mappings (198 mapped, 23 unmapped, 17 multi-match collisions audited) |
| **Pillar 5** | Stratified Pilot Sampling & Manifests | **PASS** | Exactly 320 records (20 per class), 15 columns, zero nulls in adjudication log |
| **Pillar 6** | Agreement & Empirical Divergence | **PASS** | Inter-annotator Po >= 90%, Kappa >= 0.70, empirical divergence confirmed (130/320) |
| **Pillar 7** | Governance & Exact Reconciliation | **PASS** | Weak administrative routing disclosures, auxiliary benchmark status, exact metric match |
| **Pillar 8** | Unit Test Suite Execution | **PASS** | Regression test suites pass with 0 failures across Phases 1–6 |

---

## 2. Key Audit Statistics Verified

* **Canonical Dataset Total Instances:** 45,723
* **Target Closed-Set Classes:** 16 classes
* **CFPB Source Mappings Audited:** 221 categories (198 mapped, 23 unmapped)
* **Rule Collisions Documented:** 17 multi-match patterns across distinct classes
* **Stratified Pilot Size:** 320 instances (exactly 20 per class across 16 classes)
* **Inter-Annotator Raw Agreement ($P_o$):** **97.81%**
* **Inter-Annotator Cohen's Kappa (κ):** **0.9763** (Substantial agreement)
* **Weak CFPB vs. Gold Agreement:** **59.38%** (Kappa: 0.5667)
* **Administrative Label Divergence:** **130 of 320 (40.62%)**
* **Multi-Issue Prevalence:** **48 (15.00%)**
* **Ambiguity Rate:** **0 (0.00%)**

---

## 3. Detailed Audit Execution Log

```
16:59:53 [INFO ] Starting Pillar 1: Storage & Environment Preflight...
16:59:53 [PASS ] Workspace disk space confirmed: 19.78 GB free.
16:59:53 [PASS ] Taxonomy auditor module imports cleanly and initializes 16 classes.
16:59:53 [INFO ] Starting Pillar 2: Dataset Provenance & Input File Checksums...
16:59:53 [PASS ] Source file hash verified locally: canonical_dataset.parquet (b591ba980a99ba82...).
16:59:53 [PASS ] Taxonomy config JSON exists and verified.
16:59:53 [PASS ] Source label mapping manifest exists and verified.
16:59:53 [INFO ] Starting Pillar 3: Taxonomy Codebook & Schema Invariants...
16:59:53 [PASS ] Codebook documents all 16 target classes with definitions and boundary rules.
16:59:53 [PASS ] Codebook contains all required governance, inclusion/exclusion, and multi-issue sections.
16:59:53 [INFO ] Starting Pillar 4: Source Mapping & Pattern Collision Audit...
16:59:53 [PASS ] Source mappings verified: 221 total (198 mapped, 23 unmapped, 17 collisions documented).
16:59:53 [INFO ] Starting Pillar 5: Stratified Pilot Sampling & Adjudication Invariants...
16:59:53 [PASS ] Pilot sampling manifest verified: exactly 320 records (20 per class across 16 classes).
16:59:53 [PASS ] Adjudication log verified: 320 records, 15 columns, zero nulls.
16:59:53 [INFO ] Starting Pillar 6: Inter-Annotator Agreement & Empirical Divergence Metrics...
16:59:53 [PASS ] Agreement metrics verified: Inter-annotator Po = 97.81%, Kappa = 0.9763.
16:59:53 [PASS ] Empirical divergence confirmed: 40.62% CFPB labels misaligned with gold intent.
16:59:53 [PASS ] Multi-issue prevalence: 15.00%, Ambiguity rate: 0.00%.
16:59:53 [INFO ] Starting Pillar 7: Governance Disclaimers & Exact Headline Reconciliation...
16:59:53 [PASS ] Governance notices verified in annotation agreement report.
16:59:53 [PASS ] Headline metrics reconciled exactly between manifests and report.
16:59:53 [INFO ] Starting Pillar 8: Unit Test Suite Execution...
17:00:57 [PASS ] All unit tests passed (114 tests executed across Phases 1–6 with 0 failures).
```
