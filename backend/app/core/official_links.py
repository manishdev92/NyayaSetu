"""Curated official India portals — safe to surface in prompts and API metadata."""

from __future__ import annotations

INDIA_CODE = "https://www.indiacode.nic.in/"
CYBER_CRIME_PORTAL = "https://www.cybercrime.gov.in/"
NATIONAL_EMERGENCY = "112 (India — single emergency number; 100 for police where applicable)"
CONSUMER_EDAAKHIL = "https://edaakhil.nic.in/"

OFFICIAL_LINKS_BY_SLUG: dict[str, list[str]] = {
    "criminal": [INDIA_CODE, "Use the police station with territorial jurisdiction for FIRs."],
    "cyber": [CYBER_CRIME_PORTAL, INDIA_CODE],
    "labour": [INDIA_CODE, "State labour department portal (your state .gov.in)."],
    "consumer": [CONSUMER_EDAAKHIL, INDIA_CODE],
    "traffic": [INDIA_CODE, "State transport / e-challan portal (your state .gov.in)."],
    "family": [INDIA_CODE, "District court / family court official portal for your district."],
    "civil": [INDIA_CODE],
    "unknown": [INDIA_CODE],
}


def links_for_category_slug(slug: str) -> list[str]:
    return list(OFFICIAL_LINKS_BY_SLUG.get(slug, OFFICIAL_LINKS_BY_SLUG["unknown"]))
