"""
Shim re-export (do not duplicate logic here).

**Canonical code:** `app.trust.trust_engine` (implement `build_trust_report` and friends there).
**Imports:** Prefer `from app.trust.trust_engine import ...` in new modules.
This path exists so older `from app.services.trust_engine import ...` keep working.
"""

from app.trust.trust_engine import *  # noqa: F403
