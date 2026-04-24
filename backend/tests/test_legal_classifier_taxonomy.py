"""Deterministic classifier + router smoke tests (no OpenAI).

Run from the `backend/` directory:
  python run_tests.py
  python -m unittest discover -s tests -t . -p "test_*.py" -v

Or from repo root:  python backend/run_tests.py
"""

from __future__ import annotations

import unittest

from app.core.legal_classifier import classify_legal_issue
from app.services.legal_router import route_case


class TestLegalClassifierTaxonomy(unittest.TestCase):
    def _classify(self, text: str) -> tuple[str, str, str, str]:
        lc, meta = classify_legal_issue(text)
        return (
            str(lc["issue_type"]),
            str(lc.get("sub_type") or ""),
            str(meta.get("domain") or ""),
            str(meta.get("router_intent") or ""),
        )

    def test_missing_person_high_urgency_path(self) -> None:
        it, sub, dom, ri = self._classify("My daughter has been missing since yesterday evening")
        self.assertEqual(it, "police")
        self.assertEqual(sub, "missing_person")
        self.assertEqual(dom, "criminal")
        self.assertEqual(ri, "criminal_police")
        lc, _ = classify_legal_issue("My daughter has been missing since yesterday evening")
        self.assertEqual(lc["severity"], "high")

    def test_sexual_offence(self) -> None:
        it, sub, _, _ = self._classify("I need help regarding sexual abuse at workplace pocso")
        self.assertEqual(it, "police")
        self.assertEqual(sub, "sexual_offence")

    def test_cyber_otp_sub_type(self) -> None:
        it, sub, dom, _ = self._classify("Someone took money after OTP scam on phone")
        self.assertEqual(it, "cyber")
        self.assertEqual(dom, "cyber")
        self.assertIn(sub, ("otp_fraud", "upi_fraud", "cybercrime_general"))

    def test_labour_plus_threat_police(self) -> None:
        it, sub, dom, ri = self._classify(
            "My employer has not paid salary for 3 months and threatened me with a weapon if I complain"
        )
        self.assertEqual(it, "police")
        self.assertEqual(ri, "criminal_police")
        self.assertEqual(dom, "criminal")
        self.assertEqual(sub, "labour_with_threat")

    def test_labour_pf_sub_type(self) -> None:
        it, sub, _, ri = self._classify("EPFO not crediting PF for 8 months")
        self.assertEqual(it, "salary")
        self.assertEqual(ri, "salary_issue")
        self.assertEqual(sub, "pf_issue")

    def test_police_fir_refusal_escalation(self) -> None:
        it, sub, _, ri = self._classify("Police refused to register my FIR despite repeated complaints")
        self.assertEqual(it, "police_oversight")
        self.assertEqual(ri, "police_oversight")
        self.assertEqual(sub, "police_not_registering_fir")

    def test_rti_denial(self) -> None:
        it, sub, _, ri = self._classify("RTI information denied by PIO without reasons")
        self.assertEqual(it, "rti")
        self.assertEqual(ri, "rti_grievance")
        self.assertEqual(sub, "information_denied")

    def test_civil_contract_not_police_primary_in_router(self) -> None:
        _, _, _, ri = self._classify("Breach of contract and money recovery suit against vendor")
        self.assertEqual(ri, "civil_dispute")
        rr = route_case(ri, [], "Mumbai", category="civil")
        self.assertIn("Civil Court", rr["primary_authority"])

    def test_property_dispute_civil_not_land_records_only(self) -> None:
        it, sub, dom, ri = self._classify("Property dispute with my brother over ancestral house partition")
        self.assertEqual(ri, "civil_dispute")
        self.assertEqual(dom, "civil")
        self.assertEqual(sub, "property_dispute")
        self.assertEqual(it, "civil_dispute")

    def test_financial_banking_route(self) -> None:
        it, _, _, ri = self._classify("Bank not responding and RBI ombudsman for loan harassment by recovery agents")
        self.assertEqual(it, "financial")
        self.assertEqual(ri, "banking_ombudsman")

    def test_traffic_challan_sub_type(self) -> None:
        it, sub, _, _ = self._classify("Wrong e-challan issued for signal violation I did not commit")
        self.assertEqual(it, "traffic")
        self.assertEqual(sub, "challan_dispute")

    def test_land_dispute_router_never_index_error(self) -> None:
        """Regression: route_case used secondary_forums[2] while graph had only two entries."""
        rr = route_case("land_dispute", [], "Varanasi", category="land_revenue")
        self.assertEqual(len(rr["fallback_path"]), 2)
        self.assertIn("Tehsildar", rr["primary_authority"])


if __name__ == "__main__":
    unittest.main()
