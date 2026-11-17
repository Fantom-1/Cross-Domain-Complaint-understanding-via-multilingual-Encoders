"""Train an XLM-V encoder with weakly supervised triplet InfoNCE.

This is a reproducible pilot trainer. It consumes only a pair manifest generated
from the training split; it never reads validation or test rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer


class TripletDataset(Dataset):
    def __init__(self, train_csv: Path, pairs_csv: Path):
        train = pd.read_csv(train_csv, keep_default_na=False)
        pairs = pd.read_csv(pairs_csv, keep_default_na=False)
        required_train = {"example_id", "text"}
        required_pairs = {"anchor_id", "positive_id", "negative_id", "weak_label", "negative_label", "supervision"}
        if required_train - set(train.columns):
            raise ValueError(f"Training data missing columns: {sorted(required_train - set(train.columns))}")
        if required_pairs - set(pairs.columns):
            raise ValueError(f"Pair manifest missing columns: {sorted(required_pairs - set(pairs.columns))}")
        if set(pairs["supervision"]) != {"weak_label"}:
            raise ValueError("This trainer expects explicitly tagged weak_label supervision")
        if train["example_id"].duplicated().any():
            raise ValueError("Training CSV has duplicate example IDs")
        self.text = dict(zip(train["example_id"].astype(str), train["text"].astype(str)))
        referenced = set(pairs["anchor_id"].astype(str)) | set(pairs["positive_id"].astype(str)) | set(pairs["negative_id"].astype(str))
        unknown = referenced - set(self.text)
        if unknown:
            raise ValueError(f"Pair manifest references {len(unknown)} IDs outside the training CSV")
        if pairs.empty:
            raise ValueError("Pair manifest is empty")
        self.pairs = pairs.to_dict("records")

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, index):
        row = self.pairs[index]
        return (
            self.text[str(row["anchor_id"])],
            self.text[str(row["positive_id"])],
            self.text[str(row["negative_id"])],
            str(row["weak_label"]),
            str(row["negative_label"]),
        )


class ProjectionHead(nn.Module):
    def __init__(self, hidden_size: int, projection_size: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Linear(hidden_size, projection_size),
        )

    def forward(self, x):
        return F.normalize(self.net(x), p=2, dim=-1)


def mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).to(last_hidden_state.dtype)
    return (last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--pairs-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default="facebook/xlm-v-base")
    parser.add_argument("--revision", default="68c75dd7733d2640b3a98114e3e94196dc543fe1")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=0, help="0 for full epochs")
    parser.add_argument("--eval-steps", type=int, default=250, help="Evaluate validation loss every N steps")
    parser.add_argument("--early-stopping-patience", type=int, default=4, help="Patience evaluations before early stopping (0 to disable)")
    parser.add_argument("--early-stopping-min-delta", type=float, default=0.001, help="Minimum delta to consider an improvement")
    parser.add_argument("--val-ratio", type=float, default=0.05, help="Ratio of pairs held out for validation early stopping")
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--objective", choices=["supcon", "pairwise-infonce"], default="supcon")
    parser.add_argument("--projection-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    args = parser.parse_args()

    if args.max_length < 8 or args.batch_size < 1 or args.epochs < 1 or args.temperature <= 0:
        raise ValueError("Invalid max-length, batch-size, epochs or temperature")
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {output}")
    output.mkdir(parents=True)

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = bool(args.bf16 and device.type == "cuda" and torch.cuda.is_bf16_supported())

    dataset = TripletDataset(Path(args.train_csv), Path(args.pairs_csv))
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, revision=args.revision)
    encoder = AutoModel.from_pretrained(args.model_name, revision=args.revision)
    hidden_size = int(encoder.config.hidden_size)
    projection = ProjectionHead(hidden_size, args.projection_size)
    encoder.to(device)
    projection.to(device)
    if args.gradient_checkpointing:
        encoder.gradient_checkpointing_enable()
        if hasattr(encoder.config, "use_cache"):
            encoder.config.use_cache = False

    optimizer = torch.optim.AdamW(
        list(encoder.parameters()) + list(projection.parameters()),
        lr=args.learning_rate,
        weight_decay=0.01,
    )
    if args.val_ratio > 0:
        val_size = max(1, int(len(dataset) * args.val_ratio))
        rng = random.Random(args.seed)
        shuffled = list(range(len(dataset)))
        rng.shuffle(shuffled)
        val_indices = shuffled[:val_size]
        train_indices = shuffled[val_size:]
        train_dataset = torch.utils.data.Subset(dataset, train_indices)
        val_dataset = torch.utils.data.Subset(dataset, val_indices)
        loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_dataset, batch_size=min(64, args.batch_size * 2), shuffle=False, num_workers=0)
    else:
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
        val_loader = None

    history = []
    label_values = sorted(set(pd.read_csv(args.pairs_csv, keep_default_na=False)["weak_label"].astype(str)) |
                          set(pd.read_csv(args.pairs_csv, keep_default_na=False)["negative_label"].astype(str)))
    label_to_id = {label: i for i, label in enumerate(label_values)}
    global_step = 0
    best_val_loss = float("inf")
    patience_counter = 0
    best_encoder_state = None
    best_proj_state = None
    early_stopped = False
    encoder.train()
    projection.train()

    for epoch in range(args.epochs):
        for anchor, positive, negative, anchor_labels, negative_labels in loader:
            texts = list(anchor) + list(positive) + list(negative)
            encoded = tokenizer(
                texts, padding=True, truncation=True, max_length=args.max_length,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            optimizer.zero_grad(set_to_none=True)
            if use_bf16:
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    output_model = encoder(**encoded)
                    pooled = mean_pool(output_model.last_hidden_state, encoded["attention_mask"])
                    z = projection(pooled)
                    n = len(anchor)
                    za, zp, zn = z[:n], z[n:2*n], z[2*n:]
                    if args.objective == "supcon":
                        batch_labels = torch.tensor(
                            [label_to_id[x] for x in anchor_labels]
                            + [label_to_id[x] for x in anchor_labels]
                            + [label_to_id[x] for x in negative_labels],
                            dtype=torch.long, device=device,
                        )
                        similarity = (z @ z.T) / args.temperature
                        self_mask = torch.eye(similarity.size(0), dtype=torch.bool, device=device)
                        positive_mask = batch_labels.unsqueeze(0).eq(batch_labels.unsqueeze(1)) & ~self_mask
                        logits_masked = similarity.masked_fill(self_mask, float("-inf"))
                        log_prob = logits_masked - torch.logsumexp(logits_masked, dim=1, keepdim=True)
                        positive_count = positive_mask.sum(dim=1)
                        valid = positive_count > 0
                        per_anchor = -(log_prob.masked_fill(~positive_mask, 0.0).sum(dim=1)
                                       / positive_count.clamp(min=1))
                        loss = per_anchor[valid].mean()
                    else:
                        logits = torch.stack([
                            F.cosine_similarity(za, zp, dim=-1),
                            F.cosine_similarity(za, zn, dim=-1),
                        ], dim=1) / args.temperature
                        loss = F.cross_entropy(logits, torch.zeros(n, dtype=torch.long, device=device))
            else:
                output_model = encoder(**encoded)
                pooled = mean_pool(output_model.last_hidden_state, encoded["attention_mask"])
                z = projection(pooled)
                n = len(anchor)
                za, zp, zn = z[:n], z[n:2*n], z[2*n:]
                if args.objective == "supcon":
                    batch_labels = torch.tensor(
                        [label_to_id[x] for x in anchor_labels]
                        + [label_to_id[x] for x in anchor_labels]
                        + [label_to_id[x] for x in negative_labels],
                        dtype=torch.long, device=device,
                    )
                    similarity = (z @ z.T) / args.temperature
                    self_mask = torch.eye(similarity.size(0), dtype=torch.bool, device=device)
                    positive_mask = batch_labels.unsqueeze(0).eq(batch_labels.unsqueeze(1)) & ~self_mask
                    logits_masked = similarity.masked_fill(self_mask, float("-inf"))
                    log_prob = logits_masked - torch.logsumexp(logits_masked, dim=1, keepdim=True)
                    positive_count = positive_mask.sum(dim=1)
                    valid = positive_count > 0
                    per_anchor = -(log_prob.masked_fill(~positive_mask, 0.0).sum(dim=1)
                                   / positive_count.clamp(min=1))
                    loss = per_anchor[valid].mean()
                else:
                    logits = torch.stack([
                        F.cosine_similarity(za, zp, dim=-1),
                        F.cosine_similarity(za, zn, dim=-1),
                    ], dim=1) / args.temperature
                    loss = F.cross_entropy(logits, torch.zeros(n, dtype=torch.long, device=device))

            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(encoder.parameters()) + list(projection.parameters()), 1.0
            )
            optimizer.step()
            global_step += 1
            loss_val = float(loss.detach().cpu())
            record = {"step": global_step, "epoch": epoch + 1, "loss": loss_val}

            if global_step % 25 == 0 and (not args.eval_steps or global_step % args.eval_steps != 0):
                print(f"[Step {global_step:5d}] Epoch {epoch+1} | Train Loss: {loss_val:.4f}", flush=True)

            # Periodic Evaluation and Early Stopping Check
            if args.eval_steps and global_step % args.eval_steps == 0:
                if val_loader is not None:
                    current_metric = _evaluate_triplet_val(
                        encoder, projection, tokenizer, val_loader, device,
                        use_bf16, args.max_length, args.temperature, args.objective, label_to_id
                    )
                    record["val_loss"] = current_metric
                else:
                    current_metric = float(np.mean([h["loss"] for h in history[-args.eval_steps:]])) if history else loss_val
                    record["eval_train_loss"] = current_metric

                if current_metric < best_val_loss - args.early_stopping_min_delta:
                    best_val_loss = current_metric
                    patience_counter = 0
                    best_encoder_state = {k: v.cpu().clone() for k, v in encoder.state_dict().items()}
                    best_proj_state = {k: v.cpu().clone() for k, v in projection.state_dict().items()}
                    print(f"[Step {global_step:5d}] Train Loss: {loss_val:.4f} | Eval Loss: {current_metric:.4f} (NEW BEST) | Patience: 0/{args.early_stopping_patience}", flush=True)
                else:
                    patience_counter += 1
                    print(f"[Step {global_step:5d}] Train Loss: {loss_val:.4f} | Eval Loss: {current_metric:.4f} (Best: {best_val_loss:.4f}) | Patience: {patience_counter}/{args.early_stopping_patience}", flush=True)
                    if args.early_stopping_patience > 0 and patience_counter >= args.early_stopping_patience:
                        print(f"=== Early stopping triggered at step {global_step} (Patience {args.early_stopping_patience} reached. Restoring best model at loss {best_val_loss:.4f}) ===", flush=True)
                        early_stopped = True
                        history.append(record)
                        break

            history.append(record)
            if args.max_steps and global_step >= args.max_steps:
                break
        if early_stopped or (args.max_steps and global_step >= args.max_steps):
            break

    if best_encoder_state is not None:
        print(f"Restoring best checkpoint with loss {best_val_loss:.4f}")
        encoder.load_state_dict(best_encoder_state)
        projection.load_state_dict(best_proj_state)

    encoder.save_pretrained(output / "encoder")
    tokenizer.save_pretrained(output / "encoder")
    torch.save(projection.state_dict(), output / "projection_head.pt")
    config = {
        "model_name": args.model_name,
        "revision": args.revision,
        "max_length": args.max_length,
        "projection_size": args.projection_size,
        "hidden_size": hidden_size,
        "temperature": args.temperature,
        "objective": "weakly_supervised_supervised_contrastive" if args.objective == "supcon" else "weakly_supervised_triplet_infonce",
        "supervision": "weak_label",
        "seed": args.seed,
        "steps": global_step,
        "pairs_sha256": hashlib.sha256(Path(args.pairs_csv).read_bytes()).hexdigest(),
        "training_data_sha256": hashlib.sha256(Path(args.train_csv).read_bytes()).hexdigest(),
        "warning": "Weak administrative labels are not semantic gold labels.",
    }
    (output / "contrastive_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (output / "training_history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "steps": global_step, "final_loss": history[-1]["loss"] if history else None, "device": str(device), "bf16": use_bf16}, indent=2))


def _evaluate_triplet_val(encoder, projection, tokenizer, val_loader, device, use_bf16, max_length, temperature, objective, label_to_id):
    encoder.eval()
    projection.eval()
    losses = []
    with torch.no_grad():
        for anchor, positive, negative, anchor_labels, negative_labels in val_loader:
            texts = list(anchor) + list(positive) + list(negative)
            encoded = tokenizer(
                texts, padding=True, truncation=True, max_length=max_length,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            if use_bf16:
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    output_model = encoder(**encoded)
                    pooled = mean_pool(output_model.last_hidden_state, encoded["attention_mask"])
                    z = projection(pooled)
                    n = len(anchor)
                    za, zp, zn = z[:n], z[n:2*n], z[2*n:]
                    if objective == "supcon":
                        batch_labels = torch.tensor(
                            [label_to_id[x] for x in anchor_labels]
                            + [label_to_id[x] for x in anchor_labels]
                            + [label_to_id[x] for x in negative_labels],
                            dtype=torch.long, device=device,
                        )
                        similarity = (z @ z.T) / temperature
                        self_mask = torch.eye(similarity.size(0), dtype=torch.bool, device=device)
                        positive_mask = batch_labels.unsqueeze(0).eq(batch_labels.unsqueeze(1)) & ~self_mask
                        logits_masked = similarity.masked_fill(self_mask, float("-inf"))
                        log_prob = logits_masked - torch.logsumexp(logits_masked, dim=1, keepdim=True)
                        positive_count = positive_mask.sum(dim=1)
                        valid = positive_count > 0
                        per_anchor = -(log_prob.masked_fill(~positive_mask, 0.0).sum(dim=1)
                                       / positive_count.clamp(min=1))
                        batch_loss = per_anchor[valid].mean()
                    else:
                        logits = torch.stack([
                            F.cosine_similarity(za, zp, dim=-1),
                            F.cosine_similarity(za, zn, dim=-1),
                        ], dim=1) / temperature
                        batch_loss = F.cross_entropy(logits, torch.zeros(n, dtype=torch.long, device=device))
            else:
                output_model = encoder(**encoded)
                pooled = mean_pool(output_model.last_hidden_state, encoded["attention_mask"])
                z = projection(pooled)
                n = len(anchor)
                za, zp, zn = z[:n], z[n:2*n], z[2*n:]
                if objective == "supcon":
                    batch_labels = torch.tensor(
                        [label_to_id[x] for x in anchor_labels]
                        + [label_to_id[x] for x in anchor_labels]
                        + [label_to_id[x] for x in negative_labels],
                        dtype=torch.long, device=device,
                    )
                    similarity = (z @ z.T) / temperature
                    self_mask = torch.eye(similarity.size(0), dtype=torch.bool, device=device)
                    positive_mask = batch_labels.unsqueeze(0).eq(batch_labels.unsqueeze(1)) & ~self_mask
                    logits_masked = similarity.masked_fill(self_mask, float("-inf"))
                    log_prob = logits_masked - torch.logsumexp(logits_masked, dim=1, keepdim=True)
                    positive_count = positive_mask.sum(dim=1)
                    valid = positive_count > 0
                    per_anchor = -(log_prob.masked_fill(~positive_mask, 0.0).sum(dim=1)
                                   / positive_count.clamp(min=1))
                    batch_loss = per_anchor[valid].mean()
                else:
                    logits = torch.stack([
                        F.cosine_similarity(za, zp, dim=-1),
                        F.cosine_similarity(za, zn, dim=-1),
                    ], dim=1) / temperature
                    batch_loss = F.cross_entropy(logits, torch.zeros(n, dtype=torch.long, device=device))
            losses.append(float(batch_loss.detach().cpu()))
    encoder.train()
    projection.train()
    return float(np.mean(losses)) if losses else float("inf")


if __name__ == "__main__":
    main()
