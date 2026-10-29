"""Robust, streaming CSV parser for CFPB complaint archives and auxiliary datasets.

Designed specifically to address real-world edge cases in large consumer complaint archives:
1. Multi-line complaint narratives with embedded newlines (\\r, \\n).
2. Quotes, escaped quotes, and commas inside free-text narratives.
3. Windows 32-bit C long overflow in csv.field_size_limit(sys.maxsize).
4. Direct streaming from compressed ZIP archives without loading full files into memory.
5. Strict column validation against expected schema and capture of malformed row diagnostics.
6. Clean handling of UTF-8 BOM, encoding errors, and null/whitespace fields.
"""

import csv
import dataclasses
import io
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple, Union

# ---------------------------------------------------------------------------
# Portable Field Size Limit Configuration
# ---------------------------------------------------------------------------
# On Windows (LLP64), C long is 32-bit (max 2**31 - 1 = 2,147,483,647).
# Passing 64-bit sys.maxsize (9,223,372,036,854,775,807) to csv.field_size_limit
# raises: OverflowError: Python int too large to convert to C long.
# SAFE_FIELD_SIZE_LIMIT safely caps at 2**31 - 1 across all platforms.
SAFE_FIELD_SIZE_LIMIT: int = min(sys.maxsize, 2147483647)


def ensure_safe_field_size_limit(limit: int = SAFE_FIELD_SIZE_LIMIT) -> int:
    """Configures csv.field_size_limit safely without platform overflow."""
    configured = csv.field_size_limit(limit)
    return configured


# Set the safe limit on module import
ensure_safe_field_size_limit()

# ---------------------------------------------------------------------------
# Canonical CFPB Schemas
# ---------------------------------------------------------------------------
CFPB_FOIA_COLUMNS: Tuple[str, ...] = (
    "Date received",
    "Product",
    "Sub-product",
    "Issue",
    "Sub-issue",
    "Consumer complaint narrative",
    "Company public response",
    "Company",
    "State",
    "ZIP code",
    "Tags",
    "Submitted via",
    "Date sent to company",
    "Company response to consumer",
    "Timely response?",
    "Complaint ID",
)

CFPB_BULK_COLUMNS: Tuple[str, ...] = (
    "Date received",
    "Product",
    "Sub-product",
    "Issue",
    "Sub-issue",
    "Company public response",
    "Company",
    "State",
    "ZIP code",
    "Tags",
    "Submitted via",
    "Date sent to company",
    "Company response to consumer",
    "Timely response?",
    "Complaint ID",
)

BANKING77_COLUMNS: Tuple[str, ...] = (
    "text",
    "category",
)


class CSVParseError(Exception):
    """Raised when strict parsing fails on malformed CSV data."""
    pass


