import unittest

from src.summarization.structured_summarizer import summarize_complaint


class StructuredSummarizerTests(unittest.TestCase):
    def test_output_is_source_grounded(self):
        text = (
            "I contacted my bank on March 4, 2026. The bank charged me twice for one transaction. "
            "I called customer support and received no response. I want the duplicate charge refunded."
        )
        result = summarize_complaint(text)
        self.assertIn("problem", result)
        self.assertTrue(result["timeline_and_events"])
        self.assertTrue(result["requested_resolution"])
        for field in ("customer_concern", "timeline_and_events", "requested_resolution", "supporting_evidence"):
            for item in result[field]:
                self.assertIn(item["text"], text)

    def test_empty_input_fails(self):
        with self.assertRaises(ValueError):
            summarize_complaint("   ")


if __name__ == "__main__":
    unittest.main()
