# Phase 7: Split Feasibility & Boundary Formulation Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 7 (Split Feasibility, Domain Confounding Analysis, and Boundary Formulation)  
**Dataset Version:** `canonical_dataset.parquet` (45,723 records, SHA-256 `b591ba980a99ba82...`)  
**Status:** **FORMAL PARTITION SPECIFICATION & BOUNDARY DECISION**  

---

## 1. Executive Summary & Core Research Decisions

Phase 7 evaluates the mathematical and empirical feasibility of three potential dataset partition paradigms:
1. **In-Distribution Group-Stratified Partitioning (`split_indomain.csv`):** Recommended primary benchmark.
2. **Leave-One-Domain-Out Cross-Product Partitioning:** Proven structurally confounded on the 16-class closed taxonomy.
3. **Chronological Temporal Partitioning:** Feasible as a secondary drift diagnostic, but vulnerable to template leakage and macroeconomic COVID-era concept drift.

### Core Architectural Decisions:
1. **Primary Baseline Retained:** The **group-stratified in-distribution split** (`data/manifests/split_indomain.csv`: **32,019 train**, **6,852 validation**, **6,852 test**) is formally established as the **official Phase A baseline benchmark**. It guarantees that all 16 intent classes and all 9 product domains are represented across all splits with **zero cluster leakage** ($0$ shared clusters).
2. **Leave-One-Domain-Out Proved Confounded:** Cross-product domain transfer on the full 16-class closed-set taxonomy is **mathematically ill-posed** due to domain-exclusive classes. Specifically, holding out `debt_collection` removes all training instances for 3 classes (`debt_communication`, `debt_not_owed`, `debt_threats`), while holding out `mortgage` removes `closing_process`. Zero-shot cross-domain evaluation on the full taxonomy cannot evaluate generalization because models cannot predict classes with zero training support.
3. **Multilingual Scope Formally Deferred:** Authentic, non-translated Hindi and Hinglish financial regulatory complaint corpora do not exist in the public CFPB archive (US English/Spanish FOIA). Machine-translating English narratives would evaluate translationese rather than true multilingual complaint understanding. Therefore, **Hindi/Hinglish evaluation is officially deferred/blocked** from the Phase A baseline until an authentic Indian regulatory corpus is acquired.

---

## 2. Product Domain $\times$ Label Contingency Matrix

The cross-tabulation of all **45,723** canonical records across **9 product domains** and **16 intent classes** reveals extreme label-space sparsity:

* **Total Matrix Cells:** **144** ($9 \times 16$)
* **Zero Cells:** **81 / 144** (**56.25% sparsity**)
* **Active Support Cells:** **63 / 144** (**43.75% active**)

### Distribution Across 9 Product Domains:

| `bank_account` | 5,874 | 12.85% |
| `credit_card` | 6,245 | 13.66% |
| `credit_reporting` | 6,319 | 13.82% |
| `debt_collection` | 9,714 | 21.25% |
| `money_transfer` | 4,584 | 10.03% |
| `mortgage` | 5,079 | 11.11% |
| `payday_personal_loan` | 2,049 | 4.48% |
| `student_loan` | 2,737 | 5.99% |
| `vehicle_loan` | 3,122 | 6.83% |

### Full Contingency Matrix ($9 \times 16$):

