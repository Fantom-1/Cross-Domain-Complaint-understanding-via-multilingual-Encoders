# Phase B Baseline — Architecture

## Model definition
- Checkpoint: `facebook/xlm-v-base`, pinned to an exact Hugging Face revision.
- Current model config visible on the model hub: `model_type=xlm-roberta`, vocabulary `901629`, hidden size `768`, `12` encoder layers, `12` attention heads, FFN size `3072`, maximum position embeddings `514`.
- Verify the exact config at the pinned revision. Do not hard-code the number of classes: derive K from the verified `data/processed/label_map.json`.
- Use the Transformers auto sequence-classification class supported by the pinned stack. XLM-V is a masked-language-model checkpoint, not a complaint classifier. Encoder weights should load; the task classification head is expected to be newly initialized. Verify this in load warnings and model parameter names.
- Full encoder fine-tuning + normal classification head is the baseline. Do not quietly freeze embeddings or change to PEFT/LoRA.

## Forward path
1. Text -> XLM-V tokenizer (token IDs and attention mask).
2. XLM-V/XLM-RoBERTa-family encoder produces contextual token representations.
3. The standard XLM-RoBERTa sequence-classification head uses the sequence-start representation, with dropout, dense projection/tanh, dropout and output projection.
4. Output logits of shape `[batch_size, K]`.
5. Cross-entropy against `intent_id`; validation Macro-F1 selects checkpoint.

Conceptually:
`logits = W h + b`
`p(y|x) = softmax(logits)`
`L_CE = -mean(log p(y_i|x_i))`

Input must be text only. Do not concatenate CFPB `Issue`, `Sub-issue`, or product/category fields to input because those metadata generate the target labels and would leak the answer.

## Why memory needs measurement
The embedding matrix alone is `901,629 × 768 ≈ 692M` parameters (about 2.77 GB decimal in FP32). Full fine-tuning also requires gradients, Adam states, encoder activations, CUDA context/workspace and allocator reserve. The model checkpoint file is reported around 3.12 GB, but this is not a peak-VRAM estimate.

A 24 GB MIG allocation may be workable with micro-batch 1, short sequences, BF16 where supported, gradient checkpointing and frequent checks, but this is only a hypothesis. Do not commit to a batch length or precision before a real allocated job measures it.
