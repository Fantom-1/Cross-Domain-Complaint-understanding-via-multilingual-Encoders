"""Intent mapping from raw source labels to canonical project taxonomy.

Implements rule-based semantic mapping following DATA_PREPARATION_SPEC.md.
Preserves original source label while assigning project intent label and id.
Exports data/manifests/source_label_mapping.csv.
"""

import csv
import json
import os
from typing import Dict, Optional, Tuple

TAXONOMY_PATH = "configs/taxonomy.json"
LABEL_MAPPING_PATH = "data/manifests/source_label_mapping.csv"
LABEL_MAPPING_COLUMNS = [
    "source_dataset",
    "source_label",
    "source_label_definition",
    "project_intent_label",
    "mapping_status",
    "rationale",
    "evidence_url",
    "reviewer",
    "review_date",
    "notes"
]


def load_taxonomy(path: str = TAXONOMY_PATH) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class IntentMapper:
    def __init__(self, taxonomy_path: str = TAXONOMY_PATH):
        self.taxonomy = load_taxonomy(taxonomy_path)
        self.classes = self.taxonomy["classes"]
        self.label_to_id = {c["intent_label"]: c["intent_id"] for c in self.classes}
        self.seen_mappings = {}  # (dataset, source_label) -> dict

    def map_cfpb_issue(self, issue: str, sub_issue: str) -> Tuple[Optional[str], Optional[int], str]:
        """Maps CFPB issue + sub-issue to canonical intent.
        
        Returns:
            (project_intent_label, intent_id, mapping_status)
        """
        haystack = f"{issue or ''} || {sub_issue or ''}".lower()
        
        for cls in self.classes:
            for pattern in cls["rule_patterns"]:
                if pattern in haystack:
                    label = cls["intent_label"]
                    intent_id = cls["intent_id"]
                    source_key = f"{issue} // {sub_issue}" if sub_issue else (issue or "Unknown")
                    if source_key not in self.seen_mappings:
                        self.seen_mappings[source_key] = {
                            "source_dataset": "CFPB Consumer Complaint Database",
                            "source_label": source_key,
                            "source_label_definition": cls["definition"],
                            "project_intent_label": label,
                            "mapping_status": "mapped",
                            "rationale": f"Matched pattern '{pattern}' in issue/sub-issue text",
                            "evidence_url": "https://cfpb.github.io/api/ccdb/release-notes.html",
                            "reviewer": "automated_rule_engine",
                            "review_date": "2026-10-22",
                            "notes": f"Mapped to intent_id {intent_id}"
                        }
                    return label, intent_id, "mapped"
        
        source_key = f"{issue} // {sub_issue}" if sub_issue else (issue or "Unknown")
        if source_key not in self.seen_mappings:
            self.seen_mappings[source_key] = {
                "source_dataset": "CFPB Consumer Complaint Database",
                "source_label": source_key,
                "source_label_definition": "Unmapped CFPB category",
                "project_intent_label": "unmapped",
                "mapping_status": "unmapped",
                "rationale": "No qualifying taxonomy pattern matched; excluded from closed-set baseline.",
                "evidence_url": "https://cfpb.github.io/api/ccdb/release-notes.html",
                "reviewer": "automated_rule_engine",
                "review_date": "2026-10-22",
                "notes": "Excluded to maintain label precision"
            }
        return None, None, "unmapped"

    def export_source_label_mapping(self, path: str = LABEL_MAPPING_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=LABEL_MAPPING_COLUMNS)
            writer.writeheader()
            for key, row in sorted(self.seen_mappings.items()):
                writer.writerow(row)
        print(f"Exported {len(self.seen_mappings)} source-label mappings to {path}")
