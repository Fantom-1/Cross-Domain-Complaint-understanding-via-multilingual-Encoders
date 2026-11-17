"""Train and evaluate TF-IDF + Logistic Regression lexical baseline on frozen complaint splits.

Outputs full evaluation metrics (Accuracy, Macro-F1, Weighted-F1, per-class F1,
confusion matrix, top confusions, domain slices) to enable rigorous comparison
against the neural XLM-V classifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score


def evaluate_split(clf, vectorizer, df: pd.DataFrame, split_name: str, labels: list[str]) -> dict:
    X = vectorizer.transform(df["text"].fillna(""))
    y_true = df["label"].astype(str)
    y_pred = clf.predict(X)

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    per_class = {
        label: {
            "precision": float(report[label]["precision"]),
            "recall": float(report[label]["recall"]),
            "f1": float(report[label]["f1-score"]),
            "support": int(report[label]["support"]),
        }
        for label in labels if label in report
    }

    # Confusion matrix & top confusions
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    top_confusions = []
    for i, gold in enumerate(labels):
        for j, pred in enumerate(labels):
            if i != j and cm[i, j] > 0:
                top_confusions.append({"gold": gold, "predicted": pred, "count": int(cm[i, j])})
    top_confusions.sort(key=lambda x: x["count"], reverse=True)

    # Domain slices
    domain_slices = {}
    for domain, grp in df.groupby("domain"):
        y_d_true = grp["label"].astype(str)
        y_d_pred = y_pred[grp.index]
        domain_slices[str(domain)] = {
            "samples": len(grp),
            "accuracy": float(accuracy_score(y_d_true, y_d_pred)),
            "macro_f1": float(f1_score(y_d_true, y_d_pred, average="macro", zero_division=0)),
        }

    return {
        "split": split_name,
        "samples": len(df),
        "accuracy": acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "top_confusions": top_confusions[:15],
        "domain_slices": domain_slices,
        "predictions": y_pred.tolist(),
        "confusion_matrix": cm.tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", default="data/processed/baseline_train.csv")
    parser.add_argument("--val-csv", default="data/processed/baseline_validation.csv")
    parser.add_argument("--test-csv", default="data/processed/baseline_test.csv")
    parser.add_argument("--output-dir", default="Phase 2/results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-features", type=int, default=50000)
    parser.add_argument("--c", type=float, default=1.0)
    args = parser.parse_args()

    train_df = pd.read_csv(args.train_csv, keep_default_na=False)
    val_df = pd.read_csv(args.val_csv, keep_default_na=False)
    test_df = pd.read_csv(args.test_csv, keep_default_na=False)

    labels = sorted(train_df["label"].astype(str).unique())
    print(f"Loaded datasets: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}, classes={len(labels)}")

    print(f"Fitting TF-IDF Vectorizer (ngram_range=(1, 2), max_features={args.max_features})...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=args.max_features, sublinear_tf=True)
    X_train = vectorizer.fit_transform(train_df["text"].fillna(""))
    y_train = train_df["label"].astype(str)

    print(f"Training Logistic Regression (C={args.c}, max_iter=1000, random_state={args.seed})...")
    clf = LogisticRegression(C=args.c, max_iter=1000, random_state=args.seed, n_jobs=-1)
    clf.fit(X_train, y_train)

    val_res = evaluate_split(clf, vectorizer, val_df, "validation", labels)
    test_res = evaluate_split(clf, vectorizer, test_df, "test", labels)

    print(f"Validation Macro-F1: {val_res['macro_f1']:.4f} | Accuracy: {val_res['accuracy']:.4f}")
    print(f"Test Macro-F1:       {test_res['macro_f1']:.4f} | Accuracy: {test_res['accuracy']:.4f}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_summary = {
        "model": "TF-IDF + LogisticRegression",
        "vectorizer": {"max_features": args.max_features, "ngram_range": [1, 2], "sublinear_tf": True},
        "classifier": {"C": args.c, "seed": args.seed, "max_iter": 1000},
        "validation": {
            "macro_f1": val_res["macro_f1"],
            "weighted_f1": val_res["weighted_f1"],
            "accuracy": val_res["accuracy"],
            "samples": val_res["samples"],
        },
        "test": {
            "macro_f1": test_res["macro_f1"],
            "weighted_f1": test_res["weighted_f1"],
            "accuracy": test_res["accuracy"],
            "samples": test_res["samples"],
        },
        "test_top_confusions": test_res["top_confusions"],
        "test_domain_slices": test_res["domain_slices"],
    }

    metrics_path = out_dir / "lexical_baseline_metrics.json"
    metrics_path.write_text(json.dumps(metrics_summary, indent=2) + "\n", encoding="utf-8")
    print(f"Saved lexical metrics to {metrics_path}")

    # Save per-class metrics CSV
    rows = []
    for lbl, data in test_res["per_class"].items():
        rows.append({"intent_label": lbl, **data})
    per_class_df = pd.DataFrame(rows)
    per_class_path = out_dir / "lexical_per_class_metrics.csv"
    per_class_df.to_csv(per_class_path, index=False)
    print(f"Saved per-class CSV to {per_class_path}")

    # Save predictions
    preds_df = pd.DataFrame({
        "example_id": test_df["example_id"],
        "gold_label": test_df["label"],
        "predicted_label": test_res["predictions"],
        "domain": test_df["domain"],
    })
    preds_path = out_dir / "lexical_test_predictions.csv"
    preds_df.to_csv(preds_path, index=False)
    print(f"Saved predictions to {preds_path}")


if __name__ == "__main__":
    main()

