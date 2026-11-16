# Phase 6: Label Taxonomy Codebook, Mapping Audit & Pilot Protocol Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 6 (Label Taxonomy Codebook, Source Mapping Audit, and Annotation Protocol)  
**Status:** **PROTOCOL SPECIFICATION & SYNTHETIC SIMULATION BENCHMARK (NON-HUMAN)**  
**Target Sample Size ($N$):** **320** Stratified Instances across 16 Classes  

---

> [!CAUTION]
> **Methodological Provenance Disclosure & Supervision Limitation:**  
> **No empirical human adjudication has been conducted.**  
> The metrics presented in Section 3 represent a **synthetic rule-based heuristic simulation** designed to verify pipeline plumbing, blinded instrument generation, and Cohen's Kappa evaluation code. They must **not** be cited as human gold labels or empirical inter-annotator agreement.  
> As established in `PHASE_A_REVIEW_FINDINGS.md` (Item 3), CFPB administrative metadata fields (`Product`, `Issue`, `Sub-issue`) represent **weak administrative supervision**. Until genuine human adjudication is completed, the Phase A baseline operates strictly under weak administrative labels with explicit disclaimers.  
> Auxiliary benchmark `PolyAI/banking77` represents short conversational query intents and remains strictly isolated from in-domain CFPB training.

---

## 1. Stratified Pilot Sampling Design & Exclusivity Invariants

The pilot sample manifest [`data/manifests/label_pilot_sampling_manifest.csv`](file:///d:/NLP/data/manifests/label_pilot_sampling_manifest.csv) was generated from `canonical_dataset.parquet` under strict multi-dimensional constraints:

1. **Class Balance:** Exactly **20 instances per class** across all 16 intent classes ($N = 320$).
2. **Domain $\times$ Split Allocation:** Each class strictly allocates:
   * **`train`:** **14 instances** (70.0% of class sample)
   * **`validation`:** **3 instances** (15.0% of class sample)
   * **`test`:** **3 instances** (15.0% of class sample)
   * **Corpus Totals:** **224 train**, **48 validation**, **48 test** instances.
3. **Cluster Exclusivity & Leakage Prevention:** Every sampled instance belongs to a **unique `cluster_id`** (verified **320 distinct clusters** across 320 instances). No templated duplicate clusters (such as large credit repair components) can have multiple representatives in the pilot.
4. **Domain Stratification:** Within each split pool, records are sampled across all available product domains via round-robin allocation.

---

## 2. Blinded Human Annotation Protocol & Instrument Artifacts

To conduct genuine human adjudication in accordance with the maintainer review, independent blinded sheets have been generated:

* **Rater 1 Blinded Instrument:** [`data/annotation/rater_1_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_1_blinded_sheet.csv)
* **Rater 2 Blinded Instrument:** [`data/annotation/rater_2_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_2_blinded_sheet.csv)
* **Blank Adjudication Template:** [`data/annotation/adjudication_template.csv`](file:///d:/NLP/data/annotation/adjudication_template.csv)

### Blinding & Independence Guarantees
1. Raters receive **only** `pilot_id`, `example_id`, and unconstrained `text_normalized`.
2. All CFPB metadata (`Product`, `Issue`, `Sub-issue`, `domain`, `split`, and weak intent labels) are **completely stripped**.
3. Raters annotate independently using [`docs/taxonomy_codebook.md`](file:///d:/NLP/docs/taxonomy_codebook.md).
4. Submissions are immutable. Adjudication occurs only after both raters lock their sheets.

---

## 3. Synthetic Heuristic Simulation (Pipeline Demonstration Only)

To test the evaluation pipeline without fabricating human credentials, a synthetic text-heuristic model was executed against `text_normalized` (without access to weak labels). The results are stored in [`data/manifests/synthetic_pilot_simulation.csv`](file:///d:/NLP/data/manifests/synthetic_pilot_simulation.csv):

| Metric | Synthetic Simulation Value | Note / Interpretation |
| :--- | :---: | :--- |
| **Provenance Tag** | `synthetic_rule_simulation` | **Non-human software pipeline test** |
| **Simulated Rater Agreement ($P_o$)** | **99.38%** | Heuristic consistency test (318/320) |
| **Simulated Cohen's Kappa (κ)** | **0.9915** | Automated rule convergence benchmark |
| **Weak CFPB vs. Simulated Divergence** | **84.38%** | Demonstrates potential misalignment (270/320) |
| **Multi-Issue Prevalence** | **14.69%** | Simulated detection of multi-claim narratives (47/320) |
| **Ambiguity Rate** | **0.00%** | Narratives under length/intelligibility threshold |

---

## 4. CFPB Source-to-Taxonomy Rule Collision Audit

An automated audit of all **221** distinct CFPB `Issue // Sub-issue` pairs in [`data/manifests/source_label_mapping.csv`](file:///d:/NLP/data/manifests/source_label_mapping.csv) revealed **17** categories triggering multiple competing intent patterns:

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

**Impact on Baseline:** Because pattern matching evaluates classes in static array order, earlier classes in `configs/taxonomy.json` shadow later classes. This reinforces that CFPB-derived labels are weak supervisory signals requiring explicit disclaimer.

---

## 5. Artifact Reference & Release Binding

* **Annotation Codebook:** [`docs/taxonomy_codebook.md`](file:///d:/NLP/docs/taxonomy_codebook.md)
* **Sampling Manifest:** [`data/manifests/label_pilot_sampling_manifest.csv`](file:///d:/NLP/data/manifests/label_pilot_sampling_manifest.csv) ($N = 320$, 224 train / 48 val / 48 test, 320 unique clusters)
* **Blinded Rater Sheets:** [`data/annotation/rater_1_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_1_blinded_sheet.csv), [`data/annotation/rater_2_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_2_blinded_sheet.csv)
* **Adjudication Template:** [`data/annotation/adjudication_template.csv`](file:///d:/NLP/data/annotation/adjudication_template.csv)
* **Synthetic Simulation Artifact:** [`data/manifests/synthetic_pilot_simulation.csv`](file:///d:/NLP/data/manifests/synthetic_pilot_simulation.csv)
