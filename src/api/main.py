"""FastAPI application for the complaint intelligence prototype.

Run locally only by default. Configure model/index paths with environment variables.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.api.engine import ComplaintEngine
from src.summarization.structured_summarizer import summarize_complaint


app = FastAPI(title="Complaint Intelligence API", version="0.1.0")


class ComplaintRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    domain: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    cross_domain: bool = False


@lru_cache(maxsize=1)
def get_engine() -> ComplaintEngine:
    return ComplaintEngine.from_env()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "engine_configured": all([
        __import__("os").getenv("COMPLAINT_CLASSIFIER_DIR"),
        __import__("os").getenv("COMPLAINT_LABEL_MAP"),
        __import__("os").getenv("COMPLAINT_CONTRASTIVE_DIR"),
        __import__("os").getenv("COMPLAINT_RETRIEVAL_INDEX_DIR"),
    ])}


@app.post("/predict")
def predict(request: ComplaintRequest) -> dict[str, Any]:
    try:
        return get_engine().predict_intent(request.text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/summarize")
def summarize(request: ComplaintRequest) -> dict[str, Any]:
    try:
        return summarize_complaint(request.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/retrieve")
def retrieve(request: ComplaintRequest) -> dict[str, Any]:
    try:
        return {"similar_complaints": get_engine().retrieve(
            request.text, request.top_k, request.domain, request.cross_domain
        )}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/analyze")
def analyze(request: ComplaintRequest) -> dict[str, Any]:
    try:
        return get_engine().analyze(
            request.text, request.top_k, request.domain, request.cross_domain
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
