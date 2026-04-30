import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_papers_data  # noqa: E402


class TestOpenAlexConceptExtraction(unittest.TestCase):
    def test_extracts_concept_when_present(self) -> None:
        desc = (
            "LLM-filtered feed (biomedical_signal_processing) — OpenAlex concept: "
            "Biomedical signal processing"
        )
        self.assertEqual(
            build_papers_data.extract_openalex_concept(desc),
            "Biomedical signal processing",
        )

    def test_falls_back_when_missing(self) -> None:
        desc = "LLM-filtered feed (biomedical_signal_processing)"
        self.assertEqual(
            build_papers_data.extract_openalex_concept(desc),
            build_papers_data.UNCATEGORIZED_CONCEPT,
        )


if __name__ == "__main__":
    unittest.main()

