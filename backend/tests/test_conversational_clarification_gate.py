"""Tests for conversational clarification gate — no live OpenAI calls."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services import ai_service as ais
from app.services.clarification_engine import (
    build_clarification_intent,
    key_facts_missing,
    should_ask_clarification,
)
from app.services.legal_taxonomy import LegalClassification


def _meta(**kwargs: object) -> dict:
    base = {
        "domain": "civil",
        "sub_type": "unspecified",
        "category": "civil",
        "fine_intent": "general",
        "confidence": 0.5,
        "confidence_score": 0.5,
        "router_intent": "civil_dispute",
        "is_hybrid": False,
    }
    base.update(kwargs)
    return base  # type: ignore[return-value]


def _tax(**kwargs: object) -> LegalClassification:
    t: LegalClassification = {
        "issue_type": "civil_court",
        "severity": "medium",
        "jurisdiction_type": "district",
        "sub_type": "unspecified",
    }
    for k, v in kwargs.items():
        t[k] = v  # type: ignore[index]
    return t


def _ip(**kwargs: object) -> dict:
    base = {
        "category": "civil",
        "severity": "medium",
        "intent": "information",
        "keywords": [],
        "urgency": "normal",
    }
    base.update(kwargs)
    return base  # type: ignore[return-value]


class TestShouldAskClarification(unittest.TestCase):
    def test_skips_when_taxonomy_severity_high(self) -> None:
        intent = build_clarification_intent(_meta(confidence=0.2), _tax(severity="high"), _ip())
        self.assertFalse(should_ask_clarification(intent, _meta(confidence=0.2), "x" * 80))

    def test_true_when_hybrid_even_if_confident(self) -> None:
        intent = build_clarification_intent(
            _meta(confidence=0.99, confidence_score=0.99, is_hybrid=True),
            _tax(),
            _ip(),
        )
        self.assertTrue(
            should_ask_clarification(
                intent,
                _meta(confidence=0.99, confidence_score=0.99, is_hybrid=True),
                "Neighbour built on my land side there is dispute about boundary in 2024 with some documents",
            )
        )

    def test_true_when_confidence_below_threshold(self) -> None:
        intent = build_clarification_intent(_meta(confidence=0.4), _tax(), _ip())
        self.assertTrue(should_ask_clarification(intent, _meta(confidence=0.4), "y" * 80))


class TestKeyFactsMissing(unittest.TestCase):
    def test_property_without_relationship(self) -> None:
        intent = build_clarification_intent(_meta(), _tax(issue_type="civil_court"), _ip())
        text = "Kabza on my land the other person refuses to move " * 2
        self.assertTrue(key_facts_missing(text, _meta(), intent))


class TestClarificationEarlyReturn(unittest.TestCase):
    def test_conversational_branch_when_needs_false(self) -> None:
        with patch.object(ais, "needs_clarification", return_value=(False, "", [], None)):
            with patch.object(ais, "get_llm_clarifications", return_value=None):
                with patch.object(ais, "should_ask_clarification", return_value=True):
                    with patch.object(
                        ais,
                        "generate_clarification_questions",
                        return_value=["When did this happen?", "Who is the other party?"],
                    ):
                        out = ais._clarification_early_return_if_needed(
                            "Neighbour dispute about land boundary fence",
                            classifier_meta=_meta(confidence=0.95, confidence_score=0.95, is_hybrid=True),
                            taxonomy_ui=_tax(),
                            issue_profile=_ip(),
                            interpretation={"entities": [], "intent_hint": "", "context": ""},
                            city=None,
                        )
        self.assertIsNotNone(out)
        assert out is not None
        self.assertTrue(out.get("clarification_needed"))
        cqs = out.get("clarifying_questions")
        self.assertIsInstance(cqs, list)
        self.assertGreaterEqual(len(cqs), 2)


if __name__ == "__main__":
    unittest.main()
