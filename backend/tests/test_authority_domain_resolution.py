"""Authority resolution follows router_intent / domain — no cross-domain verified leakage."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai.authority_alignment import verified_authority_breaks_domain_alignment
from app.core.legal_classifier import classify_legal_issue
from app.authority import department_for_router_intent, strict_authority_passes_domain_gate
from app.services.authority_pipeline import resolve_verified_authority


class TestAuthorityDomainResolution(unittest.TestCase):
    def test_beating_bh_gate_classifies_criminal_police(self) -> None:
        text = "Someone is beating at the BHU gate"
        lc, meta = classify_legal_issue(text, [], None)
        self.assertEqual(lc["issue_type"], "police")
        self.assertEqual(meta.get("domain"), "criminal")
        self.assertEqual(meta.get("router_intent"), "criminal_police")

    def test_criminal_police_department_is_police_not_labour(self) -> None:
        self.assertEqual(
            department_for_router_intent("criminal_police", "criminal", "Someone is beating"),
            "police",
        )

    @patch("app.services.authority_pipeline.gather_remote_candidates", return_value=[])
    def test_varanasi_internal_never_labour_for_assault(self, _mock_remote: object) -> None:
        text = "Someone is beating at the BHU gate"
        lc, meta = classify_legal_issue(text, [], None)
        verified, _ = resolve_verified_authority(
            text,
            "Varanasi",
            router_intent=meta.get("router_intent"),
            domain=meta.get("domain"),
        )
        if verified is not None:
            ot = str(verified.get("office_type") or "").lower()
            self.assertNotIn("labour", ot)
            self.assertTrue("police" in ot or "cyber" in ot)

    def test_labour_verified_rejected_under_criminal_domain(self) -> None:
        fake_verified = {
            "office_type": "Labour",
            "office_name": "Labour Commissioner Office",
            "state": "UP",
            "district": "X",
            "source": "test",
            "trust_score": 10.0,
        }
        meta = {
            "domain": "criminal",
            "router_intent": "criminal_police",
            "category": "criminal",
            "fine_intent": "assault",
            "confidence": 0.9,
            "confidence_score": 0.9,
            "sub_type": "assault",
        }
        bad, _ = verified_authority_breaks_domain_alignment(
            fake_verified, classifier_meta=meta, user_input="test"  # type: ignore[arg-type]
        )
        self.assertTrue(bad)

    def test_strict_gate_accepts_police(self) -> None:
        self.assertTrue(
            strict_authority_passes_domain_gate(
                "Police",
                router_intent="criminal_police",
                domain="criminal",
                user_input="",
            )
        )

    def test_strict_gate_rejects_labour_for_criminal_police(self) -> None:
        """From authority_mismatch log: remote row 'Labour' must not pass the criminal gate (NS-S1-01)."""
        self.assertFalse(
            strict_authority_passes_domain_gate(
                "Labour",
                router_intent="criminal_police",
                domain="criminal",
                user_input="test",
            )
        )


if __name__ == "__main__":
    unittest.main()
