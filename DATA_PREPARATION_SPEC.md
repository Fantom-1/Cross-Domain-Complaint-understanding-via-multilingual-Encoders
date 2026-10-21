# Data Preparation Specification

## Workflow
Inspect repository -> verify sources/terms -> inventory/checksum -> profile schemas and examples -> define taxonomy -> review source mappings -> conservative cleaning -> privacy/duplicate/leakage audit -> eligibility decision -> split design -> manifests and tests -> dataset card/readiness report -> user approval.

## Canonical schema
At minimum:
`example_id`, `text_original`, `text_normalized`, `intent_label`, `intent_id`, `source_label`, `parent_label`, `domain`, `language_condition`, `source_dataset`, `source_version`, `source_id`, `group_id`, `split`, `mapping_status`, `exclusion_reason`, `source_file_sha256`, `text_hash`.

Keep useful source-specific metadata in canonical data or linked tables. Use stable unique IDs. Language condition may include `en`, `hi_devanagari`, `hinglish_roman`, `hinglish_devanagari`, `other`, `unknown`; apply only when justified by inspection, not by source name.

## Inventory manifest
`data/manifests/dataset_inventory.csv` fields:
`source_dataset,source_url,local_path,file_name,file_format,source_version,release_date,retrieval_date,license,license_url,checksum_sha256,rows,columns,split,language,domain,role_decision,decision_rationale,status,notes`.
Use `unknown`/`needs_verification` rather than guessing. Prefer one row per file/config.

## Source-label mapping
`data/manifests/source_label_mapping.csv`:
`source_dataset,source_label,source_label_definition,project_intent_label,mapping_status,rationale,evidence_url,reviewer,review_date,notes`.
Preserve original labels. Mapping requires semantic equivalence. Ambiguous or multi-intent categories remain `ambiguous`/`needs_review`. Do not label text automatically with an LLM without explicit approval and human review.

## Conservative normalization
- Decode with correct encoding; log errors.
- Normalize Unicode consistently (e.g. NFC), line endings and safe whitespace.
- Keep original text separate.
- Preserve negation, numbers, meaningful punctuation, names, Hindi script, Romanized Hindi, code-switching and spelling variation.
- Do not translate, transliterate, spell-correct, remove stopwords, stem or lemmatize by default.
- Do not strip digits/punctuation blindly.
- Keep a reproducible config and record every transformation.

## Audits
Profile null/empty/short/long text; malformed encoding; class counts and label conflicts; exact/near duplicates; cross-source duplicates; repeated IDs; translations/parallel data; language/script/domain coverage; possible PII; target-leaking metadata. Do not dump full sensitive narratives into logs. Redaction does not guarantee all PII is removed.

## Taxonomy
Create `docs/label_taxonomy.md`. For each label document stable name, definition, inclusions/exclusions, reviewed examples, confusable labels, source mappings, evidence, reviewer and status. Derive from actual source labels/examples; do not invent a taxonomy before auditing.

## Splits
Use separate manifests per experiment, keyed by `experiment_id`.
1. **In-distribution:** group related examples first; fixed seed; stratify where feasible; train fits, validation selects, test stays untouched. Report class support. Resolve rare-class issues before training.
2. **Held-out domain:** choose target domain from actual data; target test excluded from training/validation; test labels must exist in train label map; group leakage prohibited. Do not tune on target test. If domain and label are confounded or overlap is insufficient, report unsupported.
Manifest fields: `experiment_id,example_id,split,group_id,source_dataset,domain,language_condition,intent_label,split_seed,split_policy_version`.

## Required outputs
`data/raw/` immutable source data or documented references; `data/interim/`; `data/processed/canonical_dataset.parquet` or documented alternative; `baseline_train.csv`, `baseline_validation.csv`, `baseline_test.csv`, `label_map.json`; manifests for inventory, source-label mapping, splits, exclusions, duplicate groups, checksums; docs for repository audit, dataset card, taxonomy, methodology and readiness; scripts under `src/data/`; tests under `tests/data/`.

Training CSV minimum: `example_id,text,label,intent_id,domain,language_condition,source_dataset,group_id`. Do not produce training-ready CSVs before the taxonomy and experiment design are approved.

## Tests
Required columns/types; unique IDs; nonempty text; approved labels only; one-to-one label-ID mapping; validation/test labels exist in train; split exclusivity; no group leakage; exact count reconciliation; deterministic output; provenance/checksums; no unexpected raw-file modification. Fail loudly; don't weaken tests to hide failures.
