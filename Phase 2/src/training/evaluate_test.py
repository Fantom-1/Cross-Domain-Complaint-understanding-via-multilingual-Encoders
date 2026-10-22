"""Standalone test-set evaluation script for the selected baseline checkpoint.
Loads the chosen model and evaluates strictly on the frozen baseline_test.csv.
Outputs:
  - metrics.json
  - test_predictions.csv
  - per_class_metrics.csv
  - confusion_matrix.csv
  - error_analysis.json
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

def evaluate_test(model_path: Path, data_dir: Path, out_dir: Path, batch_size: int = 32):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load label map
    label_map_path = data_dir / "label_map.json"
    with open(label_map_path, "r", encoding="utf-8") as f:
        label_map = json.load(f)
    num_labels = len(label_map)
    id_to_label = {int(v): str(k) for k, v in label_map.items()}

    # 2. Load test data
    test_path = data_dir / "baseline_test.csv"
    test_df = pd.read_csv(test_path, keep_default_na=False)
    print(f"Loaded {len(test_df)} test samples from {test_path}")

    # 3. Load Model & Tokenizer
    print(f"Loading model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path), trust_remote_code=False)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda().to(torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32)

    # 4. Predict in batches
    texts = test_df["text"].tolist()
    all_preds = []
    all_probs = []

    print("Running batch prediction on test set...")
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            inputs = tokenizer(batch_texts, return_tensors="pt", truncation=True, max_length=128, padding=True)
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            logits = model(**inputs).logits
            probs = torch.softmax(logits.float(), dim=-1).cpu().numpy()
            preds = np.argmax(probs, axis=-1)
            all_preds.extend(preds)
            all_probs.extend(probs)

    gold_ids = test_df["intent_id"].to_numpy(dtype=int)
    pred_ids = np.array(all_preds, dtype=int)
    confidences = np.array([p[pred] for p, pred in zip(all_probs, pred_ids)])

    # 5. Metrics calculation
    macro_f1 = float(f1_score(gold_ids, pred_ids, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(gold_ids, pred_ids, average="weighted", zero_division=0))
    acc = float(accuracy_score(gold_ids, pred_ids))

    print(f"Test Accuracy: {acc:.4f}")
    print(f"Test Macro-F1: {macro_f1:.4f}")
    print(f"Test Weighted-F1: {weighted_f1:.4f}")

    # 6. Save Predictions CSV
    preds_df = pd.DataFrame({
        "example_id": test_df["example_id"].astype(str),
        "text_preview": test_df["text"].astype(str).str.slice(0, 100),
        "gold_intent_id": gold_ids,
        "gold_label": [id_to_label[i] for i in gold_ids],
        "predicted_intent_id": pred_ids,
        "predicted_label": [id_to_label[i] for i in pred_ids],
        "confidence": confidences,
        "correct": pred_ids == gold_ids
    })
    preds_df.to_csv(out_dir / "test_predictions.csv", index=False)

    # 7. Classification Report / Per-Class Metrics
    rep_dict = classification_report(
        gold_ids, pred_ids,
        labels=list(range(num_labels)),
        target_names=[id_to_label[i] for i in range(num_labels)],
        output_dict=True,
        zero_division=0
    )
    pd.DataFrame(rep_dict).T.to_csv(out_dir / "per_class_metrics.csv")

    # 8. Confusion Matrix
    cm = confusion_matrix(gold_ids, pred_ids, labels=list(range(num_labels)))
    cm_df = pd.DataFrame(cm, index=[id_to_label[i] for i in range(num_labels)],
                         columns=[id_to_label[i] for i in range(num_labels)])
    cm_df.to_csv(out_dir / "confusion_matrix.csv")

    # 9. Top Confusions / Error Analysis
    confusions = []
    for i in range(num_labels):
        for j in range(num_labels):
            if i != j and cm[i, j] > 0:
                confusions.append({
                    "gold": id_to_label[i],
                    "predicted": id_to_label[j],
                    "count": int(cm[i, j])
                })
    confusions = sorted(confusions, key=lambda x: x["count"], reverse=True)

    summary = {
        "test_macro_f1": macro_f1,
        "test_weighted_f1": weighted_f1,
        "test_accuracy": acc,
        "num_test_samples": len(test_df),
        "num_classes": num_labels,
        "top_confusions": confusions[:10]
    }
    with open(out_dir / "test_metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Test evaluation finished successfully!")
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--data-dir", default="/apps/cdcu/data/processed")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    evaluate_test(Path(args.model_path), Path(args.data_dir), Path(args.out_dir))
