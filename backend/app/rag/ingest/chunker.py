"""
Sprint P4-2: statute-oriented chunking (Act / Section) with char budget (token proxy; no tiktoken dep).
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.rag.ingest.types import IngestChunk


def _section_title_from_line(s: str) -> str:
    t = s.strip()
    m = re.match(
        r"^(?:Section|SECTION)\s+([\dA-Za-z.\-()]+)(?:\s*[-–—:.]\s*)?(.*)$",
        t,
    )
    if m:
        return f"Section {m.group(1)} {m.group(2) or ''}".strip()[:1_200]
    m2 = re.match(r"^#{1,3}\s+(.+)$", t)
    if m2:
        return m2.group(1).strip()[:1_200]
    return ""


def _is_boundary_line(s: str) -> bool:
    t = s.strip()
    if re.match(r"^(?:Section|SECTION)\s+[\dA-Za-z.\-()]+", t):
        return True
    return bool(re.match(r"^#{1,3}\s+\S", t))


def _split_by_section_heads(text: str) -> list[tuple[str, str]]:
    """
    Return [(section_label, body), ...] in order. Header lines are included in the body
    of the section that starts there.
    """
    lines = text.splitlines(keepends=False)
    if not any(_is_boundary_line(l) for l in lines):
        return [("", text.strip())] if text.strip() else []
    out: list[tuple[str, str]] = []
    cur_title = ""
    buf: list[str] = []
    for line in lines:
        if _is_boundary_line(line) and buf:
            body = "\n".join(buf).strip()
            out.append((cur_title, body))
            cur_title = _section_title_from_line(line)
            buf = [line]
        elif _is_boundary_line(line) and not buf:
            cur_title = _section_title_from_line(line)
            buf = [line]
        else:
            buf.append(line)
    if buf:
        out.append((cur_title, "\n".join(buf).strip()))
    return out


def _windows(text: str, *, max_chars: int, overlap: int) -> Iterator[str]:
    t = text.strip()
    if not t:
        return
    if len(t) <= max_chars:
        yield t
        return
    step = max(1, max_chars - overlap)
    i = 0
    while i < len(t):
        chunk = t[i : i + max_chars]
        if chunk.strip():
            yield chunk.strip()
        if i + max_chars >= len(t):
            break
        i += step


def chunk_statute_text(
    text: str,
    *,
    max_chunk_chars: int = 3_000,
    overlap_chars: int = 200,
) -> list[IngestChunk]:
    """
    Hierarchical: Section / ## blocks first; then sliding windows for oversized bodies.
    """
    out: list[IngestChunk] = []
    part = 0
    for label, body in _split_by_section_heads(text):
        sec = (label or "(preamble)")[:1_200]
        if not body.strip():
            continue
        for win in _windows(
            body,
            max_chars=max_chunk_chars,
            overlap=overlap_chars,
        ):
            w = win.strip()
            if not w:
                continue
            out.append(
                {
                    "text": w,
                    "section": sec,
                    "part_index": part,
                }
            )
            part += 1
    return out
