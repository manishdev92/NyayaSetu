"""
Deterministic phrases for very serious public-order / infrastructure crimes so routing and
letter drafting are not under-weighted to generic "police incident" language.
"""

from __future__ import annotations

import re

_FIRED_UP_NEAR_PS = re.compile(
    r"(?i)fired\s+up.{0,100}?(thana|police\s+station|police\s+chowki|थाना)|"
    r"(thana|police\s+station|police\s+chowki|थाना).{0,60}?fired\s+up",
)

_POLICE_STATION = re.compile(
    r"\b(thana|police\s+station|police\s+chowki|थाना)\b",
    re.IGNORECASE,
)

_FIRE_ARSON = re.compile(
    r"(\bset\s+on\s+fire\b|set.{0,40}?\bon\s+fire\b|arson|torch(?:ed|ing)?|burning|burnt|burned|\bburn\b|"
    r"flames?|blaze|smoke|आग|सुलग|जल(?:ा|ाए|ाई))",
    re.IGNORECASE,
)


def alleges_arson_or_fire_at_police_station(user_text: str) -> bool:
    raw = (user_text or "").strip()
    if not raw or not _POLICE_STATION.search(raw):
        return False
    if _FIRED_UP_NEAR_PS.search(raw):
        return True
    if _FIRE_ARSON.search(raw):
        return True
    low = raw.lower()
    if "fired up" in low:
        return _FIRED_UP_NEAR_PS.search(raw) is not None
    if re.search(r"\bfired\b", low) and "fired up" not in low:
        if re.search(r"\bfired\s+(a|the)\s+(gun|shot|round|bullet)", low):
            return False
        return True
    return False
