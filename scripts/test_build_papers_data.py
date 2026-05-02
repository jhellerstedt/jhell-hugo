import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_papers_data  # noqa: E402


class TestFeedCategoryFromDescription(unittest.TestCase):
    def test_extracts_category_when_suffix_present(self) -> None:
        desc = "LLM-filtered feed (biomedical_signal_processing) — category: physics"
        self.assertEqual(build_papers_data.extract_feed_category(desc), "physics")

    def test_falls_back_when_no_category_suffix(self) -> None:
        desc = "LLM-filtered feed (biomedical_signal_processing) — no category"
        self.assertEqual(
            build_papers_data.extract_feed_category(desc),
            build_papers_data.UNCATEGORIZED_CATEGORY,
        )

    def test_tolerant_whitespace_and_first_token_only(self) -> None:
        desc = "LLM-filtered feed (foo)  —  category:  neuroscience  extra"
        self.assertEqual(build_papers_data.extract_feed_category(desc), "neuroscience")

    def test_empty_description(self) -> None:
        self.assertEqual(
            build_papers_data.extract_feed_category(""),
            build_papers_data.UNCATEGORIZED_CATEGORY,
        )


if __name__ == "__main__":
    unittest.main()
