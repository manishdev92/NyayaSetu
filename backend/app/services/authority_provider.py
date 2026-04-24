from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


class AuthorityRecord(TypedDict, total=False):
    """Verified authority row returned only by lookup providers—not by the LLM."""

    found: bool
    department: str
    name: str
    address: str | None
    phone: str | None
    email: str | None
    source: str  # e.g. json_v1


@runtime_checkable
class AuthorityLookupProvider(Protocol):
    """
    Abstraction for local authority resolution.
    Swap implementations (JSON file today; remote APIs later) without changing the pipeline.
    """

    def get_local_authority(self, city: str, issue_type: str) -> AuthorityRecord | None:
        """Return a verified record or None if nothing is found for (city, issue_type)."""
        ...
