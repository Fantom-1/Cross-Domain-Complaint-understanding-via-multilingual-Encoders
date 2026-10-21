"""Standard supervised XLM-V baseline trainer.

Safety:
- Does not install packages or change the host.
- Requires a verified frozen data release and non-null config.
- Never tunes on test: model selection uses validation Macro-F1 only.
- Writes only to the supplied, new run directory.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    set_seed,
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def project_root() -> Path:
    # src/training/train_baseline.py -> repository root
    return Path(__file__).resolve().parents[2]


def resolve(root: Path, value: str | Path) -> Path:
    p = Path(value)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def require_not_null(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            require_not_null(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            require_not_null(value, f"{path}[{i}]")
    elif obj is None:
        raise ValueError(f"Required config value is null: {path}")


def read_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("YAML config must contain a mapping at top level")
    require_not_null(cfg)
    return cfg


def verify_checksums(root: Path, manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Required checksum manifest not found: {manifest_path}. "
            "Create and review data/manifests/checksums.csv before training."
        )
    manifest = pd.read_csv(manifest_path, dtype=str).fillna("")
    path_col = next((c for c in ("path", "local_path", "file_path") if c in manifest.columns), None)
    hash_col = next((c for c in ("sha256", "checksum_sha256", "file_sha256") if c in manifest.columns), None)
    if not path_col or not hash_col:
        raise ValueError("checksums.csv must have path/local_path/file_path and sha256/checksum_sha256/file_sha256 columns")
    verified = []
    for row in manifest.to_dict("records"):
        rel = row[path_col].strip()
        expected = row[hash_col].strip().lower()
        if not rel or not expected:
            continue
        p = resolve(root, rel)
        if not p.is_file():
            raise FileNotFoundError(f"Checksum-manifest file does not exist: {p}")
        actual = sha256_file(p)
        if actual.lower() != expected:
            raise ValueError(f"SHA-256 mismatch for {p}: expected {expected}, observed {actual}")
        verified.append({"path": str(p), "sha256": actual, "bytes": p.stat().st_size})
    if not verified:
        raise ValueError("No files were verified from checksums.csv")
    return verified


def load_and_validate_data(cfg: dict, root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict, list[dict]]:
    dcfg = cfg["data"]
    train_path = resolve(root, dcfg["train_csv"])
    val_path = resolve(root, dcfg["validation_csv"])
    test_path = resolve(root, dcfg["test_csv"])
    label_path = resolve(root, dcfg["label_map"])
    manifest_path = resolve(root, dcfg["split_manifest"])
    checksums_path = resolve(root, dcfg["checksums_manifest"])

    verified_hashes = verify_checksums(root, checksums_path)
    for path in (train_path, val_path, test_path, label_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required data artefact missing: {path}")

    train = pd.read_csv(train_path, keep_default_na=False)
    val = pd.read_csv(val_path, keep_default_na=False)
    test = pd.read_csv(test_path, keep_default_na=False)
    with label_path.open("r", encoding="utf-8") as f:
        label_map = json.load(f)
    if not isinstance(label_map, dict) or not label_map:
        raise ValueError("label_map.json must map string labels to integer IDs")
    label_map = {str(k): int(v) for k, v in label_map.items()}
    ids = sorted(label_map.values())
    if ids != list(range(len(ids))) or len(ids) != len(set(ids)):
        raise ValueError(f"Label IDs must be unique contiguous 0..K-1; observed {ids}")

    required = {"example_id", "text", "label", "intent_id", "group_id"}
    for name, frame in (("train", train), ("validation", val), ("test", test)):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} CSV lacks required columns: {sorted(missing)}")
        if frame["example_id"].duplicated().any():
            raise ValueError(f"{name} has duplicate example_id values")
        if frame["text"].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name} contains empty model text")
        frame["intent_id"] = pd.to_numeric(frame["intent_id"], errors="raise").astype(int)
        if not set(frame["label"]).issubset(label_map):
            raise ValueError(f"{name} contains labels absent from label_map.json")
        expected_ids = frame["label"].map(label_map)
        if not np.array_equal(expected_ids.to_numpy(), frame["intent_id"].to_numpy()):
            raise ValueError(f"{name} label and intent_id columns disagree")

    split_ids = [set(x["example_id"]) for x in (train, val, test)]
    if split_ids[0] & split_ids[1] or split_ids[0] & split_ids[2] or split_ids[1] & split_ids[2]:
        raise ValueError("example_id leakage across train/validation/test")
    split_groups = [set(x["group_id"]) for x in (train, val, test)]
    if split_groups[0] & split_groups[1] or split_groups[0] & split_groups[2] or split_groups[1] & split_groups[2]:
        raise ValueError("group_id leakage across train/validation/test")
    train_labels = set(train["intent_id"])
    if not set(val["intent_id"]).issubset(train_labels) or not set(test["intent_id"]).issubset(train_labels):
        raise ValueError("Validation/test contains label ID not present in training")

    manifest = pd.read_csv(manifest_path, keep_default_na=False)
    manifest_required = {"example_id", "split"}
    if not manifest_required.issubset(manifest.columns):
        raise ValueError(f"Split manifest needs columns {sorted(manifest_required)}")
    if manifest["example_id"].duplicated().any():
        raise ValueError("Split manifest has duplicated example_id")
    split_col = dcfg.get("split_manifest_split_column", "split")
    for name, frame in (("train", train), ("validation", val), ("test", test)):
        manifest_part = manifest.loc[manifest[split_col].eq(name), "example_id"]
        if set(manifest_part) != set(frame["example_id"]):
            raise ValueError(f"{name} example IDs do not exactly match the frozen split manifest")
    return train, val, test, label_map, verified_hashes


def to_hf_dataset(frame: pd.DataFrame, tokenizer, max_length: int, num_proc: int = 1) -> Dataset:
    source = Dataset.from_dict({
        "text": frame["text"].astype(str).tolist(),
        "labels": frame["intent_id"].astype(int).tolist(),
    })

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    tokenized = source.map(
        tokenize,
        batched=True,
        remove_columns=["text"],
        num_proc=max(1, int(num_proc)),
        desc="Tokenizing",
    )
    return tokenized


def compute_metrics(eval_pred, num_labels: int) -> dict:
    pred_logits = eval_pred.predictions
    if isinstance(pred_logits, tuple):
        pred_logits = pred_logits[0]
    y_pred = np.argmax(pred_logits, axis=-1)
    y_true = eval_pred.label_ids
    return {
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", labels=list(range(num_labels)), zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def training_args_compat(**kwargs) -> TrainingArguments:
    # Accommodate Transformers releases that renamed evaluation_strategy to eval_strategy.
    sig = inspect.signature(TrainingArguments.__init__)
    if "eval_strategy" in sig.parameters:
        kwargs["eval_strategy"] = kwargs.pop("evaluation_strategy")
    return TrainingArguments(**kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument("--evaluate-test", action="store_true", help="Use only for the final locked run; leave off during tuning trials.")
    args = parser.parse_args()

    root = project_root()
    config_path = resolve(root, args.config)
    run_dir = resolve(root, args.run_dir)
    allowed_roots = [root]
    configured_output_root = os.environ.get("PROJECT_ALLOWED_OUTPUT_ROOT", "").strip()
    if configured_output_root:
        allowed_roots.append(Path(configured_output_root).resolve())
    is_allowed = any(run_dir == allowed or allowed in run_dir.parents for allowed in allowed_roots)
    if not is_allowed or run_dir == Path("/"):
        raise ValueError(
            f"run-dir must be inside the repository or PROJECT_ALLOWED_OUTPUT_ROOT "
            f"(a verified user-owned output directory): {run_dir}"
        )
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    cfg = read_config(config_path)

    # Never overwrite an existing run. The caller may precreate an empty run directory.
    if run_dir.exists():
        existing = list(run_dir.iterdir())
        allowed = {".keep", "job_metadata.txt", "runtime_device_report.txt"}
        unexpected = [p.name for p in existing if p.name not in allowed]
        if unexpected and not args.resume_from_checkpoint:
            raise FileExistsError(f"Run directory is not empty; refusing overwrite: {unexpected}")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)

    mcfg, dcfg, scfg, tcfg = cfg["model"], cfg["data"], cfg["sequence"], cfg["training"]
    learning_rate = float(args.learning_rate if args.learning_rate is not None else tcfg["learning_rate_candidates"][0])
    max_length = int(args.max_length if args.max_length is not None else scfg["initial_max_length"])
    epochs = float(args.epochs if args.epochs is not None else tcfg["max_tuning_epochs"])
    if max_length < 8 or max_length > 512:
        raise ValueError("max_length must be 8..512 (verify against the pinned model config)")
    if learning_rate <= 0 or epochs <= 0:
        raise ValueError("learning rate and epochs must be positive")

    train_df, val_df, test_df, label_map, hashes = load_and_validate_data(cfg, root)
    num_labels = len(label_map)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not visible. Do not silently run a cluster training job on CPU.")
    device_name = torch.cuda.get_device_name(0)
    precision = str(tcfg["precision"]).lower()
    if precision == "bf16" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Config requests BF16 but this allocated GPU/PyTorch combination reports no BF16 support.")
    if precision not in {"bf16", "fp16", "fp32"}:
        raise ValueError("training.precision must be bf16, fp16, or fp32 after GPU preflight")

    set_seed(int(tcfg["tuning_seed"]))
    model_name = mcfg["name"]
    revision = mcfg["revision"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_name, revision=revision, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        revision=revision,
        num_labels=num_labels,
        label2id=label_map,
        id2label={int(v): str(k) for k, v in label_map.items()},
        trust_remote_code=False,
    )
    model.config.use_cache = False
    if bool(tcfg["gradient_checkpointing"]):
        model.gradient_checkpointing_enable()
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()

    train_ds = to_hf_dataset(train_df, tokenizer, max_length, tcfg["num_workers"])
    val_ds = to_hf_dataset(val_df, tokenizer, max_length, tcfg["num_workers"])
    # The test set is not tokenized or evaluated during tuning unless explicitly requested for a locked final run.
    collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8 if precision in {"bf16", "fp16"} else None)

    trainer_output = run_dir / "trainer_output"
    if trainer_output.exists() and not args.resume_from_checkpoint:
        raise FileExistsError(f"Trainer output already exists: {trainer_output}")
    trainer_output.mkdir(parents=True, exist_ok=True)

    # Use step-based evaluation/checkpoints; use the same cadence as required by HF Trainer.
    eval_steps = int(tcfg["eval_save_steps"])
    kwargs = dict(
        output_dir=str(trainer_output),
        learning_rate=learning_rate,
        num_train_epochs=epochs,
        per_device_train_batch_size=int(tcfg.get("micro_batch", tcfg.get("initial_micro_batch"))),
        per_device_eval_batch_size=int(tcfg["eval_batch_size"]),
        gradient_accumulation_steps=int(tcfg.get("gradient_accumulation_steps") or 1),
        weight_decay=float(tcfg["weight_decay"]),
        warmup_ratio=float(tcfg["warmup_ratio"]),
        max_grad_norm=float(tcfg["max_grad_norm"]),
        eval_steps=eval_steps,
        save_steps=eval_steps,
        logging_steps=int(tcfg["logging_steps"]),
        logging_strategy="steps",
        evaluation_strategy="steps",
        save_strategy="steps",
        save_total_limit=int(tcfg["save_total_limit"]),
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        gradient_checkpointing=bool(tcfg["gradient_checkpointing"]),
        bf16=(precision == "bf16"),
        fp16=(precision == "fp16"),
        dataloader_num_workers=int(tcfg["num_workers"]),
        report_to=[],
        seed=int(tcfg["tuning_seed"]),
        data_seed=int(tcfg["tuning_seed"]),
        optim="adamw_torch",
        remove_unused_columns=True,
        save_safetensors=True,
    )
    training_args = training_args_compat(**kwargs)
    trainer_kwargs = dict(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        compute_metrics=lambda pred: compute_metrics(pred, num_labels),
    )
    trainer_init_params = inspect.signature(Trainer.__init__).parameters
    if "processing_class" in trainer_init_params:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_init_params:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = Trainer(**trainer_kwargs)

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": device_name,
        "gpu_visible_count": torch.cuda.device_count(),
        "bf16_supported": torch.cuda.is_bf16_supported(),
        "peak_vram_before_train_bytes": 0,
        "learning_rate": learning_rate,
        "max_length": max_length,
        "epochs": epochs,
        "num_labels": num_labels,
        "label_map": label_map,
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "data_file_hashes_verified": hashes,
        "rows": {"train": len(train_df), "validation": len(val_df), "test": len(test_df)},
        "model_name": model_name,
        "model_revision": revision,
    }
    with (run_dir / "environment.json").open("w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)

    torch.cuda.reset_peak_memory_stats()
    train_result = trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(str(run_dir / "final_model"))
    tokenizer.save_pretrained(str(run_dir / "final_model"))

    # Validation metrics from the trainer's selected checkpoint are the tuning criterion.
    val_metrics = trainer.evaluate(val_ds, metric_key_prefix="validation")
    id_to_label = {int(v): str(k) for k, v in label_map.items()}
    summary = {
        "train": train_result.metrics,
        "validation": val_metrics,
        "test_evaluated": bool(args.evaluate_test),
        "peak_vram_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_vram_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        "gpu_name": device_name,
        "rows": {"train": len(train_df), "validation": len(val_df), "test": len(test_df)},
        "config_sha256": sha256_file(config_path),
    }

    if args.evaluate_test:
        # This flag is only for a final locked run, never for tuning trials.
        test_ds = to_hf_dataset(test_df, tokenizer, max_length, tcfg["num_workers"])
        test_result = trainer.predict(test_ds, metric_key_prefix="test")
        logits = test_result.predictions[0] if isinstance(test_result.predictions, tuple) else test_result.predictions
        probs = torch.softmax(torch.tensor(logits), dim=-1).cpu().numpy()
        pred_ids = np.argmax(logits, axis=-1)
        gold_ids = test_df["intent_id"].to_numpy(dtype=int)

        predictions = pd.DataFrame({
            "example_id": test_df["example_id"].astype(str),
            "gold_intent_id": gold_ids,
            "gold_label": [id_to_label[i] for i in gold_ids],
            "predicted_intent_id": pred_ids,
            "predicted_label": [id_to_label[i] for i in pred_ids],
            "confidence": probs.max(axis=-1),
            "correct": pred_ids == gold_ids,
        })
        predictions.to_csv(run_dir / "test_predictions.csv", index=False)
        report = classification_report(
            gold_ids, pred_ids, labels=list(range(num_labels)),
            target_names=[id_to_label[i] for i in range(num_labels)],
            output_dict=True, zero_division=0,
        )
        pd.DataFrame(report).T.to_csv(run_dir / "per_class_metrics.csv")
        pd.DataFrame(confusion_matrix(gold_ids, pred_ids, labels=list(range(num_labels))),
                     index=[id_to_label[i] for i in range(num_labels)],
                     columns=[id_to_label[i] for i in range(num_labels)]).to_csv(run_dir / "confusion_matrix.csv")
        summary["test"] = test_result.metrics
        summary["test_macro_f1"] = float(f1_score(gold_ids, pred_ids, average="macro", zero_division=0))
        summary["test_accuracy"] = float(accuracy_score(gold_ids, pred_ids))
    with (run_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    logs = pd.DataFrame(trainer.state.log_history)
    logs.to_csv(run_dir / "metrics_by_step.csv", index=False)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
