"""Automated Phase 1 verification suite: Source Provenance and Release Manifest.

Enforces:
1. Exact 20-column schema for data/manifests/dataset_inventory.csv.
2. Complete catalog of all 21 CFPB FOIA narrative archive windows, bulk complaints, and BANKING77.
3. Strict chronological window contiguity (2011-12-01 to 2026-08-14) with zero gaps and zero overlap.
4. Release overlap report schema and zero pairwise record-ID overlap against Export 2.
5. Schema discrepancy enforcement: 16 columns (with narrative) in FOIA archives vs 15 columns (without narrative) in active bulk.
6. Cryptographic integrity of local baseline archive.
7. Verification of source terms and governance documentation.
"""

import csv
import hashlib
import os
import unittest
from datetime import datetime
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INVENTORY_CSV = os.path.join(REPO_ROOT, "data", "manifests", "dataset_inventory.csv")
OVERLAP_CSV = os.path.join(REPO_ROOT, "data", "manifests", "release_overlap_report.csv")
DOCS_PROVENANCE = os.path.join(REPO_ROOT, "docs", "source_terms_and_provenance.md")
LOCAL_EXPORT_2 = os.path.join(REPO_ROOT, "data", "raw", "cfpb", "CCDB_Export_2_May_2018_through_April_2021.zip")

REQUIRED_INVENTORY_COLUMNS = [
    "source_dataset",
    "source_url",
    "local_path",
    "file_name",
    "file_format",
    "source_version",
    "release_date",
    "retrieval_date",
    "license",
    "license_url",
    "checksum_sha256",
    "rows",
    "columns",
    "split",
    "language",
    "domain",
    "role_decision",
    "decision_rationale",
    "status",
    "notes",
]

REQUIRED_OVERLAP_COLUMNS = [
    "release_id",
    "source_name",
    "file_name",
    "source_url",
    "window_start_date",
    "window_end_date",
    "window_duration_days",
    "compressed_size_bytes",
    "has_narratives",
    "column_count",
    "export2_id_overlap_count",
    "export2_id_overlap_pct",
    "overlap_relationship",
    "role_decision",
    "notes",
]


