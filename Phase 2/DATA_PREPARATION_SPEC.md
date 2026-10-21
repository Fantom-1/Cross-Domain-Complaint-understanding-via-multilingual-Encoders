# Data Preparation Specification — Carry-Forward and Corrective Addendum

Use the existing repository's `DATA_PREPARATION_SPEC.md` as the canonical data-schema/processing specification, but obey the corrections in `PHASE_A_REVIEW_FINDINGS.md` and `DATA_RELEASE_GATE.md`. The current processed release is not to be overwritten.

## Required decisions and invariants
- Preserve raw source files and original labels; retain original and normalized text separately.
- Preserve the canonical schema already documented in the repository: `example_id`, `text_original`, `text_normalized`, `intent_label`, `intent_id`, `source_label`, `parent_label`, `domain`, `language_condition`, `source_dataset`, `source_version`, `source_id`, `group_id`, `split`, `mapping_status`, `exclusion_reason`, `source_file_sha256`, `text_hash`.
- Use a project taxonomy only after source mapping/rule behavior is audited. Source category-to-project-label mapping is weak supervision, not gold human annotation unless a documented human review exists.
- Keep BANKING77 auxiliary-only. Do not merge query benchmark classes into CFPB complaint labels.
- Report reservoir sampling exclusions as their own category.
- Verify source file hashes and processed data hashes; split manifest must match CSV example IDs/labels/groups row-for-row.
- No `group_id` may cross train/validation/test.
- Existing visible split is in-distribution only. Do not call it held-out-domain evaluation.
- If a decision changes rows, groups, labels or split assignments, write a new data-release version and keep the old one.
- Dataset reports must note English-only language support and class-capping limitations.
