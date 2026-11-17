"""Local inference engine joining classifier, structured summarizer and retrieval."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

from src.contrastive.train_triplet import ProjectionHead, mean_pool
from src.summarization.structured_summarizer import summarize_complaint


class ComplaintEngine:
    def __init__(self, classifier_dir: str | None, label_map_path: str,
                 contrastive_dir: str, retrieval_index_dir: str,
                 max_length: int = 256):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.max_length = max_length

        self.label_map = json.loads(Path(label_map_path).read_text(encoding="utf-8"))
        if not isinstance(self.label_map, dict) or not self.label_map:
            raise ValueError("Label map must be a non-empty label-to-ID mapping")
        self.id_to_label = {int(value): str(key) for key, value in self.label_map.items()}

        if classifier_dir and Path(classifier_dir).is_dir():
            self.classifier_tokenizer = AutoTokenizer.from_pretrained(classifier_dir)
            self.classifier = AutoModelForSequenceClassification.from_pretrained(classifier_dir)
            self.classifier.to(self.device).eval()
        else:
            self.classifier_tokenizer = None
            self.classifier = None

        self.contrastive_dir = Path(contrastive_dir).resolve()
        self.contrastive_config = json.loads(
            (self.contrastive_dir / "contrastive_config.json").read_text(encoding="utf-8")
        )
        encoder_dir = self.contrastive_dir / "encoder"
        self.retrieval_tokenizer = AutoTokenizer.from_pretrained(str(encoder_dir))
        self.retrieval_encoder = AutoModel.from_pretrained(str(encoder_dir))
        self.retrieval_encoder.to(self.device).eval()
        self.projection = ProjectionHead(
            int(self.retrieval_encoder.config.hidden_size),
            int(self.contrastive_config["projection_size"]),
        )
        self.projection.load_state_dict(torch.load(
            self.contrastive_dir / "projection_head.pt",
            map_location="cpu", weights_only=True,
        ))
        self.projection.to(self.device).eval()

        index_dir = Path(retrieval_index_dir).resolve()
        self.gallery = pd.read_csv(index_dir / "gallery_metadata.csv", keep_default_na=False)
        self.gallery_embeddings = np.load(index_dir / "gallery_embeddings.npy", allow_pickle=False)
        if len(self.gallery) != len(self.gallery_embeddings):
            raise ValueError("Retrieval metadata and embedding row counts differ")
        if self.gallery_embeddings.ndim != 2:
            raise ValueError("Gallery embeddings must be a 2D matrix")
        self.gallery_embeddings = self.gallery_embeddings.astype(np.float32, copy=False)
        norms = np.linalg.norm(self.gallery_embeddings, axis=1, keepdims=True)
        self.gallery_embeddings = self.gallery_embeddings / np.maximum(norms, 1e-12)

    @classmethod
    def from_env(cls) -> "ComplaintEngine":
        classifier_dir = os.getenv("COMPLAINT_CLASSIFIER_DIR")
        required = {
            "COMPLAINT_LABEL_MAP": os.getenv("COMPLAINT_LABEL_MAP"),
            "COMPLAINT_CONTRASTIVE_DIR": os.getenv("COMPLAINT_CONTRASTIVE_DIR"),
            "COMPLAINT_RETRIEVAL_INDEX_DIR": os.getenv("COMPLAINT_RETRIEVAL_INDEX_DIR"),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            classifier_dir,
            required["COMPLAINT_LABEL_MAP"],
            required["COMPLAINT_CONTRASTIVE_DIR"],
            required["COMPLAINT_RETRIEVAL_INDEX_DIR"],
        )

    def predict_intent(self, text: str, top_n: int = 3) -> dict[str, Any]:
        if self.classifier is not None:
            tokens = self.classifier_tokenizer(
                text, truncation=True, max_length=self.max_length, return_tensors="pt"
            )
            tokens = {k: v.to(self.device) for k, v in tokens.items()}
            with torch.inference_mode():
                logits = self.classifier(**tokens).logits[0]
                probs = torch.softmax(logits.float(), dim=-1)
                values, indices = torch.topk(probs, k=min(top_n, probs.numel()))
            predictions = [
                {"intent": self.id_to_label.get(int(idx), f"unknown_{int(idx)}"), "confidence": float(value)}
                for value, idx in zip(values.cpu(), indices.cpu())
            ]
            return {"predicted_intent": predictions[0]["intent"], "confidence": predictions[0]["confidence"],
                    "alternatives": predictions}
        else:
            # KNN retrieval-based classifier fallback using contrastive representations
            retrieval_res = self.retrieve(text, top_k=top_n)
            top_hit = retrieval_res[0] if retrieval_res else {"intent": "unknown", "similarity": 0.0}
            alternatives = [{"intent": r["intent"], "confidence": float(r["similarity"])} for r in retrieval_res]
            return {
                "predicted_intent": top_hit["intent"],
                "confidence": float(top_hit["similarity"]),
                "alternatives": alternatives,
                "mode": "knn_retrieval_classifier"
            }

    def embed(self, text: str) -> np.ndarray:
        tokens = self.retrieval_tokenizer(
            text, truncation=True, max_length=int(self.contrastive_config["max_length"]),
            return_tensors="pt",
        )
        tokens = {k: v.to(self.device) for k, v in tokens.items()}
        with torch.inference_mode():
            out = self.retrieval_encoder(**tokens).last_hidden_state
            pooled = mean_pool(out, tokens["attention_mask"])
            projected = self.projection(pooled)
        return F.normalize(projected.float(), p=2, dim=-1).cpu().numpy()[0]

    def retrieve(self, text: str, top_k: int = 5, domain: str | None = None,
                 cross_domain: bool = False) -> list[dict[str, Any]]:
        query = self.embed(text)
        scores = self.gallery_embeddings @ query
        eligible = np.ones(len(self.gallery), dtype=bool)
        if cross_domain and domain:
            eligible &= self.gallery["domain"].astype(str).to_numpy() != domain
        indices = np.flatnonzero(eligible)
        if not len(indices):
            return []
        count = min(top_k, len(indices))
        selected = indices[np.argpartition(scores[indices], -count)[-count:]]
        selected = selected[np.argsort(scores[selected])[::-1]]
        results = []
        for idx in selected:
            row = self.gallery.iloc[int(idx)]
            item = {
                "complaint_id": str(row["example_id"]),
                "intent": str(row["label"]),
                "domain": str(row["domain"]),
                "similarity": float(scores[idx]),
            }
            if "text" in row.index:
                item["text_excerpt"] = str(row["text"])[:600]
            results.append(item)
        return results

    def analyze(self, text: str, top_k: int = 5, domain: str | None = None,
                cross_domain: bool = False) -> dict[str, Any]:
        return {
            "intent": self.predict_intent(text),
            "summary": summarize_complaint(text),
            "similar_complaints": self.retrieve(text, top_k, domain, cross_domain),
            "warnings": [
                "Intent labels originate from CFPB administrative metadata.",
                "Retrieval relevance is not human-validated unless an adjudicated relevance benchmark is supplied.",
                "The summarizer is an extractive baseline, not a validated abstractive summarizer.",
            ],
        }