class TestPhase1Provenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.path.exists(INVENTORY_CSV), f"Missing {INVENTORY_CSV}"
        assert os.path.exists(OVERLAP_CSV), f"Missing {OVERLAP_CSV}"
        assert os.path.exists(DOCS_PROVENANCE), f"Missing {DOCS_PROVENANCE}"
        assert os.path.exists(LOCAL_EXPORT_2), f"Missing {LOCAL_EXPORT_2}"

        cls.df_inventory = pd.read_csv(INVENTORY_CSV)
        cls.df_overlap = pd.read_csv(OVERLAP_CSV)

    def test_01_dataset_inventory_schema(self):
        """Validates that dataset_inventory.csv contains exactly the 20 columns specified in DATA_PREPARATION_SPEC.md."""
        actual_cols = list(self.df_inventory.columns)
        self.assertEqual(
            actual_cols,
            REQUIRED_INVENTORY_COLUMNS,
            f"Inventory columns mismatch! Extra: {set(actual_cols) - set(REQUIRED_INVENTORY_COLUMNS)}, Missing: {set(REQUIRED_INVENTORY_COLUMNS) - set(actual_cols)}",
        )

    def test_02_dataset_inventory_completeness(self):
        """Ensures all 21 CFPB FOIA exports, active bulk dump, and 3 BANKING77 components are present (25 total)."""
        self.assertEqual(len(self.df_inventory), 25, f"Expected 25 inventory entries, got {len(self.df_inventory)}")

        cfpb_foia_entries = self.df_inventory[
            self.df_inventory["source_dataset"].str.contains("FOIA", case=False, na=False)
        ]
        self.assertEqual(len(cfpb_foia_entries), 21, f"Expected 21 FOIA export windows, got {len(cfpb_foia_entries)}")

        b77_entries = self.df_inventory[self.df_inventory["source_dataset"] == "BANKING77"]
        self.assertEqual(len(b77_entries), 3, f"Expected 3 BANKING77 components, got {len(b77_entries)}")

        bulk_entries = self.df_inventory[
            self.df_inventory["source_dataset"].str.contains("Active Daily Feed", case=False, na=False)
        ]
        self.assertEqual(len(bulk_entries), 1, "Expected 1 active bulk complaints entry")

    def test_03_cfpb_foia_metadata_integrity(self):
        """Verifies URLs, public domain licensing, and status of FOIA narrative archives."""
        foia_rows = self.df_inventory[
            self.df_inventory["source_dataset"].str.contains("FOIA", case=False, na=False)
        ]
        for _, row in foia_rows.iterrows():
            self.assertTrue(
                row["source_url"].startswith("https://files.consumerfinance.gov/f/documents/CCDB_Export_"),
                f"Invalid URL for {row['file_name']}: {row['source_url']}",
            )
            self.assertEqual(row["file_format"], "csv.zip")
            self.assertEqual(row["license"], "Public Domain (US Government Work)")
            self.assertEqual(row["role_decision"], "primary_eligible")

    def test_04_chronological_windows_contiguity_and_zero_overlap(self):
        """Ensures that the 21 export windows strictly connect day-to-day from 2011-12-01 to 2026-08-14 with zero gaps."""
        foia_overlap = self.df_overlap[self.df_overlap["release_id"].str.startswith("CCDB_Export_")].copy()
        self.assertEqual(len(foia_overlap), 21)

        # Sort by release_id
        foia_overlap = foia_overlap.sort_values("release_id").reset_index(drop=True)

        # Verify start of first window and end of last window
        self.assertEqual(foia_overlap.iloc[0]["window_start_date"], "2011-12-01")
        self.assertEqual(foia_overlap.iloc[-1]["window_end_date"], "2026-08-14")

        # Verify day-to-day contiguity
        for i in range(len(foia_overlap) - 1):
            end_curr = datetime.strptime(foia_overlap.iloc[i]["window_end_date"], "%Y-%m-%d")
            start_next = datetime.strptime(foia_overlap.iloc[i + 1]["window_start_date"], "%Y-%m-%d")
            day_diff = (start_next - end_curr).days
            self.assertEqual(
                day_diff,
                1,
                f"Contiguity failure between {foia_overlap.iloc[i]['release_id']} and {foia_overlap.iloc[i+1]['release_id']}: difference is {day_diff} days",
            )

    def test_05_release_overlap_report_schema_and_size(self):
        """Verifies release_overlap_report.csv schema and completeness (24 entries)."""
        actual_cols = list(self.df_overlap.columns)
        self.assertEqual(
            actual_cols,
            REQUIRED_OVERLAP_COLUMNS,
            f"Overlap columns mismatch! Extra: {set(actual_cols) - set(REQUIRED_OVERLAP_COLUMNS)}, Missing: {set(REQUIRED_OVERLAP_COLUMNS) - set(actual_cols)}",
        )
        self.assertEqual(len(self.df_overlap), 24, f"Expected 24 overlap rows, got {len(self.df_overlap)}")

    def test_06_release_overlap_invariants(self):
        """Verifies pairwise overlap with baseline snapshot (CCDB_Export_02)."""
        for _, row in self.df_overlap.iterrows():
            rel_id = row["release_id"]
            if rel_id == "CCDB_Export_02":
                self.assertEqual(row["export2_id_overlap_count"], 1041632)
                self.assertEqual(row["export2_id_overlap_pct"], "100.00%")
                self.assertEqual(row["overlap_relationship"], "reference_baseline_active")
            elif rel_id.startswith("CCDB_Export_"):
                self.assertEqual(
                    row["export2_id_overlap_count"],
                    0,
                    f"Non-zero overlap in disjoint window {rel_id}: {row['export2_id_overlap_count']}",
                )
                self.assertEqual(row["export2_id_overlap_pct"], "0.00%")
                self.assertEqual(row["overlap_relationship"], "strictly_disjoint_window")
            elif rel_id == "CCDB_Bulk_Complaints":
                self.assertEqual(row["overlap_relationship"], "metadata_only_superset")
            elif rel_id.startswith("BANKING77"):
                self.assertEqual(row["export2_id_overlap_count"], 0)
                self.assertEqual(row["overlap_relationship"], "isolated_benchmark")

    def test_07_narrative_column_discrepancy(self):
        """Enforces schema difference: 16 columns with narrative in FOIA vs 15 columns without narrative in bulk."""
        bulk_row = self.df_overlap[self.df_overlap["release_id"] == "CCDB_Bulk_Complaints"].iloc[0]
        self.assertEqual(bulk_row["column_count"], 15)
        self.assertEqual(str(bulk_row["has_narratives"]), "False")
        self.assertEqual(bulk_row["role_decision"], "ineligible_lacks_narratives")

        foia_rows = self.df_overlap[self.df_overlap["release_id"].str.startswith("CCDB_Export_")]
        for _, row in foia_rows.iterrows():
            self.assertEqual(row["column_count"], 16)
            self.assertEqual(str(row["has_narratives"]), "True")

    def test_08_local_baseline_sha256(self):
        """Verifies cryptographic hash of local baseline archive matches inventory."""
        hasher = hashlib.sha256()
        with open(LOCAL_EXPORT_2, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()
        expected_hash = "4b33ffc92fa0236836228c5618b7247f0f59ffef35760a45175c858a0d5aaf45"
        self.assertEqual(actual_hash, expected_hash, f"Baseline hash mismatch: {actual_hash} vs {expected_hash}")

    def test_09_docs_provenance_content(self):
        """Verifies that docs/source_terms_and_provenance.md contains key required sections."""
        with open(DOCS_PROVENANCE, "r", encoding="utf-8") as f:
            content = f.read()

        required_snippets = [
            "FOIA Electronic Reading Room",
            "Public Domain (United States Government Work)",
            "17 U.S.C. § 105",
            "August 14, 2026",
            "CCDB_Export_01",
            "CCDB_Export_21",
            "Mathematical Proof",
            "strictly contiguous",
            "BANKING77",
            "Indian Multilingual Evaluation Gap",
        ]
        for snippet in required_snippets:
            self.assertIn(snippet, content, f"Missing required snippet in provenance docs: '{snippet}'")


if __name__ == "__main__":
    unittest.main()
