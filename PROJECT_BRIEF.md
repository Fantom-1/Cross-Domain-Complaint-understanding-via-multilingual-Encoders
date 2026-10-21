# Project Brief

**Title:** Cross-Domain Complaint Understanding via Multilingual Encoders.

**Question:** How well does a standard supervised multilingual encoder classify complaint intent, and how does performance vary across domains and language conditions when evaluation data are separated appropriately?

**Current scope:** data acquisition/preparation first, then standard supervised fine-tuning of `facebook/xlm-v-base` with a sequence-classification head. Primary metric: Macro-F1. Secondary: accuracy, per-class precision/recall/F1, confusion matrix, and domain/language breakdowns where sample support permits.

**Candidate sources and roles**
- CFPB Consumer Complaint Database: primary candidate for real English financial complaint narratives.
- BANKING77: banking customer-service query intents; not necessarily complaints.
- MASSIVE: multilingual virtual-assistant NLU utterances; not complaint narratives by default.
- MUTANT and COMI-LINGUA: code-mixing/language resources, not complaint-intent datasets by default.
- Project-annotated complaints: potentially needed for genuine Hindi/Hinglish complaint evaluation; annotation must be real, documented and human-reviewed.

These sources do not automatically form a coherent multilingual complaint dataset. The audit may validly conclude that the current evidence supports only an English financial-complaint baseline. Do not distort the data to maintain a broader claim.

A closed-set classifier cannot predict a label absent from training. Held-out-domain evaluation must retain shared labels and prevent related examples crossing splits. The model does not detect fraud, judge complaint validity, predict resolution, or establish causality.

Expected outputs: reproducible data pipeline; source inventory; taxonomy/mapping; dataset card; split manifests and tests; later baseline code/checkpoint/logs/metrics/predictions/error analysis and limitations.
