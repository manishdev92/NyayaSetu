"""Dedupe and cap user-facing strings (alerts, explanations, next steps)."""

from __future__ import annotations

import re
from typing import Any


def deduplicate_lines(lines: list[str]) -> list[str]:
    """Drop exact duplicate lines (after strip), preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in lines:
        line = str(raw).strip()
        if not line:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def deduplicate_sections(text: str) -> str:
    """Deduplicate non-empty lines in a block of text."""
    if not (text or "").strip():
        return ""
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(deduplicate_lines(lines))


def cap_text_lines(text: str, *, max_lines: int) -> str:
    lines = [ln for ln in (text or "").splitlines() if str(ln).strip()]
    return "\n".join(lines[:max(0, max_lines)]).strip()


def _normalize_step_key(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip().lower())
    t = re.sub(r"[^\w\s]", "", t)
    return t[:160]


def dedupe_and_cap_next_steps(steps: list[str], *, max_steps: int = 4) -> list[str]:
    """Remove near-duplicate steps (e.g. repeated 112 advice), cap count."""
    seen_keys: set[str] = set()
    out: list[str] = []
    for raw in steps:
        s = str(raw).strip()
        if not s:
            continue
        k = _normalize_step_key(s)
        if "112" in s.lower() and any("112" in o.lower() for o in out):
            if k in seen_keys or _normalize_step_key(s.replace("112", "")) in seen_keys:
                continue
        if k in seen_keys:
            continue
        seen_keys.add(k)
        out.append(s)
        if len(out) >= max_steps:
            break
    return out


def validate_output_bundle(
    *,
    document: str,
    explanation: str,
    next_steps: list[str],
    meta: dict[str, Any],
) -> tuple[bool, str]:
    """
    Hard validation for production output contracts.
    Returns (ok, reason_code). Does not raise — callers may sanitize instead.
    """
    combined = f"{document}\n{explanation}\n" + " ".join(next_steps)
    low = combined.lower()
    emergency_police_only = bool(meta.get("is_emergency")) and not bool(meta.get("is_hybrid"))
    if emergency_police_only and "civil court" in low:
        return False, "non_hybrid_civil_court_leak"
    if bool(meta.get("is_emergency")):
        police_ok = any(
            m in low
            for m in (
                "police",
                "fir",
                "112",
                "station house officer",
                " sho",
                "thana",
                "complaint",
            )
        )
        if not police_ok:
            return False, "emergency_missing_police_marker"
    return True, ""


def strip_non_hybrid_civil_language(text: str) -> str:
    """Remove lines that reference civil court when output must stay police-only."""
    if not (text or "").strip():
        return ""
    out: list[str] = []
    for ln in text.splitlines():
        low = ln.lower()
        if "civil court" in low:
            continue
        out.append(ln)
    return "\n".join(out).strip()


def strip_redundant_emergency_echo(alert: str | None, explanation: str) -> str:
    """Avoid repeating the same 112 / danger wording in explanation when `alert` already covers it."""
    expl = deduplicate_sections(str(explanation or ""))
    if not (alert or "").strip() or not expl:
        return expl
    al = str(alert).strip().lower()
    kept: list[str] = []
    for ln in expl.splitlines():
        s = str(ln).strip()
        if not s:
            continue
        sl = s.lower()
        if sl in al:
            continue
        if len(al) > 40 and al in sl:
            continue
        if "112" in al and "112" in sl and len(sl) < 100 and re.search(r"\b(call|dial)\b", sl):
            continue
        kept.append(s)
    return "\n".join(kept).strip()


def evaluate_response_bundle(
    *,
    document: str,
    explanation: str,
    next_steps: list[str],
    meta: dict[str, Any],
    alert: str | None = None,
) -> tuple[str, str, list[str]]:
    """
    Evaluator step: dedupe lines, cap next steps (4), cap explanation length,
    strip civil-court leakage for emergency police-only bundles, validate contracts.
    """
    is_emergency = bool(meta.get("is_emergency"))
    crisis = bool(meta.get("crisis_triage"))
    is_hybrid = bool(meta.get("is_hybrid"))
    police_only_strip = is_emergency and not is_hybrid

    doc = deduplicate_sections(str(document or ""))
    expl = deduplicate_sections(str(explanation or ""))
    if is_emergency and alert:
        expl = strip_redundant_emergency_echo(alert, expl)

    steps_raw = [str(s).strip() for s in (next_steps or []) if str(s).strip()]
    max_step_count = 3 if (crisis or is_emergency) else 4
    steps = dedupe_and_cap_next_steps(steps_raw, max_steps=max_step_count)

    if police_only_strip:
        doc = strip_non_hybrid_civil_language(doc)
        expl = strip_non_hybrid_civil_language(expl)
        steps = [s for s in steps if "civil court" not in s.lower()]

    max_expl = 4 if (is_emergency or crisis) else 20
    expl = cap_text_lines(expl, max_lines=max_expl)

    ok, reason = validate_output_bundle(
        document=doc,
        explanation=expl,
        next_steps=steps,
        meta=meta,
    )
    if not ok and reason == "emergency_missing_police_marker":
        steps = dedupe_and_cap_next_steps(
            ["If danger is ongoing, call 112 immediately."] + steps,
            max_steps=max_step_count,
        )
    elif not ok and police_only_strip and "civil" in reason:
        doc = strip_non_hybrid_civil_language(doc)
        expl = strip_non_hybrid_civil_language(expl)
        steps = [s for s in steps if "civil court" not in s.lower()]

    return doc.strip(), expl.strip(), steps
