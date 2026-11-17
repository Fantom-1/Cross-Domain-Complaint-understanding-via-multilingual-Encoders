import csv
import tempfile
import unittest
from pathlib import Path

from src.data.split_analyzer import SplitAnalyzer


class Phase7DefaultClusterCoverageTests(unittest.TestCase):
    def test_required_cluster_manifest_defaults_to_full_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            split = root / "split.csv"
            clusters = root / "clusters.csv"
            with split.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["example_id","split","intent_label","domain","group_id"])
                writer.writeheader()
                writer.writerows([
                    {"example_id":"a","split":"train","intent_label":"account_access","domain":"bank_account","group_id":"g1"},
                    {"example_id":"b","split":"train","intent_label":"account_access","domain":"bank_account","group_id":"g2"},
                ])
            with clusters.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["example_id","cluster_id"])
                writer.writeheader()
                writer.writerow({"example_id":"a","cluster_id":"c1"})
            analyzer = SplitAnalyzer(
                parquet_path=str(root / "missing.parquet"),
                clusters_path=str(clusters),
                split_indomain_path=str(split),
            )
            with self.assertRaisesRegex(ValueError, "Incomplete cluster mapping coverage"):
                analyzer.audit_in_distribution_split(
                    split_csv_path=str(split),
                    clusters_csv_path=str(clusters),
                    validate_canonical=False,
                    require_cluster_manifest=True,
                )


if __name__ == "__main__":
    unittest.main()
