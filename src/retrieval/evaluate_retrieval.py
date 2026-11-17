"""Evaluate complaint retrieval with TF-IDF or XLM-V embeddings.

The default relevance definition is same CFPB-derived weak intent label. These
scores are weak-label retrieval metrics, not human-validated semantic relevance.
Use query=validation and gallery=train for development; reserve query=test for
the final locked evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED = {"example_id", "text", "label", "domain"}


def _validate_frames(query: pd.DataFrame, gallery: pd.DataFrame) -> None:
    for name, frame in (("query", query), ("gallery", gallery)):
        missing = REQUIRED - set(frame.columns)
        if missing:
            raise ValueError(f"{name} CSV missing columns: {sorted(missing)}")
        if frame["example_id"].duplicated().any():
            raise ValueError(f"{name} CSV contains duplicate example IDs")
        if frame["text"].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name} CSV contains empty text")
    overlap = set(query["example_id"].astype(str)) & set(gallery["example_id"].astype(str))
    if overlap:
        raise ValueError(f"Query/gallery leakage: {len(overlap)} shared example IDs")


def _encode_xlmv(texts: list[str], model_name: str, revision: str, model_dir: str | None,
                 max_length: int, batch_size: int) -> np.ndarray:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    path = Path(model_dir).resolve() if model_dir else None
    encoder_path = path / "encoder" if path and (path / "encoder").is_dir() else path
    if encoder_path and encoder_path.is_dir():
        tokenizer = AutoTokenizer.from_pretrained(str(encoder_path))
        encoder = AutoModel.from_pretrained(str(encoder_path))
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
        encoder = AutoModel.from_pretrained(model_name, revision=revision)

    class Projection(nn.Module):
        def __init__(self, hidden: int, size: int):
            super().__init__()
            self.net = nn.Sequential(nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, size))
        def forward(self, x):
            return F.normalize(self.net(x), p=2, dim=-1)

    projection = None
    if path and (path / "projection_head.pt").is_file():
        cfg = json.loads((path / "contrastive_config.json").read_text(encoding="utf-8"))
        projection = Projection(int(encoder.config.hidden_size), int(cfg["projection_size"]))
        projection.load_state_dict(torch.load(path / "projection_head.pt", map_location="cpu", weights_only=True))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device).eval()
    if projection is not None:
        projection.to(device).eval()
    chunks = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            tokens = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
            tokens = {k: v.to(device) for k, v in tokens.items()}
            out = encoder(**tokens).last_hidden_state
            mask = tokens["attention_mask"].unsqueeze(-1).to(out.dtype)
            pooled = (out * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
            if projection is not None:
                pooled = projection(pooled)
            pooled = F.normalize(pooled.float(), p=2, dim=-1)
            chunks.append(pooled.cpu().numpy())
    return np.concatenate(chunks, axis=0).astype(np.float32)


def _rank_embeddings(query_vecs: np.ndarray, gallery_vecs: np.ndarray,
                     query: pd.DataFrame, gallery: pd.DataFrame,
                     top_k: int, cross_domain: bool, backend: str) -> list[list[tuple[int, float]]]:
    domains = gallery["domain"].astype(str).to_numpy()
    query_domains = query["domain"].astype(str).to_numpy()
    ranks: list[list[tuple[int, float]]] = []

    use_faiss = backend in {"auto", "faiss"}
    faiss = None
    if use_faiss:
        try:
            import faiss as faiss_module
            faiss = faiss_module
        except ImportError:
            if backend == "faiss":
                raise ImportError("FAISS backend requested; install faiss-cpu in the project environment")
    if faiss is not None:
        indexes = {}
        for domain in sorted(set(domains)):
            indices = np.flatnonzero(domains == domain)
            index = faiss.IndexFlatIP(gallery_vecs.shape[1])
            index.add(np.ascontiguousarray(gallery_vecs[indices]))
            indexes[domain] = (index, indices)
        for i, qv in enumerate(query_vecs):
            candidate_pairs = []
            for domain, (index, original_indices) in indexes.items():
                if cross_domain and domain == query_domains[i]:
                    continue
                take = min(top_k, len(original_indices))
                scores, local_ids = index.search(np.ascontiguousarray(qv.reshape(1, -1)), take)
                candidate_pairs.extend(
                    (int(original_indices[j]), float(score))
                    for j, score in zip(local_ids[0], scores[0]) if j >= 0
                )
            ranks.append(sorted(candidate_pairs, key=lambda x: x[1], reverse=True)[:top_k])
        return ranks

    # Exact cosine search in bounded memory. Vectors are L2-normalized.
    for i, qv in enumerate(query_vecs):
        scores = gallery_vecs @ qv
        eligible = np.ones(len(gallery), dtype=bool)
        if cross_domain:
            eligible &= domains != query_domains[i]
        eligible_idx = np.flatnonzero(eligible)
        if len(eligible_idx) == 0:
            ranks.append([])
            continue
        local_scores = scores[eligible_idx]
        take = min(top_k, len(local_scores))
        chosen = np.argpartition(local_scores, -take)[-take:]
        chosen = chosen[np.argsort(local_scores[chosen])[::-1]]
        ranks.append([(int(eligible_idx[j]), float(local_scores[j])) for j in chosen])
    return ranks


def _rank_tfidf(query: pd.DataFrame, gallery: pd.DataFrame, top_k: int,
                cross_domain: bool) -> list[list[tuple[int, float]]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=200000, sublinear_tf=True)
    gallery_matrix = vectorizer.fit_transform(gallery["text"].astype(str))
    query_matrix = vectorizer.transform(query["text"].astype(str))
    gallery_domains = gallery["domain"].astype(str).to_numpy()
    query_domains = query["domain"].astype(str).to_numpy()
    ranks = []
    for i in range(query_matrix.shape[0]):
        scores = cosine_similarity(query_matrix[i], gallery_matrix).ravel()
        eligible = np.ones(len(gallery), dtype=bool)
        if cross_domain:
            eligible &= gallery_domains != query_domains[i]
        eligible_idx = np.flatnonzero(eligible)
        if not len(eligible_idx):
            ranks.append([])
            continue
        local_scores = scores[eligible_idx]
        take = min(top_k, len(local_scores))
        chosen = np.argpartition(local_scores, -take)[-take:]
        chosen = chosen[np.argsort(local_scores[chosen])[::-1]]
        ranks.append([(int(eligible_idx[j]), float(local_scores[j])) for j in chosen])
    return ranks


def evaluate_ranks(query: pd.DataFrame, gallery: pd.DataFrame,
                   ranks: list[list[tuple[int, float]]], top_k: int,
                   cross_domain: bool) -> tuple[dict[str, Any], pd.DataFrame]:
    q_labels = query["label"].astype(str).to_numpy()
    g_labels = gallery["label"].astype(str).to_numpy()
    g_domains = gallery["domain"].astype(str).to_numpy()
    q_domains = query["domain"].astype(str).to_numpy()
    metric_rows = []
    ranking_rows = []
    no_relevant = 0

    for qi, results in enumerate(ranks):
        eligible = g_domains != q_domains[qi] if cross_domain else np.ones(len(gallery), dtype=bool)
        total_relevant = int(np.sum((g_labels == q_labels[qi]) & eligible))
        if total_relevant == 0:
            no_relevant += 1
            continue
        hits = [1 if g_labels[gi] == q_labels[qi] else 0 for gi, _ in results[:top_k]]
        precision = sum(hits) / top_k
        recall = sum(hits) / total_relevant
        reciprocal_rank = next((1.0 / rank for rank, hit in enumerate(hits, start=1) if hit), 0.0)
        dcg = sum(hit / np.log2(rank + 1) for rank, hit in enumerate(hits, start=1))
        ideal_count = min(total_relevant, top_k)
        idcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_count + 1))
        ndcg = dcg / idcg if idcg else 0.0
        metric_rows.append({"precision": precision, "recall": recall, "mrr": reciprocal_rank, "ndcg": ndcg})
        for rank, (gi, score) in enumerate(results[:top_k], start=1):
            ranking_rows.append({
                "query_id": str(query.iloc[qi]["example_id"]),
                "rank": rank,
                "retrieved_id": str(gallery.iloc[gi]["example_id"]),
                "retrieved_label": str(gallery.iloc[gi]["label"]),
                "retrieved_domain": str(gallery.iloc[gi]["domain"]),
                "similarity": score,
                "weak_label_relevant": bool(g_labels[gi] == q_labels[qi]),
            })

    if not metric_rows:
        raise ValueError("No query has a relevant gallery item under the selected evaluation setting")
    metrics = {
        f"precision@{top_k}": float(np.mean([r["precision"] for r in metric_rows])),
        f"recall@{top_k}": float(np.mean([r["recall"] for r in metric_rows])),
        f"mrr@{top_k}": float(np.mean([r["mrr"] for r in metric_rows])),
        f"ndcg@{top_k}": float(np.mean([r["ndcg"] for r in metric_rows])),
        "query_count": len(query),
        "evaluated_query_count": len(metric_rows),
        "queries_without_relevant_gallery_item": no_relevant,
        "query_coverage": len(metric_rows) / len(query),
        "relevance_definition": "same CFPB-derived weak intent label",
        "cross_domain_only": cross_domain,
        "warning": "Weak-label retrieval metrics are not human-validated semantic relevance metrics.",
    }
    return metrics, pd.DataFrame(ranking_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-csv", required=True)
    parser.add_argument("--gallery-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=["tfidf", "xlmv"], default="tfidf")
    parser.add_argument("--cross-domain", action="store_true")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--model-name", default="facebook/xlm-v-base")
    parser.add_argument("--revision", default="68c75dd7733d2640b3a98114e3e94196dc543fe1")
    parser.add_argument("--model-dir", default=None, help="Contrastive run directory containing encoder/ and projection_head.pt")
    parser.add_argument("--index-backend", choices=["auto", "faiss", "numpy"], default="auto")
    args = parser.parse_args()

    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")
    query = pd.read_csv(args.query_csv, keep_default_na=False)
    gallery = pd.read_csv(args.gallery_csv, keep_default_na=False)
    _validate_frames(query, gallery)

    if args.mode == "tfidf":
        ranks = _rank_tfidf(query, gallery, args.top_k, args.cross_domain)
    else:
        gallery_vecs = _encode_xlmv(
            gallery["text"].astype(str).tolist(), args.model_name, args.revision,
            args.model_dir, args.max_length, args.batch_size,
        )
        query_vecs = _encode_xlmv(
            query["text"].astype(str).tolist(), args.model_name, args.revision,
            args.model_dir, args.max_length, args.batch_size,
        )
        ranks = _rank_embeddings(
            query_vecs, gallery_vecs, query, gallery, args.top_k,
            args.cross_domain, args.index_backend,
        )

    metrics, ranking = evaluate_ranks(query, gallery, ranks, args.top_k, args.cross_domain)
    metrics.update({"mode": args.mode, "query_csv": str(Path(args.query_csv)), "gallery_csv": str(Path(args.gallery_csv))})
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    ranking.to_csv(output / "rankings.csv", index=False)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
