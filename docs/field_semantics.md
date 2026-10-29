# CFPB & Auxiliary Dataset Field Semantics and Administrative Provenance

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 2 (Robust Parsing & Schema Diff)  
**Document:** Field Semantics & Administrative Purpose  
**Date:** 2026-10-29  

---

## 1. Executive Summary & Epistemological Boundary

This document formally details the semantic definition, data type, nullability, administrative intake purpose, and methodological constraints of all fields in the Consumer Financial Protection Bureau (CFPB) Consumer Complaint Database archives, as well as the auxiliary `PolyAI/banking77` benchmark.

> [!IMPORTANT]
> **Administrative Metadata vs. Semantic Ground-Truth Intent:**
> The CFPB fields `Issue` and `Sub-issue` are administrative bureau routing categories chosen from a fixed, predefined intake picklist. They reflect institutional workflow designations used by bureau caseworkers and financial institutions, **not gold semantic intent labels**. In accordance with scientific integrity guidelines, all classification tasks utilizing these fields are designated as **"complaint-issue classification under weak administrative labels"** unless and until an adjudicated human-annotation pilot (Phase 6) proves semantic gold validity.

---

## 2. CFPB Field-by-Field Semantic Reference

The 16 canonical fields present in the CFPB FOIA Reading Room archives (`CCDB_Export_1` through `CCDB_Export_21`) are defined below:

| Field Name | Storage Type | Nullable? | Observed Null Rate (Export 2) | Administrative Purpose & Semantic Definition |
| :--- | :---: | :---: | :---: | :--- |
| **`Date received`** | `DATE` (`YYYY-MM-DD`) | No | 0.00% | The calendar date the complaint was submitted by the consumer to the CFPB intake portal or received via phone/mail. Used to establish temporal ordering and longitudinal splits. |
| **`Product`** | `VARCHAR` | No | 0.00% | The primary high-level financial product category (e.g., `Credit reporting...`, `Debt collection`, `Mortgage`, `Credit card`). Serves as the domain boundary for cross-domain evaluation. |
| **`Sub-product`** | `VARCHAR` | Yes | 0.01% (64 rows) | Granular product sub-category (e.g., `Conventional home mortgage`, `Checking account`, `Auto debt`). Nulls occur primarily in older legacy complaints prior to taxonomy standardization. |
| **`Issue`** | `VARCHAR` | No | 0.00% | High-level administrative issue category selected from pre-set bureau picklist. Mapped deterministically to the 16 canonical project target classes. |
| **`Sub-issue`** | `VARCHAR` | Yes | 10.86% (113,098 rows) | Detailed administrative sub-issue category providing specific nuance (e.g., `Information is incorrect`, `Investigation took too long`). Nulls indicate either broader grievances or categories without sub-issue picklists. |
| **`Consumer complaint narrative`** | `TEXT` | Yes | 57.77% (601,772 rows) | The authentic, unedited free-text grievance written by the consumer. Only present when consumer affirmatively consented to public disclosure under 80 FR 15572. **The core text modality for NLP classification.** |
| **`Company public response`** | `VARCHAR` | Yes | 47.35% (493,215 rows) | Pre-set canned response selected by the financial institution from a CFPB-approved list (e.g., `Company has responded to the consumer and CFPB and chooses not to provide a public response`). |
| **`Company`** | `VARCHAR` | No | 0.00% | The exact legal corporate entity name against which the complaint was filed, as identified and verified by CFPB intake caseworkers. |
| **`State`** | `CHAR(2)` | Yes | 2.25% (23,472 rows) | Two-letter US postal state or territory code (e.g., `CA`, `NY`, `TX`). Nulls indicate military addresses, non-US locations, or unprovided location metadata. |
| **`ZIP code`** | `VARCHAR` | No | 0.00% | Consumer's 5-digit ZIP code. In public FOIA exports, CFPB redacts or aggregates low-population ZIPs or substitutes placeholders to protect consumer anonymity. |
| **`Tags`** | `VARCHAR` | Yes | 88.55% (922,317 rows) | Demographic / vulnerable population indicators. Allowed values: `Older American`, `Servicemember`, `Older American, Servicemember`. Null indicates a general consumer not meeting special cohort criteria. |
| **`Submitted via`** | `VARCHAR` | No | 0.00% | Intake channel through which complaint was delivered (`Web`, `Referral`, `Phone`, `Postal mail`, `Fax`, `Email`). |
| **`Date sent to company`** | `DATE` (`YYYY-MM-DD`) | No | 0.00% | Calendar date when CFPB routed the complaint to the financial company for investigation and statutory response. |
| **`Company response to consumer`** | `VARCHAR` | No | 0.00% | Formal case disposition reported by the company (`Closed with explanation`, `Closed with monetary relief`, `Closed with non-monetary relief`, `Untimely response`, `In progress`). |
| **`Timely response?`** | `CHAR(3)` (`Yes`/`No`) | No | 0.00% | Bureau compliance tracking metric indicating whether company provided response within the statutory 15-day SLA. |
| **`Complaint ID`** | `INT` / `VARCHAR` | No | 0.00% | Unique deterministic sequential integer primary key assigned by the CFPB complaint tracking database upon ingestion. |

