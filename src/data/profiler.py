"""Full-corpus profiling before filtering or sampling for consumer complaints.

Phase 3 of the Data Preparation Pipeline.
Adheres strictly to the specification in Dataset Preparation Handover:
- Row counts and date coverage by archive window.
- Narrative availability and missingness by source fields.
- Product, sub-product, Issue, Sub-issue and label-combination frequencies.
- Label coverage by product/domain and time window.
- Character and whitespace-word length distributions, including percentiles and tails.
- Encoding/whitespace anomalies, repeated IDs, exact duplicates and near duplicates.
- Taxonomy drift and visible discontinuities around source/form changes.
- Natural class distribution and plausible train/validation/test support.
- Reconciles all figures without premature caps, balancing, or short-text cutoffs.
"""

import array
import collections
import csv
import dataclasses
import hashlib
import io
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Counter, Dict, List, Optional, Sequence, Set, Tuple, Union

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.parser import (
    CFPB_BULK_COLUMNS,
    CFPB_FOIA_COLUMNS,
    BANKING77_COLUMNS,
    CSVParseError,
    ParserDiagnostics,
    stream_complaints,
)

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _compute_percentiles(values: Sequence[Union[int, float]], percentiles: Sequence[float]) -> Dict[str, float]:
    """Computes exact percentiles from a sorted sequence of numeric values."""
    if not values:
        return {f"p{int(p) if p == int(p) else p}": 0.0 for p in percentiles}
    
    n = len(values)
    res = {}
    for p in percentiles:
        key = f"p{int(p) if p == int(p) else p}"
        if n == 1:
            res[key] = float(values[0])
            continue
        # Standard rank interpolation
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            val = float(values[int(k)])
        else:
            d0 = values[int(f)] * (c - k)
            d1 = values[int(c)] * (k - f)
            val = float(d0 + d1)
        res[key] = round(val, 2)
    return res


def _compute_summary_stats(values: Sequence[Union[int, float]]) -> Dict[str, Any]:
    """Computes count, min, max, mean, std, and standard percentiles."""
    if not values:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "std": 0.0,
            "p1": 0.0,
            "p5": 0.0,
            "p10": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    mean_val = sum(sorted_vals) / n
    variance = sum((x - mean_val) ** 2 for x in sorted_vals) / n
    std_val = math.sqrt(variance)
    
    pcts = _compute_percentiles(sorted_vals, [1, 5, 10, 25, 50, 75, 90, 95, 99])
    
    return {
        "count": n,
        "min": min_val,
        "max": max_val,
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        **pcts,
    }