| Product Domain | `account_access` | `account_management` | `application_problem` | `closing_process` | `credit_terms_dispute` | `debt_communication` | `debt_not_owed` | `debt_threats` | `fraud_or_scam` | `funds_availability` | `payment_problem` | `reporting_improper_use` | `reporting_incorrect_information` | `reporting_investigation_dispute` | `servicing_dispute` | `transaction_problem` | **Total** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `bank_account` | 1833 | 2032 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1683 | 289 | 13 | 14 | 8 | 0 | 0 | **5,874** |
| `credit_card` | 1167 | 0 | 409 | 0 | 1843 | 0 | 0 | 0 | 164 | 0 | 290 | 73 | 97 | 189 | 55 | 1958 | **6,245** |
| `credit_reporting` | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 122 | 0 | 0 | 1624 | 2335 | 2225 | 2 | 4 | **6,319** |
| `debt_collection` | 0 | 0 | 0 | 0 | 0 | 3000 | 3000 | 3000 | 714 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **9,714** |
| `money_transfer` | 0 | 0 | 0 | 0 | 225 | 0 | 0 | 0 | 1994 | 1267 | 0 | 0 | 0 | 0 | 60 | 1038 | **4,584** |
| `mortgage` | 0 | 0 | 1447 | 1661 | 0 | 0 | 0 | 0 | 1 | 0 | 1761 | 52 | 92 | 65 | 0 | 0 | **5,079** |
| `payday_personal_loan` | 0 | 0 | 323 | 0 | 925 | 0 | 0 | 0 | 0 | 50 | 344 | 89 | 92 | 58 | 168 | 0 | **2,049** |
| `student_loan` | 0 | 0 | 133 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 59 | 148 | 176 | 2219 | 0 | **2,737** |
| `vehicle_loan` | 0 | 968 | 688 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 316 | 152 | 222 | 279 | 496 | 0 | **3,122** |
| **Total** | **3000** | **3000** | **3000** | **1661** | **3000** | **3000** | **3000** | **3000** | **3000** | **3000** | **3000** | **2062** | **3000** | **3000** | **3000** | **3000** | **45,723** |

---

## 3. Cross-Product Domain Transfer Feasibility & Confounding Proof

In cross-product transfer (leave-one-domain-out), one product domain is held out as the test set, while the remaining 8 domains serve as the training set.

### Structural Confounding Audit by Held-Out Domain:

| Held-Out Domain | Test Instances | Test Classes | Classes Missing in Train (0 Support) | Classes Untested in Test | Transfer Feasibility Verdict |
| :--- | :---: | :---: | :--- | :---: | :--- |
| `bank_account` | 5,874 | 8/16 | None (0 missing) | 8/16 | Partially Overlapping (Label-Truncated) |
| `credit_card` | 6,245 | 10/16 | None (0 missing) | 6/16 | Partially Overlapping (Label-Truncated) |
| `credit_reporting` | 6,319 | 7/16 | None (0 missing) | 9/16 | Partially Overlapping (Label-Truncated) |
| `debt_collection` | 9,714 | 4/16 | `debt_communication`, `debt_not_owed`, `debt_threats` | 12/16 | **CONFOUNDED (Zero-Shot Infeasible)** |
| `money_transfer` | 4,584 | 5/16 | None (0 missing) | 11/16 | Partially Overlapping (Label-Truncated) |
| `mortgage` | 5,079 | 7/16 | `closing_process` | 9/16 | **CONFOUNDED (Zero-Shot Infeasible)** |
| `payday_personal_loan` | 2,049 | 8/16 | None (0 missing) | 8/16 | Partially Overlapping (Label-Truncated) |
| `student_loan` | 2,737 | 6/16 | None (0 missing) | 10/16 | Partially Overlapping (Label-Truncated) |
| `vehicle_loan` | 3,122 | 8/16 | None (0 missing) | 8/16 | Partially Overlapping (Label-Truncated) |

### Mathematical Proof of Confounding:
1. **`debt_collection` Hold-Out:** Contains 9,714 records across 4 classes. However, 3 of those classes (`debt_communication`, `debt_not_owed`, `debt_threats`) have **exactly 0 training records** across the other 8 domains. In a closed-set classification head, the classifier has never received a single supervision signal for these intents.
2. **`mortgage` Hold-Out:** Contains 5,079 records. The class `closing_process` has **0 training records** across all other 8 domains.
3. **Label Truncation in Every Domain:** In *every single domain*, between **6 and 12 classes have 0 test instances**. A model evaluated on `money_transfer` only evaluates 5 classes; a model evaluated on `student_loan` only evaluates 6 classes.
4. **Conclusion:** Zero-shot leave-one-domain-out transfer across the full 16-class label space is fundamentally invalid. Any cross-domain investigation in Phase B/C must be restricted to the **domain-shared intent subset** (`fraud_or_scam`, `payment_problem`, `application_problem`, `servicing_dispute`, `credit_terms_dispute`, `reporting_*`).

