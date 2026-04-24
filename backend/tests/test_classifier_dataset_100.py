"""Regression: 100 curated user snippets vs frozen expected routing (JSON fixture)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.core.legal_classifier import classify_legal_issue

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "classifier_dataset_100.json"


class TestClassifierDataset100(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = _FIXTURE.read_text(encoding="utf-8")
        cls._payload = json.loads(raw)
        cls._cases = cls._payload["cases"]
        assert len(cls._cases) == 100, len(cls._cases)

    def test_fixture_has_100_rows(self) -> None:
        self.assertEqual(self._payload.get("version"), 1)
        self.assertEqual(len(self._cases), 100)

    def test_each_row_matches_classifier(self) -> None:
        for row in self._cases:
            text = row["text"]
            with self.subTest(id=row.get("id"), text=text[:70]):
                lc, meta = classify_legal_issue(text)
                self.assertEqual(lc["issue_type"], row["issue_type"])
                self.assertEqual(meta.get("domain"), row["domain"])
                self.assertEqual(meta.get("router_intent"), row["router_intent"])
                self.assertEqual(lc["sub_type"], row["sub_type"])
                self.assertEqual(lc["severity"], row["severity"])
                self.assertEqual(lc["jurisdiction_type"], row["jurisdiction_type"])


if __name__ == "__main__":
    unittest.main()
