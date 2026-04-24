"""Regenerate classifier_dataset_100.json from curated inputs (run from backend/)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.legal_classifier import classify_legal_issue

# Exactly 100 lines — edit here, then: python tests/fixtures/build_classifier_dataset_100.py
RAW = r"""
my phone was stolen at the market
bike chori ho gayi kal raat
burglary at our shop CCTV available
my son has been missing since Tuesday evening
person missing report needed kidnapping suspected
abduction case child missing from school gate
लापता person since last week
sexual abuse at workplace need help pocso
molestation complaint against neighbour
I was assaulted by three persons
battery and grievous hurt in fight
acid attack survivor need legal steps
attempt to murder FIR needed
UPI fraud someone debited my account
OTP scam on phone lost savings
data breach company leaked my PAN
hacking of my email account
deepfake video circulated online
internet crime reporting cyber cell
online fraud investment portal cheated
police refused to register FIR despite complaint
no FIR taken police not registering
police misconduct at station humiliated
FIR not registered for cheating case
salary not paid for 5 months employer factory
wages unpaid construction labour
EPFO PF not credited for one year
provident fund withdrawal issue delay
wrongful termination without notice period
illegal termination during maternity
gratuity not paid after resignation
workplace harassment POSH committee not formed
sexual harassment at work internal committee
bonus denied as per employment contract
company not paying salary and threatened to harm me if I complain
defective product mobile phone under warranty
service deficiency hotel booking refund
consumer complaint against airline CPA
refund not given for cancelled order
school fees too high exorbitant fees
warranty claim rejected for fridge
poor service not provided as promised
wrong e-challan issued for signal violation
DL suspended want appeal RTO
driving licence renewal issue at RTO
parking violation ticket unfair
motor accident claim procedure MACT
traffic police stopped without reason challan
divorce petition and alimony dispute
child custody battle visitation rights
domestic violence 498a help needed
maintenance under section 125 crpc
spousal maintenance not paid
family court jurisdiction divorce
mutation of land record khasra correction
tehsildar not updating jamabandi
boundary dispute survey pillar
title deed verification SDM office
birth certificate tehsil SDM collector office delay
property dispute with brother ancestral house
tenant not paying rent eviction lease
landlord harassment rent issue
breach of contract vendor did not supply
money recovery suit against debtor
civil suit for partition of property
specific performance of agreement to sell
contract dispute software services
NCLT insolvency petition against company
shareholder oppression minority rights
board of directors dispute private limited
RBI ombudsman banking complaint not resolved
loan harassment recovery agents abusive calls
cheque bounce notice bank not responding
insurance claim reject health policy
NBFC harassment for EMI default
RTI application PIO not replied in time
first appeal RTI information commission
public information officer denied file
information denied without reasons RTI
garbage not collected municipal corporation ward
illegal construction encroachment footpath civic
stray dogs sanitation issue municipal
street lights not working civic issue
admission fraud college took fees no seat
certificate withheld marksheet board
school not giving transfer certificate
college withheld degree certificate
women helpline 1091 domestic crisis
child welfare CWC inquiry needed
childline 1098 missing child support
child abuse reporting support
senior citizen maintenance tribunal 1090
elder abuse in family maintenance
__EMPTY__
general guidance about legal rights in India
something illegal happened not sure what
cheating scam duped online but not cyber keywords
theft chori report at police station
large scale fraud ponzi multi crore scam investor
identity theft morphing profile online
"""


def main() -> None:
    texts: list[str] = []
    for ln in RAW.strip().splitlines():
        s = ln.strip()
        if s == "__EMPTY__":
            texts.append("")
        else:
            texts.append(s)
    assert len(texts) == 100, len(texts)

    out_cases = []
    for i, text in enumerate(texts, start=1):
        lc, meta = classify_legal_issue(text)
        out_cases.append(
            {
                "id": i,
                "text": text,
                "issue_type": lc["issue_type"],
                "domain": meta["domain"],
                "router_intent": meta["router_intent"],
                "sub_type": lc["sub_type"],
                "severity": lc["severity"],
                "jurisdiction_type": lc["jurisdiction_type"],
            }
        )

    out = {
        "version": 1,
        "description": "NyayaSetu deterministic classifier regression set (100 rows)",
        "cases": out_cases,
    }
    path = Path(__file__).with_name("classifier_dataset_100.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path, "cases=", len(out_cases))


if __name__ == "__main__":
    main()
