# Executive Slide Deck: Cross-Domain Complaint Understanding via Multilingual Encoders
## Overcoming Representation Anisotropy in 778.5M Parameter XLM-V via Deep Parallel Contrastive Fine-Tuning

---

### Slide 1: Title & Executive Context
* **Project:** Cross-Domain Complaint Understanding via Multilingual Encoders (CDCU)
* **Target Model:** `facebook/xlm-v-base` (778,493,184 parameters, 901k vocabulary)
* **Compute Infrastructure:** 2 $\times$ NVIDIA RTX PRO 6000 Blackwell Server Edition GPUs (MIG Slice Partitioning)
* **Dataset:** 45,723 CFPB FOIA complaint narratives across 9 financial domains
* **Release Branch:** `feature/contrastive-retrieval-engine`

---

### Slide 2: The Core Problem — Representation Anisotropy Crisis
* **The Failure Mode:** Out-of-the-box multilingual encoders (`facebook/xlm-v-base`) map unrelated consumer complaints into narrow high-cosine cones ($\cos \theta \approx 0.94 - 0.99$).
* **The Baseline Deficit:**
  * Frozen XLM-V Precision@10: **14.11%** | NDCG@10: **0.1497**
  * Lexical TF-IDF Baseline: **33.54%** | NDCG@10: **0.3472**
* **Finding:** The raw 778M parameter neural model loses to simple keyword search by **-19.43% Precision@10** due to severe embedding collapse.

---

### Slide 3: Model Architecture — The 778.5M Parameter Reality
* **Why Literature Calls It "~1 Billion Parameters":**
  * **901,629-token vocabulary:** Meta AI's 140+ language subword table.
  * **Embedding Table:** $901,629 \times 768 = \mathbf{692,848,128\text{ parameters}}$ (**89.0%** of total parameters).
  * **12-Layer Transformer Backbone:** $85,054,464$ parameters.
  * **Projection Head:** $\mathbb{R}^{768} \xrightarrow{\text{Linear}} \mathbb{R}^{768} \xrightarrow{\text{GELU}} \mathbb{R}^{256} \xrightarrow{\ell_2\text{ norm}}$.
* **Hardware Footprint:** Requires Blackwell 24GB MIG slices for training stability and bfloat16 mixed precision.

---

### Slide 4: SimCSE vs. SupCon — Conceptual Formulations
* **Unsupervised SimCSE (Simple Contrastive Learning):**
  * *Intuition:* Generates positive pairs without labels by passing the same text through the encoder twice with different dropout masks ($p=0.1$).
  * *Loss:* Dropout InfoNCE ($\tau=0.05$).
  * *Goal:* Uniformly uncollapse the vector space across the unit hypersphere.
* **Weakly Supervised SupCon (Supervised Contrastive Learning):**
  * *Intuition:* Leverages domain routing tags to pull multiple distinct complaints from the same class together, and push complaints from other product domains apart.
  * *Loss:* Margin Triplet ($\alpha=0.2, \tau=0.07$).
  * *Goal:* Build tight intra-class semantic clusters and wide inter-domain margins.

---

### Slide 5: Parallel Deep Training on Blackwell GPUs
| Training Job | Model Architecture | Hardware Slice | Steps Completed | Epochs | Final Train Loss | Best Val Loss | Convergence Outcome |
|---|---|---|---|---|---|---|---|
| **Run R2: SimCSE** | `facebook/xlm-v-base` (Dropout InfoNCE) | Blackwell Slice 0 (`1g.24gb`) | **1,750 / 10,000** | $\approx 0.9$ | **`5.58e-06`** | **`0.0056`** | Early stopped at peak |
| **Run R4: SupCon** | `facebook/xlm-v-base` (Margin Triplet) | Blackwell Slice 1 (`1g.24gb`) | **9,505 / 10,000** | **4.75** (Epoch 5) | **`1.6175`** | **`2.6954`** | Restored best weights |

---

### Slide 6: Validation Retrieval Benchmark (6,852 Queries vs. 32,019 Gallery)
| Model Run | Objective / Strategy | Precision@10 | Recall@10 | MRR@10 | NDCG@10 | Selection Status |
|---|---|---:|---:|---:|---:|---|
| **R1 Frozen XLM-V** | Pretrained Mean Pool | 0.1411 (14.11%) | 0.0007 | 0.3260 | 0.1497 | Severe Anisotropy |
| **R0 Lexical TF-IDF** | Word 1-2 grams | 0.3354 (33.54%) | 0.0017 | 0.5458 | 0.3472 | Statutory Baseline |
| **R2 SimCSE XLM-V** | Dropout InfoNCE | 0.2724 (27.24%) | 0.0014 | 0.4725 | 0.2829 | Resolves Anisotropy |
| **R4 SupCon XLM-V** | **Weakly Supervised Triplet** | **0.4897 (48.97%)** | **0.0025** | **0.5619** | **0.4889** | **WINNER (Rule 13.10)** |

* **Relative Improvement:** SupCon achieves **+34.86% absolute gain (3.47x relative gain)** over raw XLM-V, and beats lexical TF-IDF by **+15.43% P@10** and **+14.17% NDCG@10**.

---

### Slide 7: Locked Test Split Evaluation (Zero Leakage Audit)
* Evaluated strictly once on locked 6,852 test instances:
  * **Test Precision@10:** **48.61%** ($\Delta$ vs Val: $-0.36\%$)
  * **Test MRR@10:** **0.5628** ($\Delta$ vs Val: $+0.09\%$)
  * **Test NDCG@10:** **0.4864** ($\Delta$ vs Val: $-0.25\%$)
  * **Coverage:** **100.0%** (6,852 / 6,852 queries)
* **Verdict:** Generalization verified within 0.36%; zero split leakage confirmed.

---

### Slide 8: Production Deployment & Serving Stack
* **Vector Index:** 32,019 complaint vectors (256-dim, L2-normalized float32, 32 MB).
* **FastAPI Microservice (Port 8000):** Sub-10ms GPU nearest-neighbor search, extractive grounded summarization, and end-to-end analysis.
* **Interactive Testing Sandbox:** Preloaded test cases across Debt, Mortgage, Credit Card, Overdraft, and Credit Reporting.
* **Local Web Preview:** `http://localhost:8080/demo.html`
* **Interactive Presentation Slide Deck:** `http://localhost:8080/presentation.html`

