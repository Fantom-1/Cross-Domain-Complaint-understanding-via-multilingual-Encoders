# Project Brief

## Research question
How well does a standard supervised multilingual encoder classify complaint intent, and how does performance vary by financial product domain when test records are separated from training correctly?

## Baseline
- Model: `facebook/xlm-v-base`, exact revision pinned when acquired.
- Classification: single-label multi-class.
- Model structure: XLM-V/XLM-RoBERTa-family encoder plus standard sequence classification head.
- Loss: multiclass cross entropy.
- Primary metric: Macro-F1.
- Secondary: accuracy, per-class precision/recall/F1 and support, confusion matrix, train/validation learning curves and resource report.

## Dataset scope
The public Git repository documents a CFPB-derived English complaint corpus with 16 mapped classes. It also documents BANKING77 as auxiliary-only. The raw and processed datasets are excluded from Git; they must be checked where they actually live. No validated Hindi/Hinglish complaint dataset is currently documented.

The current split described in the repository is an in-distribution split. Use it only for in-distribution baseline metrics; it does not prove held-out-domain generalization.

## Output
A reproducible baseline with an auditable data release ID, config, environment description, checkpoint/recovery instructions, validation-based trial selection, frozen test metrics, predictions by ID, error analysis and scientific limitations.
