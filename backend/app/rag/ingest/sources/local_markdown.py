"""
Sprint P4-1: read statute-shaped Markdown from a local directory (licensed / air-gapped drops).
No network: compliance-friendly default path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

from app.rag.ingest.types import NormalizedDocument, SourceMetadata


def parse_yaml_like_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """
    Minimal `---` / `---` block parser (avoids PyYAML dependency).
    Values are single-line; strip quotes.
    """
    t = raw.lstrip("\ufeff")
    if not t.startswith("---"):
        return {}, t
    rest = t[3:].lstrip()
    i = rest.find("\n---")
    if i < 0:
        return {}, t
    head = rest[:i].strip()
    body = rest[i + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in head.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        v = m.group(2).strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        meta[m.group(1).strip().lower()] = v
    return meta, body


class LocalMarkdownDirectorySource:
    """`*.md` under `root` (optionally recursive). Requires YAML frontmatter for Act identity."""

    def __init__(self, root: str | Path, *, recursive: bool = True) -> None:
        self._root = Path(root)
        self._recursive = recursive

    def discover_markdown_files(self) -> list[Path]:
        if not self._root.is_dir():
            return []
        if self._recursive:
            return sorted(self._root.rglob("*.md"))
        return sorted(self._root.glob("*.md"))

    def iter_documents(self) -> Iterator[NormalizedDocument]:
        for p in self.discover_markdown_files():
            raw = p.read_text(encoding="utf-8")
            fm, body = parse_yaml_like_frontmatter(raw)
            if not body.strip():
                continue
            act_id = (fm.get("act_id") or p.stem).strip()
            if not act_id:
                continue
            tags: list[str] = []
            raw_tags = fm.get("tags", "")
            if raw_tags:
                for part in re.split(r"[,;]", raw_tags):
                    t = part.strip()
                    if t:
                        tags.append(t)
            v_raw = str(fm.get("verified", "true")).lower()
            meta: SourceMetadata = {
                "act_id": act_id,
                "source_name": (fm.get("source_name") or act_id)[:1_200],
                "source_url": (fm.get("source_url") or "")[:2_000],
                "source_version": (fm.get("source_version") or "unspecified")[:200],
                "domain": (fm.get("domain") or "general").lower()[:64],
                "law_type": (fm.get("law_type") or "Act")[:32],
                "verified": v_raw not in ("0", "false", "no", "off"),
                "tags": tags,
                "local_path": str(p),
            }
            yield {"text": body, "meta": meta}


def read_manifest_path(manifest: str | Path) -> list[dict[str, Any]]:
    """JSON manifest: `[{"path": "a.md", "act_id": "..."}]` to merge overrides (optional)."""
    mp = Path(manifest)
    if not mp.is_file():
        return []
    return json.loads(mp.read_text(encoding="utf-8"))