@dataclasses.dataclass
class ParseErrorRecord:
    """Record describing a parsing error or anomaly in a source archive."""
    archive_name: str
    file_name: str
    line_number: int
    complaint_id: str
    error_type: str
    error_details: str
    raw_snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ParserDiagnostics:
    """Diagnostics and quality profile gathered during streaming parsing."""
    archive_path: str
    file_name: str
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    multiline_rows: int = 0
    quoted_rows: int = 0
    header: List[str] = dataclasses.field(default_factory=list)
    null_counts: Dict[str, int] = dataclasses.field(default_factory=dict)
    errors: List[ParseErrorRecord] = dataclasses.field(default_factory=list)

    def export_errors_csv(self, output_path: Union[str, Path]) -> None:
        """Exports error log to CSV. If zero errors, writes a header with a verified status row."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = [
            "archive_name",
            "file_name",
            "line_number",
            "complaint_id",
            "error_type",
            "error_details",
            "raw_snippet",
        ]
        
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            if self.errors:
                for err in self.errors:
                    writer.writerow(err.to_dict())
            else:
                # Write an auditable zero-error verification sentinel row
                writer.writerow({
                    "archive_name": os.path.basename(self.archive_path),
                    "file_name": self.file_name,
                    "line_number": 0,
                    "complaint_id": "N/A",
                    "error_type": "verified_zero_errors",
                    "error_details": f"Successfully parsed {self.total_rows:,} records with 0 parse errors.",
                    "raw_snippet": "N/A",
                })


def open_csv_stream(
    source: Union[str, Path, io.IOBase],
    is_zip: Optional[bool] = None,
    inner_csv: Optional[str] = None,
) -> Tuple[Any, io.TextIOBase, str, str, bool]:
    """Opens a text stream from either a direct CSV path, a ZIP archive, or an open IO object.
    
    Returns:
        (container_ref, text_stream, archive_name, inner_file_name, should_close)
    """
    if isinstance(source, (str, Path)):
        source_path = str(source)
        archive_name = os.path.basename(source_path)
        if is_zip or source_path.lower().endswith(".zip"):
            z = zipfile.ZipFile(source_path, mode="r")
            if inner_csv is None:
                csv_candidates = [n for n in z.namelist() if n.lower().endswith(".csv")]
                if not csv_candidates:
                    raise FileNotFoundError(f"No CSV file found inside archive: {source_path}")
                inner_name = csv_candidates[0]
            else:
                inner_name = inner_csv
            raw_stream = z.open(inner_name, mode="r")
            text_stream = io.TextIOWrapper(raw_stream, encoding="utf-8", errors="replace", newline="")
            return z, text_stream, archive_name, inner_name, True
        else:
            f = open(source_path, mode="r", encoding="utf-8", errors="replace", newline="")
            return f, f, archive_name, archive_name, True
    elif isinstance(source, io.IOBase):
        if hasattr(source, "name"):
            name = str(getattr(source, "name"))
        else:
            name = "<stream>"
        if isinstance(source, io.TextIOBase):
            return None, source, name, name, False
        else:
            text_stream = io.TextIOWrapper(source, encoding="utf-8", errors="replace", newline="")
            return None, text_stream, name, name, False
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")


def stream_complaints(
    source: Union[str, Path, io.IOBase],
    is_zip: Optional[bool] = None,
    inner_csv: Optional[str] = None,
    expected_columns: Optional[Sequence[str]] = None,
    max_rows: int = 0,
    on_error: str = "record",
    diagnostics: Optional[ParserDiagnostics] = None,
) -> Generator[Dict[str, str], None, None]:
    """Streams rows from a CFPB complaint CSV or ZIP archive with robust parsing.
    
    Args:
        source: File path (CSV or ZIP) or IO object.
        is_zip: Explicit flag if source is a ZIP archive (auto-detected if None).
        inner_csv: Target CSV file name inside ZIP (auto-detected if None).
        expected_columns: Optional expected column names for schema validation.
        max_rows: Maximum records to yield (0 = unlimited).
        on_error: Policy on malformed rows: 'record' (log & skip), 'raise' (raise CSVParseError), or 'skip'.
        diagnostics: Optional ParserDiagnostics instance to collect profiling metrics.
        
    Yields:
        Dictionary mapping column names to cell string values for each valid row.
    """
    ensure_safe_field_size_limit()
    
    container_ref, text_stream, archive_name, file_name, should_close = open_csv_stream(
        source, is_zip=is_zip, inner_csv=inner_csv
    )
    
    try:
        reader = csv.reader(text_stream)
        try:
            raw_header = next(reader)
        except StopIteration:
            return

        # Strip any UTF-8 BOM from the first column if present
        header = [col.lstrip("\ufeff").strip() for col in raw_header]
        col_count = len(header)
        
        # Check expected schema if requested
        if expected_columns is not None:
            expected_list = list(expected_columns)
            if header != expected_list:
                msg = f"Schema mismatch in {file_name}: Expected {expected_list}, got {header}"
                if on_error == "raise":
                    raise CSVParseError(msg)
        
        narrative_idx = header.index("Consumer complaint narrative") if "Consumer complaint narrative" in header else -1
        complaint_id_idx = header.index("Complaint ID") if "Complaint ID" in header else -1
        
        if diagnostics is not None:
            diagnostics.archive_path = archive_name
            diagnostics.file_name = file_name
            diagnostics.header = header
            diagnostics.null_counts = {col: 0 for col in header}
        
        yielded_count = 0
        line_num = 1
        
        for row in reader:
            line_num += 1
            if diagnostics is not None:
                diagnostics.total_rows += 1
            
            # Detect malformed column counts
            if len(row) != col_count:
                error_msg = f"Column count mismatch: expected {col_count}, got {len(row)}"
                cid = row[complaint_id_idx] if (0 <= complaint_id_idx < len(row)) else "UNKNOWN"
                snippet = " | ".join(row[:3])[:200]
                
                if diagnostics is not None:
                    diagnostics.error_rows += 1
                    diagnostics.errors.append(ParseErrorRecord(
                        archive_name=archive_name,
                        file_name=file_name,
                        line_number=line_num,
                        complaint_id=cid,
                        error_type="column_count_mismatch",
                        error_details=error_msg,
                        raw_snippet=snippet,
                    ))
                
                if on_error == "raise":
                    raise CSVParseError(f"Line {line_num}: {error_msg} (Snippet: {snippet})")
                elif on_error in ("record", "skip"):
                    continue
            
            # Track multiline narratives, quotes, and null counts
            if diagnostics is not None:
                diagnostics.valid_rows += 1
                for c_i, val in enumerate(row):
                    if not val.strip():
                        diagnostics.null_counts[header[c_i]] += 1
                
                if narrative_idx >= 0:
                    narr = row[narrative_idx]
                    if narr:
                        if "\n" in narr or "\r" in narr:
                            diagnostics.multiline_rows += 1
                        if '"' in narr:
                            diagnostics.quoted_rows += 1
            
            row_dict = dict(zip(header, row))
            yield row_dict
            yielded_count += 1
            
            if max_rows and yielded_count >= max_rows:
                break
                
    finally:
        if should_close:
            try:
                text_stream.close()
            except Exception:
                pass
            if container_ref is not None and hasattr(container_ref, "close"):
                try:
                    container_ref.close()
                except Exception:
                    pass


def scan_and_profile(
    archive_path: Union[str, Path],
    inner_csv: Optional[str] = None,
    max_rows: int = 0,
) -> ParserDiagnostics:
    """Scans and profiles an entire CSV or ZIP archive, returning diagnostic metrics."""
    diag = ParserDiagnostics(archive_path=str(archive_path), file_name="")
    gen = stream_complaints(
        source=archive_path,
        inner_csv=inner_csv,
        max_rows=max_rows,
        on_error="record",
        diagnostics=diag,
    )
    for _ in gen:
        pass
    return diag
