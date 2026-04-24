"""Load and render emergency FIR templates (short + contextual)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "templates" / "emergency_templates.json"

_PLACEHOLDER_LOC = "[Enter place of incident]"

_BAD_LOCATION = re.compile(
    r"\b(two\s+religions?|between\s+two\s+religions?|religious\s+groups?|faith\s+groups?|"
    r"unknown\s+place|somewhere|nowhere|don'?t\s+know|n/?a\b|"
    r"religious\s+tension|community\s+tension)\b",
    re.I,
)

_COMMUNAL = re.compile(
    r"\b(communal|hindu\s*[-/]\s*muslim|muslim\s*[-/]\s*hindu|"
    r"two\s+communities?|two\s+religions?|inter\s*[- ]?faith|interfaith|"
    r"religious\s+(riot|violence|clash|fight)|caste\s+violence|"
    r"जाति|धर्म\s*के|सांप्रदायिक)\b",
    re.I,
)


def _location_string_is_reliable(name: str) -> bool:
    s = (name or "").strip()
    if len(s) < 3:
        return False
    if _BAD_LOCATION.search(s):
        return False
    if s.lower() in ("here", "there", "local", "market", "road", "street"):
        return False
    letters = sum(1 for c in s if c.isalpha())
    if letters < 3:
        return False
    return True


def _load_templates() -> dict:
    with open(_TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def parse_emergency_narrative_context(
    user_input: str,
    *,
    location_hint: str | None = None,
) -> dict[str, str | int | bool]:
    """Extract minimal FIR facts from user text + safety follow-ups."""
    raw = (user_input or "").strip()
    low = raw.lower()
    incident_type = "violent incident"
    if re.search(r"\b(fight|fighting|brawl|marpit|jhagda)\b", low):
        incident_type = "physical fight"
    if re.search(r"\b(assault|attack|beating|beaten)\b", low):
        incident_type = "assault"
    if re.search(r"\b(riot|mob)\b", low):
        incident_type = "public disorder / riot"
    communal = bool(_COMMUNAL.search(low)) and bool(
        re.search(r"\b(fight|fighting|brawl|riot|clash|violence|attack|marpit|jhagda)\b", low)
    )
    if communal:
        incident_type = "communal clash"
    injury_count = 0
    if re.search(r"\binjury\s*:\s*yes\b", low) or re.search(
        r"\binjury\b.{0,40}?\b(yes|yep|yeah|y\b|haan)\b", low, re.I
    ):
        injury_count = 1
    elif re.search(r"\b(injured|injuries|hurt|wounded|bleeding)\b", low):
        injury_count = max(injury_count, 1)
    if re.search(r"\b(\d+)\s+(people|person|persons)\s+(were\s+)?(injured|hurt)\b", low):
        m = re.search(r"\b(\d+)\s+(people|person|persons)\s+(were\s+)?(injured|hurt)\b", low)
        if m:
            injury_count = max(injury_count, int(m.group(1)))
    ongoing = bool(
        re.search(r"\b(ongoing|happening\s+now|right\s+now|still\s+going|currently)\b", low)
        and not re.search(r"\b(stopped|ended|over|resolved|calm\s+now)\b", low)
    )
    ongoing = ongoing or bool(re.search(r"\bongoing\s*[:=]\s*yes\b", low))
    location = _PLACEHOLDER_LOC
    location_reliable = False
    if location_hint and str(location_hint).strip():
        hint = str(location_hint).strip()
        if _location_string_is_reliable(hint):
            location = hint
            location_reliable = True
    if location == _PLACEHOLDER_LOC or not location_reliable:
        ents = re.findall(
            r"\b(?:at|near|in)\s+([A-Za-z\u0900-\u097F][A-Za-z0-9\u0900-\u097F\s,\-]{2,60}?)(?:\.|,|\s+and|\s+where|\s*$)",
            raw,
            flags=re.I,
        )
        for cand in ents:
            cand_clean = str(cand).strip()
            title = cand_clean.title() if cand_clean.isascii() else cand_clean
            if _location_string_is_reliable(title):
                location = title
                location_reliable = True
                break
    if not location_reliable and location != _PLACEHOLDER_LOC and not _location_string_is_reliable(location):
        location = _PLACEHOLDER_LOC
        location_reliable = False
    return {
        "incident_type": incident_type,
        "injury_count": injury_count,
        "ongoing": ongoing,
        "location": location,
        "location_reliable": location_reliable,
    }


_IT_TRIPLES: dict[str, tuple[str, str, str]] = {
    "violent incident": ("violent incident", "हिंसक घटना", "hinsak ghatna"),
    "physical fight": ("physical fight", "शारीरिक झगड़ा", "sharirik jhagda"),
    "assault": ("assault", "हमला", "hamla"),
    "public disorder / riot": (
        "public disorder / riot",
        "सार्वजनिक उपद्रव/दंगा",
        "sarvajanik updrav/danga",
    ),
    "communal clash": ("communal clash", "सांप्रदायिक झड़प", "sampardayik jhadp"),
}


def _response_lang_kind(language: str) -> str:
    rl = (language or "en").strip().lower().replace("-", "_")
    if rl == "hi":
        return "hi"
    if rl == "hi_latn":
        return "hi_latn"
    return "en"


def _template_key_for_lang(base_key: str, language: str) -> str:
    kind = _response_lang_kind(language)
    if kind == "en":
        return base_key
    alt = f"{base_key}_{kind}"
    data = _load_templates()
    entry = data.get(alt) or {}
    lines = entry.get("content")
    if isinstance(lines, list) and len(lines) > 0:
        return alt
    return base_key


def build_incident_line(ctx: dict[str, str | int | bool], *, language: str = "en") -> str:
    kind = _response_lang_kind(language)
    it = str(ctx.get("incident_type") or "violent incident")
    loc = str(ctx.get("location") or _PLACEHOLDER_LOC).strip()
    reliable = bool(ctx.get("location_reliable"))
    if loc == _PLACEHOLDER_LOC:
        reliable = False
    n_inj = int(ctx.get("injury_count") or 0)

    if kind == "en":
        if it == "communal clash":
            line = "A communal clash occurred"
            if reliable and loc:
                line += f" at {loc}"
            line += "."
        elif reliable and loc and loc != _PLACEHOLDER_LOC:
            line = f"A {it} occurred at {loc}."
        else:
            line = f"A {it} occurred."
        if n_inj > 0:
            line += f" {n_inj} person(s) were injured."
        return line

    triple = _IT_TRIPLES.get(it, (it, it, it))
    label = triple[1] if kind == "hi" else triple[2]

    if it == "communal clash":
        if kind == "hi":
            line = f"{loc} पर सांप्रदायिक झड़प हुई।" if reliable and loc else "सांप्रदायिक झड़प हुई।"
        else:
            line = f"{loc} par sampardayik jhadp hui." if reliable and loc else "Sampardayik jhadp hui."
    elif reliable and loc and loc != _PLACEHOLDER_LOC:
        if kind == "hi":
            line = f"{loc} पर {label} के संबंध में घटना घटित हुई।"
        else:
            line = f"{loc} par {label} ke sambandh mein ghatna ghati."
    else:
        if kind == "hi":
            line = f"{label} के संबंध में घटना घटित हुई।"
        else:
            line = f"{label} ke sambandh mein ghatna ghati."

    if n_inj > 0:
        if kind == "hi":
            line += f" इसमें {n_inj} व्यक्ति घायल बताए गए।"
        else:
            line += f" Ismein {n_inj} vyakti ghayal bataye gaye."
    return line


def render_emergency_template(template_key: str, mapping: dict[str, str]) -> str:
    data = _load_templates()
    entry = data.get(template_key) or {}
    lines = entry.get("content")
    if not isinstance(lines, list):
        return ""
    out_lines: list[str] = []
    for line in lines:
        s = str(line)
        for k, v in mapping.items():
            s = s.replace("{{" + k + "}}", v)
        out_lines.append(s)
    return "\n".join(out_lines).strip() + "\n"


def render_emergency_fir_short(
    *,
    police_station: str,
    district: str,
    location: str,
    name: str,
    language: str = "en",
) -> str:
    key = _template_key_for_lang("emergency_fir_short", language)
    return render_emergency_template(
        key,
        {
            "police_station": police_station or "[Police station name]",
            "district": district or "[District]",
            "location": location or "[Location]",
            "name": name or "[Your full name]",
        },
    )


def render_emergency_fir_contextual(
    *,
    police_station: str,
    district: str,
    incident_line: str,
    name: str,
    language: str = "en",
) -> str:
    key = _template_key_for_lang("emergency_fir_contextual", language)
    return render_emergency_template(
        key,
        {
            "police_station": police_station or "[Police station name]",
            "district": district or "[District]",
            "incident_line": incident_line.strip(),
            "name": name or "[Your full name]",
        },
    )
