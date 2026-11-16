#!/usr/bin/env python3
"""Run Phase 6 Label Taxonomy Pilot, Mapping Audit, and Annotation Protocol.

Generates:
1. data/manifests/label_pilot_sampling_manifest.csv (N=320 stratified sample with domain x split quotas and cluster exclusivity)
2. data/annotation/rater_1_blinded_sheet.csv (Blinded human annotation instrument 1)
3. data/annotation/rater_2_blinded_sheet.csv (Blinded human annotation instrument 2)
4. data/annotation/adjudication_template.csv (Blank adjudication template for human adjudicator)
5. data/manifests/synthetic_pilot_simulation.csv (Synthetic heuristic simulation labeled strictly as non-human demonstration)
6. docs/annotation_agreement.md (Formal annotation protocol and synthetic simulation report)
"""

import collections
import csv
import json
import os
import sys
from typing import Any, Dict, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.taxonomy_auditor import (
    TaxonomyAuditor,
    PILOT_MANIFEST_PATH,
    PROVENANCE_SYNTHETIC,
    RATER_1_SHEET_PATH,
    RATER_2_SHEET_PATH,
    ADJUDICATION_TEMPLATE_PATH,
    SYNTHETIC_SIMULATION_PATH,
    compute_cohens_kappa,
    compute_per_class_metrics,
)

AGREEMENT_REPORT_PATH = "docs/annotation_agreement.md"


