"""Unsupervised SimCSE-style XLM-V training with duplicate-aware negatives."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

from src.contrastive.train_triplet import ProjectionHead, mean_pool


class ComplaintTextDataset(Dataset):
    def __init__(self, train_csv: Path, split_manifest: Path, clusters_csv: Path):
        train = pd.read_csv(train_csv, keep_default_na=False)
        splits = pd.read_csv(split_manifest, keep_default_na=False)
        clusters = pd.read_csv(clusters_csv, keep_default_na=False)
        required = {"example_id", "text", "group_id"}
        if required - set(train.columns):
            raise ValueError(f"Training CSV missing columns: {sorted(required - set(train.columns))}")
        if {"example_id", "split"} - set(splits.columns):
            raise ValueError("Split manifest requires example_id and split")
        if {"example_id", "cluster_id"} - set(clusters.columns):
            raise ValueError("Cluster manifest requires example_id and cluster_id")
        for frame, name in ((train, "train"), (splits, "split"), (clusters, "cluster")):
            if frame["example_id"].duplicated().any():
                raise ValueError(f"{name} manifest has duplicate example IDs")
        train_ids = set(train.example_id.astype(str))
        if train_ids != set(splits.loc[splits.split.eq("train"), "example_id"].astype(str)):
            raise ValueError("Training CSV does not exactly match train IDs in frozen split manifest")
        if not train_ids.issubset(set(clusters.example_id.astype(str))):
            raise ValueError("Duplicate-cluster manifest does not cover every train example")
        if train["group_id"].astype(str).str.strip().eq("").any():
            raise ValueError("Training data contains empty group_id")
        if train["text"].astype(str).str.strip().eq("").any():
            raise ValueError("Training data contains empty complaint text")
        cluster_map = dict(zip(clusters.example_id.astype(str), clusters.cluster_id.astype(str)))
        self.rows = [
            (str(r.example_id), str(r.text), str(r.group_id), cluster_map[str(r.example_id)])
            for r in train.itertuples(index=False)
        ]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--clusters-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default="facebook/xlm-v-base")
    parser.add_argument("--revision", default="68c75dd7733d2640b3a98114e3e94196dc543fe1")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--projection-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    args = parser.parse_args()

    if args.batch_size < 2:
        raise ValueError("SimCSE requires batch-size >= 2")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    output = Path(args.output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {output}")
    output.mkdir(parents=True)
    dataset = ComplaintTextDataset(Path(args.train_csv), Path(args.split_manifest), Path(args.clusters_csv))
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, revision=args.revision)
    encoder = AutoModel.from_pretrained(args.model_name, revision=args.revision)
    projection = ProjectionHead(int(encoder.config.hidden_size), args.projection_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = bool(args.bf16 and device.type == "cuda" and torch.cuda.is_bf16_supported())
    encoder.to(device).train()
    projection.to(device).train()
    if args.gradient_checkpointing:
        encoder.gradient_checkpointing_enable()
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(projection.parameters()), lr=args.learning_rate)
    history = []
    step = 0

    for epoch in range(args.epochs):
        for batch in loader:
            ids, texts, groups, clusters = batch
            tokens = tokenizer(list(texts), padding=True, truncation=True,
                               max_length=args.max_length, return_tensors="pt")
            tokens = {k: v.to(device) for k, v in tokens.items()}
            optimizer.zero_grad(set_to_none=True)
            if use_bf16:
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    first = projection(mean_pool(encoder(**tokens).last_hidden_state, tokens["attention_mask"]))
                    second = projection(mean_pool(encoder(**tokens).last_hidden_state, tokens["attention_mask"]))
                    z = torch.cat([first, second], dim=0)
                    loss = _simcse_loss(z, list(groups), list(clusters), args.temperature)
            else:
                first = projection(mean_pool(encoder(**tokens).last_hidden_state, tokens["attention_mask"]))
                second = projection(mean_pool(encoder(**tokens).last_hidden_state, tokens["attention_mask"]))
                z = torch.cat([first, second], dim=0)
                loss = _simcse_loss(z, list(groups), list(clusters), args.temperature)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(encoder.parameters()) + list(projection.parameters()), 1.0)
            optimizer.step()
            step += 1
            history.append({"step": step, "epoch": epoch + 1, "loss": float(loss.detach().cpu())})
            if args.max_steps and step >= args.max_steps:
                break
        if args.max_steps and step >= args.max_steps:
            break

    encoder.save_pretrained(output / "encoder")
    tokenizer.save_pretrained(output / "encoder")
    torch.save(projection.state_dict(), output / "projection_head.pt")
    config = {
        "model_name": args.model_name, "revision": args.revision,
        "max_length": args.max_length, "projection_size": args.projection_size,
        "hidden_size": int(encoder.config.hidden_size), "temperature": args.temperature,
        "objective": "unsupervised_simcse_dropout", "seed": args.seed, "steps": step,
        "train_csv_sha256": hashlib.sha256(Path(args.train_csv).read_bytes()).hexdigest(),
        "warning": "Duplicate clusters and group IDs are masked from in-batch negatives; semantic false negatives may remain.",
    }
    (output / "contrastive_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (output / "training_history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "steps": step,
                      "final_loss": history[-1]["loss"] if history else None,
                      "device": str(device), "bf16": use_bf16}, indent=2))


def _simcse_loss(z: torch.Tensor, groups: list[str], clusters: list[str], temperature: float) -> torch.Tensor:
    batch = len(groups)
    similarity = (z @ z.T) / temperature
    diagonal = torch.eye(2 * batch, dtype=torch.bool, device=z.device)
    positive = torch.zeros((2 * batch, 2 * batch), dtype=torch.bool, device=z.device)
    for i in range(batch):
        positive[i, i + batch] = True
        positive[i + batch, i] = True
    group_values = groups + groups
    cluster_values = clusters + clusters
    blocked = torch.zeros_like(diagonal)
    for i in range(2 * batch):
        for j in range(2 * batch):
            if i != j and (group_values[i] == group_values[j] or cluster_values[i] == cluster_values[j]):
                blocked[i, j] = True
    mask = diagonal | (blocked & ~positive)
    logits = similarity.masked_fill(mask, float("-inf"))
    targets = torch.cat([torch.arange(batch, 2 * batch), torch.arange(0, batch)]).to(z.device)
    return F.cross_entropy(logits, targets)


if __name__ == "__main__":
    main()
