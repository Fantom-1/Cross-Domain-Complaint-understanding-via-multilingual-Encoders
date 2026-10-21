# Source Guide — Verify Before Acquisition

URLs below are starting points. At execution time verify the current revision, configuration, actual license/terms, download file, fields, release date and checksum. A hosted copy is not proof of a particular license or version.

## 1. CFPB Consumer Complaint Database — primary candidate
Official portal: https://www.consumerfinance.gov/data-research/consumer-complaints/  
Narratives archive: https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/  
API/release notes: https://cfpb.github.io/api/ccdb/release-notes.html

Likely fields vary by export and release: complaint ID, product, sub-product, issue, sub-issue, narrative, company, dates and response metadata. Verify the exact schema. CFPB documents historical changes to category wording and exported fields. Inspect narrative availability, source taxonomy, nulls, lengths, duplicates, PII and metadata leakage. Product/issue/sub-issue may represent different taxonomy levels; do not conflate them. Narratives are a subset of complaints and do not represent all consumers. Record the exact snapshot. Candidate for an English financial complaint baseline; not evidence of Hindi/Hinglish coverage.

## 2. BANKING77 — auxiliary intent data
Dataset card: https://huggingface.co/datasets/PolyAI/banking77  
Paper: https://arxiv.org/abs/2003.04807

Published benchmark description: 77 banking intent classes; often reported as 13,083 examples (10,003 train / 3,080 test). These are reference figures only: inspect the downloaded revision/configuration and compute actual counts. Audit text/label fields, original split, license, intent definitions, complaint-vs-query semantics and cross-split duplicates. Preserve the original 77-way labels. Do not merge with CFPB categories without reviewed semantic mapping.

## 3. MASSIVE — multilingual assistant NLU, not complaints by default
Paper: https://aclanthology.org/2023.acl-long.235/  
Dataset card: https://huggingface.co/datasets/AmazonScience/massive

Published description: about one million virtual-assistant utterances across 51 languages with intent and slot annotations, localized from English SLURP. Inspect revision/config, language codes, utterance, intent, slots, split and parallel-example leakage. Do not merge into complaint training by default; it does not establish real multilingual complaint coverage.

## 4. MUTANT — Hindi-English code-mixed resource
Resource page: https://lingo.iitgn.ac.in/codemixing/

The resource page describes MUTANT as multi-sentential Hindi-English code-mixed text sourced from political speeches, press releases and Hindi news. Verify exact linked paper citation, repository, license and task. Do not use a guessed paper URL. Not complaint-intent data by default.

## 5. COMI-LINGUA — code-mixing annotation resource
Paper: https://aclanthology.org/2025.findings-emnlp.422/  
Repository: https://github.com/lingo-iitgn/COMI-LINGUA  
Resource page: https://lingo.iitgn.ac.in/codemixing/

Supports language identification, matrix-language identification, NER, POS and machine translation across Hindi-English code-mixing and Roman/Devanagari scripts. Repository describes 181,463 instances and CC BY 4.0; verify the current revision, per-task files and license. Use for language/script diagnostics or a separately approved task, not complaint-intent labels.

## 6. Project-annotated complaints
If no source supports genuine Hindi/Hinglish complaint evaluation, report that gap. Any future collection needs documented provenance/rights/consent, annotation guidelines, qualified annotators, adjudication, agreement analysis where feasible, privacy review and leakage-safe groups. Do not generate or translate examples and call them naturally occurring complaints.

## Eligibility labels
For every source and, where needed, each record, use `primary_eligible`, `auxiliary_only`, `needs_review`, or `excluded`, with rationale and evidence. Selection is based on task semantics, not convenience.
