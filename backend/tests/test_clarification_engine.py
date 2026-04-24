"""Tests for clarification_engine — no OpenAI required."""

import unittest

from app.ai.llm_issue_classifier import merge_issue_profile
from app.core.legal_classifier import classify_legal_issue
from app.services import clarification_engine as ce
from app.services.clarification_engine import needs_clarification
from app.services.legal_taxonomy import LegalClassification


def _tax(lc: dict) -> LegalClassification:
    return {
        "issue_type": lc["issue_type"],
        "severity": lc["severity"],
        "jurisdiction_type": lc["jurisdiction_type"],
        "sub_type": lc.get("sub_type") or "",
    }


class TestClarificationEngine(unittest.TestCase):
    def test_wallet_missing_asks_lost_vs_stolen(self) -> None:
        text = "My wallet is missing"
        lc, meta = classify_legal_issue(text, [], None)
        ip = merge_issue_profile(text, lc, meta, None)
        needed, q, opts, pts = needs_clarification(meta, _tax(lc), ip, text)
        self.assertTrue(needed)
        self.assertIn("stolen", q.lower())
        flat = pts[0]["options"] if pts else opts
        self.assertGreaterEqual(len(flat), 2)

    def test_phone_lost_asks_clarification(self) -> None:
        text = "my phone lost"
        lc, meta = classify_legal_issue(text, [], None)
        ip = merge_issue_profile(text, lc, meta, None)
        needed, _, opts, pts = needs_clarification(meta, _tax(lc), ip, text)
        self.assertTrue(needed)
        flat = pts[0]["options"] if pts else opts
        self.assertTrue(any("lost" in o.lower() for o in flat))

    def test_money_account_ambiguous(self) -> None:
        text = "Money gone from account"
        lc, meta = classify_legal_issue(text, [], None)
        ip = merge_issue_profile(text, lc, meta, None)
        needed, q, opts, pts = needs_clarification(meta, _tax(lc), ip, text)
        self.assertTrue(needed)
        self.assertTrue(pts or opts)
        self.assertTrue(q)

    def test_fees_school_no_clarification_when_confident_consumer(self) -> None:
        text = "Fees too high school"
        lc, meta = classify_legal_issue(text, [], None)
        ip = merge_issue_profile(text, lc, meta, None)
        needed, q, _, _ = needs_clarification(meta, _tax(lc), ip, text)
        self.assertFalse(needed)
        self.assertEqual(q, "")

    def test_ambiguous_lost_property_not_when_stolen(self) -> None:
        self.assertIsNone(ce._ambiguous_lost_property("My wallet was stolen at the market"))

    def test_lost_followup_classifies_police_no_repeat_clarify(self) -> None:
        text = "My wallet is missing\n\nAdditional detail (my choice): Lost / misplaced"
        lc, meta = classify_legal_issue(text, [], None)
        self.assertEqual(lc["issue_type"], "police")
        self.assertEqual(lc.get("sub_type"), "lost_property")
        ip = merge_issue_profile(text, lc, meta, None)
        needed, q, _, _ = needs_clarification(meta, _tax(lc), ip, text)
        self.assertFalse(needed)
        self.assertEqual(q, "")


if __name__ == "__main__":
    unittest.main()
