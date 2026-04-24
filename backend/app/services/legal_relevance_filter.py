from __future__ import annotations

from typing import Any

# Strict whitelist: issue taxonomy → allowed `domain` values on knowledge chunks.
ISSUE_ALLOWED_DOMAINS: dict[str, frozenset[str]] = {
    "corporate": frozenset({"civil", "procedure", "administrative"}),
    "general": frozenset({"civil", "procedure", "administrative"}),
    "civil_dispute": frozenset({"civil", "procedure", "administrative"}),
    "traffic": frozenset({"traffic", "motor"}),
    "salary": frozenset({"labour", "employment"}),
    "cyber": frozenset({"cyber", "it_act"}),
    "fraud": frozenset({"criminal", "procedure"}),
    "land": frozenset({"land", "revenue", "civil"}),
    "police": frozenset({"criminal", "procedure"}),
    "police_oversight": frozenset({"criminal", "procedure"}),
    "family": frozenset({"family"}),
    "consumer": frozenset({"consumer"}),
    "financial": frozenset({"banking", "administrative", "civil", "procedure"}),
    "rti": frozenset({"administrative", "procedure"}),
    "civic": frozenset({"administrative", "civil"}),
    "education": frozenset({"consumer", "administrative", "civil"}),
    "women_child": frozenset({"family", "criminal", "procedure"}),
    "senior_citizen": frozenset({"family", "administrative"}),
}

TAG_EXCLUDE_FOR_ISSUE: dict[str, frozenset[str]] = {
    "police": frozenset({"rti", "consumer", "labour"}),
    "fraud": frozenset({"rti", "consumer", "labour"}),
    "police_oversight": frozenset({"rti", "consumer", "labour"}),
    "salary": frozenset({"rti", "criminal"}),
    "consumer": frozenset({"rti", "criminal"}),
    "traffic": frozenset({"rti", "criminal", "labour"}),
    "family": frozenset({"rti", "traffic"}),
    "cyber": frozenset({"rti", "labour"}),
    "financial": frozenset({"rti", "criminal"}),
    "rti": frozenset({"criminal", "labour", "consumer"}),
    "civic": frozenset({"criminal", "labour", "consumer"}),
    "education": frozenset({"criminal", "traffic"}),
    "women_child": frozenset({"rti", "traffic"}),
    "senior_citizen": frozenset({"rti", "traffic", "cyber"}),
    "land": frozenset({"rti"}),
    "corporate": frozenset({"rti", "criminal"}),
    "general": frozenset(),
    "civil_dispute": frozenset({"rti", "criminal"}),
}

TAG_REQUIRE_ANY: dict[str, frozenset[str]] = {
    "police": frozenset({"fir", "police", "investigation", "bns", "ipc", "criminal", "bnss", "crpc"}),
    "fraud": frozenset({"fir", "police", "investigation", "bns", "ipc", "criminal", "fraud"}),
    "police_oversight": frozenset({"fir", "police", "magistrate", "bns", "ipc", "criminal", "bnss", "crpc"}),
    "salary": frozenset({"salary", "wages", "labour", "employer", "pf", "esi", "benefits"}),
    "consumer": frozenset({"consumer", "refund", "defect", "service"}),
    "cyber": frozenset({"cyber", "online", "upi", "fraud", "computer", "internet"}),
    "traffic": frozenset({"traffic", "challan", "rto", "licence", "motor", "accident", "claim"}),
    "financial": frozenset({"banking", "rbi", "loan", "insurance", "ombudsman", "cheque", "nbfc"}),
    "rti": frozenset({"rti", "grievance", "pio", "information", "appeal"}),
    "civic": frozenset({"municipal", "sanitation", "local", "grievance", "government", "scheme"}),
    "education": frozenset({"education", "school", "consumer", "board", "university"}),
    "women_child": frozenset({"women", "child", "family", "custody", "posco", "cwc"}),
    "senior_citizen": frozenset({"senior", "maintenance", "tribunal", "family", "welfare"}),
    "land": frozenset({"land", "mutation", "tehsildar", "sdm", "khasra", "revenue"}),
    "family": frozenset({"family", "divorce", "maintenance", "custody", "dv", "protection"}),
    "corporate": frozenset({"contract", "civil", "court", "filing", "petition", "nclt"}),
    "general": frozenset({"contract", "civil", "court", "filing", "petition", "evidence"}),
    "civil_dispute": frozenset({"contract", "civil", "court", "filing", "petition", "evidence"}),
}


def filter_entries_by_issue_type(entries: list[dict[str, Any]], issue_type: str) -> list[dict[str, Any]]:
    allowed = ISSUE_ALLOWED_DOMAINS.get(issue_type)
    if not allowed:
        allowed = ISSUE_ALLOWED_DOMAINS["general"]
    exclude_tags = TAG_EXCLUDE_FOR_ISSUE.get(issue_type, frozenset())
    require_any = TAG_REQUIRE_ANY.get(issue_type)
    out: list[dict[str, Any]] = []
    for e in entries:
        dom = (e.get("domain") or "").strip().lower()
        if dom not in allowed:
            continue
        tags = {str(x).strip().lower() for x in (e.get("tags") or []) if str(x).strip()}
        if tags & exclude_tags:
            continue
        if require_any is not None and not (tags & require_any):
            continue
        out.append(e)
    return out