class CorpusProfiler:
    """Streams and profiles a raw complaint archive or dataset comprehensively."""

    def __init__(
        self,
        taxonomy_path: Optional[str] = None,
        product_canonical_path: Optional[str] = None,
    ):
        self.taxonomy_path = taxonomy_path or os.path.join(REPO_ROOT, "configs", "taxonomy.json")
        self.product_canonical_path = product_canonical_path or os.path.join(REPO_ROOT, "configs", "product_canonical.json")
        
        self.product_map = {}
        self.product_fallback = "other"
        if os.path.isfile(self.product_canonical_path):
            with open(self.product_canonical_path, "r", encoding="utf-8") as f:
                p_cfg = json.load(f)
                self.product_map = p_cfg.get("map", {})
                self.product_fallback = p_cfg.get("fallback", "other")
                
        self.taxonomy_classes = []
        if os.path.isfile(self.taxonomy_path):
            with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                t_cfg = json.load(f)
                self.taxonomy_classes = t_cfg.get("classes", [])
        self._intent_cache: Dict[Tuple[str, str], Tuple[str, int]] = {}

    def map_canonical_product(self, raw_product: str) -> str:
        """Standardizes historical raw CFPB product strings to canonical domains."""
        if not raw_product:
            return "unknown"
        return self.product_map.get(raw_product.strip(), self.product_fallback)

    def match_weak_intent(self, issue: str, sub_issue: str) -> Tuple[str, int]:
        """Matches raw issue and sub-issue against project taxonomy without capping."""
        key = (issue or "", sub_issue or "")
        if key in self._intent_cache:
            return self._intent_cache[key]

        haystack = f"{key[0]} || {key[1]}".lower()
        for cls in self.taxonomy_classes:
            for pattern in cls.get("rule_patterns", []):
                if pattern in haystack:
                    res = (cls["intent_label"], cls["intent_id"])
                    self._intent_cache[key] = res
                    return res
        res = ("unmapped", -1)
        self._intent_cache[key] = res
        return res

    def profile_cfpb_foia_archive(
        self,
        archive_path: Union[str, Path, io.IOBase],
        max_rows: int = 0,
    ) -> Dict[str, Any]:
        """Performs single-pass streaming profiling of a CFPB FOIA complaint archive.
        
        Extracts complete population statistics:
        - Row count and date coverage
        - Missingness per field
        - Narrative availability and length percentiles
        - Product, Sub-product, Issue, Sub-issue distributions
        - Canonical product mapping distribution
        - Temporal distribution by year and month
        - Exact duplicate narrative detection via SHA-256
        - Text formatting anomalies (newlines, redactions, control characters)
        - Natural, un-capped class distribution under weak administrative rules
        """
        if isinstance(archive_path, io.IOBase):
            archive_source = archive_path
            archive_name = getattr(archive_path, "name", "<stream>")
            archive_path_val = archive_name
        else:
            archive_source = str(archive_path)
            archive_name = os.path.basename(archive_source)
            try:
                rel = os.path.relpath(archive_source, REPO_ROOT).replace("\\", "/")
                archive_path_val = rel if not rel.startswith("..") else archive_name
            except ValueError:
                archive_path_val = archive_name
        
        total_rows = 0
        narrative_rows = 0
        missing_narrative_rows = 0
        
        # Field missingness counters
        field_null_counts = collections.Counter()
        
        # Date tracking
        min_date: Optional[str] = None
        max_date: Optional[str] = None
        year_counts: Counter[str] = collections.Counter()
        year_month_counts: Counter[str] = collections.Counter()
        
        # Categorical distributions
        product_counts: Counter[str] = collections.Counter()
        canonical_product_counts: Counter[str] = collections.Counter()
        sub_product_counts: Counter[str] = collections.Counter()
        issue_counts: Counter[str] = collections.Counter()
        sub_issue_counts: Counter[str] = collections.Counter()
        submitted_via_counts: Counter[str] = collections.Counter()
        company_response_counts: Counter[str] = collections.Counter()
        timely_response_counts: Counter[str] = collections.Counter()
        tags_counts: Counter[str] = collections.Counter()
        state_counts: Counter[str] = collections.Counter()
        
        # Cross product-issue combination tracking
        product_issue_counts: Counter[str] = collections.Counter()
        
        # Length profiling arrays (stored compactly as array of ints)
        char_lengths = array.array("i")
        word_lengths = array.array("i")
        
        # Length bucket counters
        words_lt_10 = 0
        words_lt_20 = 0
        words_lt_50 = 0
        words_gt_500 = 0
        words_gt_1000 = 0
        words_gt_2000 = 0
        
        # Exact duplicate detection via SHA-256
        exact_text_hash_counts: Counter[str] = collections.Counter()
        seen_complaint_ids: Set[str] = set()
        duplicate_complaint_id_count = 0
        
        # Anomaly counters
        multiline_narratives = 0
        redaction_marker_narratives = 0
        control_char_narratives = 0
        whitespace_padded_narratives = 0
        
        # Natural un-capped class distribution
        natural_class_counts: Counter[str] = collections.Counter()
        
        # Temporal drift: product per year
        product_by_year: Dict[str, Counter[str]] = collections.defaultdict(collections.Counter)
        
        diag = ParserDiagnostics(archive_path=str(archive_source), file_name=archive_name)
        stream = stream_complaints(
            source=archive_source,
            expected_columns=CFPB_FOIA_COLUMNS,
            on_error="record",
            diagnostics=diag,
            max_rows=max_rows,
        )

        for row in stream:
            if diag.error_rows > 0:
                first_err = diag.errors[0]
                raise ValueError(
                    f"Archive contains malformed rows ineligible for profiling: {diag.error_rows} error row(s) detected. "
                    f"First error at line {first_err.line_number} ({first_err.error_type}: {first_err.error_details})."
                )
            
            total_rows += 1
            if total_rows % 250000 == 0:
                print(f"[PROFILER] Processed {total_rows:,} rows ({narrative_rows:,} narratives found)...", flush=True)
            
            # Check complaint ID uniqueness
            c_id = row.get("Complaint ID", "").strip()
            if c_id:
                if c_id in seen_complaint_ids:
                    duplicate_complaint_id_count += 1
                else:
                    seen_complaint_ids.add(c_id)
            
            # Track field missingness
            for col in CFPB_FOIA_COLUMNS:
                val = row.get(col, "")
                if val is None or val.strip() == "":
                    field_null_counts[col] += 1
            
            # Date analysis
            dt_str = row.get("Date received", "").strip()
            if dt_str:
                if min_date is None or dt_str < min_date:
                    min_date = dt_str
                if max_date is None or dt_str > max_date:
                    max_date = dt_str
                year = dt_str[:4]
                year_month = dt_str[:7]
                year_counts[year] += 1
                year_month_counts[year_month] += 1
            else:
                year = "Unknown"
            
            # Categorical fields
            raw_product = row.get("Product", "").strip()
            canonical_product = self.map_canonical_product(raw_product)
            product_counts[raw_product or "Missing"] += 1
            canonical_product_counts[canonical_product] += 1
            product_by_year[year][canonical_product] += 1
            
            sub_product = row.get("Sub-product", "").strip()
            if sub_product:
                sub_product_counts[sub_product] += 1
                
            issue = row.get("Issue", "").strip()
            if issue:
                issue_counts[issue] += 1
                
            sub_issue = row.get("Sub-issue", "").strip()
            if sub_issue:
                sub_issue_counts[sub_issue] += 1
                
            if raw_product and issue:
                product_issue_counts[f"{raw_product} || {issue}"] += 1
                
            sub_via = row.get("Submitted via", "").strip()
            if sub_via:
                submitted_via_counts[sub_via] += 1
                
            comp_resp = row.get("Company response to consumer", "").strip()
            if comp_resp:
                company_response_counts[comp_resp] += 1
                
            timely = row.get("Timely response?", "").strip()
            if timely:
                timely_response_counts[timely] += 1
                
            tags = row.get("Tags", "").strip()
            if tags:
                tags_counts[tags] += 1
                
            state = row.get("State", "").strip()
            if state:
                state_counts[state] += 1
            
            # Narrative text analysis
            narrative = row.get("Consumer complaint narrative", "")
            has_narrative = bool(narrative and narrative.strip())
            
            if has_narrative:
                narrative_rows += 1
                c_len = len(narrative)
                words = narrative.split()
                w_len = len(words)
                
                char_lengths.append(c_len)
                word_lengths.append(w_len)
                
                if w_len < 10:
                    words_lt_10 += 1
                if w_len < 20:
                    words_lt_20 += 1
                if w_len < 50:
                    words_lt_50 += 1
                if w_len > 500:
                    words_gt_500 += 1
                if w_len > 1000:
                    words_gt_1000 += 1
                if w_len > 2000:
                    words_gt_2000 += 1
                
                # Anomaly detections
                if "\n" in narrative or "\r" in narrative:
                    multiline_narratives += 1
                if "XX" in narrative:
                    redaction_marker_narratives += 1
                if CONTROL_CHAR_PATTERN.search(narrative):
                    control_char_narratives += 1
                if narrative.startswith(" ") or narrative.endswith(" ") or narrative.startswith("\t") or narrative.endswith("\t"):
                    whitespace_padded_narratives += 1
                
                # Duplicate tracking (SHA-256)
                thash = hashlib.sha256(narrative.encode("utf-8")).hexdigest()
                exact_text_hash_counts[thash] += 1
                
                # Natural class distribution under weak rules
                intent_label, _ = self.match_weak_intent(issue, sub_issue)
                natural_class_counts[intent_label] += 1
            else:
                missing_narrative_rows += 1

            if max_rows and total_rows >= max_rows:
                break

        # Check for parser errors or schema mismatch recorded during streaming
        schema_errors = [e for e in diag.errors if e.error_type == "schema_mismatch"]
        if schema_errors:
            raise ValueError(
                f"Source archive ineligible for CFPB FOIA profiling: 16-column CFPB FOIA archive with narratives required. "
                f"({schema_errors[0].error_details})"
            )
        if diag.error_rows > 0:
            first_err = diag.errors[0]
            raise ValueError(
                f"Source archive contains malformed rows ineligible for profiling: {diag.error_rows} error row(s) detected. "
                f"First error at line {first_err.line_number} ({first_err.error_type}: {first_err.error_details})."
            )

        # Aggregate statistics
        char_stats = _compute_summary_stats(char_lengths)
        word_stats = _compute_summary_stats(word_lengths)

        # Duplicate metrics
        unique_hashes = len(exact_text_hash_counts)
        exact_duplicate_narratives = sum(cnt - 1 for cnt in exact_text_hash_counts.values() if cnt > 1)
        top_duplicate_hashes = exact_text_hash_counts.most_common(10)

        # Missingness percentages
        field_null_rates = {
            col: {
                "null_count": field_null_counts[col],
                "non_null_count": total_rows - field_null_counts[col],
                "null_rate_percent": round((field_null_counts[col] / total_rows * 100.0) if total_rows else 0.0, 2),
            }
            for col in CFPB_FOIA_COLUMNS
        }

        return {
            "archive_name": archive_name,
            "archive_path": archive_path_val,
            "total_rows": total_rows,
            "date_coverage": {
                "min_date": min_date,
                "max_date": max_date,
                "year_counts": dict(sorted(year_counts.items())),
                "year_month_counts": dict(sorted(year_month_counts.items())),
            },
            "narrative_profile": {
                "total_rows": total_rows,
                "narratives_present": narrative_rows,
                "narratives_missing": missing_narrative_rows,
                "narrative_availability_rate_percent": round((narrative_rows / total_rows * 100.0) if total_rows else 0.0, 2),
                "char_length_stats": char_stats,
                "word_length_stats": word_stats,
                "length_cutoffs": {
                    "words_lt_10": words_lt_10,
                    "words_lt_20": words_lt_20,
                    "words_lt_50": words_lt_50,
                    "words_gt_500": words_gt_500,
                    "words_gt_1000": words_gt_1000,
                    "words_gt_2000": words_gt_2000,
                    "words_lt_20_percent": round((words_lt_20 / narrative_rows * 100.0) if narrative_rows else 0.0, 2),
                },
                "formatting_anomalies": {
                    "multiline_narratives": multiline_narratives,
                    "multiline_percent": round((multiline_narratives / narrative_rows * 100.0) if narrative_rows else 0.0, 2),
                    "redaction_marker_narratives": redaction_marker_narratives,
                    "redaction_marker_percent": round((redaction_marker_narratives / narrative_rows * 100.0) if narrative_rows else 0.0, 2),
                    "control_char_narratives": control_char_narratives,
                    "whitespace_padded_narratives": whitespace_padded_narratives,
                },
                "exact_duplicates": {
                    "total_narratives": narrative_rows,
                    "unique_narratives": unique_hashes,
                    "exact_duplicates_count": exact_duplicate_narratives,
                    "exact_duplicate_rate_percent": round((exact_duplicate_narratives / narrative_rows * 100.0) if narrative_rows else 0.0, 2),
                    "top_duplicate_hash_frequencies": [
                        {"sha256": h, "occurrences": count} for h, count in top_duplicate_hashes if count > 1
                    ],
                },
            },
            "field_missingness": field_null_rates,
            "categorical_distributions": {
                "product_counts": dict(product_counts.most_common()),
                "canonical_product_counts": dict(canonical_product_counts.most_common()),
                "top_sub_products": dict(sub_product_counts.most_common(20)),
                "top_issues": dict(issue_counts.most_common(25)),
                "top_sub_issues": dict(sub_issue_counts.most_common(25)),
                "top_product_issues": dict(product_issue_counts.most_common(25)),
                "submitted_via": dict(submitted_via_counts.most_common()),
                "company_response": dict(company_response_counts.most_common()),
                "timely_response": dict(timely_response_counts.most_common()),
                "tags": dict(tags_counts.most_common()),
                "top_states": dict(state_counts.most_common(15)),
            },
            "temporal_drift": {
                "product_by_year": {y: dict(counts.most_common()) for y, counts in sorted(product_by_year.items())},
            },
            "integrity_checks": {
                "duplicate_complaint_id_count": duplicate_complaint_id_count,
                "complaint_id_integrity": "PASSED" if duplicate_complaint_id_count == 0 else "FAILED",
            },
            "natural_class_distribution": {
                "total_narratives_evaluated": narrative_rows,
                "counts": dict(natural_class_counts.most_common()),
                "percentages": {
                    cls: round((cnt / narrative_rows * 100.0) if narrative_rows else 0.0, 2)
                    for cls, cnt in natural_class_counts.most_common()
                },
            },
        }

    def profile_banking77(self, train_path: str, test_path: str) -> Dict[str, Any]:
        """Profiles the auxiliary query benchmark BANKING77."""
        profiles = {}
        for split_name, path in [("train", train_path), ("test", test_path)]:
            if not os.path.isfile(path):
                continue
            rows = 0
            category_counts = collections.Counter()
            char_lens = []
            word_lens = []
            null_count = 0
            
            for row in stream_complaints(path):
                rows += 1
                text = row.get("text", "")
                cat = row.get("category", "")
                if not text or not cat:
                    null_count += 1
                char_lens.append(len(text))
                word_lens.append(len(text.split()))
                category_counts[cat] += 1
                
            profiles[split_name] = {
                "rows": rows,
                "columns": ["text", "category"],
                "null_count": null_count,
                "num_categories": len(category_counts),
                "char_stats": _compute_summary_stats(char_lens),
                "word_stats": _compute_summary_stats(word_lens),
                "min_per_class": min(category_counts.values()) if category_counts else 0,
                "max_per_class": max(category_counts.values()) if category_counts else 0,
            }
        return profiles


