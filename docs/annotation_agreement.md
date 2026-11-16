# Phase 6: Label Taxonomy & Human Annotation Validity Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 6 (Label Taxonomy and Human-Validity Audit)  
**Execution Mode:** Empirical Human-Adjudicated Pilot ($N = 320$, Stratified across 16 Intent Classes)  
**Evaluation Scope:** CFPB Consumer Complaint Database vs. Adjudicated Semantic Gold  

---

> [!IMPORTANT]
> **Core Empirical Finding & Governance Boundary:**  
> This audit provides empirical confirmation that **CFPB administrative routing labels are weak supervision tags**, diverging from adjudicated semantic gold intent in **40.6%** of sampled narratives (130 of 320).  
> Auxiliary out-of-domain benchmark `PolyAI/banking77` represents atomic conversational queries and remains strictly isolated from in-domain CFPB training.

---

## 1. Executive Summary & Headline Agreement Metrics

| Metric | Measured Value | Standard Benchmark / Interpretation | Status |
| :--- | :---: | :--- | :---: |
| **Pilot Sample Size ($N$)** | **320** | 20 instances per class across 16 closed-set classes | **VERIFIED** |
| **Inter-Annotator Observed Agreement ($P_o$)** | **97.81%** | Proportion of unanimous independent labels (313/320) | **PASS** |
| **Inter-Annotator Cohen's Kappa (κ)** | **0.9763** | Substantial agreement (κ ≥ 0.70) under unconstrained narratives | **PASS** |
| **CFPB Weak vs. Gold Observed Agreement** | **59.38%** | Empirical accuracy of CFPB administrative intake routing (190/320) | **AUDITED** |
| **CFPB Weak vs. Gold Cohen's Kappa (κ)** | **0.5667** | Moderate alignment; reflects intake picklist routing noise | **AUDITED** |
| **Administrative Label Divergence Rate** | **40.62%** | Proportion of CFPB metadata tags misaligned with narrative intent | **AUDITED** |
| **Multi-Issue Prevalence Rate** | **15.00%** | Narratives alleging ≥ 2 distinct substantive consumer harms (48/320) | **AUDITED** |
| **Ambiguity / Low-Signal Rate** | **0.00%** | Truncated, heavily redacted, or unclassifiable text (0/320) | **BOUNDED** |

---

## 2. Source-to-Taxonomy Rule Collision Audit

In `src/data/map_intents.py`, CFPB intake issues and sub-issues are mapped to the 16 project classes via substring pattern rules. An automated scan of all **221** distinct CFPB `Issue // Sub-issue` pairs revealed that **17** source categories trigger multiple intent patterns across distinct classes.

Because pattern evaluation evaluates classes in static array order, earlier classes in `configs/taxonomy.json` take priority.

### Illustrative Rule Collision Cases

| CFPB Source Issue // Sub-issue | Statically Assigned Class | Competing Matched Classes & Patterns |
| :--- | :--- | :--- |
| `Attempts to collect debt not owed // Debt was result of identity theft` | `fraud_or_scam` | `fraud_or_scam` ('identity theft'), `debt_not_owed` ('attempts to collect debt not owed') |
| `Credit monitoring or identity theft protection services // Billing dispute for services` | `reporting_improper_use` | `reporting_improper_use` ('credit monitoring or identity theft'), `fraud_or_scam` ('identity theft') |
| `Credit monitoring or identity theft protection services // Didn't receive services that were advertised` | `reporting_improper_use` | `reporting_improper_use` ('credit monitoring or identity theft'), `fraud_or_scam` ('identity theft') |
| `Credit monitoring or identity theft protection services // Problem canceling credit monitoring or identify theft protection service` | `reporting_improper_use` | `reporting_improper_use` ('credit monitoring or identity theft'), `fraud_or_scam` ('identity theft') |
| `Credit monitoring or identity theft protection services // Problem with product or service terms changing` | `reporting_improper_use` | `reporting_improper_use` ('credit monitoring or identity theft'), `fraud_or_scam` ('identity theft') |
| `Credit monitoring or identity theft protection services // Received unwanted marketing or advertising` | `reporting_improper_use` | `reporting_improper_use` ('credit monitoring or identity theft'), `fraud_or_scam` ('identity theft') |
| `Getting a credit card // Card opened as result of identity theft or fraud` | `fraud_or_scam` | `fraud_or_scam` ('identity theft'), `application_problem` ('getting a credit card') |
| `Getting a loan // Confusing or misleading advertising` | `application_problem` | `application_problem` ('getting a loan'), `credit_terms_dispute` ('confusing or misleading advertising') |

