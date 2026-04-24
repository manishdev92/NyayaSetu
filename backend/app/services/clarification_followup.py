"""Parse structured clarification replies and inject hints for downstream classification."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClarificationFollowupSignals:
    force_or_threat_yes: bool = False
    no_force_peaceful: bool = False
    documents_yes: bool = False


def _structured_blob(user_text: str) -> str | None:
    t = (user_text or "").strip()
    if not t:
        return None
    m = re.search(
        r"(?:^|\n)\s*Additional details(?:\s*\(structured\))?\s*:\s*(.+)$",
        t,
        re.I | re.S,
    )
    if m:
        return m.group(1).strip()
    return None


def parse_followup_signals(user_text: str) -> ClarificationFollowupSignals:
    blob = _structured_blob(user_text)
    if not blob:
        return ClarificationFollowupSignals()
    sig = ClarificationFollowupSignals()
    for segment in re.split(r"[,;]\s*", blob):
        seg = segment.strip().lower()
        if not seg:
            continue
        if seg.startswith("document") or seg.startswith("documents"):
            if re.search(r"\byes\b|available|have\s+proof|deed|registry|papers", seg):
                sig.documents_yes = True
        elif "force" in seg or "threat" in seg or "violence" in seg:
            if re.search(r"\bno\b|not\s+involved|peaceful|civil\s+only|without\s+force", seg):
                sig.no_force_peaceful = True
            elif re.search(r"\byes\b|involved|present|reported", seg) or (
                "involved" in seg and "not" not in seg[:12]
            ):
                sig.force_or_threat_yes = True
    if not sig.force_or_threat_yes and not sig.no_force_peaceful:
        low = blob.lower()
        if "documents" in low and re.search(r"\byes\b", low):
            sig.documents_yes = True
        if re.search(r"\bno\s+force\b|\bno\s+threat\b|peaceful\s+civil", low):
            sig.no_force_peaceful = True
        elif re.search(r"force|threat|violence", low) and "no " not in low[:30]:
            sig.force_or_threat_yes = True
    return sig


def inject_classification_hints(user_text: str) -> str:
    """
    Append deterministic tokens so hybrid / classifier layers can react without LLM parsing.
    """
    sig = parse_followup_signals(user_text)
    if not (sig.force_or_threat_yes or sig.no_force_peaceful or sig.documents_yes):
        return user_text
    tail_parts: list[str] = []
    if sig.no_force_peaceful:
        tail_parts.append("nyayasetu_signal_no_force_peaceful_civil_only")
    elif sig.force_or_threat_yes:
        tail_parts.append("nyayasetu_signal_force_or_threat_reported forcefully threatened")
    if sig.documents_yes:
        tail_parts.append("nyayasetu_signal_documents_available possession papers available")
    if not tail_parts:
        return user_text
    return user_text.strip() + "\n\n" + " ".join(tail_parts)