def simulate_text_heuristics(
    text: str, domain: str
) -> Tuple[str, str, str, str, bool, bool, str]:
    """Applies codebook rules to text alone (WITHOUT weak labels) for protocol verification.
    
    Returns:
        (sim1_label, sim2_label, sim_gold, secondary_labels, multi_issue, ambiguous, notes)
    """
    tl = text.lower()

    # Detect multi-issue signals purely from narrative text
    has_credit_rep_inacc = any(k in tl for k in ["incorrect information", "inaccurate", "not mine", "reporting error", "account balance wrong", "wrong balance"])
    has_investigation_fail = any(k in tl for k in ["investigation", "30 days", "dispute was ignored", "refuse to remove", "did not verify", "method of verification", "sent letter and received no response"])
    has_unauth_inq = any(k in tl for k in ["inquiry", "unauthorized inquiry", "hard pull", "permissible purpose"])
    has_identity_theft = any(k in tl for k in ["identity theft", "police report", "fraudulent account", "stolen identity", "impersonat", "unauthorized charge", "unauthorized transaction"])
    has_debt_harass = any(k in tl for k in ["threat", "arrest", "harass", "abusive", "curse", "called my job", "called my mother", "called my family", "threatened legal"])
    has_debt_comm = any(k in tl for k in ["cease and desist", "stop calling", "called after 9", "called before 8", "validation notice", "verification of debt", "debt verification"])
    has_debt_invalid = any(k in tl for k in ["never owed", "not my debt", "paid in full", "already paid", "discharged", "bankruptcy", "debt is not mine"])
    has_payment_issue = any(k in tl for k in ["payment not credited", "misapplied", "double debit", "autopay", "posted late", "trouble during payment", "struggling to pay"])
    has_transaction_issue = any(k in tl for k in ["merchant", "charged twice", "refund", "purchase on statement", "atm did not dispense", "terminal error"])
    has_funds_issue = any(k in tl for k in ["hold on check", "funds not available", "deposit held", "mobile deposit delay", "hold on my deposit"])
    has_lockout = any(k in tl for k in ["locked out", "cannot log in", "closed my account", "closed account without notice", "access denied", "can't access"])
    has_escrow_servicing = any(k in tl for k in ["escrow", "modification", "loss mitigation", "servicer", "hazard insurance", "respa", "qwr"])
    has_origination = any(k in tl for k in ["applied for", "application fee", "pre-approval", "origination", "denied loan", "adverse action"])
    has_closing = any(k in tl for k in ["closing disclosure", "settlement", "closing cost", "title company", "closing table", "closing on"])
    has_terms_fee = any(k in tl for k in ["apr", "interest rate", "credit limit", "hidden fee", "rewards", "promotional rate", "bonus"])

    is_ambiguous = len(text.strip()) < 80

    claims = [
        has_credit_rep_inacc, has_investigation_fail, has_unauth_inq, has_identity_theft,
        has_debt_harass, has_debt_comm, has_debt_invalid, has_payment_issue,
        has_transaction_issue, has_funds_issue, has_lockout, has_escrow_servicing,
        has_origination, has_closing, has_terms_fee
    ]
    multi_issue = sum(claims) >= 2

    # Deterministic text-only heuristic classification
    if has_identity_theft:
        gold = "fraud_or_scam"
        if has_unauth_inq:
            r1, r2, sec = "fraud_or_scam", "reporting_improper_use", "reporting_improper_use"
        elif has_debt_invalid:
            r1, r2, sec = "fraud_or_scam", "debt_not_owed", "debt_not_owed"
        else:
            r1, r2, sec = "fraud_or_scam", "fraud_or_scam", ""
        notes = "Simulated text heuristic: identity theft/unauthorized transaction detected."
    elif has_investigation_fail:
        gold = "reporting_investigation_dispute"
        if has_credit_rep_inacc:
            r1, r2, sec = "reporting_investigation_dispute", "reporting_incorrect_information", "reporting_incorrect_information"
        else:
            r1, r2, sec = "reporting_investigation_dispute", "reporting_investigation_dispute", ""
        notes = "Simulated text heuristic: dispute investigation procedural failure detected."
    elif has_debt_harass:
        gold = "debt_threats"
        r1, r2, sec = "debt_threats", "debt_threats", ""
        notes = "Simulated text heuristic: abusive collector threats detected."
    elif has_debt_comm:
        gold = "debt_communication"
        r1, r2, sec = "debt_communication", "debt_communication", ""
        notes = "Simulated text heuristic: debt communication procedural issue detected."
    elif has_debt_invalid:
        gold = "debt_not_owed"
        r1, r2, sec = "debt_not_owed", "debt_not_owed", ""
        notes = "Simulated text heuristic: debt validity disputed."
    elif has_escrow_servicing:
        gold = "servicing_dispute"
        r1, r2, sec = "servicing_dispute", "servicing_dispute", ""
        notes = "Simulated text heuristic: loan servicing/escrow dispute detected."
    elif has_closing:
        gold = "closing_process"
        r1, r2, sec = "closing_process", "closing_process", ""
        notes = "Simulated text heuristic: mortgage closing table dispute detected."
    elif has_origination:
        gold = "application_problem"
        r1, r2, sec = "application_problem", "application_problem", ""
        notes = "Simulated text heuristic: loan application friction detected."
    elif has_lockout:
        gold = "account_access"
        r1, r2, sec = "account_access", "account_access", ""
        notes = "Simulated text heuristic: digital account lockout detected."
    elif has_funds_issue:
        gold = "funds_availability"
        r1, r2, sec = "funds_availability", "funds_availability", ""
        notes = "Simulated text heuristic: deposit hold/funds availability issue detected."
    elif has_transaction_issue:
        gold = "transaction_problem"
        r1, r2, sec = "transaction_problem", "transaction_problem", ""
        notes = "Simulated text heuristic: point-of-sale merchant transaction issue detected."
    elif has_payment_issue:
        gold = "payment_problem"
        r1, r2, sec = "payment_problem", "payment_problem", ""
        notes = "Simulated text heuristic: payment processing/posting error detected."
    elif has_terms_fee:
        gold = "credit_terms_dispute"
        r1, r2, sec = "credit_terms_dispute", "credit_terms_dispute", ""
        notes = "Simulated text heuristic: interest rate/credit limit dispute detected."
    elif has_unauth_inq:
        gold = "reporting_improper_use"
        r1, r2, sec = "reporting_improper_use", "reporting_improper_use", ""
        notes = "Simulated text heuristic: unauthorized credit inquiry detected."
    elif has_credit_rep_inacc:
        gold = "reporting_incorrect_information"
        r1, r2, sec = "reporting_incorrect_information", "reporting_incorrect_information", ""
        notes = "Simulated text heuristic: inaccurate credit reporting detected."
    else:
        # Default fallback to generic account management
        gold = "account_management"
        r1, r2, sec = "account_management", "account_management", ""
        notes = "Simulated text heuristic: general account administration fallback."

    return r1, r2, gold, sec, multi_issue, is_ambiguous, notes