**Mitigation & Governance:** All 221 mappings in `data/manifests/source_label_mapping.csv` are audited and frozen for the Phase A baseline. For subsequent model training, researchers must document that source routing maps represent weak heuristic supervision.

---

## 3. Class-by-Class Performance of CFPB Weak Labels vs. Adjudicated Gold

When treating human-adjudicated labels as gold reference, the performance of the raw CFPB administrative picklist tags is summarized below:

| Intent Class | Support (Gold) | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: |
| `account_access` | 13 | 0.550 | 0.846 | 0.667 |
| `account_management` | 8 | 0.400 | 1.000 | 0.571 |
| `application_problem` | 21 | 0.500 | 0.476 | 0.488 |
| `closing_process` | 12 | 0.350 | 0.583 | 0.438 |
| `credit_terms_dispute` | 19 | 0.600 | 0.632 | 0.615 |
| `debt_communication` | 10 | 0.450 | 0.900 | 0.600 |
| `debt_not_owed` | 28 | 0.750 | 0.536 | 0.625 |
| `debt_threats` | 32 | 0.650 | 0.406 | 0.500 |
| `fraud_or_scam` | 23 | 0.700 | 0.609 | 0.651 |
| `funds_availability` | 17 | 0.850 | 1.000 | 0.919 |
| `payment_problem` | 13 | 0.550 | 0.846 | 0.667 |
| `reporting_improper_use` | 18 | 0.600 | 0.667 | 0.632 |
| `reporting_incorrect_information` | 19 | 0.650 | 0.684 | 0.667 |
| `reporting_investigation_dispute` | 48 | 0.800 | 0.333 | 0.471 |
| `servicing_dispute` | 17 | 0.450 | 0.529 | 0.486 |
| `transaction_problem` | 22 | 0.650 | 0.591 | 0.619 |

### Systematic Divergence Modes Identified

1. **Credit Repair & Statutory Investigation Misrouting:**
   Consumers complaining of failure by credit bureaus to investigate disputes within 30 days are frequently tagged administratively under generic `Incorrect information on your report`. Semantically, these represent `reporting_investigation_dispute` under the Fair Credit Reporting Act (FCRA).
2. **Identity Theft vs. Inquiries:**
   Consumers experiencing criminal identity theft often focus on fraudulent credit inquiries, causing bureau intake to tag the complaint as `improper use of your report` (`reporting_improper_use`). Adjudication reclassifies criminal identity theft to `fraud_or_scam` per Codebook Priority Rule 2.
3. **Debt Collection Billing vs. Unauthorized Debits:**
   Disputes where a collector or servicer debited a checking account without authorization are tagged under `credit_terms_dispute` or `account_management` rather than `payment_problem`.

---

## 4. Multi-Issue and Ambiguity Analysis

* **Multi-Issue Complexity:** **15.0%** of sampled narratives contain multiple distinct legal allegations. The Codebook Priority Hierarchy successfully resolved all multi-issue instances by isolating the primary actionable harm while recording secondary claims.
* **Ambiguity Boundaries:** Only **0.0%** of narratives exhibited severe redaction or lack of factual substantiation, well within the project tolerance (< 5.0%).

---

## 5. Artifact Reference & Release Binding

* **Annotation Codebook:** [`docs/taxonomy_codebook.md`](file:///d:/NLP/docs/taxonomy_codebook.md)
* **Stratified Sampling Manifest:** [`data/manifests/label_pilot_sampling_manifest.csv`](file:///d:/NLP/data/manifests/label_pilot_sampling_manifest.csv) ($N = 320$)
* **Full Adjudication Log:** [`data/manifests/adjudication_log.csv`](file:///d:/NLP/data/manifests/adjudication_log.csv) ($N = 320$, 15 columns)
* **Source Label Mapping:** [`data/manifests/source_label_mapping.csv`](file:///d:/NLP/data/manifests/source_label_mapping.csv) (221 mappings, 17 multi-match cases documented)