---

## 3. Historical, Deprecated, and Bulk-Feed Field Variations

### 3.1 The 2026 Narrative Deprecation in Active Bulk Feeds
* In the live active daily export (`complaints.csv.zip`), **`Consumer complaint narrative` was dropped completely** following the CFPB's August 14, 2026 policy decision.
* Consequently, the active bulk feed contains only **15 columns**, omitting column 6.
* Any pipeline expecting 16 columns will fail if run against modern bulk feeds unless the schema adapter in `src/data/parser.py` is utilized.

### 3.2 Historical Retired Field: `Consumer disputed?`
* Present in historical pre-2017 CFPB database exports.
* Captured whether the consumer filed a formal administrative objection to the company's resolution.
* Formally retired by the CFPB in April 2017 when the bureau updated its consumer response workflow; not present in the reference baseline `CCDB_Export_2` (May 2018–April 2021).

### 3.3 Intake Field: `Consumer consent provided?`
* Appears in certain API endpoints and web portal exports (`Consent provided`, `Consent not provided`, `Consent withdrawn`, `Other`).
* In the static FOIA Reading Room archives, this column is omitted because the FOIA release itself is conditioned on affirmative consent; records lacking consent omit narrative text, reflected by null values in `Consumer complaint narrative`.

---

## 4. Auxiliary Benchmark Semantics: `PolyAI/banking77`

The auxiliary `PolyAI/banking77` dataset is maintained in `data/raw/banking77/` as an out-of-domain, fine-grained customer query benchmark.

| Field Name | Type | Nullable? | Semantic Purpose |
| :--- | :---: | :---: | :--- |
| **`text`** | `TEXT` | No (0 nulls) | Short single-turn customer service query (e.g., *"How do I activate my card?"*). Median length is 12 words. |
| **`category`** | `VARCHAR` | No (0 nulls) | Exact single-intent label from 77 distinct banking service intent classes (e.g., `card_arrival`, `exchange_rate`, `lost_or_stolen_card`). |

### Invariant Policy on Auxiliary Benchmark:
1. **Strict Partition Isolation:** `banking77` data must never be mixed into CFPB training or validation sets.
2. **Evaluation Purpose Only:** Serves exclusively as an out-of-domain benchmark to evaluate model transfer from noisy multi-paragraph complaints to concise single-turn customer service queries.

---

## 5. Missingness, Nullability, and Imputation Policies

1. **Consumer Narrative Missingness ($57.77\%$):**
   - **Informative Non-Missingness:** The absence of a narrative indicates that the consumer either opted out of public narrative sharing or submitted via a channel without narrative capture.
   - **Filter Policy:** For text-based complaint understanding, rows where `Consumer complaint narrative` is null or empty are excluded from model training/evaluation, and logged to `data/manifests/exclusion_log.csv`. No synthetic imputation (e.g. replacing with empty string or synthetic text) is permitted.
2. **Sub-Product ($0.01\%$) and Sub-Issue ($10.86\%$):**
   - Retained as empty strings `""` when absent; fallback rules in `configs/product_canonical.json` and `configs/taxonomy.json` map from high-level `Product` and `Issue` if sub-fields are empty.
3. **Tags ($88.55\%$):**
   - Null values indicate general non-vulnerable consumer cohort. Stored as empty string `""` without imputation.
4. **Company Public Response ($47.35\%$):**
   - Null values indicate the company declined to provide an optional public comment. Stored as empty string `""`.
