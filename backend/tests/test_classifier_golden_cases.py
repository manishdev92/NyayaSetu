"""Table-driven checks: one representative line per taxonomy bucket (deterministic).

Run:  python run_tests.py   (from backend/) or   python backend/run_tests.py   (from repo root).
"""

from __future__ import annotations

import unittest

from app.core.legal_classifier import classify_legal_issue


# (user_text_snippet, expected_issue_type, expected_domain substring check, min_router_intent)
_GOLDEN: list[tuple[str, str, str, str]] = [
    ("my bike was stolen yesterday", "police", "criminal", "criminal_police"),
    ("I was assaulted in a road rage incident", "police", "criminal", "criminal_police"),
    ("online UPI fraud phishing link", "cyber", "cyber", "cyber_fraud"),
    ("salary not paid for 4 months factory worker", "salary", "labour", "salary_issue"),
    ("wrongful termination without notice", "salary", "labour", "salary_issue"),
    ("workplace harassment POSH committee", "salary", "labour", "salary_issue"),
    ("defective product warranty claim refund", "consumer", "consumer", "consumer_issue"),
    ("school fees overcharging exorbitant", "consumer", "consumer", "consumer_issue"),
    ("e-challan dispute traffic fine wrong", "traffic", "traffic", "traffic_violation"),
    ("driving licence renewal issue RTO", "traffic", "traffic", "traffic_violation"),
    ("motor accident hit and run MACT", "traffic", "traffic", "traffic_violation"),
    ("divorce and child custody battle", "family", "family", "family_matters"),
    ("mutation khasra land records tehsil", "land", "government", "land_dispute"),
    ("NCLT shareholder oppression winding up", "corporate", "civil", "share_dispute"),
    ("money recovery civil suit partition", "civil_dispute", "civil", "civil_dispute"),
    ("tenant not paying rent eviction lease dispute", "civil_dispute", "civil", "civil_dispute"),
    ("cheating fraud duped investor", "fraud", "criminal", "fraud_general"),
    ("RTI first appeal PIO", "rti", "rti", "rti_grievance"),
    ("garbage not collected municipal corporation", "civic", "civic", "civic_local"),
    ("illegal construction neighbour encroachment civic", "civic", "civic", "civic_local"),
    ("RBI ombudsman banking cheque bounce", "financial", "financial", "banking_ombudsman"),
    ("admission fraud school withheld marksheet", "education", "education", "education_dispute"),
    ("women helpline 1091 child welfare CWC", "women_child", "women_child", "women_child_route"),
    ("senior citizen maintenance tribunal 1090", "senior_citizen", "senior_citizen", "senior_maintenance"),
    ("police misconduct no action by police", "police_oversight", "police_complaint", "police_oversight"),
    ("factory bonus not paid statutory bonus Act dispute", "salary", "labour", "salary_issue"),
    ("PF transfer from old employer to new UAN stuck", "salary", "labour", "salary_issue"),
    ("illegal parking towed car traffic police fine dispute", "police", "criminal", "criminal_police"),
    ("armed robbery at jewellery shop FIR", "police", "criminal", "criminal_police"),
    ("human trafficking rescued minor police complaint", "police", "criminal", "criminal_police"),
    ("blackmail threats intimate photos cyber extortion", "cyber", "cyber", "cyber_fraud"),
    ("forgery of property sale deed registration fraud", "fraud", "criminal", "fraud_general"),
    ("consumer forum defective AC compressor warranty", "consumer", "consumer", "consumer_issue"),
    ("NCLAT appeal against NCLT order corporate insolvency", "corporate", "civil", "share_dispute"),
    ("my wallet is missing after noon today", "police", "criminal", "criminal_police"),
    ("mera batuaa ratanpura block ke samne se kayab ho gya", "police", "criminal", "criminal_police"),
]


class TestClassifierGoldenCases(unittest.TestCase):
    def test_golden_rows(self) -> None:
        for text, exp_it, exp_dom, exp_ri in _GOLDEN:
            with self.subTest(text=text[:48]):
                lc, meta = classify_legal_issue(text)
                self.assertEqual(lc["issue_type"], exp_it, msg=f"issue_type for {text!r}")
                self.assertEqual(meta.get("domain"), exp_dom, msg=f"domain for {text!r}")
                self.assertEqual(meta.get("router_intent"), exp_ri, msg=f"router for {text!r}")


if __name__ == "__main__":
    unittest.main()