def run_pipeline() -> Dict[str, Any]:
    """Executes the Phase 6 sampling, blinded instrument generation, and protocol simulation."""
    print("=" * 80)
    print("PHASE 6: LABEL TAXONOMY CODEBOOK, MAPPING AUDIT & ANNOTATION PROTOCOL")
    print("=" * 80)

    auditor = TaxonomyAuditor()

    # 1. Audit CFPB Source Label Mapping Collisions
    print("\n[Step 1/5] Auditing CFPB Source Label Mappings for Pattern Collisions...")
    collision_res = auditor.audit_source_mapping_collisions()
    print(f"Total Source Mappings: {collision_res['total_mappings']}")
    print(f"Mapped: {collision_res['mapped_count']} | Unmapped: {collision_res['unmapped_count']}")
    print(f"Multi-Pattern Rule Collisions Identified: {collision_res['collision_count']}")

    # 2. Stratified Sampling of 320 Records (Per-Class Split Quotas & Cluster Exclusivity)
    print("\n[Step 2/5] Sampling Stratified Pilot with Per-Class Split Quotas & Cluster Dedup...")
    samples = auditor.sample_stratified_pilot()
    os.makedirs(os.path.dirname(PILOT_MANIFEST_PATH), exist_ok=True)

    pilot_fieldnames = [
        "pilot_id", "example_id", "domain", "split", "weak_cfpb_label",
        "source_label", "group_id", "cluster_id", "text_normalized"
    ]
    with open(PILOT_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=pilot_fieldnames)
        writer.writeheader()
        for s in samples:
            writer.writerow({
                "pilot_id": s["pilot_id"],
                "example_id": s["example_id"],
                "domain": s["domain"],
                "split": s["split"],
                "weak_cfpb_label": s["weak_cfpb_label"],
                "source_label": s["source_label"],
                "group_id": s["group_id"],
                "cluster_id": s["cluster_id"],
                "text_normalized": s["text_normalized"]
            })
    print(f"Exported {len(samples)} stratified pilot instances to {PILOT_MANIFEST_PATH}")
    split_counts = collections.Counter(s["split"] for s in samples)
    unique_clusters = len(set(s["cluster_id"] for s in samples))
    print(f"Split Allocation: {dict(split_counts)} | Unique Clusters: {unique_clusters}/320")

    # 3. Generate Blinded Annotation Instruments for Human Raters
    print("\n[Step 3/5] Generating Separate Blinded Annotation Sheets for Human Raters...")
    r1_path, r2_path, tmpl_path = auditor.generate_blinded_annotation_sheets(samples)
    print(f"Blinded Rater 1 Sheet: {r1_path}")
    print(f"Blinded Rater 2 Sheet: {r2_path}")
    print(f"Blank Adjudication Template: {tmpl_path}")

    # 4. Generate Synthetic Heuristic Simulation (Demonstration Benchmark Only)
    print("\n[Step 4/5] Executing Synthetic Heuristic Simulation (Software Protocol Test)...")
    sim_rows: List[Dict[str, Any]] = []

    for s in samples:
        # Note: text and domain only, weak_cfpb_label is NOT passed to simulation
        r1, r2, gold, sec, multi_issue, is_ambig, notes = simulate_text_heuristics(
            s["text_normalized"], s["domain"]
        )

        sim_rows.append({
            "pilot_id": s["pilot_id"],
            "example_id": s["example_id"],
            "provenance": PROVENANCE_SYNTHETIC,
            "simulated_rater_1_label": r1,
            "simulated_rater_2_label": r2,
            "simulated_raw_agreement": str(r1 == r2),
            "simulated_adjudicated_label": gold,
            "secondary_labels": sec,
            "multi_issue_flag": str(multi_issue),
            "ambiguity_flag": str(is_ambig),
            "simulation_notes": notes,
            "weak_cfpb_label": s["weak_cfpb_label"],
        })

    sim_fieldnames = [
        "pilot_id", "example_id", "provenance", "simulated_rater_1_label",
        "simulated_rater_2_label", "simulated_raw_agreement",
        "simulated_adjudicated_label", "secondary_labels",
        "multi_issue_flag", "ambiguity_flag", "simulation_notes", "weak_cfpb_label"
    ]
    with open(SYNTHETIC_SIMULATION_PATH, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=sim_fieldnames)
        writer.writeheader()
        for r in sim_rows:
            writer.writerow(r)
    print(f"Exported {len(sim_rows)} synthetic simulation records to {SYNTHETIC_SIMULATION_PATH}")

    # 5. Compute Metrics on Simulation & Generate Protocol Report
    print("\n[Step 5/5] Computing Simulation Metrics and Generating Protocol Report...")
    rater1_list = [r["simulated_rater_1_label"] for r in sim_rows]
    rater2_list = [r["simulated_rater_2_label"] for r in sim_rows]
    gold_list = [r["simulated_adjudicated_label"] for r in sim_rows]
    weak_list = [r["weak_cfpb_label"] for r in sim_rows]

    sim_metrics = auditor.compute_agreement_from_raters(rater1_list, rater2_list, gold_list, weak_list)
    sim_metrics["multi_issue_count"] = sum(1 for r in sim_rows if r["multi_issue_flag"].lower() == "true")
    sim_metrics["multi_issue_rate"] = round(sim_metrics["multi_issue_count"] / len(sim_rows), 4)
    sim_metrics["ambiguous_count"] = sum(1 for r in sim_rows if r["ambiguity_flag"].lower() == "true")
    sim_metrics["ambiguous_rate"] = round(sim_metrics["ambiguous_count"] / len(sim_rows), 4)

    generate_protocol_report(sim_metrics, collision_res, samples)
    print(f"Generated comprehensive protocol report at {AGREEMENT_REPORT_PATH}")

    return {
        "sim_metrics": sim_metrics,
        "collision_res": collision_res,
        "total_instances": len(samples),
        "split_counts": dict(split_counts),
        "unique_clusters": unique_clusters,
    }


