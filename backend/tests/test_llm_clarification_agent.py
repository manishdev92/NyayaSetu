"""Tests for LLM clarification agent and gates — no live OpenAI required."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services import ai_service as ais
from app.services.clarification_engine import (
    _looks_like_clarification_followup,
    is_clear_reported_theft_case,
    should_use_llm_clarification,
)
from app.services.legal_taxonomy import LegalClassification
from app.services.llm_clarification_agent import (
    _coerce_result,
    rule_fallback_questions,
    run_llm_clarification_agent,
)


def _meta(**kwargs: object) -> dict:
    base = {
        "domain": "civil",
        "sub_type": "boundary",
        "category": "civil",
        "fine_intent": "property",
        "confidence": 0.8,
        "confidence_score": 0.8,
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
        "sub_type": "boundary",
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


class TestCoerceResult(unittest.TestCase):
    def test_coerce_truncates_to_three(self) -> None:
        raw = {
            "questions": [{"id": "a", "question": "Q1 here enough?", "type": "yes_no", "options": ["Yes", "No"]}] * 5,
            "reason": "x",
            "confidence_hint": 0.5,
        }
        out = _coerce_result(raw)
        self.assertLessEqual(len(out["questions"]), 3)


class TestRuleFallback(unittest.TestCase):
    def test_land_dispute_threat_and_ownership(self) -> None:
        out = rule_fallback_questions(
            domain="civil",
            issue_type="civil_court",
            router_intent="land_dispute",
            is_hybrid=False,
            soft_optional=False,
            missing_entities={},
        )
        ids = [q["id"] for q in out["questions"]]
        self.assertIn("threat_or_force", ids)
        self.assertIn("ownership_docs", ids)

    def test_lost_vs_stolen_intent(self) -> None:
        out = rule_fallback_questions(
            domain="civil",
            issue_type="police",
            router_intent="lost_property",
            is_hybrid=False,
            soft_optional=False,
            missing_entities={"lost_vs_theft": True},
        )
        self.assertTrue(any("lost" in q["question"].lower() or "stolen" in q["question"].lower() for q in out["questions"]))

    def test_hybrid_optional_one_or_two(self) -> None:
        out = rule_fallback_questions(
            domain="civil",
            issue_type="civil_court",
            router_intent="civil_dispute",
            is_hybrid=True,
            soft_optional=True,
            missing_entities={},
        )
        self.assertLessEqual(len(out["questions"]), 2)
        self.assertFalse(out["questions"][0]["required"])


class TestLooksLikeFollowup(unittest.TestCase):
    def test_additional_detail_line(self) -> None:
        text = "Land issue kabza\n\nAdditional detail: Yes, there was threat"
        self.assertTrue(_looks_like_clarification_followup(text))


class TestShouldUseLlmClarification(unittest.TestCase):
    def test_clear_theft_no_agent(self) -> None:
        meta = _meta(fine_intent="theft", sub_type="theft", confidence=0.95, router_intent="criminal_police")
        text = "My bike was stolen yesterday I want to file FIR at police station"
        self.assertTrue(is_clear_reported_theft_case(meta, text))
        use, soft = should_use_llm_clarification(meta, _tax(issue_type="police"), _ip(), text, skip_clarification=False)
        self.assertFalse(use)
        self.assertFalse(soft)

    def test_hybrid_high_conf_soft_optional(self) -> None:
        meta = _meta(is_hybrid=True, confidence=0.92, confidence_score=0.92)
        use, soft = should_use_llm_clarification(
            meta, _tax(), _ip(), "Land boundary dispute with neighbour regarding fence and access path " * 2,
            skip_clarification=False,
        )
        self.assertTrue(use)
        self.assertTrue(soft)

    def test_follow_up_skips_loop(self) -> None:
        meta = _meta(confidence=0.5)
        text = "Original issue\n\nAdditional detail: Yes, there was a threat"
        self.assertTrue(_looks_like_clarification_followup(text))
        use, _ = should_use_llm_clarification(meta, _tax(), _ip(), text, skip_clarification=False)
        self.assertFalse(use)

    def test_skip_clarification_flag(self) -> None:
        use, _ = should_use_llm_clarification(_meta(), _tax(), _ip(), "x" * 80, skip_clarification=True)
        self.assertFalse(use)


class TestGetLlmClarificationsMerge(unittest.TestCase):
    def test_returns_structured_bundle(self) -> None:
        fake = {
            "questions": [
                {
                    "id": "t1",
                    "question": "Was there any threat or force?",
                    "type": "yes_no",
                    "options": ["Yes", "No"],
                    "required": True,
                }
            ],
            "reason": "test",
            "confidence_hint": 0.7,
        }
        with patch("app.services.ai_service.run_llm_clarification_agent", return_value=fake):
            bundle = ais.get_llm_clarifications(
                "Neighbour encroached land boundary",
                classifier_meta=_meta(is_hybrid=True, confidence=0.9, confidence_score=0.9),
                taxonomy_ui=_tax(),
                issue_profile=_ip(),
                skip_clarification=False,
            )
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertTrue(bundle.get("clarification_agent_questions"))
        self.assertTrue(bundle.get("clarifying_questions"))


class TestRunAgentNoApiKey(unittest.TestCase):
    def test_fallback_when_no_key(self) -> None:
        with patch("app.services.llm_clarification_agent.settings") as s:
            s.openai_api_key = ""
            out = run_llm_clarification_agent(
                "property fight",
                domain="civil",
                sub_type="boundary",
                issue_type="civil_court",
                router_intent="land_dispute",
                confidence=0.7,
                is_hybrid=False,
                missing_entities={},
                ambiguous_intent=False,
                soft_optional=False,
            )
        self.assertGreaterEqual(len(out["questions"]), 1)


if __name__ == "__main__":
    unittest.main()