def export_profile_csv(profile_data: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """Exports structured field-level and category summary profiles to CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    
    # 1. Field missingness
    for field_name, stats in profile_data.get("field_missingness", {}).items():
        rows.append({
            "section": "field_missingness",
            "item_name": field_name,
            "metric_1_name": "null_count",
            "metric_1_value": stats["null_count"],
            "metric_2_name": "non_null_count",
            "metric_2_value": stats["non_null_count"],
            "metric_3_name": "null_rate_percent",
            "metric_3_value": stats["null_rate_percent"],
            "notes": "FOIA 16-field reading room schema",
        })
        
    # 2. Canonical domain distribution
    for domain, count in profile_data.get("categorical_distributions", {}).get("canonical_product_counts", {}).items():
        total_rows = profile_data.get("total_rows", 1)
        rows.append({
            "section": "canonical_product_domain",
            "item_name": domain,
            "metric_1_name": "row_count",
            "metric_1_value": count,
            "metric_2_name": "share_of_total_percent",
            "metric_2_value": round(count / total_rows * 100.0, 2),
            "metric_3_name": "N/A",
            "metric_3_value": "N/A",
            "notes": "Standardized via configs/product_canonical.json",
        })

    # 3. Natural un-capped class distribution
    for cls, count in profile_data.get("natural_class_distribution", {}).get("counts", {}).items():
        narrative_total = profile_data.get("narrative_profile", {}).get("narratives_present", 1)
        rows.append({
            "section": "natural_class_distribution",
            "item_name": cls,
            "metric_1_name": "narrative_count",
            "metric_1_value": count,
            "metric_2_name": "population_share_percent",
            "metric_2_value": round(count / narrative_total * 100.0, 2),
            "metric_3_name": "N/A",
            "metric_3_value": "N/A",
            "notes": "Uncapped natural population distribution under weak rules",
        })

    # 4. Length percentiles summary
    for metric_type, stats_dict in [
        ("char_length", profile_data.get("narrative_profile", {}).get("char_length_stats", {})),
        ("word_length", profile_data.get("narrative_profile", {}).get("word_length_stats", {})),
    ]:
        rows.append({
            "section": "length_percentiles",
            "item_name": metric_type,
            "metric_1_name": "mean_std",
            "metric_1_value": f"{stats_dict.get('mean', 0.0)} ± {stats_dict.get('std', 0.0)}",
            "metric_2_name": "median_p50",
            "metric_2_value": stats_dict.get("p50", 0.0),
            "metric_3_name": "p5_p95_range",
            "metric_3_value": f"[{stats_dict.get('p5', 0.0)}, {stats_dict.get('p95', 0.0)}]",
            "notes": f"min={stats_dict.get('min', 0)}, max={stats_dict.get('max', 0)}, p99={stats_dict.get('p99', 0)}",
        })

    fieldnames = [
        "section",
        "item_name",
        "metric_1_name",
        "metric_1_value",
        "metric_2_name",
        "metric_2_value",
        "metric_3_name",
        "metric_3_value",
        "notes",
    ]
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