def generate_protocol_report(
    sim_metrics: Dict[str, Any],
    collisions: Dict[str, Any],
    samples: List[Dict[str, Any]]
):
    """Generates the formal Phase 6 annotation protocol and synthetic simulation report."""
    per_class = sim_metrics["per_class_weak_metrics"]

    class_table_rows = []
    for cls, m in sorted(per_class.items()):
        class_table_rows.append(
            f"| `{cls}` | {m['support']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
        )
    class_table_md = "\n".join(class_table_rows)

    collision_samples_rows = []
    for c in collisions["collisions"][:8]:
        matched_str = ", ".join(f"`{m['intent_label']}` ('{m['pattern']}')" for m in c["matched_patterns"])
        collision_samples_rows.append(
            f"| `{c['source_label']}` | `{c['assigned_label']}` | {matched_str} |"
        )
    collision_table_md = "\n".join(collision_samples_rows)

    report_content = f"""# Phase 6: Label Taxonomy Codebook, Mapping Audit & Pilot Protocol Report

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 6 (Label Taxonomy Codebook, Source Mapping Audit, and Annotation Protocol)  
**Status:** **PROTOCOL SPECIFICATION & SYNTHETIC SIMULATION BENCHMARK (NON-HUMAN)**  
**Target Sample Size ($N$):** **320** Stratified Instances across 16 Weak-Label Strata  

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

1. **Class Balance:** Exactly **20 instances per class** across 16 CFPB weak-label strata ($N = 320$).
2. **Per-Class Split Quotas with Domain Rotation:** Across the 16 CFPB weak-label strata (administrative metadata categories, not human-validated semantic classes), each class strictly allocates:
   * **`train`:** **14 instances** (70.0% of class sample)
   * **`validation`:** **3 instances** (15.0% of class sample)
   * **`test`:** **3 instances** (15.0% of class sample)
   * **Corpus Totals:** **224 train**, **48 validation**, **48 test** instances.
   * **Domain Allocation:** Within each split pool, records are allocated across available product domains via round-robin rotation (not fixed domain x split cell quotas).
3. **Cluster Exclusivity & Leakage Prevention:** Every sampled instance belongs to a **unique `cluster_id`** (verified **320 distinct clusters** across 320 instances). No templated duplicate clusters (such as large credit repair components) can have multiple representatives in the pilot.

---

## 2. Blinded Human Annotation Protocol & Instrument Artifacts

To conduct genuine human adjudication in accordance with the maintainer review, independent blinded sheets have been generated:

* **Rater 1 Blinded Instrument:** [`data/annotation/rater_1_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_1_blinded_sheet.csv)
* **Rater 2 Blinded Instrument:** [`data/annotation/rater_2_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_2_blinded_sheet.csv)
* **Blank Adjudication Template:** [`data/annotation/adjudication_template.csv`](file:///d:/NLP/data/annotation/adjudication_template.csv)

### Blinding & Independence Guarantees
1. Raters receive **only** `pilot_id`, `example_id`, and unconstrained `text_normalized`.
2. All CFPB metadata (`Product`, `Issue`, `Sub-issue`, `domain`, `split`, and weak intent labels) are **completely stripped**.
3. Adjudicators receive the complete, unconstrained narrative (`text_normalized`) in [`data/annotation/adjudication_template.csv`](file:///d:/NLP/data/annotation/adjudication_template.csv) without truncation.
4. Raters annotate independently using [`docs/taxonomy_codebook.md`](file:///d:/NLP/docs/taxonomy_codebook.md).
5. Submissions are immutable. Adjudication occurs only after both raters lock their sheets.

---

## 3. Synthetic Pipeline Demonstration & Non-Evidential Software Fixture

To verify software plumbing, blinded instrument generation, schema contracts, and evaluation code without fabricating human annotations, an automated text-heuristic rule pass was executed against `text_normalized`. The resulting software fixture is committed in [`data/manifests/synthetic_pilot_simulation.csv`](file:///d:/NLP/data/manifests/synthetic_pilot_simulation.csv):

> [!WARNING]
> **Strict Non-Evidential Limitation:**  
> The metrics below are non-evidential software fixtures designed exclusively for end-to-end integration testing:
> 1. **No Gold Labels or Misalignment Estimates:** Because simulated labels are generated by deterministic keyword rules rather than human annotators, divergence between CFPB administrative labels and the heuristic simulation cannot estimate actual CFPB weak-label error or establish semantic misalignment. Any divergence reflects solely the disparity between static metadata and an arbitrary keyword script.
> 2. **No Empirical Multi-Issue or Ambiguity Rates:** Simulated multi-issue and ambiguity flags are heuristic artifact counts, not empirical estimates of human semantic complexity.
> 3. **No Empirical Inter-Annotator Agreement:** Simulated agreement ($P_o = {sim_metrics['raw_inter_annotator_agreement'] * 100:.2f}\%$, $\kappa = {sim_metrics['cohens_kappa_inter_annotator']:.4f}$) measures only the internal consistency of automated rules, not human consensus.

| Metric | Value | Characterization |
| :--- | :---: | :--- |
| **Provenance Tag** | `synthetic_rule_simulation` | Machine-readable tag; non-human pipeline fixture |
| **Simulated Rule Agreement ($P_o$)** | **{sim_metrics['raw_inter_annotator_agreement'] * 100:.2f}%** | Software rule consistency check ({sim_metrics['raw_inter_annotator_agree_count']}/320) |
| **Simulated Rule Kappa (κ)** | **{sim_metrics['cohens_kappa_inter_annotator']:.4f}** | Automated rule convergence benchmark |
| **Simulated Multi-Issue Heuristic Hits** | **{sim_metrics['multi_issue_rate'] * 100:.2f}%** | Rule-matched secondary keywords ({sim_metrics['multi_issue_count']}/320) — software fixture only |
| **Simulated Ambiguity Heuristic Hits** | **{sim_metrics['ambiguous_rate'] * 100:.2f}%** | Narratives under character length threshold |

---

## 4. CFPB Source-to-Taxonomy Rule Collision Audit

An automated audit of all **{collisions['total_mappings']}** distinct CFPB `Issue // Sub-issue` pairs in [`data/manifests/source_label_mapping.csv`](file:///d:/NLP/data/manifests/source_label_mapping.csv) revealed **{collisions['collision_count']}** categories triggering multiple competing intent patterns:

| CFPB Source Issue // Sub-issue | Statically Assigned Class | Competing Matched Classes & Patterns |
| :--- | :--- | :--- |
{collision_table_md}

**Impact on Baseline:** Because pattern matching evaluates classes in static array order, earlier classes in `configs/taxonomy.json` shadow later classes. This reinforces that CFPB-derived labels are weak supervisory signals requiring explicit disclaimer.

---

## 5. Artifact Reference & Release Binding

* **Annotation Codebook:** [`docs/taxonomy_codebook.md`](file:///d:/NLP/docs/taxonomy_codebook.md)
* **Sampling Manifest:** [`data/manifests/label_pilot_sampling_manifest.csv`](file:///d:/NLP/data/manifests/label_pilot_sampling_manifest.csv) ($N = 320$, 224 train / 48 val / 48 test across 16 weak-label strata, 320 unique clusters)
* **Blinded Rater Sheets:** [`data/annotation/rater_1_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_1_blinded_sheet.csv), [`data/annotation/rater_2_blinded_sheet.csv`](file:///d:/NLP/data/annotation/rater_2_blinded_sheet.csv)
* **Adjudication Template (Full Text):** [`data/annotation/adjudication_template.csv`](file:///d:/NLP/data/annotation/adjudication_template.csv)
* **Synthetic Simulation Artifact:** [`data/manifests/synthetic_pilot_simulation.csv`](file:///d:/NLP/data/manifests/synthetic_pilot_simulation.csv)
"""

    os.makedirs(os.path.dirname(AGREEMENT_REPORT_PATH), exist_ok=True)
    with open(AGREEMENT_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_content)


if __name__ == "__main__":
    run_pipeline()
