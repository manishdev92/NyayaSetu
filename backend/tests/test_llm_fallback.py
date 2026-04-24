"""LLM classification fallback — no live OpenAI calls (mocked where needed)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai import llm_fallback_classifier as lfb
from app.core.legal_classifier import classify_legal_issue


class TestLlmFallback(unittest.TestCase):
    def test_trigger_only_weak_general_bucket(self) -> None:
        lc, meta = classify_legal_issue("something vague about papers qqpapersvague", [], None)
        self.assertEqual(lc["issue_type"], "general")
        self.assertTrue(lfb.deterministic_triggers_llm_fallback(lc, meta))

    def test_no_trigger_confident_consumer(self) -> None:
        lc, meta = classify_legal_issue("Fees too high school", [], None)
        self.assertFalse(lfb.deterministic_triggers_llm_fallback(lc, meta))

    def test_no_trigger_police_above_threshold(self) -> None:
        lc, meta = classify_legal_issue("my bike was stolen yesterday", [], None)
        self.assertEqual(lc["issue_type"], "police")
        self.assertFalse(lfb.deterministic_triggers_llm_fallback(lc, meta))

    def test_violence_override_forces_police(self) -> None:
        raw = {
            "issue_type": "consumer",
            "domain": "consumer",
            "sub_type": "wrong",
            "router_intent": "consumer_issue",
            "severity": "low",
            "urgency": "low",
            "suggested_authority": "consumer commission",
            "confidence": 0.9,
        }
        lc, meta = lfb._llm_dict_to_classification(
            raw,
            user_text="boss hit me and assault at workplace",
            raw_for_trace={"llm": raw},
        )
        self.assertEqual(lc["issue_type"], "police")
        self.assertEqual(meta.get("router_intent"), "criminal_police")
        self.assertEqual(lc["severity"], "high")

    def test_normalize_unknown_router_to_general_issue(self) -> None:
        self.assertEqual(lfb._normalize_router_intent("made_up_mega_office_xyz"), "general_issue")

    @patch.object(lfb, "classify_with_llm_fallback")
    def test_maybe_apply_uses_llm_json(self, mock_llm) -> None:
        mock_llm.return_value = {
            "issue_type": "consumer",
            "domain": "consumer",
            "sub_type": "fees",
            "router_intent": "consumer_issue",
            "severity": "medium",
            "urgency": "medium",
            "suggested_authority": "consumer commission",
            "confidence": 0.8,
        }
        text = "something vague about papers qqpapersvague2"
        lc, meta = classify_legal_issue(text, [], None)
        self.assertEqual(lc["issue_type"], "general")
        lc2, meta2 = lfb.maybe_apply_llm_classification_fallback(text, lc, meta)
        self.assertTrue(meta2.get("is_llm_fallback"))
        self.assertTrue(meta2.get("needs_llm_fallback"))
        self.assertEqual(meta2.get("router_intent"), "consumer_issue")
        self.assertEqual(lc2["issue_type"], "consumer")

    def test_defer_lost_wallet_skips_llm(self) -> None:
        text = "My wallet is missing"
        lc, meta = classify_legal_issue(text, [], None)
        with patch.object(lfb, "classify_with_llm_fallback") as mock_llm:
            lc2, meta2 = lfb.maybe_apply_llm_classification_fallback(text, lc, meta)
            mock_llm.assert_not_called()
        self.assertEqual(lc2["issue_type"], lc["issue_type"])
        self.assertNotIn("needs_llm_fallback", meta2)


if __name__ == "__main__":
    unittest.main()
