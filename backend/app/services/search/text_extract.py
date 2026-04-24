from __future__ import annotations

import re

_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# Indian mobile-style (+91 optional, 10 digits starting 6-9)
_PHONE = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")


def extract_email(text: str | None) -> str | None:
    if not text:
        return None
    m = _EMAIL.search(text)
    return m.group(0).strip() if m else None


def extract_phone(text: str | None) -> str | None:
    if not text:
        return None
    m = _PHONE.search(text.replace(" ", ""))
    return m.group(0).strip() if m else None


def first_line(text: str | None, max_len: int = 240) -> str | None:
    if not text:
        return None
    line = text.strip().split("\n")[0].strip()
    if len(line) > max_len:
        return line[: max_len - 1] + "…"
    return line or None
