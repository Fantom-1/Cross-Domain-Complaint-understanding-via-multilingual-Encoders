"""Conservative text normalization for consumer complaint understanding.

Requirements from DATA_PREPARATION_SPEC.md:
- NFC Unicode normalization
- Safe whitespace collapsing
- Preserve original text separately
- Handle repetitive redaction markers: collapse runs of X{2,} to <REDACTED>
- Preserve negation, numbers, punctuation, casing, and typos
- Strictly DO NOT remove stopwords, stem, lemmatize, or alter casing
"""

import re
import unicodedata

XX_RUN_PATTERN = re.compile(r"X{2,}")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_complaint_text(raw_text: str) -> str:
    """Conservatively normalizes raw complaint text.
    
    1. Unicode normalization to NFC.
    2. Collapses redaction marker sequences (e.g. 'XXXX', 'XXXX/XXXX/2019') to '<REDACTED>'.
    3. Collapses consecutive whitespace (newlines, tabs, spaces) into a single space.
    4. Strips leading and trailing whitespace.
    """
    if not raw_text:
        return ""
    
    # 1. Unicode NFC normalization
    text = unicodedata.normalize("NFC", raw_text)
    
    # 2. Normalize CFPB redaction markers
    text = XX_RUN_PATTERN.sub("<REDACTED>", text)
    
    # 3. Collapse whitespace safely
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    
    return text


def word_count(text: str) -> int:
    """Computes whitespace-delimited word count."""
    return len(text.split()) if text else 0
