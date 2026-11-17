"""Evidence-grounded structured complaint summarization baseline.

This is a conservative extractive baseline, not a trained abstractive model.
Every generated text field is composed from source sentences to reduce unsupported
inference. It must be human-evaluated before operational use.
"""
from __future__ import annotations

import re
from typing import Any

DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)
REQUEST_TERMS = (
    "i want", "i would like", "please", "request", "refund", "remove",
    "correct", "investigate", "resolve", "stop", "reverse", "return",
)
CONCERN_TERMS = (
    "concern", "worried", "unable", "cannot", "can't", "incorrect",
    "wrong", "unauthorized", "fraud", "charged", "withheld", "denied",
    "harass", "threat", "dispute", "problem", "issue",
)
EVENT_TERMS = (
    "called", "contacted", "received", "submitted", "paid", "charged",
    "transferred", "reported", "disputed", "sent", "responded", "account",
)


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _select(sentences: list[str], terms: tuple[str, ...], limit: int = 3) -> list[dict[str, Any]]:
    selected = []
    for index, sentence in enumerate(sentences):
        lower = sentence.lower()
        if any(term in lower for term in terms):
            selected.append({"sentence_index": index, "text": sentence})
            if len(selected) >= limit:
                break
    return selected


def summarize_complaint(narrative: str) -> dict[str, Any]:
    sentences = split_sentences(narrative)
    if not sentences:
        raise ValueError("Complaint narrative must not be empty")

    problem = " ".join(sentences[:2])
    concern = _select(sentences, CONCERN_TERMS, 3)
    events = []
    for index, sentence in enumerate(sentences):
        if DATE_RE.search(sentence) or any(term in sentence.lower() for term in EVENT_TERMS):
            events.append({"sentence_index": index, "text": sentence})
        if len(events) >= 5:
            break
    requested = _select(sentences, REQUEST_TERMS, 3)
    evidence = []
    seen = set()
    for item in concern + events + requested:
        key = item["sentence_index"]
        if key not in seen:
            evidence.append(item)
            seen.add(key)
        if len(evidence) >= 6:
            break

    summary_sentences = []
    for sentence in sentences:
        candidate = " ".join(summary_sentences + [sentence])
        if summary_sentences and len(candidate) > 900:
            break
        summary_sentences.append(sentence)
    short_summary = " ".join(summary_sentences)

    result = {
        "problem": problem,
        "customer_concern": concern,
        "timeline_and_events": events,
        "requested_resolution": requested,
        "supporting_evidence": evidence,
        "short_summary": short_summary,
        "limitations": [
            "Extractive baseline: selected sentences may omit context.",
            "No reference-summary or human factuality evaluation is included by this function.",
            "Absence of a field means the narrative did not contain a detected statement; it does not mean the event did not occur.",
        ],
    }
    validate_summary(result, narrative)
    return result


def validate_summary(summary: dict[str, Any], narrative: str) -> None:
    source = re.sub(r"\s+", " ", str(narrative)).strip()
    for field in ("problem", "short_summary"):
        value = summary.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Summary field {field} must be a non-empty string")
        if value not in source:
            raise ValueError(f"Summary field {field} contains text not found verbatim in source")
    for field in ("customer_concern", "timeline_and_events", "requested_resolution", "supporting_evidence"):
        if not isinstance(summary.get(field), list):
            raise ValueError(f"Summary field {field} must be a list")
        for item in summary[field]:
            if item.get("text") not in source:
                raise ValueError(f"{field} contains evidence not found verbatim in source")


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    print(json.dumps(summarize_complaint(args.text), indent=2, ensure_ascii=False))