---

## 4. Chronological & Temporal Distribution Analysis

Complaints in `canonical_dataset.parquet` span **36 continuous months**, from **`2018-05-01`** to **`2021-04-30`**.

### Key Temporal Invariants:
1. **Stable Volume:** Complaint volume remains active across all 36 months, averaging **1,270 complaints/month** (range: 959 to 2,106).
2. **Class Persistence:** All 16 classes remain actively represented in all four calendar years (2018, 2019, 2020, 2021). No intent disappears or first appears mid-dataset.
3. **Near-Duplicate Cluster Spanning:** Multi-item near-duplicate template clusters (such as credit repair campaigns) span up to **1,000+ days**. Partitioning purely by narrative timestamp would cause massive cross-partition leakage of identical form letters.
4. **COVID-19 Pandemic Concept Drift:** Spring 2020 introduced severe legal and macroeconomic shifts (CARES Act mortgage forbearance, stimulus payment hold disputes). A prospective test split (e.g. 2021) evaluates regulatory policy shock adaptation rather than stable linguistic intent understanding.
5. **Verdict:** Temporal splitting is documented as a secondary diagnostic benchmark for temporal drift analysis, but rejected as the primary baseline partition due to template leakage and macroeconomic confounding.

---

## 5. Multilingual & Modality Scope Boundaries (Hindi/Hinglish Status)

* **Repository Finding:** The CFPB dataset is a US consumer financial protection archive containing English (98.4%) and Spanish (1.6%) narratives.
* **Authenticity Barrier:** There are zero authentic Hindi or Hinglish complaints in the public CFPB archive.
* **Methodological Risk of Synthetic MT:** Machine-translating English CFPB complaints into Hindi or Hinglish would evaluate neural translation artifacts (translationese) rather than real-world Indian consumer complaint semantics.
* **Formal Decision:** Hindi and Hinglish evaluation is **formally deferred/blocked** from the Phase A baseline. The approved baseline scope is strictly bounded to:
  1. Primary: English CFPB Consumer Complaints (`canonical_dataset.parquet`).
  2. Auxiliary In-Domain Intent Benchmark: `PolyAI/banking77` (13,083 queries, strictly isolated).

---

## 6. Official In-Distribution Baseline Verification (`split_indomain.csv`)

The in-distribution split satisfies all requirements of `DATA_PREPARATION_SPEC.md` and Phase 5 deduplication invariants:

| Metric | Required Specification | Verified Manifest Value | Audit Status |
| :--- | :---: | :---: | :---: |
| **Total Instances** | 45,723 | **45,723** | **PASS** |
| **Training Split (`train`)** | 32,019 (70.0%) | **32,019** (70.03%) | **PASS** |
| **Validation Split (`validation`)** | 6,852 (15.0%) | **6,852** (14.99%) | **PASS** |
| **Test Split (`test`)** | 6,852 (15.0%) | **6,852** (14.99%) | **PASS** |
| **Train $\cap$ Val Cluster Leakage** | 0 clusters | **0 clusters** | **PASS** |
| **Train $\cap$ Test Cluster Leakage** | 0 clusters | **0 clusters** | **PASS** |
| **Val $\cap$ Test Cluster Leakage** | 0 clusters | **0 clusters** | **PASS** |
| **Class Coverage across Splits** | 16 in all 3 splits | **16 in all 3 splits** | **PASS** |
| **Domain Coverage across Splits** | 9 in all 3 splits | **9 in all 3 splits** | **PASS** |

---

## 7. Artifact Ledger

* **Class Domain Coverage Manifest:** `data/manifests/class_domain_coverage.csv`
* **Temporal Monthly Distribution:** `data/manifests/temporal_distribution.csv`
* **Temporal Class Support:** `data/manifests/temporal_class_distribution.csv`
* **In-Distribution Split Manifest:** `data/manifests/split_indomain.csv`
* **Split Feasibility Report:** `docs/split_feasibility.md`
